# -*- coding: utf-8 -*-
"""生成六一精灵图联系表(中性灰底，便于检查绿边) + 抠像质量量化。"""
import os, numpy as np
from PIL import Image

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "dyberpet", "res", "role", "六一")
ACTION = os.path.join(OUT, "action")
SHEET = os.path.join(OUT, "info", "contact_sheet.png")

SAMPLES = [
    ("stand_0.png", "待机/站立"),
    ("drag_start_48.png", "抓取"),
    ("fall_72.png", "下落"),
    ("land_15.png", "落地弹跳"),
    ("leftwalk_96.png", "向左走"),
    ("sneeze_48.png", "打喷嚏"),
    ("tailshake_60.png", "摇尾巴"),
    ("roll_72.png", "翻滚"),
    ("jump_48.png", "跳跃"),
    ("fallasleep_wake_84.png", "醒来"),
]

def fringe_metric(rgba):
    r, g, b, a = rgba[...,0].astype(float), rgba[...,1].astype(float), rgba[...,2].astype(float), rgba[...,3].astype(float)
    gdiff = g - np.maximum(r, b)
    opaque = a > 200
    fringe = opaque & (gdiff > 40)
    frac = fringe.sum() / max(1, opaque.sum())
    return float(frac)

cols, rows = 5, 2
cell_w, cell_h = 256, 144
sheet = Image.new("RGB", (cols*cell_w, rows*cell_h), (220, 220, 220))
worst = 0.0
for i, (fn, label) in enumerate(SAMPLES):
    p = os.path.join(ACTION, fn)
    if not os.path.exists(p):
        print("missing", fn); continue
    img = Image.open(p).convert("RGBA")
    fr = fringe_metric(np.asarray(img))
    worst = max(worst, fr)
    bg = Image.new("RGB", img.size, (220, 220, 220))
    comp = Image.composite(img, bg, img.split()[3]).convert("RGB")
    comp.thumbnail((cell_w, cell_h), Image.LANCZOS)
    cx = (i % cols) * cell_w + (cell_w - comp.width)//2
    cy = (i // cols) * cell_h + (cell_h - comp.height)//2
    sheet.paste(comp, (cx, cy))
    # 标注
    from PIL import ImageDraw
    d = ImageDraw.Draw(sheet)
    d.text((cx, cy + cell_h - 16), f"{label} fr={fr*100:.2f}%", fill=(120,0,0))

sheet.save(SHEET)
print(f"联系表已保存: {SHEET}")
print(f"最差绿边占比(不透明像素中仍为绿的比例): {worst*100:.3f}%  -> {'良好' if worst < 0.01 else '需关注'}")
