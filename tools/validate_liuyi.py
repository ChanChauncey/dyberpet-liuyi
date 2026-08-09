# -*- coding: utf-8 -*-
"""无头校验六一角色文件完整性（等价于 conf.CheckCharFiles 的逻辑，但无需 PySide6）。"""
import os, re, json, glob

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "dyberpet", "res", "role", "六一")

def load(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def main():
    ok = True
    # 1. pet_conf / act_conf 可读
    try:
        pet = load(os.path.join(OUT, "pet_conf.json"))
    except Exception as e:
        print("FAIL [1] pet_conf.json:", e); return
    try:
        act = load(os.path.join(OUT, "act_conf.json"))
    except Exception as e:
        print("FAIL [2] act_conf.json:", e); return
    print("[ok] pet_conf.json / act_conf.json 解析成功")

    # 2. 每个 action 有 images，且 PNG 帧索引连续
    error_action, missing_imgs = [], []
    for name, d in act.items():
        if "images" not in d:
            error_action.append(name); continue
        images = d["images"]
        img_dir = os.path.normpath(os.path.join(OUT, f"action/{images}"))
        files = glob.glob(f"{img_dir}_*.png")
        pat = re.compile(rf"^{re.escape(images)}_(\d+)\.png$")
        idx = sorted([int(pat.match(os.path.basename(x)).group(1)) for x in files if pat.match(os.path.basename(x))],
                     key=lambda v: int(v))
        if not idx:
            missing_imgs.append(f"{img_dir}_*.png (无文件)"); continue
        pw = len(str(idx[0]))
        m, n = idx[0], idx[-1]
        miss = [f"{img_dir}_{i:0{pw}}.png" for i in range(m, n + 1) if i not in set(idx)]
        missing_imgs += miss
    if error_action:
        ok = False; print("FAIL [3] 缺 images 属性:", error_action)
    else:
        print("[ok] 所有 action 含 images 属性")
    if missing_imgs:
        ok = False; print(f"FAIL [4] 缺帧 ({len(missing_imgs)}):", missing_imgs[:10])
    else:
        print("[ok] 所有 action 帧索引连续无缺失")

    # 3. required keys
    req = ["default", "drag", "fall"]
    miss = [k for k in req if k not in pet]
    if miss:
        ok = False; print("FAIL [5] pet_conf 缺必需 key:", miss)
    else:
        print("[ok] pet_conf 含必需 key:", req)

    # 4. pet_conf 引用的 action 都存在于 act_conf
    keys = ["default", "up", "down", "left", "right", "drag", "fall", "on_floor"]
    refs = [pet[k] for k in keys if k in pet]
    if "patpat" in pet:
        p = pet["patpat"]
        refs += [p] if isinstance(p, str) else list(p.values())
    for r in pet.get("random_act", []):
        refs += r.get("act_list", [])
    for r in pet.get("accessory_act", []):
        refs += r.get("act_list", []) + r.get("acc_list", [])
    missing = [a for a in set(refs) if a not in act]
    if missing:
        ok = False; print("FAIL [6] pet_conf 引用的 action 不在 act_conf:", missing)
    else:
        print("[ok] pet_conf 引用的所有 action 均存在于 act_conf")

    # 5. info
    info_path = os.path.join(OUT, "info", "info.json")
    if os.path.exists(info_path):
        info = load(info_path)
        pfp = os.path.join(OUT, "info", info.get("pfp", ""))
        cov = os.path.join(OUT, "info", (info.get("coverImages") or [""])[0])
        print(f"[ok] info/info.json: petName={info.get('petName')!r}, pfp存在={os.path.exists(pfp)}, cover存在={os.path.exists(cov)}")
        if not os.path.exists(pfp) or not os.path.exists(cov):
            ok = False; print("FAIL [7] 角色卡图片缺失")
    else:
        ok = False; print("FAIL [7] info/info.json 缺失")

    print("\n==>", "全部通过 ✅" if ok else "存在错误 ❌")

if __name__ == "__main__":
    main()
