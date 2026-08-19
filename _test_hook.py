import sys, os

# 模拟 frozen 环境
sys.frozen = True
sys.executable = r'C:\DyberPet\dist_pet\六一桌宠\六一桌宠.exe'

# 执行 run_DyberPet.py 的钩子部分（前 60 行左右，到 except Exception: pass）
exec(compile(open(r'C:\DyberPet\dyberpet\run_DyberPet.py', encoding='utf-8').read().split('from sys import platform')[0], 'hook', 'exec'))

# 验证关键导入来自松散目录
import DyberPet
print('DyberPet __file__:', DyberPet.__file__)
print('DyberPet __path__:', DyberPet.__path__)

from DyberPet import settings
print('settings __file__:', settings.__file__)
print('settings VERSION:', settings.VERSION)

from DyberPet.utils import read_json
print('read_json from:', read_json.__module__, DyberPet.utils.__file__)

from DyberPet.DyberSettings import BasicSettingUI
print('BasicSettingUI __file__:', BasicSettingUI.__file__)
