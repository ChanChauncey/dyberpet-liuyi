"""绿幕抠图管线——软色键 + 引导滤波 + 去绿溢。

针对猫毛边缘优化：色键生成连续 alpha → 引导滤波保边缘 → 去绿溢。

用法：
    python sam2_mask.py <frames_dir> <output_dir>
    python sam2_mask.py <frames_dir> <output_dir> --bg-threshold 20 --fg-threshold 80

管线：
1. 四角+底中采样背景绿色（每帧独立）
2. RGB 欧氏距离 → smoothstep 生成连续 alpha（0.0~1.0）
3. 引导滤波：边缘感知平滑，保留毛发细节
4. 去绿溢：半透明区域压制绿色通道
5. 形态学后处理：去零星噪点
6. 合成 RGBA PNG
"""

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image


def sample_bg_color(frame: np.ndarray) -> np.ndarray:
    """从四角+底部中央采样绿色背景。"""
    h, w = frame.shape[:2]
    m = 10
    corners = [
        frame[0:m, 0:m],
        frame[0:m, w - m : w],
        frame[h - m : h, 0:m],
        frame[h - m : h, w - m : w],
        frame[h - m : h, w // 2 - m // 2 : w // 2 + m // 2],
    ]
    samples = np.vstack([c.reshape(-1, 3) for c in corners])
    return samples.mean(axis=0).astype(np.float32)


def smoothstep(x: np.ndarray) -> np.ndarray:
    """Hermite smoothstep: 3x² - 2x³, clamps [0,1]."""
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)


def guided_filter(I: np.ndarray, p: np.ndarray, radius: int = 8, eps: float = 1e-5) -> np.ndarray:
    """引导滤波——边缘感知平滑。

    Args:
        I: 引导图 (单通道, float32, [0,1])
        p: 待滤波图 (单通道, float32, [0,1])
        radius: 滤波半径
        eps: 正则化系数

    Returns:
        滤波后图像 q
    """
    I = I.astype(np.float32)
    p = p.astype(np.float32)

    ksize = (radius * 2 + 1, radius * 2 + 1)
    mean_I = cv2.blur(I, ksize)
    mean_p = cv2.blur(p, ksize)
    corr_I = cv2.blur(I * I, ksize)
    corr_Ip = cv2.blur(I * p, ksize)

    var_I = corr_I - mean_I * mean_I
    cov_Ip = corr_Ip - mean_I * mean_p

    a = cov_Ip / (var_I + eps)
    b = mean_p - a * mean_I

    mean_a = cv2.blur(a, ksize)
    mean_b = cv2.blur(b, ksize)

    q = mean_a * I + mean_b
    return q


def despill(frame: np.ndarray, alpha: np.ndarray, strength: float = 0.6) -> tuple[np.ndarray, np.ndarray]:
    """去绿溢+去蓝边+去影子——只限制通道，不改变原始颜色。

    核心思路：只在半透明边缘区域做通道限制（G不超过max(B,R)），主体完全不动。
    """
    f = frame.astype(np.float32)
    result = f.copy()
    alpha_result = alpha.copy()
    h, w = f.shape[:2]

    # ========== 步骤1：边缘通道限制（只处理半透明区域） ==========
    edge_mask = (alpha_result > 0.01) & (alpha_result < 0.8)
    if edge_mask.any():
        # 绿色过剩 → 压制到 max(B,R)+1
        green_excess = result[:, :, 1] - np.maximum(result[:, :, 0], result[:, :, 2])
        green_spill = edge_mask & (green_excess > 2.0)
        if green_spill.any():
            gy, gx = np.where(green_spill)
            max_br = np.maximum(result[gy, gx, 0], result[gy, gx, 2])
            result[gy, gx, 1] = np.minimum(result[gy, gx, 1], max_br + 1)

        # 蓝色过剩 → 压制到 max(G,R)+1
        blue_excess = result[:, :, 0] - np.maximum(result[:, :, 1], result[:, :, 2])
        blue_spill = edge_mask & (blue_excess > 2.0)
        if blue_spill.any():
            by, bx = np.where(blue_spill)
            max_gr = np.maximum(result[by, bx, 1], result[by, bx, 2])
            result[by, bx, 0] = np.minimum(result[by, bx, 0], max_gr + 1)

    # ========== 步骤2：主体区域绿色通道压制 ==========
    body_mask = alpha_result > 0.8
    if body_mask.any():
        body_pixels = result[body_mask]
        g, r, b = body_pixels[:,1], body_pixels[:,2], body_pixels[:,0]
        max_rb = np.maximum(r, b)
        green_excess = g > max_rb + 2
        if green_excess.any():
            body_pixels[green_excess, 1] = max_rb[green_excess] + 1
            result[body_mask] = body_pixels

    # ========== 步骤3：自动检测并清除底部影子 ==========
    bottom_y = 0
    for y in range(h - 1, 0, -1):
        if alpha_result[y, :].max() > 0.5:
            bottom_y = y
            break

    if bottom_y > 0:
        below_mask = np.zeros((h, w), dtype=bool)
        below_mask[bottom_y:, :] = True
        alpha_result[below_mask & (alpha_result < 0.8)] = 0.0

    return np.clip(result, 0, 255).astype(np.uint8), alpha_result


