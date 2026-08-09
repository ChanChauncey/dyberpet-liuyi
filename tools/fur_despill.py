"""毛发感知去绿溢——根据黑毛/白毛区域做不同策略的颜色修正。

原理：
1. 从 alpha>0.9 的不透明区域采样"本色"（黑毛、白毛）
2. 按亮度把前景像素分为黑毛区/白毛区
3. 绿色过剩的像素：用对应区域的本色替换绿色通道
4. alpha 越低（越靠边缘），替换越温和，保留毛发质感

用法：
    python fur_despill.py <image_path> <output_path>
    python fur_despill.py <frames_dir> <output_dir> --batch
"""

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np


def sample_fur_colors(frame_bgr: np.ndarray, alpha: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """从不透明区域采样黑毛和白毛的本色。

    Returns:
        (dark_color, light_color): 黑毛平均色、白毛平均色 (BGR float32)
    """
    # 不透明区域
    opaque = alpha > 0.9
    if not opaque.any():
        # fallback: 用中心区域
        h, w = alpha.shape
        cy, cx = h // 2, w // 2
        region = frame_bgr[cy - 20:cy + 20, cx - 20:cx + 20]
        avg = region.mean(axis=(0, 1)).astype(np.float32)
        return avg * 0.3, avg * 0.8

    colors = frame_bgr[opaque].astype(np.float32)  # (N, 3) BGR
    brightness = colors.mean(axis=1)  # 亮度

    # 按亮度中位数分成黑毛/白毛
    median_bright = np.median(brightness)
    dark_mask = brightness < median_bright
    light_mask = brightness >= median_bright

    dark_color = colors[dark_mask].mean(axis=0) if dark_mask.any() else np.array([30, 30, 30], dtype=np.float32)
    light_color = colors[light_mask].mean(axis=0) if light_mask.any() else np.array([200, 200, 200], dtype=np.float32)

    return dark_color, light_color


def fur_aware_despill(
    frame_bgr: np.ndarray,
    alpha: np.ndarray,
    strength: float = 0.9,
    edge_threshold: float = 1.0,
) -> np.ndarray:
    """毛发感知去绿溢——只动边缘，主体不变。

    策略：
    - alpha > 0.5（猫主体）：完全不动
    - alpha 0.01~0.5（边缘毛发）：绿色变灰色

    Args:
        frame_bgr: 原始 BGR 图像 (uint8)
        alpha: alpha 通道 (float32, [0,1])
        strength: 替换强度 (0~1)

    Returns:
        去绿后的 BGR 图像 (uint8)
    """
    f = frame_bgr.astype(np.float32)
    result = f.copy()

    # 绿色过剩 = G - max(B, R)
    green_excess = f[:, :, 1] - np.maximum(f[:, :, 0], f[:, :, 2])

    # 只处理边缘：alpha 0.01~0.5 + 有绿色过剩
    edge_mask = (alpha > 0.01) & (alpha < 0.5) & (green_excess > edge_threshold)
    if not edge_mask.any():
        return frame_bgr

    ey, ex = np.where(edge_mask)
    r_ch = f[ey, ex, 0]
    g_ch = f[ey, ex, 1]
    b_ch = f[ey, ex, 2]
    a = alpha[ey, ex]

    # 灰色目标 = 三通道均值
    gray = (r_ch + g_ch + b_ch) / 3.0

    # alpha 越低（越靠边缘）→ 拉向灰越狠
    # alpha=0.01 → 拉 90%，alpha=0.5 → 拉 0%
    edge_factor = (0.5 - a) / 0.5  # 0~1
    gray_ratio = edge_factor * strength

    # 三通道都拉向灰色
    result[ey, ex, 0] = r_ch + (gray - r_ch) * gray_ratio
    result[ey, ex, 1] = g_ch + (gray - g_ch) * gray_ratio
    result[ey, ex, 2] = b_ch + (gray - b_ch) * gray_ratio

    return np.clip(result, 0, 255).astype(np.uint8)


def process_image(image_path: str, output_path: str, strength: float = 0.7):
    """处理单张图片（需要已有 alpha，即 RGBA 输入）。"""
    # 读取 RGBA
    img = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
    if img is None:
        print(f"错误：无法读取 {image_path}")
        return

    if img.shape[2] == 4:
        bgr = img[:, :, :3]
        alpha = img[:, :, 3].astype(np.float32) / 255.0
    else:
        bgr = img
        alpha = np.ones(img.shape[:2], dtype=np.float32)

    h, w = bgr.shape[:2]
    print(f"处理: {image_path} ({w}x{h})")

    # 采样本色
    dark_color, light_color = sample_fur_colors(bgr, alpha)
    print(f"  黑毛本色 BGR: ({dark_color[0]:.0f}, {dark_color[1]:.0f}, {dark_color[2]:.0f})")
    print(f"  白毛本色 BGR: ({light_color[0]:.0f}, {light_color[1]:.0f}, {light_color[2]:.0f})")

    # 去绿
    bgr_clean = fur_aware_despill(bgr, alpha, strength=strength)

    # 合成
    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    rgba[:, :, :3] = bgr_clean
    rgba[:, :, 3] = (alpha * 255).astype(np.uint8)

    cv2.imwrite(output_path, rgba)
    print(f"  保存: {output_path}")


def process_batch(frames_dir: str, output_dir: str, strength: float = 0.7):
    """批量处理目录。"""
    frames_dir = Path(frames_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    png_files = sorted(frames_dir.glob("*.png"))
    if not png_files:
        print(f"错误：{frames_dir} 中无 PNG 文件")
        sys.exit(1)

    total = len(png_files)
    for i, f in enumerate(png_files):
        img = cv2.imread(str(f), cv2.IMREAD_UNCHANGED)
        if img is None or img.shape[2] < 4:
            continue

        bgr = img[:, :, :3]
        alpha = img[:, :, 3].astype(np.float32) / 255.0
        bgr_clean = fur_aware_despill(bgr, alpha, strength=strength)

        h, w = bgr.shape[:2]
        rgba = np.zeros((h, w, 4), dtype=np.uint8)
        rgba[:, :, :3] = bgr_clean
        rgba[:, :, 3] = (alpha * 255).astype(np.uint8)

        out_path = output_dir / f"{f.stem}_fur.png"
        cv2.imwrite(str(out_path), rgba)

        if (i + 1) % 50 == 0:
            print(f"  {i+1}/{total}")

    print(f"完成: {total} 帧 → {output_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="毛发感知去绿溢")
    parser.add_argument("input", help="输入图片路径 或 帧目录（配合 --batch）")
    parser.add_argument("output", help="输出路径")
    parser.add_argument("--batch", action="store_true", help="批量处理目录")
    parser.add_argument("--strength", type=float, default=0.7, help="替换强度 0~1（默认 0.7）")
    args = parser.parse_args()

    if args.batch:
        process_batch(args.input, args.output, strength=args.strength)
    else:
        process_image(args.input, args.output, strength=args.strength)
