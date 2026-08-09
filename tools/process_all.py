"""全流程：sam2_mask 提取 alpha + 绿色变灰色。

对 data/pipeline/frames/ 下所有动作目录执行：
1. sam2_mask.py 生成 RGBA
2. 绿色过剩像素 G = (B+R)/2

用法：
    python tools/process_all.py
"""

import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from sam2_mask import sample_bg_color, soft_key, guided_filter, cleanup_alpha

ROOT = Path(r"D:\Claude专用\桌面宠物")
FRAMES_DIR = ROOT / "data" / "pipeline" / "frames"
OUTPUT_DIR = ROOT / "data" / "pipeline" / "rgba"


def process_frame(frame, bg_color):
    """sam2 alpha + 绿色变灰色。"""
    h, w = frame.shape[:2]

    # sam2_mask 核心流程
    alpha = soft_key(frame, bg_color, bg_threshold=20.0, fg_threshold=80.0)
    guide = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
    alpha = guided_filter(guide, alpha, radius=8, eps=1e-5)
    alpha = np.clip(alpha, 0.0, 1.0)
    alpha = cleanup_alpha(alpha)

    # 绿色变灰色
    f = frame.astype(np.float32)
    green_excess = f[:, :, 1] - np.maximum(f[:, :, 0], f[:, :, 2])
    mask = (green_excess > 0) & (alpha > 0.01)
    if mask.any():
        y, x = np.where(mask)
        f[y, x, 1] = (f[y, x, 0] + f[y, x, 2]) / 2.0

    # 合成 RGBA
    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    rgba[:, :, :3] = np.clip(f, 0, 255).astype(np.uint8)
    rgba[:, :, 3] = (alpha * 255).astype(np.uint8)
    return rgba


def read_image_pil(path):
    """用 PIL 读取图片（支持中文路径），返回 BGR numpy 数组。"""
    img = Image.open(path).convert("RGB")
    arr = np.array(img)
    return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)


def write_image_pil(path, rgba):
    """用 PIL 保存 RGBA 图片（支持中文路径）。"""
    Image.fromarray(cv2.cvtColor(rgba[:, :, :3], cv2.COLOR_BGR2RGB)).save(
        path, alpha=Image.fromarray(rgba[:, :, 3])
    )


def process_action(action_name):
    """处理一个动作目录。"""
    frames_dir = FRAMES_DIR / action_name
    out_dir = OUTPUT_DIR / action_name
    out_dir.mkdir(parents=True, exist_ok=True)

    png_files = sorted(frames_dir.glob("*.png"))
    if not png_files:
        print(f"  跳过 {action_name}：无 PNG 文件")
        return

    # 从第一帧采样背景色
    first = read_image_pil(png_files[0])
    bg_color = sample_bg_color(first)

    total = len(png_files)
    for i, f in enumerate(png_files):
        frame = read_image_pil(f)
        rgba = process_frame(frame, bg_color)

        # 用 PIL 保存（支持中文路径）
        out_path = out_dir / f"{f.stem}_rgba.png"
        rgba_rgb = cv2.cvtColor(rgba[:, :, :3], cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgba_rgb, "RGB")
        pil_alpha = Image.fromarray(rgba[:, :, 3], "L")
        pil_img.putalpha(pil_alpha)
        pil_img.save(str(out_path))

        if (i + 1) % 50 == 0 or (i + 1) == total:
            print(f"  {action_name}: {i+1}/{total}")

    print(f"  {action_name}: 完成 {total} 帧 → {out_dir}")


def main():
    actions = [
        "stand", "grab_start", "grab_loop", "fall", "land",
        "walk_left", "walk_right", "sleep_onset", "sleep_loop", "wake_up",
    ]

    print("=" * 50)
    print("全流程处理：sam2 alpha + 绿色变灰色")
    print("=" * 50)

    for action in actions:
        print(f"\n处理 {action}...")
        process_action(action)

    print("\n" + "=" * 50)
    print("全部完成")
    print("=" * 50)


if __name__ == "__main__":
    main()
