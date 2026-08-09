# -*- coding: utf-8 -*-
"""
build_liuyi.py — 将 Video/ 下的 17 个绿幕视频转换为「六一」桌面宠物精灵图。

修复要点（相对上一版）：
  - 上一版按「每个动作各自的包围盒」独立缩放，导致手臂上举/跳跃等“高个”动作被
    缩小、站立等“矮个”动作被放大。切换动作时身体忽大忽小（肉眼可见“卡一下然后变大”）。
  - 本版改用【全局统一缩放比例 + 全局统一偏移】：
      * 所有动作共用同一个 S（绿幕原始 1280x720 -> 640x360，S=0.5），
        角色身体在任意动作里尺寸完全一致。
      * 垂直方向保留视频里真实的相对位置（跳跃仍能离地、下落仍会掉），
        仅把“最低点”统一对齐到画布底部上方 BOTTOM_MARGIN 处（脚落地面）。
      * 水平方向按所有帧的全局中心居中，避免左右漂移。

流程：
  1. 第一遍：解码全部视频，绿幕抠像，统计全局最低点 global_foot 与全局水平中心 global_cx
  2. 第二遍：按统一 S 缩放/抠像，粘贴到 (offx, 0)，脚落在 global_foot
  3. 依据实际帧数生成 act_conf.json / pet_conf.json / info/ *

用法：
  python tools/build_liuyi.py
"""
import os, json
import numpy as np
import imageio.v2 as imageio
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VIDEO_DIR = os.path.abspath(os.path.join(ROOT, "..", "Video"))   # D:/CAT/Video
ROLE_DIR = os.path.join(ROOT, "dyberpet", "res", "role")
OUT_DIR = os.path.join(ROLE_DIR, "六一")
ACTION_DIR = os.path.join(OUT_DIR, "action")
INFO_DIR = os.path.join(OUT_DIR, "info")

# ---- 统一缩放与画布参数 ----
S = 0.5                      # 绿幕原始 1280x720 -> 640x360
SRC_W, SRC_H = 1280, 720
OUT_W = int(round(SRC_W * S))            # 640
FRAME_H = int(round(SRC_H * S))          # 360（缩放后单帧高度）
BOTTOM_MARGIN = 35        # 脚下方透明：配合 anchor[0,0]，脚贴近任务栏（约 8~26px 上方）
OUT_H = FRAME_H + BOTTOM_MARGIN          # 占位，第二遍后按 global_foot 修正

FRAME_REFRESH = 0.04
FALL_REFRESH = 0.02

VIDEO_MAP = [
    ("00-待机.mp4",   "stand"),
    ("01-抓取.mp4",   "drag_start"),
    ("02-悬挂.mp4",   "drag_loop"),
    ("03-下落.mp4",   "fall"),
    ("04-落地.mp4",   "land"),
    ("05-向左走.mp4", "leftwalk"),
    ("06-向右走.mp4", "rightwalk"),
    ("07-入睡.mp4",   "fallasleep_onset"),
    ("08-睡梦中.mp4", "fallasleep_loop"),
    ("09-醒来.mp4",   "fallasleep_wake"),
    ("10-打喷嚏.mp4", "sneeze"),
    ("11-伸懒腰.mp4", "stretch"),
    ("12-舔毛.mp4",   "groom"),
    ("13-抓苍蝇.mp4", "flycatch"),
    ("14-摇尾巴.mp4", "tailshake"),
    ("15-翻滚.mp4",   "roll"),
    ("16-跳跃.mp4",   "jump"),
]


def key_greenscreen(rgb: np.ndarray) -> np.ndarray:
    """绿幕抠像：返回 RGBA (H,W,4) uint8。"""
    r = rgb[..., 0].astype(np.float32)
    g = rgb[..., 1].astype(np.float32)
    b = rgb[..., 2].astype(np.float32)
    gdiff = g - np.maximum(r, b)            # 绿色主导程度
    t_hard, t_soft = 55.0, 30.0            # 阈值：>t_hard 全透明，<t_soft 不透明
    alpha = np.clip((t_hard - gdiff) / (t_hard - t_soft), 0.0, 1.0) * 255.0
    alpha = alpha.astype(np.uint8)
    # 边缘去绿：半透明像素降低 G 通道，减轻绿边
    semi = (alpha > 5) & (alpha < 250)
    g_clean = np.where(semi, (r + b) * 0.5, g)
    out = np.empty((rgb.shape[0], rgb.shape[1], 4), dtype=np.uint8)
    out[..., 0] = r.astype(np.uint8)
    out[..., 1] = np.clip(g_clean, 0, 255).astype(np.uint8)
    out[..., 2] = b.astype(np.uint8)
    out[..., 3] = alpha
    return out


