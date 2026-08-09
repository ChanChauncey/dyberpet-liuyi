"""
从物品合图中抠出单个物品图标，输出为透明背景正方形 PNG。
用法: python cut_items.py <图片路径> [输出目录] [--padding 0.1] [--threshold 240]
"""

import cv2
import numpy as np
import os
import sys
import argparse


def detect_items(img, threshold=240, min_area=2000):
    """检测图片中的物品区域，返回 bounding box 列表 (x, y, w, h)"""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 白色背景 → 黑色，物品 → 白色
    _, binary = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY_INV)

    # 形态学操作：填充物品内部空洞、去除噪点
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=3)
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=2)

    # 找轮廓
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # 按面积过滤，保留足够大的物体
    boxes = []
    for c in contours:
        area = cv2.contourArea(c)
        if area >= min_area:
            x, y, w, h = cv2.boundingRect(c)
            boxes.append((x, y, w, h))

    # 按从上到下、从左到右排序（先 y 后 x）
    boxes.sort(key=lambda b: (b[1], b[0]))

    return boxes


def crop_and_remove_bg(img, box, padding=0.1):
    """裁剪物品并去除白色背景，输出正方形透明 PNG"""
    x, y, w, h = box
    ih, iw = img.shape[:2]

    # 添加 padding
    pad_x = int(w * padding)
    pad_y = int(h * padding)
    x1 = max(0, x - pad_x)
    y1 = max(0, y - pad_y)
    x2 = min(iw, x + w + pad_x)
    y2 = min(ih, y + h + pad_y)

    # 裁剪
    crop = img[y1:y2, x1:x2].copy()

    # 调整为正方形（以最长边为边长）
    ch, cw = crop.shape[:2]
    size = max(cw, ch)
    square = np.zeros((size, size, 3), dtype=np.uint8)
    square[:] = (255, 255, 255)  # 白色填充

    # 居中放置
    ox = (size - cw) // 2
    oy = (size - ch) // 2
    square[oy:oy+ch, ox:ox+cw] = crop

    # 去除白色背景 → 透明
    hsv = cv2.cvtColor(square, cv2.COLOR_BGR2HSV)
    # 白色区域：饱和度低 + 明度高
    white_mask = (hsv[:, :, 1] < 30) & (hsv[:, :, 2] > 220)

    # 转 BGRA
    bgra = cv2.cvtColor(square, cv2.COLOR_BGR2BGRA)
    bgra[white_mask, 3] = 0  # 白色区域设为透明

    # 边缘抗锯齿：半透明过渡
    alpha = bgra[:, :, 3].astype(np.float32)
    alpha_blur = cv2.GaussianBlur(alpha, (3, 3), 0)
    # 边缘区域（alpha 在 0-255 之间）用模糊值
    edge = (alpha > 0) & (alpha < 255)
    bgra[edge, 3] = alpha_blur[edge].astype(np.uint8)

    return bgra


def main():
    parser = argparse.ArgumentParser(description='从物品合图中抠出单个物品图标')
    parser.add_argument('image', help='输入图片路径')
    parser.add_argument('output_dir', nargs='?', default=None, help='输出目录（默认在图片同目录下创建 items/）')
    parser.add_argument('--padding', type=float, default=0.1, help='物品周围的 padding 比例（默认 0.1）')
    parser.add_argument('--threshold', type=int, default=240, help='白色背景阈值 0-255（默认 240）')
    parser.add_argument('--min-area', type=int, default=2000, help='最小轮廓面积（默认 2000）')
    parser.add_argument('--names', nargs='+', default=None,
                        help='物品名称列表（按顺序），不指定则自动编号')
    args = parser.parse_args()

    img = cv2.imread(args.image)
    if img is None:
        print(f'错误: 无法读取图片 {args.image}')
        sys.exit(1)

    # 输出目录
    if args.output_dir is None:
        img_dir = os.path.dirname(os.path.abspath(args.image))
        args.output_dir = os.path.join(img_dir, 'items')
    os.makedirs(args.output_dir, exist_ok=True)

    print(f'图片尺寸: {img.shape[1]}x{img.shape[0]}')
    print(f'白色背景阈值: {args.threshold}')
    print(f'最小面积: {args.min_area}')

    boxes = detect_items(img, threshold=args.threshold, min_area=args.min_area)
    print(f'检测到 {len(boxes)} 个物品区域')

    if args.names and len(args.names) != len(boxes):
        print(f'警告: 名称数量({len(args.names)})与检测数量({len(boxes)})不匹配，使用自动编号')

    for i, box in enumerate(boxes):
        if args.names and i < len(args.names):
            name = args.names[i]
        else:
            name = f'item_{i+1:02d}'

        result = crop_and_remove_bg(img, box, padding=args.padding)
        out_path = os.path.join(args.output_dir, f'{name}.png')
        cv2.imwrite(out_path, result)

        x, y, w, h = box
        print(f'  [{i+1:2d}] {name:20s} → {out_path}  (位置: {x},{y} 尺寸: {w}x{h})')

    print(f'\n完成！共导出 {len(boxes)} 个物品到 {args.output_dir}')


if __name__ == '__main__':
    main()
