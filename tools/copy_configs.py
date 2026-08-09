import shutil
from pathlib import Path

role_dir = Path(r'D:\Claude专用\桌面宠物\dyberpet\res\role\六一')
role_dir.mkdir(parents=True, exist_ok=True)

# Copy configs
shutil.copy2(r'D:\Claude专用\桌面宠物\assets\configs\pet_conf.json', role_dir / 'pet_conf.json')
shutil.copy2(r'D:\Claude专用\桌面宠物\assets\configs\act_conf.json', role_dir / 'act_conf.json')
print('Configs copied')
print(f'  {role_dir / "pet_conf.json"}')
print(f'  {role_dir / "act_conf.json"}')
print(f'Sprites: {len(list((role_dir / "action").glob("*.png")))} files')
