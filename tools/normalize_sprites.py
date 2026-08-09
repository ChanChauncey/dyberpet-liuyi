"""精灵图归一化——用猫体质心对齐所有动作到同一锚点。

解决 stand→drag_start 过渡抖动：每帧猫的主体位置不一致。

策略：
1. 计算每帧的猫体质心（alpha 加权中心）
2. 以 stand_0 的质心为参考锚点
3. 将每帧平移，使质心对齐到参考位置
4. 统一画布尺寸（取最大尺寸）

用法：python tools/normalize_sprites.py
"""

from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(r"D:\Claude专用\桌面宠物")
ACTION_DIR = ROOT / "dyberpet" / "res" / "role" / "六一" / "action"


def cat_mass_center(arr):
    """猫体质心（alpha 加权水平/垂直中心）。"""
    alpha = arr[:, :, 3].astype(np.float64)
    total = alpha.sum()
    if total == 0:
        return arr.shape[1] // 2, arr.shape[0] // 2
    ys, xs = np.where(alpha > 0)
    weights = alpha[ys, xs]
    cx = int(np.average(xs, weights=weights))
    cy = int(np.average(ys, weights=weights))
    return cx, cy


def shift_frame(arr, dx, dy):
    """将帧平移 (dx, dy)，超出部分裁剪，空位补零。"""
    h, w = arr.shape[:2]
    new = np.zeros_like(arr)
    # 源区域
    sx0 = max(0, -dx)
    sy0 = max(0, -dy)
    sx1 = min(w, w - dx)
    sy1 = min(h, h - dy)
    # 目标区域
    dx0 = max(0, dx)
    dy0 = max(0, dy)
    dh = sy1 - sy0
    dw = sx1 - sx0
    if dh > 0 and dw > 0:
        new[dy0:dy0 + dh, dx0:dx0 + dw] = arr[sy0:sy0 + dh, sx0:sx0 + dw]
    return new


def main():
    # 1. 计算每帧质心
    frames = {}
    for f in sorted(ACTION_DIR.glob("*.png")):
        arr = np.array(Image.open(f))
        cx, cy = cat_mass_center(arr)
        frames[f.name] = (arr, cx, cy)

    # 2. stand_0 为参考锚点
    ref_cx, ref_cy = frames["stand_0.png"][1], frames["stand_0.png"][2]
    print(f"Reference (stand_0): center=({ref_cx}, {ref_cy})")

    # 3. 计算每帧需要的偏移
    shifts = {}
    for name, (arr, cx, cy) in frames.items():
        dx = ref_cx - cx
        dy = ref_cy - cy
        shifts[name] = (dx, dy)

    # 4. 计算对齐后所需的最大画布尺寸
    max_w, max_h = 0, 0
    for name, (arr, cx, cy) in frames.items():
        dx, dy = shifts[name]
        h, w = arr.shape[:2]
        new_w = w + abs(dx)
        new_h = h + abs(dy)
        max_w = max(max_w, new_w)
        max_h = max(max_h, new_h)
    print(f"Target canvas: {max_w}x{max_h}")

    # 5. 平移并对齐所有帧
    for name, (arr, cx, cy) in frames.items():
        dx, dy = shifts[name]
        if dx == 0 and dy == 0:
            shifted = arr
        else:
            shifted = shift_frame(arr, dx, dy)

        # 填充到统一画布
        h, w = shifted.shape[:2]
        if w < max_w or h < max_h:
            new = np.zeros((max_h, max_w, 4), dtype=np.uint8)
            new[:h, :w] = shifted
            shifted = new

        Image.fromarray(shifted).save(ACTION_DIR / name)

    # 6. 裁剪到 union bbox（去掉空白边缘）
    ux0, uy0, ux1, uy1 = 99999, 99999, 0, 0
    for f in ACTION_DIR.glob("*.png"):
        arr = np.array(Image.open(f))
        alpha = arr[:, :, 3]
        r = np.any(alpha > 0, axis=1)
        c = np.any(alpha > 0, axis=0)
        if r.any():
            uy0 = min(uy0, np.where(r)[0][0])
            uy1 = max(uy1, np.where(r)[0][-1])
        if c.any():
            ux0 = min(ux0, np.where(c)[0][0])
            ux1 = max(ux1, np.where(c)[0][-1])

    print(f"\nUnion bbox after alignment: ({ux0},{uy0})-({ux1},{uy1}) = "
          f"{ux1-ux0+1}x{uy1-uy0+1}")

    for f in sorted(ACTION_DIR.glob("*.png")):
        arr = np.array(Image.open(f))
        cropped = arr[uy0:uy1+1, ux0:ux1+1]
        Image.fromarray(cropped).save(f)

    # 7. 验证
    print("\nVerification:")
    for name in ["stand_0.png", "stand_35.png", "stand_72.png",
                  "drag_start_0.png", "drag_start_10.png", "drag_start_20.png",
                  "drag_start_23.png"]:
        fpath = ACTION_DIR / name
        if fpath.exists():
            arr = np.array(Image.open(fpath))
            cx, cy = cat_mass_center(arr)
            alpha = arr[:, :, 3]
            r = np.any(alpha > 0, axis=1)
            c = np.any(alpha > 0, axis=0)
            y0, y1 = np.where(r)[0][[0, -1]]
            x0, x1 = np.where(c)[0][[0, -1]]
            print(f"  {name}: center=({cx},{cy}) bbox=({x0},{y0},{x1},{y1}) "
                  f"size={arr.shape[1]}x{arr.shape[0]} "
                  f"shift=({shifts[name][0]},{shifts[name][1]})")


if __name__ == "__main__":
    main()
