"""裁剪精灵图透明边距 + 缩放到统一尺寸。

1. 对每个动作组，找到所有帧的并集边界框（union bbox）
2. 加 10px padding 后裁剪
3. 缩放使猫高度统一 ~500px（适配 540px 的 DyberPet 窗口）
4. 同一动作组所有帧填充到相同画布尺寸（保证无跳变）
"""

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(r"D:\Claude专用\桌面宠物")
ACTION_DIR = ROOT / "dyberpet" / "res" / "role" / "六一" / "action"
PET_CONF_PATH = ROOT / "dyberpet" / "res" / "role" / "六一" / "pet_conf.json"
ASSETS_PET_CONF = ROOT / "assets" / "configs" / "pet_conf.json"

TARGET_CAT_HEIGHT = 300   # 猫在画面中的目标高度（Kitty 仅 64-96px，300 已足够呈现细节）
PADDING = 15              # bbox 四周留白


def get_action_groups():
    """按动作名分组。"""
    groups = {}
    for f in sorted(ACTION_DIR.glob("*.png")):
        # stand_0.png → stand
        base = f.stem.rsplit("_", 1)[0]
        groups.setdefault(base, []).append(f)
    return groups


def union_bbox(files):
    """计算一组文件的并集边界框（所有帧的非透明像素的最大范围）。"""
    min_x, min_y, max_x, max_y = 99999, 99999, 0, 0
    for f in files:
        img = Image.open(f)
        arr = np.array(img)
        alpha = arr[:, :, 3]
        rows = np.any(alpha > 0, axis=1)
        cols = np.any(alpha > 0, axis=0)
        if rows.any() and cols.any():
            y0, y1 = np.where(rows)[0][[0, -1]]
            x0, x1 = np.where(cols)[0][[0, -1]]
            min_x = min(min_x, x0)
            min_y = min(min_y, y0)
            max_x = max(max_x, x1)
            max_y = max(max_y, y1)
    return min_x, min_y, max_x, max_y


def process_action(name, files):
    """处理一个动作组的所有帧。"""
    # 1. 计算并集 bbox
    min_x, min_y, max_x, max_y = union_bbox(files)
    bbox_w = max_x - min_x + 1
    bbox_h = max_y - min_y + 1

    # 2. 加 padding（不超出原图边界）
    # 先加载一张图获取原图尺寸
    sample = Image.open(files[0])
    img_w, img_h = sample.size
    crop_x0 = max(0, min_x - PADDING)
    crop_y0 = max(0, min_y - PADDING)
    crop_x1 = min(img_w, max_x + PADDING + 1)
    crop_y1 = min(img_h, max_y + PADDING + 1)
    crop_w = crop_x1 - crop_x0
    crop_h = crop_y1 - crop_y0

    # 3. 计算缩放比例（使 cat 高度 = TARGET_CAT_HEIGHT）
    scale = TARGET_CAT_HEIGHT / crop_h
    new_w = int(crop_w * scale)
    new_h = TARGET_CAT_HEIGHT

    # 4. 处理每一帧
    for f in files:
        img = Image.open(f)
        # 裁剪
        cropped = img.crop((crop_x0, crop_y0, crop_x1, crop_y1))
        # 缩放
        resized = cropped.resize((new_w, new_h), Image.LANCZOS)
        # 覆盖保存
        resized.save(f)

    print(f"  {name}: crop {crop_w}x{crop_h} → resize {new_w}x{new_h}  (scale={scale:.2f})")
    return new_w, new_h


def main():
    groups = get_action_groups()
    print(f"处理 {len(groups)} 个动作组...\n")

    max_w, max_h = 0, 0
    for name, files in sorted(groups.items()):
        w, h = process_action(name, files)
        max_w = max(max_w, w)
        max_h = max(max_h, h)

    # 5. 更新 pet_conf.json
    display_w = max_w
    display_h = max_h
    print(f"\n最大精灵图: {max_w}x{max_h}")

    for conf_path in [PET_CONF_PATH, ASSETS_PET_CONF]:
        with open(conf_path, "r", encoding="utf-8") as f:
            conf = json.load(f)
        conf["width"] = display_w
        conf["height"] = display_h
        conf["scale"] = 1.0
        with open(conf_path, "w", encoding="utf-8") as f:
            json.dump(conf, f, ensure_ascii=False, indent=2)
        print(f"pet_conf.json → {conf_path}  (size={display_w}x{display_h})")

    print("done.")


if __name__ == "__main__":
    main()
