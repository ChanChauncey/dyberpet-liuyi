"""BiRefNet 批量抠图——毛发级精度。

使用 rembg (BiRefNet-general ONNX) 进行逐帧抠图。
只处理精灵图需要的帧（不是全部帧），节省时间。

用法：
    python tools/birefnet_mask.py
"""

from pathlib import Path

from PIL import Image
from rembg import new_session, remove

ROOT = Path(r"D:\Claude专用\桌面宠物")
FRAMES_DIR = ROOT / "data" / "pipeline" / "frames"
RGBA_DIR = ROOT / "data" / "pipeline" / "rgba"


def select_frames(files: list, start: int, end: int, step: int = 1) -> list:
    return files[start:end:step]


def process_action(action: str, frame_indices: list):
    """处理一个动作的指定帧索引。"""
    all_frames = sorted((FRAMES_DIR / action).glob("*.png"))
    out_dir = RGBA_DIR / action
    out_dir.mkdir(parents=True, exist_ok=True)

    # 清旧文件
    for old in out_dir.glob("*_rgba.png"):
        old.unlink()

    session = new_session("birefnet-general")
    total = len(frame_indices)

    for i, idx in enumerate(frame_indices):
        in_path = all_frames[idx]
        out_path = out_dir / f"{in_path.stem}_rgba.png"

        img = Image.open(in_path).convert("RGB")
        result = remove(img, session=session, alpha_matting=False)
        result.save(out_path)

        if (i + 1) % 10 == 0:
            print(f"  {action}: {i+1}/{total}")


def main():
    print("BiRefNet batch masking (only needed frames for sprites)\n")

    # stand: 73 frames (already extracted every 2nd frame)
    stand_indices = list(range(73))
    print(f"stand: {len(stand_indices)} frames")
    process_action("stand", stand_indices)

    # walk_right: 193 total, Phase 2 loop frames 48-143, every 2nd
    wr_indices = list(range(48, 144, 2))
    print(f"walk_right: {len(wr_indices)} frames (of 193)")
    process_action("walk_right", wr_indices)

    # walk_left: same
    wl_indices = list(range(48, 144, 2))
    print(f"walk_left: {len(wl_indices)} frames (of 193)")
    process_action("walk_left", wl_indices)

    # grab_fall: 217 total, 3 phases
    gf_indices = list(range(0, 72, 2)) + list(range(72, 144, 2)) + list(range(144, 217, 2))
    print(f"grab_fall: {len(gf_indices)} frames (of 217)")
    process_action("grab_fall", gf_indices)

    # sleep_loop: 145 frames, every 2nd → 73 frames
    sl_indices = list(range(0, 145, 2))
    print(f"sleep_loop: {len(sl_indices)} frames (of 145)")
    process_action("sleep_loop", sl_indices)

    # sleep_onset: 169 frames, every 2nd → 85 frames
    so_indices = list(range(0, 169, 2))
    print(f"sleep_onset: {len(so_indices)} frames (of 169)")
    process_action("sleep_onset", so_indices)

    # wake_up: 169 frames, every 2nd → 85 frames
    wu_indices = list(range(0, 169, 2))
    print(f"wake_up: {len(wu_indices)} frames (of 169)")
    process_action("wake_up", wu_indices)

    # stretch: 145 frames, every 2nd → 73 frames
    st_indices = list(range(0, 145, 2))
    print(f"stretch: {len(st_indices)} frames (of 145)")
    process_action("stretch", st_indices)

    print("\ndone: all actions processed")


if __name__ == "__main__":
    main()
