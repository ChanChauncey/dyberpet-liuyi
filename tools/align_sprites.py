"""精灵图对齐工具——将抠图后的猫帧统一位置和大小。

以参考帧（默认动作0首帧）的猫体位置为标准，对其他帧做缩放+平移，
使所有帧中猫的大小和位置一致。

用法：
    python align_sprites.py <rgba_dir> <output_dir> [--reference act0_frame0000_rgba.png]
"""

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np


def find_bbox(rgba: np.ndarray, alpha_threshold: int = 10):
    """找到非透明像素的边界框。"""
    alpha = rgba[:, :, 3]
    ys, xs = np.where(alpha > alpha_threshold)
    if len(ys) == 0:
        return None
    return {
        "min_x": xs.min(), "max_x": xs.max(),
        "min_y": ys.min(), "max_y": ys.max(),
    }


def get_cat_params(rgba: np.ndarray):
    """从RGBA图像提取猫体参数：宽、高、中心X、脚底Y。"""
    bb = find_bbox(rgba)
    if bb is None:
        return None
    w = bb["max_x"] - bb["min_x"] + 1
    h = bb["max_y"] - bb["min_y"] + 1
    cx = (bb["min_x"] + bb["max_x"]) / 2.0
    bottom = bb["max_y"]
    return {"w": w, "h": h, "cx": cx, "bottom": bottom, "bbox": bb}


def align_cat(
    src_rgba: np.ndarray,
    ref_params: dict,
    canvas_size: tuple[int, int],
) -> np.ndarray:
    """将源图中的猫对齐到参考位置。

    Args:
        src_rgba: 源RGBA图像 (H, W, 4)
        ref_params: 参考猫体参数，含 target_h, target_cx, target_bottom
        canvas_size: 输出画布 (width, height)

    Returns:
        对齐后的RGBA图像 (canvas_h, canvas_w, 4)
    """
    src_params = get_cat_params(src_rgba)
    if src_params is None:
        print("  警告：源图无猫体，返回空画布")
        return np.zeros((canvas_size[1], canvas_size[0], 4), dtype=np.uint8)

    bb = src_params["bbox"]
    src_h, src_w = src_rgba.shape[:2]

    # 裁剪出猫体区域（带少量padding防止边缘丢失）
    pad = 4
    crop_x1 = max(0, bb["min_x"] - pad)
    crop_y1 = max(0, bb["min_y"] - pad)
    crop_x2 = min(src_w, bb["max_x"] + pad + 1)
    crop_y2 = min(src_h, bb["max_y"] + pad + 1)

    cat_crop = src_rgba[crop_y1:crop_y2, crop_x1:crop_x2].copy()
    crop_h, crop_w = cat_crop.shape[:2]

    # 缩放因子：使猫高度匹配参考
    scale = ref_params["target_h"] / src_params["h"]
    new_w = int(crop_w * scale)
    new_h = int(crop_h * scale)

    if new_w <= 0 or new_h <= 0:
        print(f"  错误：缩放后尺寸异常 ({new_w}x{new_h})")
        return np.zeros((canvas_size[1], canvas_size[0], 4), dtype=np.uint8)

    resized = cv2.resize(cat_crop, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)

    # 在裁剪图中的猫中心偏移
    cat_cx_in_crop = src_params["cx"] - crop_x1
    cat_bottom_in_crop = src_params["bottom"] - crop_y1

    # 缩放后猫在resized图中的位置
    scaled_cx = cat_cx_in_crop * scale
    scaled_bottom = cat_bottom_in_crop * scale

    # 在目标画布上的粘贴位置
    paste_x = int(ref_params["target_cx"] - scaled_cx)
    paste_y = int(ref_params["target_bottom"] - scaled_bottom)

    cw, ch = canvas_size
    canvas = np.zeros((ch, cw, 4), dtype=np.uint8)

    # 计算实际可粘贴区域
    src_x1 = max(0, -paste_x)
    src_y1 = max(0, -paste_y)
    src_x2 = min(new_w, cw - paste_x)
    src_y2 = min(new_h, ch - paste_y)

    dst_x1 = max(0, paste_x)
    dst_y1 = max(0, paste_y)
    dst_x2 = dst_x1 + (src_x2 - src_x1)
    dst_y2 = dst_y1 + (src_y2 - src_y1)

    if src_x2 > src_x1 and src_y2 > src_y1:
        canvas[dst_y1:dst_y2, dst_x1:dst_x2] = resized[src_y1:src_y2, src_x1:src_x2]

    return canvas