def key_alpha(rgb: np.ndarray) -> np.ndarray:
    """仅返回 alpha 掩码（uint8），用于统计包围盒。"""
    r = rgb[..., 0].astype(np.float32)
    g = rgb[..., 1].astype(np.float32)
    b = rgb[..., 2].astype(np.float32)
    gdiff = g - np.maximum(r, b)
    t_hard, t_soft = 55.0, 30.0
    alpha = np.clip((t_hard - gdiff) / (t_hard - t_soft), 0.0, 1.0) * 255.0
    return alpha.astype(np.uint8)


def first_pass_stats():
    """遍历全部视频，统计缩放后坐标系下的 global_foot(最低点) 与 global_cx(水平中心)。"""
    gx0, gx1 = 10**9, -1
    gy1 = -1
    for fname, prefix in VIDEO_MAP:
        p = os.path.join(VIDEO_DIR, fname)
        if not os.path.exists(p):
            continue
        reader = imageio.get_reader(p, format="ffmpeg")
        for frame in reader:
            a = key_alpha(frame)
            ys, xs = np.where(a > 2)
            if len(xs):
                gx0 = min(gx0, int(xs.min()))
                gx1 = max(gx1, int(xs.max()))
                gy1 = max(gy1, int(ys.max()))      # 仅关心最低点
        reader.close()
    if gx1 < 0:
        return None, None
    # 转到缩放后坐标系
    global_cx = (gx0 + gx1) / 2.0 * S
    global_foot = gy1 * S
    return global_foot, global_cx


def second_pass(global_foot, global_cx, counts: dict):
    """按统一 S 缩放/抠像，粘贴到 (offx, 0)，脚落在 global_foot。"""
    offx = OUT_W / 2.0 - global_cx
    sw, sh = OUT_W, FRAME_H
    canvas_h = int(round(global_foot)) + BOTTOM_MARGIN
    print(f"画布尺寸: {OUT_W}x{canvas_h}  统一缩放 S={S}  offx={offx:.1f}  global_foot={global_foot:.1f}")
    for fname, prefix in VIDEO_MAP:
        p = os.path.join(VIDEO_DIR, fname)
        if not os.path.exists(p):
            print(f"  跳过（找不到）: {fname}")
            continue
        reader = imageio.get_reader(p, format="ffmpeg")
        i = 0
        for frame in reader:
            img = Image.fromarray(frame).resize((sw, sh), Image.LANCZOS)
            rgba = key_greenscreen(np.asarray(img))
            out = Image.fromarray(rgba, "RGBA")
            canvas = Image.new("RGBA", (OUT_W, canvas_h), (0, 0, 0, 0))
            canvas.paste(out, (int(round(offx)), 0))
            canvas.save(os.path.join(ACTION_DIR, f"{prefix}_{i}.png"))
            i += 1
        reader.close()
        counts[prefix] = i
        print(f"  {prefix}: {i} 帧")


def walk_phases(N: int):
    return [
        {"start": 0,                 "end": int(0.18 * N), "speed": 0},
        {"start": int(0.18 * N),     "end": int(0.33 * N), "speed": "0->10"},
        {"start": int(0.33 * N),     "end": int(0.72 * N), "speed": 10},
        {"start": int(0.72 * N),     "end": int(0.80 * N), "speed": "10->0"},
        {"start": int(0.80 * N),     "end": N - 1,         "speed": 0},
    ]


