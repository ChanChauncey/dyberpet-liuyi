import subprocess, json, sys, os

REPO = "ChanChauncey/dyberpet-liuyi"
TAG = "v1.0.11"
EXE = r"C:\DyberPet\dist_logo_inst\LiuYi_Setup_v1.0.11.exe"
SRC = r"C:\DyberPet\DyberPet_source.zip"
NAME = "六一桌宠 v1.0.11"
BODY = """## 六一桌宠 v1.0.11

### 修复：v1.0.10 点击掉落完全不进背包
- **根因**：v1.0.10 在 `DashboardUI.py` 里加了运行时断开 Dashboard 背包信号的逻辑，而 `QApplication.instance().p` 确实存在，导致 Dashboard 背包一初始化就把自己的掉落/金币/升级奖励监听全断了；同时 `run_DyberPet.py` 里 Dashboard 的连接又被注释掉，最终没有任何背包在监听 `addItem_toInven`，所以点了小猫后通知和地面动画还在，但背包里一个都不进。
- **修复**：
  - 彻底移除 `DashboardUI.py` 里的自断信号逻辑。
  - `run_DyberPet.py` 启动时立即创建 `DashboardMainWindow` 并连接 Dashboard 背包信号，确保掉落、金币、升级奖励都有接收方。
  - `DyberPet.py` 中断掉旧的 `extra_windows.Inventory` 对掉落/金币/升级奖励的监听，避免两个背包重复处理。
  - `patpat()` 先随机选出要掉的物品，再带名字发射 `addItem_toInven(1, [item_name])`，`Dashboard/inventoryUI.py` 和 `extra_windows.py` 的 `add_items()` 也改成优先使用调用方指定的物品列表，防止多个背包各自随机出不同物品。

### 仍包含 v1.0.9/v1.0.10 的关联修复
- 点击小猫「掉两个只进一个」问题通过「单背包处理 + 掉落物品预选定」彻底解决。
- 更新时 UAC 提权不再弹黑框（`SW_HIDE`）。

### 升级方式
- **推荐**：点「立即更新」下载约 247KB 增量源码包覆盖 `DyberPet/`，几秒完成。
- 想完整重装：下载本完整安装包覆盖安装即可。
"""


def git_token():
    out = subprocess.run(
        ["git", "-c", "credential.helper=", "-c", "credential.helper=wincred", "credential", "fill"],
        input="protocol=https\nhost=github.com\n", capture_output=True, text=True,
    ).stdout
    for line in out.splitlines():
        if line.startswith("password="):
            return line[len("password="):]
    raise SystemExit("no token from wincred")


def curl(method, url, headers, data=None, binary=False, timeout=1800):
    cmd = ["curl", "-sS", "-m", str(timeout), "-X", method, url]
    for k, v in headers.items():
        cmd += ["-H", f"{k}: {v}"]
    if data is not None:
        cmd += ["--data-binary", "@" + data] if binary else ["-d", data]
    r = subprocess.run(cmd, capture_output=True, text=(not binary))
    return r.returncode, r.stdout, r.stderr


tok = git_token()
print("token length:", len(tok), file=sys.stderr)
auth = {"Authorization": f"Bearer {tok}", "Accept": "application/vnd.github+json"}
api = f"https://api.github.com/repos/{REPO}/releases"

# 清理已存在的 v1.0.11（release + tag），保证干净重建
rc, out, err = curl("GET", f"{api}/tags/{TAG}", auth)
print("lookup rc=", rc, "err=", err[:200], file=sys.stderr)
if rc == 0 and out.strip():
    try:
        rel = json.loads(out)
        rid = rel["id"]
        print("deleting existing release id=", rid, file=sys.stderr)
        curl("DELETE", f"{api}/{rid}", auth)
    except Exception as e:
        print("parse existing release failed:", e, file=sys.stderr)
dtrc, _, dterr = curl("DELETE",
    f"https://api.github.com/repos/{REPO}/git/refs/tags/{TAG}", auth)
print("delete tag rc=", dtrc, dterr[:120], file=sys.stderr)

# 创建新 release
print("=== creating release ===", file=sys.stderr)
payload = json.dumps({
    "tag_name": TAG,
    "name": NAME,
    "body": BODY,
    "draft": False,
    "prerelease": False,
})
rc, out, err = curl("POST", api, auth, data=payload)
print("create rc=", rc, "err=", err[:300], file=sys.stderr)
rel = json.loads(out)
rid = rel["id"]
up = rel["upload_url"].split("{")[0]
print("release id=", rid, "upload_url=", up, file=sys.stderr)

# 先传小体积增量源码包，让「立即更新」尽早可用（exe 上传期间用户也能走增量）
print("=== uploading DyberPet_source.zip ===", file=sys.stderr)
asset_url2 = up + "?name=DyberPet_source.zip"
rc3, out3, err3 = curl("POST", asset_url2,
    {"Authorization": f"Bearer {tok}", "Content-Type": "application/octet-stream"},
    data=SRC, binary=True, timeout=600)
print("upload src rc=", rc3, "err=", err3[:300], file=sys.stderr)
if rc3 != 0:
    print("SRC_UPLOAD_FAIL")
    sys.exit(1)

# 再传完整安装包
print("=== uploading LiuYi_Setup_v1.0.11.exe ===", file=sys.stderr)
asset_url = up + "?name=LiuYi_Setup_v1.0.11.exe"
rc2, out2, err2 = curl("POST", asset_url,
    {"Authorization": f"Bearer {tok}", "Content-Type": "application/octet-stream"},
    data=EXE, binary=True, timeout=1800)
print("upload exe rc=", rc2, "err=", err2[:300], file=sys.stderr)
if rc2 != 0:
    print("EXE_UPLOAD_FAIL")
    sys.exit(1)

print("ALL_UPLOAD_OK")
