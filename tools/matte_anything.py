"""Matte Anything + 传统色度键抠图。

流程：
1. 传统色度键生成粗略 mask
2. 用 SAM 生成精确 mask
3. 用 ViTMatte 精炼 alpha matte
4. 迭代精炼直到边缘干净
5. despill 去绿色

用法：
    python tools/matte_anything.py <image_path> <output_path>
"""

import sys
from pathlib import Path

import cv2
import numpy as np
import torch
from PIL import Image
from segment_anything import sam_model_registry, SamPredictor
from transformers import VitMatteForImageMatting, VitMatteImageProcessor


def sample_bg_color(frame: np.ndarray) -> np.ndarray:
    """从四角+底部中央采样绿色背景。"""
    h, w = frame.shape[:2]
    m = 10
    corners = [
        frame[0:m, 0:m],
        frame[0:m, w - m : w],
        frame[h - m : h, 0:m],
        frame[h - m : h, w - m : w],
        frame[h - m : h, w // 2 - m // 2 : w // 2 + m // 2],
    ]
    samples = np.vstack([c.reshape(-1, 3) for c in corners])
    return samples.mean(axis=0).astype(np.float32)


def chroma_key_mask(frame: np.ndarray, bg_color: np.ndarray, threshold: float = 30.0) -> np.ndarray:
    """传统色度键生成粗略二值 mask。"""
    diff = frame.astype(np.float32) - bg_color
    dist = np.sqrt(np.sum(diff ** 2, axis=2))
    mask = (dist > threshold).astype(np.uint8) * 255
    return mask


def generate_trimap(mask: np.ndarray, erode_size: int = 15, dilate_size: int = 15) -> np.ndarray:
    """从二值 mask 生成 trimap。"""
    kernel_erode = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (erode_size, erode_size))
    kernel_dilate = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (dilate_size, dilate_size))

    fg = cv2.erode(mask, kernel_erode, iterations=3)
    bg = cv2.dilate(mask, kernel_dilate, iterations=3)
    bg_inv = 255 - bg

    trimap = np.full(mask.shape, 128, dtype=np.uint8)
    trimap[fg == 255] = 255
    trimap[bg_inv == 255] = 0

    return trimap


def sam_refine(frame_rgb: np.ndarray, mask: np.ndarray, sam_predictor: SamPredictor) -> np.ndarray:
    """用 SAM 精炼 mask。"""
    # 设置图像
    sam_predictor.set_image(frame_rgb)

    # 从 mask 生成提示点
    coords = np.where(mask > 128)
    if len(coords[0]) == 0:
        return mask

    # 找到猫的主体区域
    min_y, max_y = int(coords[0].min()), int(coords[0].max())
    min_x, max_x = int(coords[1].min()), int(coords[1].max())
    center_y = (min_y + max_y) // 2
    center_x = (min_x + max_x) // 2

    # 生成多个正提示点（覆盖猫的主体，包括耳朵）
    positive_points = []

    # 中心区域
    for dy in [-30, 0, 30]:
        for dx in [-30, 0, 30]:
            py = center_y + dy
            px = center_x + dx
            if 0 <= py < mask.shape[0] and 0 <= px < mask.shape[1]:
                if mask[py, px] > 128:
                    positive_points.append([px, py])

    # 耳朵区域（上方两侧）
    ear_y = min_y + 30
    ear_left_x = center_x - (max_x - min_x) // 4
    ear_right_x = center_x + (max_x - min_x) // 4

    for ear_x in [ear_left_x, ear_right_x]:
        for dy in [-20, 0, 20]:
            for dx in [-20, 0, 20]:
                py = ear_y + dy
                px = ear_x + dx
                if 0 <= py < mask.shape[0] and 0 <= px < mask.shape[1]:
                    positive_points.append([px, py])

    # 底部区域（爪子）
    bottom_y = max_y - 30
    for dx in [-30, 0, 30]:
        px = center_x + dx
        if 0 <= bottom_y < mask.shape[0] and 0 <= px < mask.shape[1]:
            positive_points.append([px, bottom_y])

    if not positive_points:
        positive_points = [[center_x, center_y]]

    # 负提示点（四角，背景区域）
    h, w = mask.shape
    negative_points = [
        [10, 10],
        [10, w - 10],
        [h - 10, 10],
        [h - 10, w - 10],
    ]

    # 合并提示点
    input_points = np.array(positive_points + negative_points)
    input_labels = np.array([1] * len(positive_points) + [0] * len(negative_points))

    # 预测
    masks, scores, logits = sam_predictor.predict(
        point_coords=input_points,
        point_labels=input_labels,
        multimask_output=True,
    )

    # 选择得分最高的 mask
    best_idx = np.argmax(scores)
    sam_mask = masks[best_idx].astype(np.uint8) * 255

    return sam_mask


