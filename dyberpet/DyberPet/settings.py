import os
import sys
import json
import ctypes
from sys import platform
from collections import defaultdict

from PySide6.QtGui import QImage, QPixmap
from DyberPet.conf import PetData, TaskData, ActData, ItemData
from PySide6 import QtCore

if platform == 'win32':
    if getattr(sys, 'frozen', False):
        basedir = os.path.dirname(sys.executable)
        configdir = basedir
    else:
        basedir = ''
        configdir = ''
    BASEDIR = basedir
else:
    #from pathlib import Path
    basedir = os.path.dirname(__file__) #Path(os.path.dirname(__file__))
    #basedir = basedir.parent
    basedir = basedir.replace('\\','/')
    basedir = '/'.join(basedir.split('/')[:-1])
    BASEDIR = basedir

if platform == 'linux':
    configdir = os.path.dirname(os.environ['HOME']+'/.config/DyberPet/DyberPet')
    CONFIGDIR = configdir
elif platform == 'win32':
    # configdir already set above (frozen: exe dir, source: empty)
    CONFIGDIR = configdir
else:
    configdir = basedir
    CONFIGDIR = configdir

DEFAULT_THEME_COL = "#009faa"

HELP_URL = "https://github.com/ChaozhongLiu/DyberPet/issues"
PROJECT_URL = "https://github.com/ChaozhongLiu/DyberPet"
DEVDOC_URL = "https://github.com/ChaozhongLiu/DyberPet/blob/main/docs/art_dev.md"
VERSION = "v1.0.1"
AUTHOR = "https://github.com/ChaozhongLiu"
CHARCOLLECT_LINK = "https://github.com/ChaozhongLiu/DyberPet/blob/main/docs/collection.md"
ITEMCOLLECT_LINK = "https://github.com/ChaozhongLiu/DyberPet/blob/main/docs/collection.md"
PETCOLLECT_LINK = "https://github.com/ChaozhongLiu/DyberPet/blob/main/docs/collection.md"

RELEASE_API = "https://api.github.com/repos/ChanChauncey/dyberpet-liuyi/releases/latest"
RELEASE_URL = "https://github.com/ChanChauncey/dyberpet-liuyi/releases/latest"

# UI 尺寸常量（需与 DyberPet.py 保持一致）
STATBAR_H = 20  # 状态栏/信息条高度，widget 总高度 = 2*STATBAR_H + 图片高度
UPDATE_NEEDED = False

HP_TIERS = [0,20,70,100]
TIER_NAMES = ['Starving', 'Hungry', 'Normal', 'Energetic']
HP_INTERVAL = 2
LVL_BAR_V1 = [20, 120, 300, 600, 1200, 1800, 2400, 3200]
LVL_BAR = [20] + [120]*200
PP_HEART = 0.8
PP_COIN = 0.9
COIN_MU = 10
COIN_SIGMA = 5
PP_ITEM = 0.95
PP_AUDIO = 0.8
PP_BUBBLE = 0.15

# Depreciation when sell item to shop
ITEM_DEPRECIATION = 0.75

# Coin reward once a task is checked from Task Panel
SINGLETASK_REWARD = 200
# Coin reward every 5 task
FIVETASK_REWARD = 1500
# Multiply HP and FV effect if item is required by bubble `feed_required`
FACTOR_FEED_REQ = 5

HUNGERSTR = "Satiety"
FAVORSTR = "Favorability"

LINK_PERMIT = {"BiliBili":"https://space.bilibili.com/",
               "微博":"https://m.weibo.cn/profile/",
               "抖音": "https://www.douyin.com/user/",
               "GitHub":"https://github.com/",
               "爱发电":"https://afdian.net/a/",
               "TikTok":"https://www.tiktok.com/",
               "YouTube":"https://www.youtube.com/"}

ITEM_BGC = {'consumable': '#EFEBDF',
            'collection': '#e1eaf4',
            'Empty': '#f0f0ef',
            'dialogue': '#e1eaf4',
            'subpet': '#f6eae9',
            'autofeed': '#e7f1e4'}
ITEM_BGC_DEFAULT = '#EFEBDF'
ITEM_BDC = '#B1C790'

