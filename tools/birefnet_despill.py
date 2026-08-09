"""BiRefNet 抠图 + despill 后处理——去除边缘绿色残留。"""

import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from rembg import new_session, remove


def despill(frame: np.ndarray, alpha: np.ndarray, strength: float = 0.8) -> np.ndarray:
    """去绿溢——压制半透明边缘的绿色通道。

    Args:
        frame: 原始 BGR 图像 (uint8)
        alpha: alpha 通道 (float32, [0,1])
        strength: 压制强度 (0~1, 越大压制越狠)

    Returns:
        去绿后的 BGR 图像 (uint8)
    """
    f = frame.astype(np.float32)
    result = f.copy()

    # 半透明区域（边缘）
    edge_mask = (alpha > 0.05) & (alpha < 0.95)
    if not edge_mask.any():
        return frame

    # 绿色过剩 = G - max(B, R)
    # OpenCV BGR: channel 0=B, 1=G, 2=R
    green_excess = f[:, :, 1] - np.maximum(f[:, :, 0], f[:, :, 2])

    # 只在绿色确实过剩的区域处理
    spill_mask = edge_mask & (green_excess > 3.0)
    if not spill_mask.any():
        return frame

    cy, cx = np.where(spill_mask)
    excess = green_excess[cy, cx]
    # alpha 越低（越透明），绿溢越多，压制更强
    edge_factor = 1.0 - alpha[cy, cx]
    reduction = excess * strength * edge_factor
    result[cy, cx, 1] -= reduction

    # 额外：在接近透明的区域，降低整体亮度（模拟环境光吸收）
    very_edge = (alpha > 0.01) & (alpha < 0.3)
    if very_edge.any():
        vy, vx = np.where(very_edge)
        fade = alpha[vy, vx] / 0.3  # 0~1
        for c in range(3):
            result[vy, vx, c] = result[vy, vx, c] * fade + (1 - fade) * 128  # 向灰色过渡

    return np.clip(result, 0, 255).astype(np.uint8)


def process_frame(frame_bgr: np.ndarray, session) -> np.ndarray:
    """处理单帧：BiRefNet 抠图 + despill。"""
    # BiRefNet 抠图
    frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    img_pil = Image.fromarray(frame_rgb)
    result_pil = remove(img_pil, session=session, alpha_matting=False)

    # 提取 alpha
    result_rgba = np.array(result_pil)
    alpha = result_rgba[:, :, 3].astype(np.float32) / 255.0

    # despill 去绿溢
    frame_clean = despill(frame_bgr, alpha, strength=0.8)

    # 合成 RGBA
    h, w = frame_bgr.shape[:2]
    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    rgba[:, :, :3] = frame_clean
    rgba[:, :, 3] = result_rgba[:, :, 3]

    return rgba


def main():
    if len(sys.argv) < 3:
        print("用法: python birefnet_despill.py <frames_dir> <output_dir>")
        sys.exit(1)

    frames_dir = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])
    output_dir.mkdir(parents=True, exist_ok=True)

    png_files = sorted(frames_dir.glob("*.png"))
    if not png_files:
        print(f"错误：{frames_dir} 中无 PNG 文件")
        sys.exit(1)

    print(f"BiRefNet + despill 处理 {len(png_files)} 帧...")

    session = new_session("birefnet-general")

    for i, f in enumerate(png_files):
        frame = cv2.imread(str(f))
        if frame is None:
            continue

        rgba = process_frame(frame, session)
        out_path = output_dir / f"{f.stem}_rgba.png"
        cv2.imwrite(str(out_path), rgba)

        if (i + 1) % 10 == 0:
            print(f"  {i+1}/{len(png_files)}")

    print(f"完成：{len(png_files)} 帧 → {output_dir}")


if __name__ == "__main__":
    main()
