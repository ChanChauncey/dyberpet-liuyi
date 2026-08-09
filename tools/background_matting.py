"""使用 BackgroundMattingV2 处理绿幕抠图。

用法：
    python tools/background_matting.py <image_path> <output_path>
"""

import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from rembg import new_session, remove


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

    # 使用 rembg 的 isnet 模型（更好的边缘处理）
    print("  使用 isnet 模型处理...")
    session = new_session("isnet-general-use")
    img_pil = Image.fromarray(frame_rgb)
    result_pil = remove(img_pil, session=session, alpha_matting=True, alpha_matting_erode_size=1)

    # 提取 alpha
    result_rgba = np.array(result_pil)
    alpha = result_rgba[:, :, 3].astype(np.float32) / 255.0

    print(f"  Alpha 范围: [{alpha.min():.3f}, {alpha.max():.3f}]")
    print(f"  Alpha 均值: {alpha.mean():.3f}")

    # 颜色替换（去除绿色溢出）- 最激进方案
    print("  颜色替换...")
    f = frame_bgr.astype(np.float32)
    result = f.copy()

    # 计算绿色过剩
    green_excess = f[:, :, 1] - np.maximum(f[:, :, 0], f[:, :, 2])

    # 对所有 alpha > 0.01 且绿色过剩 > 0 的像素进行替换
    spill_mask = (alpha > 0.01) & (green_excess > 0)
    if spill_mask.any():
        cy, cx = np.where(spill_mask)

        # 最激进：直接把 G 设为 B 和 R 的最小值
        min_br = np.minimum(f[cy, cx, 0], f[cy, cx, 2])
        result[cy, cx, 1] = min_br

    # 合成 RGBA
    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    rgba[:, :, :3] = np.clip(result, 0, 255).astype(np.uint8)
    rgba[:, :, 3] = (alpha * 255).astype(np.uint8)

    # 保存
    cv2.imwrite(output_path, rgba)
    print(f"  保存到: {output_path}")

    # 保存 alpha 调试图
    debug_dir = Path(output_path).parent / "debug"
    debug_dir.mkdir(exist_ok=True)
    stem = Path(output_path).stem
    cv2.imwrite(str(debug_dir / f"{stem}_alpha.png"), (alpha * 255).astype(np.uint8))
    print(f"  Alpha 调试图: {debug_dir / f'{stem}_alpha.png'}")


def main():
    if len(sys.argv) < 3:
        print("用法: python background_matting.py <image_path> <output_path>")
        print("示例: python background_matting.py data/pipeline/frames/stand/frame_0000.png output.png")
        sys.exit(1)

    image_path = sys.argv[1]
    output_path = sys.argv[2]

    process_image(image_path, output_path)


if __name__ == "__main__":
    main()
