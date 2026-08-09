"""验证「保留原有游戏数据」选项的行为。"""
import json
import os
import subprocess

T = r"C:\Users\76215\AppData\Local\Temp\liuyi_savechk"
INST = r"C:\DyberPet\installer\dist_inst_new3\六一桌宠安装程序.exe"
PET = os.path.join(T, "data", "pet_data.json")

FAKE = {"六一": {"HP": 150, "HP_tier": 3, "FV": 88, "FV_lvl": 5,
                 "fv_sys_ver": "v2", "items": {"苹果": [1, 9]},
                 "coins": 999, "days": 30, "last_opened": "2026-8-8"}}


def show(tag):
    with open(PET, encoding="utf-8") as f:
        raw = f.read()
    try:
        d = json.loads(raw)
    except Exception:
        print("  %s -> unreadable" % tag)
        return
    p = d.get("六一")
    if not p:
        print("  %s -> EMPTY (全新开始)  raw=%s" % (tag, raw[:40]))
    else:
        print("  %s -> coins=%s FV_lvl=%s days=%s items=%s"
              % (tag, p.get("coins"), p.get("FV_lvl"), p.get("days"), p.get("items")))


def run(args):
    r = subprocess.run([INST, "--silent", "--target", T] + args,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return r.returncode


# 造一份"玩了很久"的存档
with open(PET, "w", encoding="utf-8") as f:
    json.dump(FAKE, f, ensure_ascii=False)
print("[setup] 伪造存档:")
show("before")

print("\n[A] 重装 + 勾选保留数据 (--keep-data):")
run(["--keep-data"])
show("after ")

print("\n[B] 重装 + 不保留 (默认, 全新开始):")
# 再造一次存档，确认这次会被清掉
with open(PET, "w", encoding="utf-8") as f:
    json.dump(FAKE, f, ensure_ascii=False)
run([])
show("after ")
