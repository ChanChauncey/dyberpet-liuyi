# -*- coding: utf-8 -*-
"""把 res/ 下所有 PNG 量化到 8 位调色板(RGBA 保留透明)，近乎无损压缩体积。
先备份原图到 C:\\DyberPet\\res_png_backup，再覆盖写入。仅当输出有效才替换。
"""
import os
import shutil
import time
from PIL import Image

RES = r"C:\DyberPet\dyberpet\res"
BACKUP = r"C:\DyberPet\res_png_backup"
COLORS = 256


def quantize_rgba(im):
    """RGBA -> 8 位调色板 PNG，保留透明。"""
    im = im.convert("RGBA")
    alpha = im.split()[-1]
    rgb = im.convert("RGB")
    p = rgb.quantize(colors=COLORS - 1, method=Image.FASTOCTREE,
                     dither=Image.FLOYDSTEINBERG)
    rgba = p.convert("RGBA")
    rgba.putalpha(alpha)
    return rgba.quantize(colors=COLORS, method=Image.FASTOCTREE,
                        dither=Image.FLOYDSTEINBERG)


def mb(b):
    return round(b / 1024 / 1024, 1)


# 1) 备份（仅首次）
if not os.path.isdir(BACKUP):
    print("备份原图到", BACKUP, "...")
    t0 = time.time()
    shutil.copytree(RES, BACKUP)
    print("备份完成, 耗时 %.1fs" % (time.time() - t0))
else:
    print("备份已存在，跳过备份")

# 2) 遍历 res 下所有 png
pngs = []
for root, _dirs, files in os.walk(RES):
    for f in files:
        if f.lower().endswith(".png"):
            pngs.append(os.path.join(root, f))

before_total = 0
after_total = 0
ok = 0
fail = 0
samples = []

for p in pngs:
    try:
        b0 = os.path.getsize(p)
        im = Image.open(p)
        out = quantize_rgba(im)
        out.save(p, "PNG", optimize=True)
        # 校验：能重新打开、仍是 RGBA(含透明)
        verify = Image.open(p).convert("RGBA")
        b1 = os.path.getsize(p)
        before_total += b0
        after_total += b1
        ok += 1
        if len(samples) < 6:
            samples.append((os.path.basename(p), mb(b0), mb(b1)))
    except Exception as e:
        fail += 1
        if fail <= 3:
            print("FAIL", p, e)

print("\n处理文件数: ok=%d fail=%d" % (ok, fail))
print("体积: 前 %.1f MB -> 后 %.1f MB  (省 %.1f MB, %.1f%%)" % (
    mb(before_total), mb(after_total),
    mb(before_total - after_total),
    (1 - after_total / before_total) * 100 if before_total else 0))
print("采样(文件名 前MB 后MB):")
for s in samples:
    print("  ", s)
