"""精灵图部署——最简版。

流程：
1. 读取 rgba 帧（1280×720）
2. 等比例缩小到 640×360
3. 保存 + 生成配置

用法：python tools/deploy_sprites.py
"""

import json
from pathlib import Path
from PIL import Image

ROOT = Path(r"D:\Claude专用\桌面宠物")
RGBA_DIR = ROOT / "data" / "pipeline" / "rgba"
ACTION_DIR = ROOT / "dyberpet" / "res" / "role" / "六一" / "action"
CONFIG_SRC = ROOT / "assets" / "configs"
CONFIG_DST = ROOT / "dyberpet" / "res" / "role" / "六一"

# resize 到原图一半（从第一帧自动检测）
TARGET_W = None
TARGET_H = None

# 动作定义：(rgba目录名, 输出前缀, act_conf键, 额外配置)
ACTIONS = [
    ("stand", "stand", ["stand", "default", "up", "down", "left", "right"], {}),
    ("walk_right", "rightwalk", ["right_walk"], {"need_move": True, "direction": "right", "frame_move": 10}),
    ("walk_left", "leftwalk", ["left_walk"], {"need_move": True, "direction": "left", "frame_move": 10}),
]

# grab/fall 序列：每个动作对应独立的 rgba 目录
GRAB_ACTIONS = [
    ("grab_start", "drag_start", ["drag_start"], {}),
    ("grab_loop", "drag_loop", ["drag_loop", "drag"], {}),
    ("fall", "fall", ["fall", "fall_loop"], {}),
    ("land", "land_bounce", ["land_bounce"], {}),
    ("land", "land_stay", ["land_stay", "land", "on_floor"], {}),
]

# 其他独立动作
SLEEPActions = [
    ("sleep_onset", "fallasleep_onset", ["fallasleep_onset"], {}),
    ("sleep_loop", "fallasleep_loop", ["fallasleep_loop"], {}),
    ("wake_up", "fallasleep_wake", ["fallasleep_wake"], {}),
    ("stretch", "stretch", ["stretch"], {}),
    ("sneeze", "sneeze", ["sneeze"], {}),
    ("groom", "groom", ["groom"], {}),
    ("flycatch", "flycatch", ["flycatch"], {}),
    ("tailshake", "tailshake", ["tailshake"], {}),
    ("roll", "roll", ["roll"], {}),
    ("jump", "jump", ["jump"], {}),
    ("feed_猫粮", "feed_猫粮", ["feed_猫粮"], {}),
    ("动作19 汉堡", "feed_汉堡", ["feed_汉堡"], {}),
    ("动作20 薯条", "feed_薯条", ["feed_薯条"], {}),
    ("动作21 果酱", "feed_果酱", ["feed_果酱"], {}),
    ("动作23 苹果", "feed_苹果", ["feed_苹果"], {}),
    ("动作24 香蕉", "feed_香蕉", ["feed_香蕉"], {}),
    ("动作25 小鱼干", "feed_小鱼干", ["feed_小鱼干"], {}),
    ("动作26 冻干", "feed_冻干", ["feed_冻干"], {}),
    ("动作28 酸奶", "feed_酸奶", ["feed_酸奶"], {}),
    ("动作30 西红柿炒蛋", "feed_番茄炒蛋", ["feed_番茄炒蛋"], {}),
]


def process_simple(name, paths, tail_blend=0):
    """读取 → resize 到一半 → 保存。tail_blend: 在末尾生成 N 个尾→首插值帧。"""
    global TARGET_W, TARGET_H
    ACTION_DIR.mkdir(parents=True, exist_ok=True)
    imgs = []
    for p in sorted(paths):
        img = Image.open(p).convert("RGBA")
        # 首次调用时检测尺寸并设为一半
        if TARGET_W is None:
            orig_w, orig_h = img.size
            TARGET_W, TARGET_H = orig_w // 2, orig_h // 2
            print(f"  原始尺寸: {orig_w}x{orig_h} → 部署尺寸: {TARGET_W}x{TARGET_H}")
        if TARGET_W != img.size[0] or TARGET_H != img.size[1]:
            img = img.resize((TARGET_W, TARGET_H), Image.LANCZOS)
        imgs.append(img)

    # 在末尾追加：最后一帧 → 第一帧 的插值过渡帧
    if tail_blend > 0 and len(imgs) >= 2:
        for b in range(1, tail_blend + 1):
            alpha = b / (tail_blend + 1)
            blended = Image.blend(imgs[-1], imgs[0], alpha)
            imgs.append(blended)

    for i, img in enumerate(imgs):
        img.save(ACTION_DIR / f"{name}_{i}.png")
    print(f"  {name}: {len(imgs)}f  {TARGET_W}x{TARGET_H}")
    return len(imgs)