def main():
    parser = argparse.ArgumentParser(description="对齐精灵图首帧")
    parser.add_argument("rgba_dir", help="输入RGBA PNG目录")
    parser.add_argument("output_dir", help="输出对齐后PNG目录")
    parser.add_argument("--reference", default="act0_frame0000_rgba.png",
                        help="参考帧文件名（默认act0_frame0000_rgba.png）")
    parser.add_argument("--canvas-width", type=int, default=705,
                        help="输出画布宽度（默认705）")
    parser.add_argument("--canvas-height", type=int, default=380,
                        help="输出画布高度（默认380）")
    parser.add_argument("--target-cat-height", type=int, default=None,
                        help="目标猫高度px（默认使用参考帧的猫高度）")
    parser.add_argument("--target-cx", type=int, default=None,
                        help="目标猫中心X（默认使用参考帧的中心X）")
    parser.add_argument("--target-bottom", type=int, default=None,
                        help="目标猫脚底Y（默认使用参考帧的脚底Y）")
    args = parser.parse_args()

    rgba_dir = Path(args.rgba_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 加载参考帧
    ref_path = rgba_dir / args.reference
    if not ref_path.exists():
        print(f"错误：参考帧不存在 {ref_path}")
        sys.exit(1)

    ref_rgba = cv2.imread(str(ref_path), cv2.IMREAD_UNCHANGED)
    if ref_rgba is None:
        print(f"错误：无法读取参考帧 {ref_path}")
        sys.exit(1)

    ref_params = get_cat_params(ref_rgba)
    if ref_params is None:
        print("错误：参考帧中未找到猫体")
        sys.exit(1)

    print(f"参考帧 {args.reference}:")
    print(f"  猫体 {ref_params['w']}x{ref_params['h']} "
          f"中心=({ref_params['cx']:.0f},{ref_params['bottom'] - ref_params['h']/2:.0f}) "
          f"脚底={ref_params['bottom']}")

    # 使用命令行覆盖或参考帧值
    target_h = args.target_cat_height or ref_params["h"]
    target_cx = args.target_cx or ref_params["cx"]
    target_bottom = args.target_bottom or ref_params["bottom"]

    ref_alignment = {"target_h": target_h, "target_cx": target_cx, "target_bottom": target_bottom}
    canvas_size = (args.canvas_width, args.canvas_height)

    print(f"对齐参数: cat_h={target_h} cx={target_cx:.0f} bottom={target_bottom}")
    print(f"画布: {canvas_size[0]}x{canvas_size[1]}")
    print()

    # 处理所有帧
    png_files = sorted(rgba_dir.glob("*_rgba.png"))
    if not png_files:
        print("错误：未找到RGBA PNG文件")
        sys.exit(1)

    for png_path in png_files:
        src = cv2.imread(str(png_path), cv2.IMREAD_UNCHANGED)
        if src is None:
            print(f"跳过：无法读取 {png_path.name}")
            continue

        src_params = get_cat_params(src)
        if src_params:
            print(f"{png_path.name}: "
                  f"猫={src_params['w']}x{src_params['h']} "
                  f"cx={src_params['cx']:.0f} bottom={src_params['bottom']} "
                  f"→ scale={target_h/src_params['h']:.3f}")

        aligned = align_cat(src, ref_alignment, canvas_size)

        # 输出文件名：去掉 _rgba 后缀，加上 _aligned
        out_name = png_path.name.replace("_rgba.png", "_aligned.png")
        out_path = output_dir / out_name
        cv2.imwrite(str(out_path), aligned)

    print(f"\n完成：{len(png_files)} 帧 → {output_dir}")


if __name__ == "__main__":
    main()
