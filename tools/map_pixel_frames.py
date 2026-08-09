# coding:utf-8
"""
将切割好的像素帧映射到项目的动画命名格式。
用法: D:\Python\python.exe tools/map_pixel_frames.py
"""
import os
import shutil
import json

BASEDIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ACTION_DIR = os.path.join(BASEDIR, 'res/role/花椒/action')
TEMP_DIR = os.path.join(ACTION_DIR, '_raw')

# 映射表: row编号 -> (动画名, 方向说明)
# 基于观察到的精灵图布局
ROW_MAP = {
    0: 'stand',       # 站立（正面）
    1: 'stand',       # 站立变体
    2: 'left_walk',   # 左走
    3: 'left_walk',   # 左走变体
    4: 'right_walk',  # 右走
    5: 'right_walk',  # 右走变体
    6: 'fallasleep_loop',  # 躺下/睡觉
    7: 'fallasleep_loop',
    8: 'fallasleep_loop',
    9: 'fallasleep_loop',
    10: 'fallasleep_loop',
    11: 'fallasleep_loop',
    12: 'stand',      # 坐着
    13: 'stand',
    14: 'stand',
    15: 'stand',
    16: 'stand',
    17: 'stand',
    18: 'stand',
    19: 'stand',
    20: 'stand',
    21: 'stand',
    22: 'stand',
    23: 'stand',
    24: 'stand',
    25: 'stand',
    26: 'stand',
    27: 'stand',
    28: 'stand',
    29: 'left_walk',  # 行走
    30: 'right_walk',
    31: 'stand',
    32: 'left_walk',
    33: 'right_walk',
    34: 'left_walk',
    35: 'right_walk',
    36: 'left_walk',
    37: 'right_walk',
    38: 'stand',
    39: 'left_walk',
    40: 'right_walk',
    41: 'left_walk',
    42: 'right_walk',
    43: 'stand',
    44: 'stand',
    45: 'stand',
    46: 'stand',
    47: 'stand',
    48: 'stand',
    49: 'stand',
    50: 'stand',
    51: 'stand',
    52: 'stand',
    53: 'stand',
    54: 'stand',
    55: 'stand',
    56: 'stand',
    57: 'stand',
    58: 'stand',
    59: 'stand',
    60: 'stand',
    61: 'stand',
    62: 'stand',
    63: 'stand',
    64: 'stand',
    65: 'stand',
}


def map_frames():
    # 收集每个动画的所有帧
    animations = {}
    for row_idx in range(66):
        anim_name = ROW_MAP.get(row_idx, 'stand')
        if anim_name not in animations:
            animations[anim_name] = []

        # 找这一行的所有帧
        col = 0
        while True:
            src = os.path.join(TEMP_DIR, f'row{row_idx:02d}_frame{col:02d}.png')
            if not os.path.exists(src):
                break
            animations[anim_name].append(src)
            col += 1

    # 复制帧到目标目录
    for anim_name, frames in animations.items():
        for i, src in enumerate(frames):
            dst = os.path.join(ACTION_DIR, f'{anim_name}_{i}.png')
            shutil.copy2(src, dst)

    # 输出统计
    for anim_name, frames in sorted(animations.items()):
        print(f"  {anim_name}: {len(frames)} 帧")

    return animations


def create_act_conf(animations):
    """生成简化版 act_conf.json"""
    act_conf = {}
    for anim_name, frames in animations.items():
        act_conf[anim_name] = {
            "images": anim_name,
            "act_num": len(frames),
            "act_type": "random_act"
        }

    path = os.path.join(BASEDIR, 'res/role/花椒/act_conf.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(act_conf, f, ensure_ascii=False, indent=4)
    print(f"\n已写入 {path}")


def create_pet_conf(animations):
    """生成 pet_conf.json"""
    pet_conf = {
        "width": 64,
        "height": 64,
        "scale": 3.0,
        "interact_speed": 0.02,
        "default": "stand",
        "up": "stand",
        "down": "stand",
        "left": "left_walk",
        "right": "right_walk",
        "drag_start": "stand",
        "drag": "stand",
        "fall": "stand",
        "fall_loop": "stand",
        "on_floor": "stand",
        "focus": "stand",
        "patpat": "stand",
        "random_act": [
            {
                "name": "站立",
                "act_list": ["stand"],
                "act_prob": 1.0,
                "act_type": [2, 0]
            },
            {
                "name": "左右行走",
                "act_list": ["left_walk", "right_walk", "stand"],
                "act_prob": 0.15,
                "act_type": [3, 1]
            }
        ],
        "accessory_act": [],
        "item_favorite": {},
        "item_dislike": {}
    }

    path = os.path.join(BASEDIR, 'res/role/花椒/pet_conf.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(pet_conf, f, ensure_ascii=False, indent=4)
    print(f"已写入 {path}")


if __name__ == '__main__':
    print("映射帧文件...")
    animations = map_frames()
    print("\n生成配置文件...")
    create_act_conf(animations)
    create_pet_conf(animations)
    print("\n完成!")
