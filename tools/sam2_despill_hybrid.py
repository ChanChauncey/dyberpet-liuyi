"""方案B：sam2_mask 提供 alpha + birefnet_despill 强力去绿。

流程：
1. sam2_mask 的软色键 + 引导滤波生成高质量 alpha
2. birefnet_despill 的强力 despill 去绿边（含灰色过渡）
3. 合成 RGBA 输出

用法：
    python sam2_despill_hybrid.py <frames_dir> <output_dir>
    python sam2_despill_hybrid.py <frames_dir> <output_dir> --bg-threshold 20 --fg-threshold 80
"""

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

# 从 sam2_mask 导入核心函数
sys.path.insert(0, str(Path(__file__).parent))
from sam2_mask import sample_bg_color, soft_key, guided_filter, cleanup_alpha


def despill_strong(frame_bgr: np.ndarray, alpha: np.ndarray, strength: float = 0.8) -> np.ndarray:
    """强力去绿溢——来自 birefnet_despill 的策略。

    1. 边缘区域检测（alpha 0.05~0.95）
    2. 绿色过剩压制（alpha 越低压制越狠）
    3. 接近透明区域向灰色过渡（模拟环境光吸收）
    """
    f = frame_bgr.astype(np.float32)
    result = f.copy()

    # 边缘区域（半透明）
    edge_mask = (alpha > 0.05) & (alpha < 0.95)
    if not edge_mask.any():
        return frame_bgr

    # 绿色过剩 = G - max(B, R)
    green_excess = f[:, :, 1] - np.maximum(f[:, :, 0], f[:, :, 2])

    # 只在绿色确实过剩的区域处理
    spill_mask = edge_mask & (green_excess > 3.0)
    if spill_mask.any():
        cy, cx = np.where(spill_mask)
        excess = green_excess[cy, cx]
        # alpha 越低（越透明），绿溢越多，压制更强
        edge_factor = 1.0 - alpha[cy, cx]
        reduction = excess * strength * edge_factor
        result[cy, cx, 1] -= reduction

    # 额外：在接近透明的区域，降低整体亮度（模拟环境光吸收）
    very_edge = (alpha > 0.01) & (alpha < 0.3)
    if very_edge.any():
        vy, vx = np.where(very_edge)
        fade = alpha[vy, vx] / 0.3  # 0~1
        for c in range(3):
            result[vy, vx, c] = result[vy, vx, c] * fade + (1 - fade) * 128  # 向灰色过渡

    return np.clip(result, 0, 255).astype(np.uint8)


def despill_edge_gray(
    frame_bgr: np.ndarray,
    alpha: np.ndarray,
    strength: float = 0.9,
) -> np.ndarray:
    """边缘去绿——只动半透明区域，G 直接压到 min(B,R)。

    - alpha > 0.8（猫主体）：完全不动
    - alpha 0.01~0.8（边缘毛发）：G = min(B,R)
    """
    f = frame_bgr.astype(np.float32)
    result = f.copy()

    # 绿色过剩 = G - max(B, R)
    green_excess = f[:, :, 1] - np.maximum(f[:, :, 0], f[:, :, 2])

    # 处理边缘：alpha 0.01~0.8 + 有绿色过剩
    edge_mask = (alpha > 0.01) & (alpha < 0.8) & (green_excess > 0.5)
    if not edge_mask.any():
        return frame_bgr

    ey, ex = np.where(edge_mask)
    r_ch = f[ey, ex, 0]
    g_ch = f[ey, ex, 1]
    b_ch = f[ey, ex, 2]
    a = alpha[ey, ex]

    # G 目标 = min(B, R) — 直接压绿
    target_g = np.minimum(b_ch, r_ch)

    # 边缘像素 G 通道直接设为 min(B,R)，不混合
    result[ey, ex, 1] = target_g

    return np.clip(result, 0, 255).astype(np.uint8)


def process_frame(
    frame: np.ndarray,
    bg_color: np.ndarray,
    bg_threshold: float = 20.0,
    fg_threshold: float = 80.0,
    gf_radius: int = 8,
    gf_eps: float = 1e-5,
    despill_strength: float = 0.8,
) -> np.ndarray:
    """处理单帧：sam2 alpha + 边缘灰色去绿。"""
    h, w = frame.shape[:2]

    # Step 1: 软色键 → 连续 alpha
    alpha = soft_key(frame, bg_color, bg_threshold, fg_threshold)

    # Step 2: 引导滤波 → 边缘感知平滑
    guide = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
    alpha = guided_filter(guide, alpha, radius=gf_radius, eps=gf_eps)
    alpha = np.clip(alpha, 0.0, 1.0)

    # Step 3: 形态学清理
    alpha = cleanup_alpha(alpha)

    # Step 4: 边缘去绿——三通道拉向灰色
    frame_clean = despill_edge_gray(frame, alpha, strength=despill_strength)

    # Step 5: 合成 RGBA
    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    rgba[:, :, :3] = frame_clean
    rgba[:, :, 3] = (alpha * 255).astype(np.uint8)

    return rgba


def process_frames(
    frames_dir: str,
    output_dir: str,
    bg_threshold: float = 20.0,
    fg_threshold: float = 80.0,
    gf_radius: int = 8,
    gf_eps: float = 1e-5,
    despill_strength: float = 0.8,
):
    """批量处理帧目录。"""
    frames_dir = Path(frames_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    png_files = sorted(frames_dir.glob("*.png"))
    if not png_files:
        print(f"错误：{frames_dir} 中无 PNG 文件")
        sys.exit(1)

    # 从第一帧采样背景色
    first = cv2.imread(str(png_files[0]))
    if first is None:
        print("错误：无法读取第一帧")
        sys.exit(1)

    bg_color = sample_bg_color(first)
    print(f"背景色: BGR=({bg_color[0]:.0f}, {bg_color[1]:.0f}, {bg_color[2]:.0f})")

    total = len(png_files)

    for i, png_path in enumerate(png_files):
        frame = cv2.imread(str(png_path))
        if frame is None:
            continue

        rgba = process_frame(
            frame, bg_color,
            bg_threshold=bg_threshold,
            fg_threshold=fg_threshold,
            gf_radius=gf_radius,
            gf_eps=gf_eps,
            despill_strength=despill_strength,
        )

        out_path = output_dir / f"{png_path.stem}_rgba.png"
        cv2.imwrite(str(out_path), rgba)

        if (i + 1) % 50 == 0:
            print(f"  {i+1}/{total}")

    print(f"完成: {total} 帧 → {output_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="sam2 alpha + 强力 despill")
    parser.add_argument("frames", help="输入帧 PNG 目录")
    parser.add_argument("output", help="输出 RGBA PNG 目录")
    parser.add_argument("--bg-threshold", type=float, default=20.0)
    parser.add_argument("--fg-threshold", type=float, default=80.0)
    parser.add_argument("--gf-radius", type=int, default=8)
    parser.add_argument("--gf-eps", type=float, default=1e-5)
    parser.add_argument("--despill", type=float, default=0.8, help="去绿强度 0~1（默认 0.8）")
    args = parser.parse_args()

    process_frames(
        args.frames, args.output,
        bg_threshold=args.bg_threshold,
        fg_threshold=args.fg_threshold,
        gf_radius=args.gf_radius,
        gf_eps=args.gf_eps,
        despill_strength=args.despill,
    )
