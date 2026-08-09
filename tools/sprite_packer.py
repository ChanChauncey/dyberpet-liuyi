"""将 RGBA 帧序列拼接为精灵图和逐帧 PNG，供 DyberPet 使用。

用法：
    python sprite_packer.py <frames_dir> <output_dir>

输出：逐帧 PNG（按 DyberPet 命名） + sprite_sheet.png 总览
"""

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np


def pack_sprites(frames_dir: str, output_dir: str):
    frames_dir = Path(frames_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    png_files = sorted(frames_dir.glob("*.png"))
    if not png_files:
        print(f"错误：{frames_dir} 中没有 PNG 文件")
        sys.exit(1)

    frames = []
    max_h = 0
    for p in png_files:
        img = cv2.imread(str(p), cv2.IMREAD_UNCHANGED)
        if img is None:
            continue
        h, w = img.shape[:2]
        max_h = max(max_h, h)
        frames.append(img)

    # 水平拼接精灵图
    total_w = sum(img.shape[1] for img in frames)
    sprite_sheet = np.zeros((max_h, total_w, 4), dtype=np.uint8)

    x_offset = 0
    for img in frames:
        h, w = img.shape[:2]
        y_offset = (max_h - h) // 2
        if img.shape[2] == 4:
            alpha = img[:, :, 3:4] / 255.0
            for c in range(3):
                sprite_sheet[y_offset:y_offset + h, x_offset:x_offset + w, c] = (
                    img[:, :, c] * alpha[:, :, 0]
                ).astype(np.uint8)
            sprite_sheet[y_offset:y_offset + h, x_offset:x_offset + w, 3] = img[:, :, 3]
        else:
            sprite_sheet[y_offset:y_offset + h, x_offset:x_offset + w, :3] = img
            sprite_sheet[y_offset:y_offset + h, x_offset:x_offset + w, 3] = 255
        x_offset += w

    # 写入逐帧 PNG
    for i, img in enumerate(frames):
        out_name = f"{frames_dir.name}_{i}.png"
        cv2.imwrite(str(output_dir / out_name), img)

    # 写入精灵图总览
    cv2.imwrite(str(output_dir / "sprite_sheet.png"), sprite_sheet)

    print(f"完成：{len(frames)} 帧 → {output_dir}")
    print(f"  精灵图总宽度: {total_w}px, 高度: {max_h}px")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="帧序列拼精灵图")
    parser.add_argument("frames", help="输入 RGBA 帧目录")
    parser.add_argument("output", help="输出目录")
    args = parser.parse_args()

    pack_sprites(args.frames, args.output)
