"""提取所有视频的帧 - 使用PIL支持中文路径"""

import cv2
from pathlib import Path
from PIL import Image

VIDEO_DIR = Path("D:/Claude专用/桌面宠物/视频生成")
FRAME_DIR = Path("D:/Claude专用/桌面宠物/data/pipeline/frames")

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
    """提取帧，使用PIL保存（支持中文路径）"""
    output_dir.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        print(f"错误：无法打开视频 {video_path}")
        return 0

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    src_fps = cap.get(cv2.CAP_PROP_FPS)
    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        out_path = output_dir / f"frame_{frame_idx:04d}.png"
        # 使用PIL保存（支持中文路径）
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        Image.fromarray(frame_rgb).save(str(out_path))
        frame_idx += 1

    cap.release()
    print(f"完成：{frame_idx} 帧（源{total_frames}帧，{src_fps:.1f}fps）")
    return frame_idx


def main():
    videos = sorted(VIDEO_DIR.glob("*.mp4"))
    print(f"找到 {len(videos)} 个视频\n")

    total = 0
    for video in videos:
        video_name = video.stem
        action_name = ACTION_MAP.get(video_name)
        if not action_name:
            print(f"跳过未知: {video_name}")
            continue

        output_dir = FRAME_DIR / action_name
        print(f"{video_name} → {action_name}...", end=" ", flush=True)
        count = extract_frames(video, output_dir)
        total += count

    print(f"\n总计：{total} 帧")


if __name__ == "__main__":
    main()
