"""
用 rembg 语义分割抠出物品合图中的单个物品，输出为透明背景正方形 PNG。
策略：按行切割 → 逐行 rembg → 检测单个物品 → 输出
用法: python cut_items_rembg.py <图片路径> [输出目录] [--names ...]
"""

import cv2
import numpy as np
import os
import sys
import argparse
from rembg import remove
from PIL import Image
import io


def remove_background(img_path):
    """用 rembg 去背景"""
    with open(img_path, 'rb') as f:
        input_data = f.read()
    output_data = remove(input_data)
    pil_img = Image.open(io.BytesIO(output_data)).convert('RGBA')
    return np.array(pil_img)


def remove_background_from_array(bgr):
    """从 numpy 数组去背景"""
    pil_img = Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
    buf = io.BytesIO()
    pil_img.save(buf, format='PNG')
    output_data = remove(buf.getvalue())
    result = Image.open(io.BytesIO(output_data)).convert('RGBA')
    return np.array(result)


def detect_items(alpha, min_area=2000):
    """从 alpha 通道检测物品区域"""
    binary = (alpha > 20).astype(np.uint8) * 255

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=3)
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


def crop_square(bgra, box, padding=0.15):
    """裁剪物品为正方形，保留透明通道"""
    x, y, w, h = box
    ih, iw = bgra.shape[:2]

    pad_x = int(w * padding)
    pad_y = int(h * padding)
    x1 = max(0, x - pad_x)
    y1 = max(0, y - pad_y)
    x2 = min(iw, x + w + pad_x)
    y2 = min(ih, y + h + pad_y)

    crop = bgra[y1:y2, x1:x2].copy()
    ch, cw = crop.shape[:2]
    size = max(cw, ch)
    square = np.zeros((size, size, 4), dtype=np.uint8)
    ox = (size - cw) // 2
    oy = (size - ch) // 2
    square[oy:oy+ch, ox:ox+cw] = crop
    return square


def split_rows(img, row_gap_threshold=80):
    """根据 y 坐标间隙将物品分组为行"""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 245, 255, cv2.THRESH_BINARY_INV)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=3)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    items = []
    for c in contours:
        if cv2.contourArea(c) >= 1000:
            x, y, w, h = cv2.boundingRect(c)
            items.append((x, y, w, h))
    items.sort(key=lambda b: b[1])

    if not items:
        return []

    # 按 y 坐标间隙分行
    rows = []
    current_row = [items[0]]
    for item in items[1:]:
        if item[1] - current_row[-1][1] > row_gap_threshold:
            rows.append(current_row)
            current_row = [item]
        else:
            current_row.append(item)
    rows.append(current_row)
    return rows


def main():
    parser = argparse.ArgumentParser(description='用 rembg 逐行抠出物品合图中的单个物品')
    parser.add_argument('image', help='输入图片路径')
    parser.add_argument('output_dir', nargs='?', default=None, help='输出目录')
    parser.add_argument('--padding', type=float, default=0.15, help='物品周围 padding（默认 0.15）')
    parser.add_argument('--min-area', type=int, default=2000, help='最小轮廓面积（默认 2000）')
    parser.add_argument('--names', nargs='+', default=None, help='物品名称列表（按顺序）')
    args = parser.parse_args()

    if not os.path.exists(args.image):
        print(f'错误: 文件不存在 {args.image}')
        sys.exit(1)

    if args.output_dir is None:
        img_dir = os.path.dirname(os.path.abspath(args.image))
        args.output_dir = os.path.join(img_dir, 'items_rembg')
    os.makedirs(args.output_dir, exist_ok=True)

    img = cv2.imread(args.image)
    if img is None:
        print(f'错误: 无法读取图片 {args.image}')
        sys.exit(1)

    print(f'图片尺寸: {img.shape[1]}x{img.shape[0]}')

    # 按 y 坐标分行（不切割图片，只记录每行的 y 范围）
    rows = split_rows(img)
    print(f'检测到 {len(rows)} 行物品')

    all_boxes = []
    for row_idx, row_items in enumerate(rows):
        # 计算行的 y 范围（留 padding）
        y_min = min(item[1] for item in row_items) - 20
        y_max = max(item[1] + item[3] for item in row_items) + 20
        y_min = max(0, y_min)
        y_max = min(img.shape[0], y_max)

        # 切割行
        row_img = img[y_min:y_max, :]
        row_path = os.path.join(args.output_dir, f'_row_{row_idx}.png')
        cv2.imwrite(row_path, row_img)

        print(f'  Row {row_idx+1}: 处理 {len(row_items)} 个物品 (y={y_min}-{y_max})...')
        row_bgra = remove_background_from_array(row_img)

        # 保存行去背图（调试）
        row_rembg_path = os.path.join(args.output_dir, f'_row_{row_idx}_rembg.png')
        cv2.imwrite(row_rembg_path, cv2.cvtColor(row_bgra, cv2.COLOR_RGBA2BGRA))

        # 检测物品
        alpha = row_bgra[:, :, 3]
        boxes = detect_items(alpha, min_area=args.min_area)
        print(f'    检测到 {len(boxes)} 个物品')

        for bx, by, bw, bh in boxes:
            # 转换回全局坐标
            all_boxes.append((bx, by + y_min, bw, bh))

        # 清理临时文件
        os.remove(row_path)

    print(f'\n总计检测到 {len(all_boxes)} 个物品')
    all_boxes.sort(key=lambda b: (b[1], b[0]))

    # 去背整图用于最终裁剪
    print('正在对整图做最终去背...')
    full_bgra = remove_background(args.image)

    if args.names and len(args.names) != len(all_boxes):
        print(f'警告: 名称数量({len(args.names)})与检测数量({len(all_boxes)})不匹配，使用自动编号')

    for i, box in enumerate(all_boxes):
        if args.names and i < len(args.names):
            name = args.names[i]
        else:
            name = f'item_{i+1:02d}'

        result = crop_square(full_bgra, box, padding=args.padding)
        out_path = os.path.join(args.output_dir, f'{name}.png')
        cv2.imwrite(out_path, cv2.cvtColor(result, cv2.COLOR_RGBA2BGRA))

        x, y, w, h = box
        print(f'  [{i+1:2d}] {name:20s} → {out_path}  (位置: {x},{y} 尺寸: {w}x{h})')

    # 清理临时行图
    for f in os.listdir(args.output_dir):
        if f.startswith('_row_'):
            os.remove(os.path.join(args.output_dir, f))

    print(f'\n完成！共导出 {len(all_boxes)} 个物品到 {args.output_dir}')


if __name__ == '__main__':
    main()