# when falling met the screen boundary, 
# it will be bounced back with this speed decay factor
SPEED_DECAY = 0.5
AUTOFEED_THRESHOLD = 60

# Poop feature
POOP_CHECK_INTERVAL = 10      # 检查间隔（分钟）
POOP_PROBABILITY = 0.3        # 每次检查的触发概率
POOP_FV_REWARD = 10           # 点击消除获得的亲密度

# 窗口当前位置（供 InteractionThread 读取）
widget_pos = [0, 0]

# 半屏方向限制：猫窗口中心 X 和屏幕宽度（供子线程读取）
pet_center_x = 0
screen_width = 1920

# 地面定位：猫脚到任务栏顶部的间距
# taskbar_feet_gap: 猫脚底到任务栏顶部的距离（像素）。
#   正值 = 脚在任务栏上方（悬空）；0 = 脚踩任务栏顶部；负值 = 脚陷入任务栏内。
#   默认 -3：脚踩进任务栏一点点，看起来像真正“踩”在任务栏上。可右键→Adjust Floor 微调。
# pet_feet_bottom_pad: 当前宠物脚底到图片底边的透明边距（按当前缩放），在 init_conf 中动态计算。
taskbar_feet_gap = -3
pet_feet_bottom_pad = 0
floor_y_offset = -3  # 运行时由 compute_floor_offset() 自动覆盖，此值仅为兼容旧代码

def init():
    # computer system ==================================================
    global platform
    platform = platform

    # check if data directory exists ===================================
    newpath = os.path.join(configdir, 'data')
    if not os.path.exists(newpath):
        os.makedirs(newpath)
    
    global pet_conf
    pet_conf = None

    # Image and animation related variable =============================
    global current_img, previous_img
    # Make img-to-show a global variable for multi-thread behaviors
    current_img = None #QPixmap()
    previous_img = None #Pixmap()
    global current_anchor, previous_anchor
    current_anchor = [0,0]
    previous_anchor = [0,0]

    global onfloor, draging, set_fall, playid
    global mouseposx1,mouseposx2,mouseposx3,mouseposx4,mouseposx5
    global mouseposy1,mouseposy2,mouseposy3,mouseposy4,mouseposy5
    global dragspeedx,dragspeedy,fixdragspeedx, fixdragspeedy, fall_right, gravity
    global drag_start_done
    global fall_frame, fall_direction, fall_tick, fall_n_frames
    # Drag and fall related global variable
    onfloor = 1
    draging = 0
    set_fall = True # default is allow drag
    playid = 0
    mouseposx1,mouseposx2,mouseposx3,mouseposx4,mouseposx5=0,0,0,0,0
    mouseposy1,mouseposy2,mouseposy3,mouseposy4,mouseposy5=0,0,0,0,0
    dragspeedx,dragspeedy=0,0
    fixdragspeedx, fixdragspeedy = 1.0, 1.0
    fall_right = False
    gravity = 0.1
    drag_start_done = False  # drag_start 是否播放完毕
    # fall 动画状态
    fall_frame = 0          # 当前帧索引
    fall_direction = 1      # 1=正放, -1=倒放
    fall_tick = 0           # 当前 tick
    fall_n_frames = 175     # fall 总帧数 (18-192)
    fall_phase = 'fall'     # 'fall'=播放18-192一次, 'fall_loop'=循环192-60-192, 'fall_bounce'=倒放正放循环
    fall_loop_frame = 123   # fall_loop 当前帧
    # 弹跳物理状态（只弹一次，帧驱动）
    global bouncing, bounce_tick, bounce_total_frames
    global bounce_start_pos, bounce_peak_height, bounce_drift_x
    bouncing = False
    bounce_tick = 0                 # 累计弹跳 tick（每 tick +1，不受动画循环影响）
    bounce_total_frames = 22        # land_bounce 动画帧数（物理 tick = 帧数 × ticks_per_frame）
    bounce_start_pos = [0, 0]       # 弹跳起始窗口位置
    bounce_peak_height = 0          # 弹跳最高点偏移（像素）
    bounce_drift_x = 0.0            # 水平漂移总量（像素）

    global act_id, current_act, previous_act
    # Select animation to show
    act_id = 0
    current_act, previous_act = None, None

    # prefall 动画状态（鼠标松开后下落预备动作）
    global prefall
    prefall = None

    global showing_dialogue_now
    showing_dialogue_now = False

    global is_sleeping
    is_sleeping = False

    global is_starting_up
    is_starting_up = False

    global click_through_mode
    click_through_mode = False

    # size settings
    global size_factor, screen_scale, font_factor, status_margin, statbar_h, tunable_scale
    try:
        size_factor = 1.0 #ctypes.windll.shcore.GetScaleFactorForDevice(0) / 100
    except:
        size_factor = 1.0
    tunable_scale = 1.0

    # buff related arguments
    global HP_stop, FV_stop
    HP_stop = False
    FV_stop = False

    # sound volumn =====================================================
    global volume
    volume = 0.4

    # pet name =========================================================
    global petname
    petname = ''

    # which screen =====================================================
    global screens, current_screen
    screens = []
    current_screen = None

    # Always on top ====================================================
    # 置顶：让宠物稳定“坐”在任务栏上，失焦后也不会被任务栏弹开。
    # 配合较小的 taskbar_feet_gap（负值=窗口底边轻微探入任务栏）实现“只遮一点点”。
    global on_top_hint, pets
    on_top_hint = True

    # Translations ====================================================
    global lang_dict
    lang_dict = json.load(open(os.path.join(basedir, 'res/language/language.json'), 'r', encoding='UTF-8'))

    # Settings =========================================================
    pets = get_petlist(os.path.join(basedir, 'res/role'))
    init_settings()
    global default_pet
    if default_pet not in pets:
        default_pet = '六一'
    else:
        pets.remove(default_pet)
        pets.sort()
        pets = [default_pet] + pets
    save_settings()

    # Focus Timer
    global focus_timer_on
    focus_timer_on = False

    global poop_enabled
    poop_enabled = True

    # Load in pet data ================================================
    global pet_data 
    pet_data = PetData(pets)

    # Load in task data ================================================
    global task_data 
    task_data = TaskData()

    # Init animation config data ================================================
    global act_data 
    act_data = ActData(pets)

    # Load in Language Choice ==========================================
    global language_code, translator
    change_translator(language_code)

    # Load in items data ==========================================
    global items_data, required_item
    items_data = None
    required_item = None