def vitmatte_refine(frame_rgb: np.ndarray, trimap: np.ndarray) -> np.ndarray:
    """用 ViTMatte 精细化 alpha matte。"""
    processor = VitMatteImageProcessor.from_pretrained("hustvl/vitmatte-base-composition-1k")
    model = VitMatteForImageMatting.from_pretrained("hustvl/vitmatte-base-composition-1k")
    model.eval()

    pil_image = Image.fromarray(frame_rgb)
    pil_trimap = Image.fromarray(trimap)

    inputs = processor(images=pil_image, trimaps=pil_trimap, return_tensors="pt")

    with torch.no_grad():
        outputs = model(**inputs)

    alpha = outputs.alphas[0, 0].numpy()
    alpha = np.clip(alpha, 0.0, 1.0)

    h, w = frame_rgb.shape[:2]
    alpha = alpha[:h, :w]

    return alpha


def check_edge_green(frame_bgr: np.ndarray, alpha: np.ndarray) -> int:
    """检查边缘区域的绿色像素数量。"""
    # 边缘区域：alpha 在 0.1-0.9 之间
    edge_mask = (alpha > 0.1) & (alpha < 0.9)
    if not edge_mask.any():
        return 0

    # 计算绿色过剩
    f = frame_bgr.astype(np.float32)
    green_excess = f[:, :, 1] - np.maximum(f[:, :, 0], f[:, :, 2])

    # 检查绿色过剩 > 5 的像素
    green_pixels = np.count_nonzero((edge_mask) & (green_excess > 5))

    return green_pixels