def build_configs(counts: dict, out_h: int):
    s = counts["stand"]
    ds = counts["drag_start"]
    dl = counts["drag_loop"]
    f = counts["fall"]
    la = counts["land"]
    lw = counts["leftwalk"]
    rw = counts["rightwalk"]

    si = int(0.55 * s)            # stand_idle / stand_wag 切分点
    lb = int(0.30 * la)          # land_bounce / land_stay 切分点
    fl = int(0.08 * f)           # fall 起始
    fll = int(0.60 * f)          # fall_loop 起始

    act_conf = {}

    # stand 相关（共享 stand 精灵表）
    act_conf["stand"] = {"images": "stand", "act_num": 1, "frame_refresh": FRAME_REFRESH}
    act_conf["stand_idle"] = {"images": "stand", "act_num": 1, "frame_refresh": FRAME_REFRESH,
                              "frame_start": 0, "frame_end": si}
    act_conf["stand_wag"] = {"images": "stand", "act_num": 1, "frame_refresh": FRAME_REFRESH,
                             "frame_start": si + 1, "frame_end": s - 1}
    for k in ["default", "up", "down", "left", "right"]:
        act_conf[k] = {"images": "stand", "act_num": 1, "frame_refresh": FRAME_REFRESH}

    # walk
    act_conf["left_walk"] = {"images": "leftwalk", "act_num": 1, "frame_refresh": FRAME_REFRESH,
                             "need_move": True, "direction": "left", "frame_move": 10,
                             "move_phases": walk_phases(lw)}
    act_conf["right_walk"] = {"images": "rightwalk", "act_num": 1, "frame_refresh": FRAME_REFRESH,
                              "need_move": True, "direction": "right", "frame_move": 10,
                              "move_phases": walk_phases(rw)}
    act_conf["leftwalk"] = {"images": "leftwalk", "act_num": 1, "frame_refresh": FRAME_REFRESH}
    act_conf["rightwalk"] = {"images": "rightwalk", "act_num": 1, "frame_refresh": FRAME_REFRESH}

    # drag
    act_conf["drag_start"] = {"images": "drag_start", "act_num": 1, "frame_refresh": FRAME_REFRESH,
                              "frame_start": 0, "frame_end": ds - 1}
    act_conf["drag_loop"] = {"images": "drag_loop", "act_num": 1, "frame_refresh": FRAME_REFRESH}
    act_conf["drag"] = {"images": "drag_loop", "act_num": 1, "frame_refresh": FRAME_REFRESH}

    # fall
    act_conf["fall"] = {"images": "fall", "act_num": 1, "frame_refresh": FALL_REFRESH,
                        "frame_start": fl, "frame_end": f - 1}
    act_conf["fall_loop"] = {"images": "fall", "act_num": 1, "frame_refresh": FALL_REFRESH,
                             "frame_start": fll, "frame_end": f - 1}
    act_conf["prefall"] = {"images": "fall", "act_num": 1, "frame_refresh": FRAME_REFRESH}

    # land（共享 land 精灵表）
    act_conf["land_bounce"] = {"images": "land", "act_num": 1, "frame_refresh": FRAME_REFRESH,
                               "frame_start": 0, "frame_end": lb}
    act_conf["land_stay"] = {"images": "land", "act_num": 1, "frame_refresh": FRAME_REFRESH,
                             "frame_start": lb + 1, "frame_end": la - 1}
    act_conf["land"] = {"images": "land", "act_num": 1, "frame_refresh": FRAME_REFRESH}

    # 睡眠 + 自娱自乐 + 跳跃 + 伸懒腰（独立精灵表）
    for key in ["fallasleep_onset", "fallasleep_loop", "fallasleep_wake",
                "sneeze", "groom", "flycatch", "tailshake", "roll", "jump", "stretch"]:
        act_conf[key] = {"images": key, "act_num": 1, "frame_refresh": FRAME_REFRESH}

    pet_conf = {
        "width": OUT_W,
        "height": out_h,
        "scale": 1.0,
        "interact_speed": 0.02,
        "default": "stand_idle",
        "up": "stand_idle",
        "down": "stand_idle",
        "left": "left_walk",
        "right": "right_walk",
        "drag_start": "drag_start",
        "drag": "drag",
        "fall": "fall",
        "fall_loop": "fall_loop",
        "on_floor": "land",
        "focus": "stand_idle",
        "patpat": "stand_idle",
        "random_act": [
            {"name": "站立", "act_list": ["stand_idle", "stand_idle", "stand_idle", "stand_idle", "stand_wag"],
             "act_prob": 1.0, "act_type": [1, 0]},
            {"name": "左右行走", "act_list": ["left_walk", "right_walk", "stand"],
             "act_prob": 0.286, "act_type": [3, 3]},
            {"name": "睡觉", "act_list": ["fallasleep_onset", "fallasleep_loop", "fallasleep_wake"],
             "act_prob": 0.143, "act_type": [1, 0]},
            {"name": "打喷嚏", "act_list": ["sneeze"], "act_prob": 0.114, "act_type": [2, 0], "entertainment": True},
            {"name": "舔毛", "act_list": ["groom"], "act_prob": 0.114, "act_type": [2, 2], "entertainment": True},
            {"name": "抓苍蝇", "act_list": ["flycatch"], "act_prob": 0.114, "act_type": [2, 2], "entertainment": True},
            {"name": "摇尾巴", "act_list": ["tailshake"], "act_prob": 0.114, "act_type": [2, 1], "entertainment": True},
            {"name": "打滚", "act_list": ["roll"], "act_prob": 0.114, "act_type": [2, 3], "entertainment": True},
            {"name": "跳跃", "act_list": ["jump"], "act_prob": 0.114, "act_type": [2, 3], "entertainment": True},
        ],
        "accessory_act": [],
        "item_favorite": {},
        "item_dislike": {},
        "restore_btn_offset": [int(round(OUT_W * 0.645)), int(round(out_h * 0.52))],
    }

    with open(os.path.join(OUT_DIR, "act_conf.json"), "w", encoding="utf-8") as fp:
        json.dump(act_conf, fp, ensure_ascii=False, indent=2)
    with open(os.path.join(OUT_DIR, "pet_conf.json"), "w", encoding="utf-8") as fp:
        json.dump(pet_conf, fp, ensure_ascii=False, indent=2)
    return act_conf, pet_conf


