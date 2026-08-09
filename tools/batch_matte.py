"""批量抠图脚本 - 处理视频生成目录下的所有视频"""

import sys
import os
from pathlib import Path
import subprocess
import time

# 配置
VIDEO_DIR = Path("D:/Claude专用/桌面宠物/视频生成")
FRAME_DIR = Path("D:/Claude专用/桌面宠物/data/pipeline/frames")
RGBA_DIR = Path("D:/Claude专用/桌面宠物/data/pipeline/rgba")
PYTHON = "D:/Python/python.exe"

# 动作名映射（视频文件名 → 动作名）
ACTION_MAP = {
    "动作0 待机": "stand",
    "动作1 抓取": "grab_start",
    "动作2 悬挂": "grab_loop",
    "动作3 下落": "fall",
    "动作4 落地": "land",
    "动作5 向左走": "walk_left",
    "动作6 向右走": "walk_right",
    "动作7 入睡": "sleep_onset",
    "动作8 睡梦中": "sleep_loop",
    "动作9 醒来": "wake_up",
}


def extract_frames(video_path: Path, output_dir: Path):
    """从视频提取帧"""
    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        PYTHON,
        "D:/Claude专用/桌面宠物/tools/frame_extractor.py",
        str(video_path),
        str(output_dir),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  提取帧失败: {result.stderr}")
        return False
    return True


def matte_frame(frame_path: Path, output_path: Path):
    """对单帧进行抠图"""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 导入并调用 process_image
    sys.path.insert(0, "D:/Claude专用/桌面宠物/tools")
    from matte_anything import process_image

    process_image(str(frame_path), str(output_path))


def process_video(video_name: str):
    """处理单个视频"""
    video_path = VIDEO_DIR / f"{video_name}.mp4"
    if not video_path.exists():
        print(f"视频不存在: {video_path}")
        return

    # 获取动作名
    action_name = ACTION_MAP.get(video_name)
    if not action_name:
        print(f"未知动作: {video_name}")
        return

    print(f"\n{'='*60}")
    print(f"处理: {video_name} → {action_name}")
    print(f"{'='*60}")

    # 帧目录
    frame_dir = FRAME_DIR / action_name
    rgba_dir = RGBA_DIR / action_name

    # 删除旧的 RGBA 输出
    if rgba_dir.exists():
        import shutil
        shutil.rmtree(rgba_dir)
        print(f"  删除旧目录: {rgba_dir}")

    # 步骤1：提取帧
    print(f"\n步骤1: 提取帧...")
    if not extract_frames(video_path, frame_dir):
        return

    # 获取帧列表
    frames = sorted(frame_dir.glob("frame_*.png"))
    print(f"  提取了 {len(frames)} 帧")

    if len(frames) == 0:
        print(f"  警告：没有找到帧文件，跳过")
        return

    # 步骤2：逐帧抠图
    print(f"\n步骤2: 抠图处理...")
    start_time = time.time()

    for i, frame_path in enumerate(frames):
        frame_name = frame_path.stem
        output_path = rgba_dir / f"{frame_name}_rgba.png"

        print(f"  [{i+1}/{len(frames)}] {frame_name}...", end=" ", flush=True)
        matte_frame(frame_path, output_path)
        print("完成")

    elapsed = time.time() - start_time
    print(f"\n完成! 耗时: {elapsed:.1f}秒 ({elapsed/len(frames):.1f}秒/帧)")
    print(f"输出目录: {rgba_dir}")


def main():
    print("=" * 60)
    print("批量抠图 - 处理所有绿幕素材")
    print("=" * 60)

    # 列出所有视频
    videos = sorted(VIDEO_DIR.glob("*.mp4"))
    print(f"\n找到 {len(videos)} 个视频:")
    for v in videos:
        print(f"  - {v.stem}")

    # 逐个处理
    total_start = time.time()
    for video in videos:
        video_name = video.stem
        process_video(video_name)

    total_elapsed = time.time() - total_start
    print(f"\n{'='*60}")
    print(f"全部完成! 总耗时: {total_elapsed:.1f}秒")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