'''
def init_pet():
    global pet_data 
    pet_data = PetData()
    init_settings()
    save_settings()
'''


def init_settings():
    global file_path, settingGood
    file_path = os.path.join(configdir, 'data/settings.json')

    global gravity, fixdragspeedx, fixdragspeedy, tunable_scale, scale_dict, volume, \
           language_code, on_top_hint, default_pet, defaultAct, themeColor, minipet_scale, \
           toaster_on, usertag_dict, auto_lock, bubble_on, poop_enabled

    # check json file integrity
    try:
        json.load(open(file_path, 'r', encoding='UTF-8'))
        settingGood = True
    except:
        if os.path.isfile(file_path):
            settingGood = False
        else:
            settingGood = True

    if os.path.isfile(file_path) and settingGood:
        data_params = json.load(open(file_path, 'r', encoding='UTF-8'))

        fixdragspeedx, fixdragspeedy = data_params['fixdragspeedx'], data_params['fixdragspeedy']
        gravity = data_params['gravity']
        #tunable_scale = data_params['tunable_scale']
        volume = data_params['volume']
        language_code = data_params.get('language_code', QtCore.QLocale().name())
        on_top_hint = data_params.get('on_top_hint', True)
        default_pet = data_params.get('default_pet', '六一')
        defaultAct = data_params.get('defaultAct', {})
        themeColor = data_params.get('themeColor', None)

        # Fix a bug version distributed to users =============
        if defaultAct is None:
            defaultAct = {}
        elif type(defaultAct) == str:
            defaultAct = {}

        for pet in pets:
            defaultAct[pet] = defaultAct.get(pet, None)
        #=====================================================

        # update for app <= v0.2.2 ===========================
        if language_code == 'CN':
            language_code = QtCore.QLocale().name()
        #=====================================================

        # v0.4.8 update ======================================
        global set_fall
        set_fall = data_params.get('set_fall', True)
        #=====================================================

        # v0.5.0 update ======================================
        # First time open v0.5.0, get the original 
        # tunable_scale as all default
        tunable_scale = data_params.get('tunable_scale', 1.0)
        # v0.5.0 tunable_scales are specified for each character
        scale_dict_tmp = data_params.get('scale_dict', {})
        scale_dict = {}
        for pet in pets:
            pet_scale = scale_dict_tmp.get(pet, 0.5 if pet == '六一' else tunable_scale)
            # Ensure type is int
            try:
                pet_scale = float(pet_scale)
            except:
                pet_scale = 1.0
            pet_scale = max( 0, min(5, pet_scale) )
            scale_dict[pet] = pet_scale
        tunable_scale = scale_dict[default_pet]

        # mini-pet scale settings
        minipet_scale = data_params.get('minipet_scale', defaultdict(dict))
        minipet_scale = check_dict_datatype(minipet_scale, dict, {})
        minipet_scale = defaultdict(dict, minipet_scale)
        for minipet, sdict in minipet_scale.items():
            minipet_scale[minipet] = check_dict_datatype(sdict, float, 1.0)
        #=====================================================

        # v0.5.3 Toaster can be turned off
        toaster_on = data_params.get('toaster_on', True)
        #=====================================================

        # v0.6.1 User Tag (how pet will call the user)
        usertag_dict_tmp = data_params.get('usertag_dict', {})
        usertag_dict = {}
        for pet in pets:
            usertag = usertag_dict_tmp.get(pet, '')
            usertag_dict[pet] = usertag

        # v0.6.5 stop HP & FV changes when screen locked
        auto_lock = data_params.get('auto_lock', False)
        #=====================================================

        # v0.6.7 Bubble can be turned off
        bubble_on = data_params.get('bubble_on', True)
        #=====================================================

        # Poop feature toggle
        poop_enabled = data_params.get('poop_enabled', True)
        #=====================================================

    else:
        fixdragspeedx, fixdragspeedy = 1.0, 1.0
        gravity = 0.1
        volume = 0.5
        language_code = QtCore.QLocale().name()
        on_top_hint = True
        default_pet = '六一'
        defaultAct = {}
        themeColor = None
        for pet in pets:
            defaultAct[pet] = defaultAct.get(pet, None)
        scale_dict = {}
        for pet in pets:
            scale_dict[pet] = 0.5 if pet == '六一' else 1.0
        tunable_scale = 1.0
        minipet_scale = defaultdict(dict)
        toaster_on = True
        bubble_on = True
        usertag_dict = {}
        auto_lock = False
        poop_enabled = True
    check_locale()
    save_settings()