def despill(frame_bgr: np.ndarray, alpha: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """去绿溢——改进版四步策略。

    1. 收紧 alpha：低 alpha 直接设为透明（降低阈值保留边缘细节）
    2. 强力绿色抑制：G 通道限制为 min(G, max(B,R) + 1)
    3. 边缘颜色修正：用邻近内部像素颜色替换（非全局平均）
    4. 阴影区域处理：底部阴影单独压暗
    """
    h, w = frame_bgr.shape[:2]
    f = frame_bgr.astype(np.float32)

    # 步骤1：收紧 alpha - 降低阈值保留更多边缘细节
    alpha_clean = alpha.copy()
    alpha_clean[alpha_clean < 0.05] = 0.0

    # 步骤2：强力绿色抑制 - 所有前景像素，G 通道严格限制
    fg_mask = alpha_clean > 0.01
    if fg_mask.any():
        max_br = np.maximum(f[:, :, 0], f[:, :, 2])  # max(B, R)
        # G 不能超过 max(B,R) + 1（允许极小的自然绿色）
        green_too_high = (f[:, :, 1] > max_br + 1) & fg_mask
        if green_too_high.any():
            cy, cx = np.where(green_too_high)
            f[cy, cx, 1] = np.minimum(f[cy, cx, 1], max_br[cy, cx] + 1)

    result = f.copy()

    # 步骤3：边缘颜色修正 - 用邻近内部像素颜色替换
    # 找到内部参考点（alpha > 0.9 的区域）
    internal_mask = alpha_clean > 0.9
    if not internal_mask.any():
        internal_mask = alpha_clean > 0.7

    if internal_mask.any():
        # 计算内部区域的颜色统计
        internal_pixels = f[internal_mask]
        avg_color = internal_pixels.mean(axis=0)

        # 边缘区域：alpha 在 0.05-0.5 之间的像素
        edge_mask = (alpha_clean > 0.05) & (alpha_clean < 0.5)
        if edge_mask.any():
            cy, cx = np.where(edge_mask)
            a = alpha_clean[cy, cx]
            # alpha 越低，越接近内部颜色（更强的混合）
            blend = np.clip((0.5 - a) / 0.45, 0.0, 0.8)
            orig = f[cy, cx]
            fixed = orig * (1.0 - blend.reshape(-1, 1)) + avg_color * blend.reshape(-1, 1)
            result[cy, cx] = fixed

    # 步骤4：阴影区域处理 - 底部阴影压暗
    # 检测底部区域（y > 0.7 * h）且 alpha 较低的像素
    shadow_y = int(h * 0.7)
    shadow_region = np.zeros((h, w), dtype=bool)
    shadow_region[shadow_y:, :] = True
    shadow_mask = shadow_region & (alpha_clean > 0.1) & (alpha_clean < 0.6)

    if shadow_mask.any():
        sy, sx = np.where(shadow_mask)
        # 压暗阴影区域（降低亮度 30%）
        result[sy, sx] = result[sy, sx] * 0.7

    return np.clip(result, 0, 255).astype(np.uint8), alpha_clean


def process_image(image_path: str, output_path: str, max_iterations: int = 5):
    """处理单张图片。"""
    # 使用 PIL 读取（支持中文路径）
    try:
        pil_img = Image.open(image_path)
        frame_rgb = np.array(pil_img)
        if frame_rgb.shape[2] == 4:  # RGBA → RGB
            frame_rgb = frame_rgb[:, :, :3]
        frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
    except Exception as e:
        print(f"错误：无法读取图片 {image_path}: {e}")
        return

    h, w = frame_bgr.shape[:2]
    print(f"处理图片: {image_path} ({w}x{h})")

    # Step 1: 传统色度键
    print("  Step 1: 传统色度键...")
    bg_color = sample_bg_color(frame_bgr)
    mask = chroma_key_mask(frame_bgr, bg_color, threshold=30.0)
    print(f"    背景色: BGR=({bg_color[0]:.0f}, {bg_color[1]:.0f}, {bg_color[2]:.0f})")

    # Step 2: SAM 精炼
    print("  Step 2: SAM 精炼...")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    sam = sam_model_registry["vit_b"](checkpoint="models/sam_vit_b.pth")
    sam.to(device)
    sam_predictor = SamPredictor(sam)

    sam_mask = sam_refine(frame_rgb, mask, sam_predictor)
    print(f"    SAM mask 像素: {np.count_nonzero(sam_mask)}")

    # Step 3: 生成 trimap
    print("  Step 3: 生成 trimap...")
    trimap = generate_trimap(sam_mask, erode_size=15, dilate_size=15)
    print(f"    前景像素: {np.count_nonzero(trimap == 255)}")
    print(f"    背景像素: {np.count_nonzero(trimap == 0)}")
    print(f"    未知像素: {np.count_nonzero(trimap == 128)}")

    # Step 4: ViTMatte 精细化 + 迭代
    print("  Step 4: ViTMatte 精细化 + 迭代...")
    alpha = vitmatte_refine(frame_rgb, trimap)
    print(f"    初始 Alpha 范围: [{alpha.min():.3f}, {alpha.max():.3f}]")

    for iteration in range(max_iterations):
        # 检查边缘绿色
        green_pixels = check_edge_green(frame_bgr, alpha)
        print(f"    迭代 {iteration + 1}: 边缘绿色像素 = {green_pixels}")

        if green_pixels == 0:
            print(f"    边缘已干净，停止迭代")
            break

        # 用当前 alpha 作为新的 trimap 继续精炼
        alpha_u8 = (alpha * 255).astype(np.uint8)
        trimap = generate_trimap(alpha_u8, erode_size=10, dilate_size=10)
        alpha = vitmatte_refine(frame_rgb, trimap)

    # Step 5: despill
    print("  Step 5: despill 去绿溢...")
    frame_clean, alpha_new = despill(frame_bgr, alpha)

    # Step 6: 合成 RGBA
    print("  Step 6: 合成 RGBA...")
    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    rgba[:, :, :3] = frame_clean
    rgba[:, :, 3] = (alpha_new * 255).astype(np.uint8)

    # 使用 PIL 保存（支持中文路径）
    Image.fromarray(rgba).save(output_path)
    print(f"  保存到: {output_path}")

    # 保存调试图
    debug_dir = Path(output_path).parent / "debug"
    debug_dir.mkdir(exist_ok=True)
    stem = Path(output_path).stem
    Image.fromarray((alpha * 255).astype(np.uint8)).save(str(debug_dir / f"{stem}_alpha.png"))
    Image.fromarray(mask).save(str(debug_dir / f"{stem}_mask.png"))
    Image.fromarray(sam_mask).save(str(debug_dir / f"{stem}_sam_mask.png"))
    print(f"  调试文件保存到: {debug_dir}")


def main():
    if len(sys.argv) < 3:
        print("用法: python matte_anything.py <image_path> <output_path>")
        print("示例: python matte_anything.py data/pipeline/frames/stand/frame_0000.png output.png")
        sys.exit(1)

    image_path = sys.argv[1]
    output_path = sys.argv[2]

    process_image(image_path, output_path)


if __name__ == "__main__":
    main()
