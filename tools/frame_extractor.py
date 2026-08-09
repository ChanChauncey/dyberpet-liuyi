"""从 AI 生成的 MP4 视频中按帧提取 PNG 序列。

用法：
    python frame_extractor.py <video.mp4> <output_dir> [--every 1] [--size 640x360]

    --every N: 每 N 帧取 1 帧（默认 1，即原速提帧）
    --size WxH: resize 到指定分辨率（可选）
"""

import argparse
import sys
from pathlib import Path

import cv2
from PIL import Image
import numpy as np


def parse_size(size_str: str) -> tuple[int, int]:
    """解析 WxH 格式的尺寸字符串。"""
    parts = size_str.lower().split("x")
    if len(parts) != 2:
        raise argparse.ArgumentTypeError(f"尺寸格式错误：{size_str}，应为 WxH（如 640x360）")
    return int(parts[0]), int(parts[1])


def extract_frames(video_path: str, output_dir: str, every: int = 1, size: tuple[int, int] | None = None):
    video_path = Path(video_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        print(f"错误：无法打开视频 {video_path}")
        sys.exit(1)

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    src_fps = cap.get(cv2.CAP_PROP_FPS)
    src_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    src_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frame_idx = 0
    saved_idx = 0

    if size:
        print(f"源视频：{src_w}x{src_h} @ {src_fps:.1f}fps → resize 到 {size[0]}x{size[1]}")
    else:
        print(f"源视频：{src_w}x{src_h} @ {src_fps:.1f}fps")

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_idx % every == 0:
            if size:
                frame = cv2.resize(frame, size, interpolation=cv2.INTER_AREA)
            out_path = output_dir / f"frame_{saved_idx:04d}.png"
            # 使用 PIL 保存以支持中文路径
            img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            img.save(str(out_path))
            saved_idx += 1
        frame_idx += 1

    cap.release()
    effective_fps = src_fps / every if every > 0 else src_fps
    print(f"完成：{saved_idx} 帧提取自 {total_frames} 总帧 → {output_dir}")
    print(f"采样间隔：every={every}，有效帧率：{effective_fps:.1f}fps")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="从视频提取 PNG 帧序列")
    parser.add_argument("video", help="输入 MP4 文件路径")
    parser.add_argument("output", help="输出目录")
    parser.add_argument("--every", type=int, default=1, help="每 N 帧取 1 帧（默认 1）")
    parser.add_argument("--size", type=parse_size, default=None, help="resize 到 WxH（如 640x360）")
    args = parser.parse_args()

    extract_frames(args.video, args.output, args.every, args.size)
