"""提取所有视频的帧 - every=1 保留所有帧"""

import subprocess
from pathlib import Path

VIDEO_DIR = Path("D:/Claude专用/桌面宠物/视频生成")
FRAME_DIR = Path("D:/Claude专用/桌面宠物/data/pipeline/frames")
PYTHON = "D:/Python/python.exe"

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

def main():
    videos = sorted(VIDEO_DIR.glob("*.mp4"))
    print(f"找到 {len(videos)} 个视频\n")

    for video in videos:
        video_name = video.stem
        action_name = ACTION_MAP.get(video_name)
        if not action_name:
            print(f"跳过未知: {video_name}")
            continue

        output_dir = FRAME_DIR / action_name
        print(f"{video_name} → {action_name}...", end=" ", flush=True)

        cmd = [
            PYTHON,
            "D:/Claude专用/桌面宠物/tools/frame_extractor.py",
            str(video),
            str(output_dir),
            "--every", "1",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            # 从输出中提取帧数
            for line in result.stdout.split("\n"):
                if "完成" in line:
                    print(line)
                    break
            else:
                print("完成")
        else:
            print(f"失败: {result.stderr}")

if __name__ == "__main__":
    main()
