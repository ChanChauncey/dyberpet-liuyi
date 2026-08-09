import shutil
from pathlib import Path

src = Path(r'D:\Claude专用\桌面宠物\dyberpet\res\role\Kitty\action')
dst = Path(r'D:\Claude专用\桌面宠物\dyberpet\res\role\六一\action')
dst.mkdir(parents=True, exist_ok=True)

for f in sorted(src.glob('*.png')):
    shutil.copy2(f, dst / f.name)
    print(f'  {f.name}')

print(f'\nDone: {len(list(dst.glob("*.png")))} files copied')