def save_settings():
    global file_path, set_fall, gravity, fixdragspeedx, fixdragspeedy, scale_dict, volume, \
           language_code, on_top_hint, default_pet, defaultAct, themeColor, minipet_scale, \
           toaster_on, usertag_dict, auto_lock, bubble_on, poop_enabled

    data_js = {'gravity':gravity,
               'set_fall': set_fall,
               'fixdragspeedx':fixdragspeedx,
               'fixdragspeedy':fixdragspeedy,
               'usertag_dict':usertag_dict,
               'scale_dict':scale_dict,
               'minipet_scale':minipet_scale,
               'volume':volume,
               'on_top_hint':on_top_hint,
               'toaster_on':toaster_on,
               'bubble_on':bubble_on,
               'default_pet':default_pet,
               'defaultAct':defaultAct,
               'language_code':language_code,
               'themeColor':themeColor,
               'auto_lock':auto_lock,
               'poop_enabled':poop_enabled
               }

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data_js, f, ensure_ascii=False, indent=4)

def get_petlist(dirname):
    folders = os.listdir(dirname)
    pets = []
    # subpets = []
    # v0.3.3 subpet now moved to folder: res/pet/
    for folder in folders:
        folder_path = os.path.join(dirname, folder)
        if folder != 'sys' and os.path.isdir(folder_path):
            pets.append(folder)
            #conf_path = os.path.join(folder_path, 'pet_conf.json')
            #conf = dict(json.load(open(conf_path, 'r', encoding='UTF-8')))
            #subpets += [i for i in conf.get('subpet',{}).keys()]
    pets = sorted(set(pets))
    #subpets = list(set(subpets))
    #for subpet in subpets:
    #    pets.remove(subpet)
    return pets