def main():
    # 清空输出目录（只删除本脚本会生成的文件名模式）
    generated_prefixes = {a[1] for a in ACTIONS}
    generated_prefixes.update(a[1] for a in GRAB_ACTIONS)
    generated_prefixes.update(p for _, p, _, _ in SLEEPActions)

    if ACTION_DIR.exists():
        deleted = 0
        for f in ACTION_DIR.glob("*.png"):
            # 只删除以已知动作前缀开头的文件
            prefix = f.stem.rsplit("_", 1)[0] if "_" in f.stem else f.stem
            if prefix in generated_prefixes:
                f.unlink()
                deleted += 1
        print(f"已清理 {deleted} 个旧精灵图")
    ACTION_DIR.mkdir(parents=True, exist_ok=True)

    act_conf = {}

    # ── Stand + Walk ──
    for src_dir, prefix, conf_keys, extra in ACTIONS:
        paths = sorted((RGBA_DIR / src_dir).glob("frame_*_rgba.png"))
        count = process_simple(prefix, paths)
        for k in conf_keys:
            act_conf[k] = {
                "images": prefix, "act_num": 1, "frame_refresh": 0.04,
                **extra,
            }
    # default/up/down/left/right 用 stand 素材，帧率同 stand
    for k in ["default", "up", "down", "left", "right"]:
        act_conf[k] = {"images": "stand", "act_num": 1, "frame_refresh": 0.04}

    # ── Grab/Fall ──
    for src_dir, prefix, conf_keys, extra in GRAB_ACTIONS:
        paths = sorted((RGBA_DIR / src_dir).glob("frame_*_rgba.png"))
        if paths:
            process_simple(prefix, paths)
            for k in conf_keys:
                act_conf[k] = {
                    "images": prefix, "act_num": 1, "frame_refresh": 0.04,
                    **extra,
                }

    # ── Sleep + Stretch ──
    for src_dir, prefix, conf_keys, extra in SLEEPActions:
        paths = sorted((RGBA_DIR / src_dir).glob("frame_*_rgba.png"))
        if paths:
            process_simple(prefix, paths)
            for k in conf_keys:
                act_conf[k] = {
                    "images": prefix, "act_num": 1, "frame_refresh": 0.04,
                    **extra,
                }

    # ── 扫描目录中未被 act_conf 覆盖的已有精灵 ──
    existing_prefixes = set()
    if ACTION_DIR.exists():
        for f in ACTION_DIR.glob("*.png"):
            prefix = f.stem.rsplit("_", 1)[0] if "_" in f.stem else f.stem
            existing_prefixes.add(prefix)
    for prefix in sorted(existing_prefixes - set(act_conf.keys())):
        act_conf[prefix] = {"images": prefix, "act_num": 1, "frame_refresh": 0.04}

    # ── 配置 ──
    print(f"\ncanvas: {TARGET_W}x{TARGET_H}")

    for cp in [CONFIG_DST / "pet_conf.json", CONFIG_SRC / "pet_conf.json"]:
        c = {}
        if cp.exists():
            try:
                with open(cp, "r", encoding="utf-8") as f:
                    c = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                pass
        c["width"] = TARGET_W
        c["height"] = TARGET_H
        c["scale"] = 1.0
        with open(cp, "w", encoding="utf-8") as f:
            json.dump(c, f, ensure_ascii=False, indent=2)

    for dst in [CONFIG_DST / "act_conf.json", CONFIG_SRC / "act_conf.json"]:
        # 合并：保留已有配置，只添加新 key
        if dst.exists():
            try:
                with open(dst, "r", encoding="utf-8") as f:
                    existing = json.load(f)
                for k, v in act_conf.items():
                    if k not in existing:
                        existing[k] = v
                act_conf = existing
            except (json.JSONDecodeError, FileNotFoundError):
                pass
        with open(dst, "w", encoding="utf-8") as f:
            json.dump(act_conf, f, ensure_ascii=False, indent=2)

    total = len(list(ACTION_DIR.glob("*.png")))
    print(f"act_conf: {len(act_conf)} actions, {total} sprites")


if __name__ == "__main__":
    main()
