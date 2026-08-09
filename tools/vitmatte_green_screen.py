"""绿幕色度键 + ViTMatte 精细化抠图。

流程：
1. 传统色度键生成粗略 mask
2. 生成 trimap（前景/背景/未知区域）
3. ViTMatte 精细化 alpha
4. despill 去绿溢
5. 合成 RGBA

用法：
    python tools/vitmatte_green_screen.py <image_path> <output_path>
"""

import sys
from pathlib import Path

import cv2
import numpy as np
import torch
from PIL import Image
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
    """从二值 mask 生成 trimap。

    - 255: 确定前景（猫）
    - 0: 确定背景（绿幕）
    - 128: 未知区域（边缘，需要 ViTMatte 精细化）
    """
    kernel_erode = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (erode_size, erode_size))
    kernel_dilate = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (dilate_size, dilate_size))

    # 确定前景：erode mask（向内收缩）
    fg = cv2.erode(mask, kernel_erode, iterations=3)

    # 确定背景：dilate mask 的反向（向外扩展）
    bg = cv2.dilate(mask, kernel_dilate, iterations=3)
    bg_inv = 255 - bg

    # 生成 trimap
    trimap = np.full(mask.shape, 128, dtype=np.uint8)  # 默认未知
    trimap[fg == 255] = 255  # 确定前景
    trimap[bg_inv == 255] = 0  # 确定背景

    return trimap


def vitmatte_refine(frame_rgb: np.ndarray, trimap: np.ndarray) -> np.ndarray:
    """用 ViTMatte 精细化 alpha matte。"""
    # 加载模型
    processor = VitMatteImageProcessor.from_pretrained("hustvl/vitmatte-base-composition-1k")
    model = VitMatteForImageMatting.from_pretrained("hustvl/vitmatte-base-composition-1k")
    model.eval()

    # 准备输入
    pil_image = Image.fromarray(frame_rgb)
    pil_trimap = Image.fromarray(trimap)

    inputs = processor(images=pil_image, trimaps=pil_trimap, return_tensors="pt")

    # 推理
    with torch.no_grad():
        outputs = model(**inputs)

    # 后处理：outputs.alphas 形状是 (batch, 1, H, W)
    alpha = outputs.alphas[0, 0].numpy()  # 取第一个 batch，第一个通道
    alpha = np.clip(alpha, 0.0, 1.0)

    # 裁剪到原始尺寸
    h, w = frame_rgb.shape[:2]
    alpha = alpha[:h, :w]

    return alpha


def despill(frame_bgr: np.ndarray, alpha: np.ndarray, strength: float = 1.0):
    """去绿溢——基于 alpha 权重的颜色替换。

    策略：
    1. 用 min(B, R) 替换 G 通道——避免蓝色溢出
    2. 对半透明区域限制 B 通道——防止青色残留

    Returns:
        (frame_clean, alpha_final): 处理后的帧和原始 alpha
    """
    f = frame_bgr.astype(np.float32)
    result = f.copy()

    # 计算绿色过剩 = G - max(B, R)
    green_excess = f[:, :, 1] - np.maximum(f[:, :, 0], f[:, :, 2])

    # 对所有 alpha > 0.1 的像素进行处理
    process_mask = alpha > 0.1
    if not process_mask.any():
        return frame_bgr, alpha

    # 对所有绿色过剩 > 0 的像素进行替换
    spill_mask = process_mask & (green_excess > 0)
    if spill_mask.any():
        cy, cx = np.where(spill_mask)
        a = alpha[cy, cx]  # alpha 值

        # Step 1: 用 min(B, R) 替换 G 通道——避免蓝色溢出
        min_br = np.minimum(f[cy, cx, 0], f[cy, cx, 2])
        blend_factor = a * strength
        result[cy, cx, 1] = f[cy, cx, 1] * (1.0 - blend_factor) + min_br * blend_factor

    # Step 2: 对半透明区域，限制 B 通道不超过 max(R, G) + 20
    # 防止 despill 后 B 相对过高导致青色残留
    semi_mask = (alpha > 0.1) & (alpha < 0.9)
    if semi_mask.any():
        sy, sx = np.where(semi_mask)
        r_vals = result[sy, sx, 0]
        g_vals = result[sy, sx, 1]
        b_vals = result[sy, sx, 2]
        max_rg = np.maximum(r_vals, g_vals)
        # 如果 B > max(R,G) + 20，压低到 max(R,G) + 10
        too_blue = b_vals > max_rg + 20
        if too_blue.any():
            result[sy[too_blue], sx[too_blue], 2] = max_rg[too_blue] + 10

    return np.clip(result, 0, 255).astype(np.uint8), alpha


def process_image(image_path: str, output_path: str):
    """处理单张图片。"""
    # 读取图片
    frame_bgr = cv2.imread(image_path)
    if frame_bgr is None:
        print(f"错误：无法读取图片 {image_path}")
        return

    frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    h, w = frame_bgr.shape[:2]

    print(f"处理图片: {image_path} ({w}x{h})")

    # Step 1: 传统色度键
    print("  Step 1: 传统色度键...")
    bg_color = sample_bg_color(frame_bgr)
    mask = chroma_key_mask(frame_bgr, bg_color, threshold=30.0)
    print(f"    背景色: BGR=({bg_color[0]:.0f}, {bg_color[1]:.0f}, {bg_color[2]:.0f})")

    # Step 2: 生成 trimap
    print("  Step 2: 生成 trimap...")
    trimap = generate_trimap(mask, erode_size=15, dilate_size=15)
    print(f"    前景像素: {np.count_nonzero(trimap == 255)}")
    print(f"    背景像素: {np.count_nonzero(trimap == 0)}")
    print(f"    未知像素: {np.count_nonzero(trimap == 128)}")

    # Step 3: ViTMatte 精细化
    print("  Step 3: ViTMatte 精细化...")
    alpha = vitmatte_refine(frame_rgb, trimap)
    print(f"    Alpha 范围: [{alpha.min():.3f}, {alpha.max():.3f}]")
    print(f"    Alpha 均值: {alpha.mean():.3f}")

    # Step 4: despill + 收缩 alpha
    print("  Step 4: despill + 收缩 alpha...")
    frame_clean, alpha_final = despill(frame_bgr, alpha, strength=1.0)

    # Step 5: 合成 RGBA
    print("  Step 5: 合成 RGBA...")
    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    rgba[:, :, :3] = frame_clean
    rgba[:, :, 3] = (alpha_final * 255).astype(np.uint8)

    # 保存
    cv2.imwrite(output_path, rgba)
    print(f"  保存到: {output_path}")

    # 保存中间结果用于调试
    debug_dir = Path(output_path).parent / "debug"
    debug_dir.mkdir(exist_ok=True)
    stem = Path(output_path).stem

    cv2.imwrite(str(debug_dir / f"{stem}_mask.png"), mask)
    cv2.imwrite(str(debug_dir / f"{stem}_trimap.png"), trimap)
    cv2.imwrite(str(debug_dir / f"{stem}_alpha.png"), (alpha * 255).astype(np.uint8))

    print(f"  调试文件保存到: {debug_dir}")


def main():
    if len(sys.argv) < 3:
        print("用法: python vitmatte_green_screen.py <image_path> <output_path>")
        print("示例: python vitmatte_green_screen.py data/pipeline/frames/stand/frame_0000.png output.png")
        sys.exit(1)

    image_path = sys.argv[1]
    output_path = sys.argv[2]

    process_image(image_path, output_path)


if __name__ == "__main__":
    main()