def compute_pet_feet_bottom_pad(pixmap):
    """从当前宠物图片计算脚底到图片底边的透明边距（按当前缩放后）。"""
    global pet_feet_bottom_pad
    img = pixmap.toImage()
    w, h = img.width(), img.height()
    for y in range(h - 1, -1, -1):
        for x in range(w):
            if img.pixelColor(x, y).alpha() > 10:
                pet_feet_bottom_pad = h - 1 - y
                return pet_feet_bottom_pad
    pet_feet_bottom_pad = 0
    return pet_feet_bottom_pad

def compute_floor_offset(screen):
    """根据屏幕几何信息自动计算 floor_y_offset。

    定位公式：窗口底边 = availableGeometry().bottom() - floor_y_offset
    想让猫脚离任务栏顶 taskbar_feet_gap 像素（正值为在任务栏上方），需考虑
    图片底边到猫脚有 pet_feet_bottom_pad 像素的透明边距，因此：
        floor_y_offset = taskbar_feet_gap - pet_feet_bottom_pad
    当 taskbar_feet_gap = 0 时，脚踩在任务栏顶部，窗口底边会探入任务栏 pet_feet_bottom_pad 像素。
    """
    global floor_y_offset
    floor_y_offset = taskbar_feet_gap - pet_feet_bottom_pad
    return floor_y_offset

def save_taskbar_feet_gap(gap):
    """将 taskbar_feet_gap 写入 settings.py 并更新运行时变量"""
    global taskbar_feet_gap
    taskbar_feet_gap = int(gap)
    file_path = os.path.join(os.path.dirname(__file__), 'settings.py')
    lines = open(file_path, 'r', encoding='utf-8').readlines()
    for i, line in enumerate(lines):
        if line.strip().startswith('taskbar_feet_gap'):
            lines[i] = f'taskbar_feet_gap = {int(gap)}\n'
            break
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)

def save_floor_offset(offset):
    """兼容旧接口：将 offset 转换为 taskbar_feet_gap 保存"""
    # 反推 taskbar_feet_gap 不可靠，直接保存 offset 并更新全局
    global floor_y_offset
    floor_y_offset = int(offset)
    file_path = os.path.join(os.path.dirname(__file__), 'settings.py')
    lines = open(file_path, 'r', encoding='utf-8').readlines()
    for i, line in enumerate(lines):
        if line.strip().startswith('floor_y_offset'):
            lines[i] = f'floor_y_offset = {int(offset)}\n'
            break
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)

def change_translator(language_code):
    global translator
    if language_code == 'en_US':
        translator = None
    else:
        translator = QtCore.QTranslator()
        translator.load(QtCore.QLocale(language_code), "langs", ".", os.path.join(basedir, "res/language/"))

        global TIER_NAMES, HUNGERSTR, FAVORSTR
        TIER_NAMES = [translator.translate("others", i) for i in TIER_NAMES] #.encode('utf-8')
        HUNGER_trans = translator.translate("others", HUNGERSTR) #.encode('utf-8'))
        if HUNGER_trans:
            HUNGERSTR = HUNGER_trans
        FAVOR_trans = translator.translate("others", FAVORSTR) #.encode('utf-8'))
        if FAVOR_trans:
            FAVORSTR = FAVOR_trans

def check_locale():
    global language_code, lang_dict
    if language_code not in lang_dict.values():
        if language_code.split("_")[0] == 'zh':
            language_code = "zh_CN"
        else:
            language_code = "en_US"
            

def check_dict_datatype(raw_dict:dict, dtype, default_value):
    """
    Checks the datatype of values in a dictionary. If a value does not match the specified datatype, it is replaced with a default value.

    Parameters:
    raw_dict (dict): The dictionary to check.
    dtype (type): The expected datatype for the values.
    default_value: The value to replace if the datatype does not match.

    Returns:
    dict: A new dictionary with corrected datatypes.
    """
    return {k: (v if isinstance(v, dtype) else default_value) for k, v in raw_dict.items()}