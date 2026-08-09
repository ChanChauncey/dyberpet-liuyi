"""
两步走：1. 轮廓检测定位物品 → 2. 逐个 rembg 抠背景
用法: python cut_items_hybrid.py <图片路径> [输出目录] [--names ...]
"""

import cv2
import numpy as np
import os
import sys
import argparse
from rembg import remove
from PIL import Image
import io


def detect_items(img, threshold=240, min_area=2000):
    """白色背景轮廓检测，返回 bounding box 列表"""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY_INV)

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=2)
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=1)

    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    boxes = []
    for c in contours:
        area = cv2.contourArea(c)
        if area >= min_area:
            x, y, w, h = cv2.boundingRect(c)
            boxes.append((x, y, w, h))

    boxes.sort(key=lambda b: (b[1], b[0]))
    return boxes


def rembg_crop(bgr_crop):
    """对单个裁剪图做 rembg 去背景"""
    pil_img = Image.fromarray(cv2.cvtColor(bgr_crop, cv2.COLOR_BGR2RGB))
    buf = io.BytesIO()
    pil_img.save(buf, format='PNG')
    output = remove(buf.getvalue())
    return np.array(Image.open(io.BytesIO(output)).convert('RGBA'))


def crop_square(bgra, padding=0.15):
    """将去背后的图调整为正方形"""
    ch, cw = bgra.shape[:2]
    size = max(cw, ch)
    square = np.zeros((size, size, 4), dtype=np.uint8)
    ox = (size - cw) // 2
    oy = (size - ch) // 2
    square[oy:oy+ch, ox:ox+cw] = bgra
    return square


def main():
    parser = argparse.ArgumentParser(description='轮廓定位 + rembg 逐个抠图')
    parser.add_argument('image', help='输入图片路径')
    parser.add_argument('output_dir', nargs='?', default=None, help='输出目录')
    parser.add_argument('--padding', type=float, default=0.2, help='裁剪 padding（默认 0.2）')
    parser.add_argument('--threshold', type=int, default=230, help='白色背景阈值（默认 230）')
    parser.add_argument('--min-area', type=int, default=1500, help='最小轮廓面积（默认 1500）')
    parser.add_argument('--names', nargs='+', default=None, help='物品名称列表')
    args = parser.parse_args()

    img = cv2.imread(args.image)
    if img is None:
        print(f'错误: 无法读取 {args.image}')
        sys.exit(1)

    if args.output_dir is None:
        img_dir = os.path.dirname(os.path.abspath(args.image))
        args.output_dir = os.path.join(img_dir, 'items_final')
    os.makedirs(args.output_dir, exist_ok=True)

    ih, iw = img.shape[:2]
    print(f'图片尺寸: {iw}x{ih}')

    # 第一步：轮廓检测定位
    boxes = detect_items(img, threshold=args.threshold, min_area=args.min_area)
    print(f'检测到 {len(boxes)} 个物品区域')

    if args.names and len(args.names) != len(boxes):
        print(f'警告: 名称({len(args.names)})与检测数({len(boxes)})不匹配，使用自动编号')

    # 第二步：逐个裁剪 + rembg 抠图
    for i, (x, y, w, h) in enumerate(boxes):
        if args.names and i < len(args.names):
            name = args.names[i]
        else:
            name = f'item_{i+1:02d}'

        # 裁剪（带 padding）
        pad_x = int(w * args.padding)
        pad_y = int(h * args.padding)
        x1 = max(0, x - pad_x)
        y1 = max(0, y - pad_y)
        x2 = min(iw, x + w + pad_x)
        y2 = min(ih, y + h + pad_y)
        crop = img[y1:y2, x1:x2]

        # rembg 去背景
        bgra = rembg_crop(crop)

        # 调整为正方形
        result = crop_square(bgra, padding=0.05)

        # 保存
        out_path = os.path.join(args.output_dir, f'{name}.png')
        cv2.imwrite(out_path, cv2.cvtColor(result, cv2.COLOR_RGBA2BGRA))

        print(f'  [{i+1:2d}] {name:20s} → {out_path}  ({w}x{h})')

    print(f'\n完成！共导出 {len(boxes)} 个物品到 {args.output_dir}')


if __name__ == '__main__':
    main()