def soft_key(
    frame: np.ndarray,
    bg_color: np.ndarray,
    bg_threshold: float = 20.0,
    fg_threshold: float = 80.0,
) -> np.ndarray:
    """软色键——组合绿色优势+RGB距离，适配各种绿幕。

    对高饱和绿幕用绿色优势，对低饱和/偏色背景用RGB距离。
    """
    f = frame.astype(np.float32)

    # 方法1：绿色优势 = G - max(R, B)
    green_dominance = f[:, :, 1] - np.maximum(f[:, :, 0], f[:, :, 2])

    # 方法2：RGB欧氏距离
    diff = f - bg_color
    rgb_dist = np.sqrt(np.sum(diff ** 2, axis=2))

    # 根据背景绿色优势选择主方法
    bg_green_dom = bg_color[1] - max(bg_color[0], bg_color[2])

    if bg_green_dom > 50:
        # 高饱和绿幕：用绿色优势（更精准）
        auto_bg_thresh = bg_green_dom * 0.6
        auto_fg_thresh = bg_green_dom * 0.15
    else:
        # 低饱和/偏色背景：仍用绿色优势，但降低阈值
        auto_bg_thresh = bg_green_dom * 0.5
        auto_fg_thresh = bg_green_dom * 0.1

    # 映射到 alpha：绿色优势大 → alpha=0（背景）
    t = (auto_bg_thresh - green_dominance) / (auto_bg_thresh - auto_fg_thresh)
    alpha = smoothstep(np.clip(t, 0.0, 1.0))
    return alpha.astype(np.float32)


def cleanup_alpha(alpha: np.ndarray, open_size: int = 3, close_size: int = 5) -> np.ndarray:
    """形态学清理——去零星噪点、填小空洞。

    Args:
        alpha: (float32, [0,1])
        open_size: 开运算核大小（去噪点）
        close_size: 闭运算核大小（填空洞）

    Returns:
        清理后的 alpha (float32, [0,1])
    """
    alpha_u8 = (alpha * 255).astype(np.uint8)
    ko = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (open_size, open_size))
    kc = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (close_size, close_size))

    # 开运算去噪点
    alpha_u8 = cv2.morphologyEx(alpha_u8, cv2.MORPH_OPEN, ko)
    # 闭运算填空洞
    alpha_u8 = cv2.morphologyEx(alpha_u8, cv2.MORPH_CLOSE, kc)

    return alpha_u8.astype(np.float32) / 255.0


def process_frame(
    frame: np.ndarray,
    bg_color: np.ndarray,
    bg_threshold: float = 20.0,
    fg_threshold: float = 80.0,
    gf_radius: int = 8,
    gf_eps: float = 1e-5,
    despill_strength: float = 0.6,
) -> np.ndarray:
    """处理单帧——完整抠图管线。

    Args:
        frame: BGR 图像 (uint8)
        bg_color: 采样背景绿色 BGR
        bg_threshold: 纯背景距离阈值
        fg_threshold: 纯前景距离阈值
        gf_radius: 引导滤波半径
        gf_eps: 引导滤波正则化
        despill_strength: 去绿溢强度

    Returns:
        RGBA 图像 (uint8, H×W×4)
    """
    h, w = frame.shape[:2]

    # Step 1: 软色键 → 连续 alpha
    alpha = soft_key(frame, bg_color, bg_threshold, fg_threshold)

    # Step 2: 引导滤波 → 边缘感知平滑
    guide = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
    alpha = guided_filter(guide, alpha, radius=gf_radius, eps=gf_eps)
    alpha = np.clip(alpha, 0.0, 1.0)

    # Step 3: 形态学清理
    alpha = cleanup_alpha(alpha)

    # Step 3.5: 清除低alpha像素（去掉边缘的"脏"半透明像素）
    alpha[alpha < 0.15] = 0.0

    # Step 4: 去绿溢+去蓝边+去影子
    frame_clean, alpha_clean = despill(frame, alpha, strength=despill_strength)

    # Step 5: 合成 RGBA
    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    rgba[:, :, :3] = frame_clean
    rgba[:, :, 3] = (alpha_clean * 255).astype(np.uint8)

    # 清除背景像素（alpha=0）的RGB值，避免绿色残留
    bg_mask = alpha_clean < 0.01
    rgba[bg_mask, :3] = 0

    return rgba


