# -*- coding: utf-8 -*-
"""把 LOGO 外圈白底变成透明，保留卡片/猫咪自身的白色细节。"""
import os, shutil, collections
from PIL import Image

# 原始未处理图（备份）
SRC_BAK = r'C:\Users\76215\Documents\给宝的\桌宠\dyberpet-dahui\LOGO.png.bak'
# 输出的透明 LOGO
SRC = r'C:\Users\76215\Documents\给宝的\桌宠\dyberpet-dahui\LOGO.png'
JUNCTION = r'C:\DyberPet\LOGO.png'

TH = 250  # 背景白阈值，保留猫咪浅色毛发

# 1) 从原始备份读取
img = Image.open(SRC_BAK).convert('RGBA')
W, H = img.size
px = img.load()

# 2) Flood-fill 从图像边界开始，只抠与外部连通的白底
visited = [[False] * H for _ in range(W)]
q = collections.deque()
for x in range(W):
    q.append((x, 0))
    q.append((x, H - 1))
for y in range(H):
    q.append((0, y))
    q.append((W - 1, y))

changed = 0
while q:
    x, y = q.popleft()
    if x < 0 or x >= W or y < 0 or y >= H:
        continue
    if visited[x][y]:
        continue
    r, g, b, a = px[x, y]
    # 已经是透明 或 接近白色背景，才继续扩散
    if a == 0 or (r >= TH and g >= TH and b >= TH):
        visited[x][y] = True
        if a > 0:
            px[x, y] = (r, g, b, 0)
            changed += 1
        q.extend([(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)])

print('border-connected white->transparent pixels:', changed)

# 3) 保存透明 LOGO（覆盖当前工作副本）
img.save(SRC)
img.save(JUNCTION)
print('saved transparent LOGO')

# 4) 生成预览（灰底验证透明区域）
bg = Image.new('RGBA', img.size, (128, 128, 128, 255))
preview = Image.alpha_composite(bg, img)
preview.convert('RGB').save(r'C:\DyberPet\_logo_transparent_preview.png')

# 5) 重建 app_icon.ico / app_icon.png（透明背景，居中，不补白）
bbox = img.getbbox()
print('non-transparent bbox', bbox)
cx = (bbox[0] + bbox[2]) // 2
cy = (bbox[1] + bbox[3]) // 2
half = max(bbox[2] - bbox[0], bbox[3] - bbox[1]) // 2
left = max(0, cx - half)
top = max(0, cy - half)
right = min(W, cx + half)
bottom = min(H, cy + half)
cropped = img.crop((left, top, right, bottom))
size = max(cropped.width, cropped.height)
square = Image.new('RGBA', (size, size), (0, 0, 0, 0))
off = ((size - cropped.width) // 2, (size - cropped.height) // 2)
square.paste(cropped, off, cropped)

png_path = r'C:\DyberPet\dyberpet\app_icon.png'
square.resize((256, 256), Image.LANCZOS).save(png_path)

frames = [square.resize((s, s), Image.LANCZOS) for s in (256, 128, 96, 64, 48, 32, 24, 16)]
ico_path = r'C:\DyberPet\dyberpet\app_icon.ico'
frames[0].save(ico_path, format='ICO',
               sizes=[(f.width, f.height) for f in frames],
               append_images=frames[1:])
print('saved', png_path, ico_path)

# 6) 信息卡封面 cover1.png（透明底）
cover = Image.new('RGBA', (1080, 1080), (0, 0, 0, 0))
fit = square.resize((1080, 1080), Image.LANCZOS)
cover.paste(fit, (0, 0), fit)
cover_path = r'C:\DyberPet\dist_pet\六一桌宠\res\role\六一\info\cover1.png'
cover.save(cover_path)
print('saved', cover_path)

# 7) 同步到其它 dist 目录
for base in (
    r'C:\DyberPet\dist_logo\六一桌宠',
    r'C:\DyberPet\dist_pet\六一桌宠',
    r'C:\DyberPet\dist_liuyi_new\六一桌宠',
    r'C:\DyberPet\dist_final\六一桌宠',
):
    if not os.path.isdir(base):
        continue
    for s, rel in ((ico_path, 'app_icon.ico'), (png_path, 'app_icon.png'),
                     (cover_path, r'res\role\六一\info\cover1.png')):
        dst = os.path.join(base, rel)
        if not os.path.isdir(os.path.dirname(dst)):
            continue
        try:
            shutil.copy2(s, dst)
        except PermissionError:
            print('locked skip', dst)
    print('synced', base)