def build_info_card():
    """用待机首帧（已抠像）生成 pfp.png（头像，透明）与 cover1.png（封面，粉色底）。"""
    os.makedirs(INFO_DIR, exist_ok=True)
    first = Image.open(os.path.join(ACTION_DIR, "stand_0.png")).convert("RGBA")
    arr = np.asarray(first)
    alpha = arr[..., 3]
    ys, xs = np.where(alpha > 10)
    if len(xs) and len(ys):
        x0, x1 = xs.min(), xs.max()
        y0, y1 = ys.min(), ys.max()
        pad = 24
        x0 = max(0, x0 - pad); y0 = max(0, y0 - pad)
        x1 = min(first.width - 1, x1 + pad); y1 = min(first.height - 1, y1 + pad)
        crop = first.crop((x0, y0, x1 + 1, y1 + 1))
    else:
        crop = first

    # 头像：等比缩放到最长边 256，透明背景
    crop.thumbnail((256, 256), Image.LANCZOS)
    crop.save(os.path.join(INFO_DIR, "pfp.png"))

    # 封面：1080x1080 正方形，角色居中，浅粉底
    bg = Image.new("RGB", (1080, 1080), (255, 240, 245))
    fg = first.convert("RGBA")
    fg.thumbnail((int(1080 * 0.8), int(1080 * 0.8)), Image.LANCZOS)
    x = (1080 - fg.width) // 2
    y = (1080 - fg.height) // 2
    bg_rgba = bg.convert("RGBA")
    bg_rgba.paste(fg, (x, y), fg)
    bg_rgba.convert("RGB").save(os.path.join(INFO_DIR, "cover1.png"))

    info = {
        "pfp": "pfp.png",
        "petName": "六一",
        "coverImages": ["cover1.png"],
        "intro": "我是六一～一只元气满满的小猫，陪你在桌面上一起摸鱼、打滚、晒太阳！",
        "author": {
            "name": "六一的朋友们",
            "pfp": "pfp.png",
            "frameColor": "#FFB6C1",
            "infos": "六一角色 · 基于 Video 素材二次开发"
        },
    }
    with open(os.path.join(INFO_DIR, "info.json"), "w", encoding="utf-8") as fp:
        json.dump(info, fp, ensure_ascii=False, indent=2)


def main():
    os.makedirs(ACTION_DIR, exist_ok=True)
    print("=== 第一遍：统计全局脚点/水平中心 ===")
    global_foot, global_cx = first_pass_stats()
    if global_foot is None:
        print("未找到任何视频，退出。")
        return
    print(f"global_foot={global_foot:.2f}  global_cx={global_cx:.2f}")

    counts = {}
    print("=== 第二遍：统一缩放生成精灵图 ===")
    second_pass(global_foot, global_cx, counts)

    out_h = int(round(global_foot)) + BOTTOM_MARGIN
    total = sum(counts.values())
    print(f"\n合计 {len(counts)} 个动作精灵表，{total} 张 PNG，画布高 {out_h}")

    print("=== 生成配置 ===")
    build_configs(counts, out_h)
    build_info_card()
    print("act_conf.json / pet_conf.json / info/info.json / pfp.png / cover1.png 已生成")
    print("输出目录:", OUT_DIR)


if __name__ == "__main__":
    main()