def process_frames(
    frames_dir: str,
    output_dir: str,
    bg_threshold: float = 20.0,
    fg_threshold: float = 80.0,
    gf_radius: int = 8,
    gf_eps: float = 1e-5,
    despill_strength: float = 0.6,
):
    """批量处理帧目录。"""
    frames_dir = Path(frames_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    png_files = sorted(frames_dir.glob("*.png"))
    if not png_files:
        print(f"错误：{frames_dir} 中无 PNG 文件")
        sys.exit(1)

    # 从第一帧采样背景色（用于初始验证）
    # 使用 PIL 读取以支持中文路径
    first_pil = Image.open(str(png_files[0]))
    first = cv2.cvtColor(np.array(first_pil), cv2.COLOR_RGB2BGR)
    if first is None:
        print("错误：无法读取第一帧")
        sys.exit(1)

    bg_color = sample_bg_color(first)
    print(f"初始背景色: BGR=({bg_color[0]:.0f}, {bg_color[1]:.0f}, {bg_color[2]:.0f})"
          f"  RGB=({bg_color[2]:.0f}, {bg_color[1]:.0f}, {bg_color[0]:.0f})")

    # 验证色键质量
    h, w = first.shape[:2]
    diff = first.astype(np.float32) - bg_color
    dist = np.sqrt(np.sum(diff ** 2, axis=2))

    # 猫中心区域距离
    cat_region = dist[h // 2 - 40 : h // 2 + 40, w // 2 - 40 : w // 2 + 40]
    # 背景角区域距离
    bg_region = dist[5:35, 5:35]
    # 边缘过渡
    edge_row = dist[h // 2, :]
    nonzero = np.where(edge_row >= bg_threshold)[0]

    print(f"猫中心距离: min={cat_region.min():.0f} median={np.median(cat_region):.0f} max={cat_region.max():.0f}")
    print(f"背景角距离: min={bg_region.min():.0f} median={np.median(bg_region):.0f} max={bg_region.max():.0f}")
    print(f"安全余量: {cat_region.min() - bg_region.max():.0f}")

    if len(nonzero) > 0:
        ex = nonzero[0]
        edge_dists = [f"{edge_row[max(0, ex - 3 + i)]:.0f}" for i in range(min(9, w - max(0, ex - 3)))]
        print(f"边缘过渡距离: {edge_dists}")
        print(f"过渡宽度: ~{len([d for d in edge_dists if float(d) > bg_threshold and float(d) < fg_threshold])}px")

    total = len(png_files)
    semitransparent_total = 0
    fg_total = 0

    for i, png_path in enumerate(png_files):
        # 使用 PIL 读取以支持中文路径
        try:
            frame_pil = Image.open(str(png_path))
            frame = cv2.cvtColor(np.array(frame_pil), cv2.COLOR_RGB2BGR)
        except Exception as e:
            print(f"警告：无法读取 {png_path}: {e}")
            continue

        # 每帧独立采样背景色（处理绿幕光照不均匀）
        frame_bg = sample_bg_color(frame)

        rgba = process_frame(
            frame, frame_bg,
            bg_threshold=bg_threshold,
            fg_threshold=fg_threshold,
            gf_radius=gf_radius,
            gf_eps=gf_eps,
            despill_strength=despill_strength,
        )

        # 统计半透明像素（毛发边缘质量指标）
        alpha = rgba[:, :, 3]
        semi = ((alpha > 0) & (alpha < 255)).sum()
        fg = (alpha > 0).sum()
        semitransparent_total += semi
        fg_total += fg

        out_path = output_dir / f"{png_path.stem}_rgba.png"
        # 使用 PIL 保存以支持中文路径（BGR→RGB 转换）
        rgba_rgb = cv2.cvtColor(rgba, cv2.COLOR_BGRA2RGBA)
        rgba_pil = Image.fromarray(rgba_rgb)
        rgba_pil.save(str(out_path))

        if (i + 1) % 50 == 0:
            print(f"  {i+1}/{total}")

    avg_semi_pct = 100 * semitransparent_total / max(fg_total, 1)
    print(f"完成: {total} 帧 → {output_dir}")
    print(f"平均半透明像素: {avg_semi_pct:.1f}%（毛发边缘质量指标，越高越细腻）")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="绿幕抠图——软色键 + 引导滤波 + 去绿溢")
    parser.add_argument("frames", help="输入帧 PNG 目录")
    parser.add_argument("output", help="输出 RGBA PNG 目录")
    parser.add_argument("--bg-threshold", type=float, default=20.0,
                        help="纯背景距离阈值（默认 20）")
    parser.add_argument("--fg-threshold", type=float, default=80.0,
                        help="纯前景距离阈值（默认 80）")
    parser.add_argument("--gf-radius", type=int, default=8,
                        help="引导滤波半径（默认 8）")
    parser.add_argument("--gf-eps", type=float, default=1e-5,
                        help="引导滤波正则化（默认 1e-5）")
    parser.add_argument("--despill", type=float, default=0.6,
                        help="去绿溢强度 0~1（默认 0.6）")
    args = parser.parse_args()

    process_frames(
        args.frames, args.output,
        bg_threshold=args.bg_threshold,
        fg_threshold=args.fg_threshold,
        gf_radius=args.gf_radius,
        gf_eps=args.gf_eps,
        despill_strength=args.despill,
    )
