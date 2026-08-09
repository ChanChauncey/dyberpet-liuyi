# coding:utf-8
"""
从像素精灵图表格中切割出单独的帧文件。
用法: D:\Python\python.exe tools/cut_pixel_sprites.py <sprite_sheet.png> <output_dir> [frame_size]
"""
import sys
import os
from PIL import Image
import numpy as np


def find_content_rows(img_array, frame_size, threshold=10):
    """找到有内容的行，返回 [(row_idx, num_frames)]"""
    h, w = img_array.shape[:2]
    rows_with_content = []

    for row_idx in range(h // frame_size):
        row_start = row_idx * frame_size
        row_end = row_start + frame_size
        row_data = img_array[row_start:row_end, :, :]

        # 检查这一行每一列是否有内容
        max_frame = 0
        for col_idx in range(w // frame_size):
            col_start = col_idx * frame_size
            col_end = col_start + frame_size
            tile = row_data[:, col_start:col_end, :]
            if tile.shape[2] == 4:  # RGBA
                alpha = tile[:, :, 3]
                if np.max(alpha) > threshold:
                    max_frame = col_idx + 1

        if max_frame > 0:
            rows_with_content.append((row_idx, max_frame))

    return rows_with_content


def cut_sprites(sheet_path, output_dir, frame_size=64):
    """切割精灵图表格"""
    img = Image.open(sheet_path).convert('RGBA')
    img_array = np.array(img)

    print(f"精灵图尺寸: {img.size[0]}x{img.size[1]}")
    print(f"帧大小: {frame_size}x{frame_size}")
    print(f"列数: {img.size[0] // frame_size}, 行数: {img.size[1] // frame_size}")

    rows = find_content_rows(img_array, frame_size)
    print(f"有内容的行数: {len(rows)}")

    os.makedirs(output_dir, exist_ok=True)

    total_frames = 0
    for i, (row_idx, num_frames) in enumerate(rows):
        print(f"  行 {row_idx}: {num_frames} 帧")
        for col_idx in range(num_frames):
            x = col_idx * frame_size
            y = row_idx * frame_size
            frame = img.crop((x, y, x + frame_size, y + frame_size))
            frame_path = os.path.join(output_dir, f"row{i:02d}_frame{col_idx:02d}.png")
            frame.save(frame_path)
            total_frames += 1

    print(f"\n总共切割 {total_frames} 帧到 {output_dir}")
    return rows


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("用法: python cut_pixel_sprites.py <sprite_sheet.png> <output_dir> [frame_size]")
        sys.exit(1)

    sheet_path = sys.argv[1]
    output_dir = sys.argv[2]
    frame_size = int(sys.argv[3]) if len(sys.argv) > 3 else 64

    cut_sprites(sheet_path, output_dir, frame_size)
