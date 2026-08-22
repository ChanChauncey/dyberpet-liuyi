import subprocess, json, sys, os

REPO = "ChanChauncey/dyberpet-liuyi"
TAG = "v1.0.12"
EXE = r"C:\DyberPet\dist_logo_inst\LiuYi_Setup_v1.0.12.exe"
SRC = r"C:\DyberPet\DyberPet_source.zip"
NAME = "六一桌宠 v1.0.12"
BODY = """## 六一桌宠 v1.0.12

### 新增：背包双击使用物品
- 背包里双击物品即可直接使用，不必先点选再按「使用」按钮；空格子双击无效。

### 优化：点击小猫掉落概率显著提升
- 原逻辑把物品掉落钳死在约 8%~10%，且好感度加成完全失效。
- 改为独立掷骰判定：好感 0 时 30%、每级好感 +2%、好感 15 级封顶 60%。

### 优化：饱食度衰减调慢
- 默认从每分钟掉 1 点改为每 3 分钟掉 1 点（亲密值节奏不变），可在设置里调节快慢。

### 修复：启动动画卡顿
- 醒来动画开始时的「卡一下」修复：首帧单独轻量加载，整组帧改为后台线程预加载，不再阻塞启动。

### 修复：自动检查更新不彻底静默
- 无更新时保持静默，不再误弹提示框或浏览器。

### 修复：多处文件句柄未关闭
- 53 处文件读写统一改为 `with open(...)`，消除句柄泄漏。

### 升级方式
- **推荐**：点「立即更新」下载约几百 KB 的增量源码包覆盖 `DyberPet/`，几秒完成。
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

# 清理已存在的 v1.0.12（release + tag），保证干净重建
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
print("=== uploading LiuYi_Setup_v1.0.12.exe ===", file=sys.stderr)
asset_url = up + "?name=LiuYi_Setup_v1.0.12.exe"
rc2, out2, err2 = curl("POST", asset_url,
    {"Authorization": f"Bearer {tok}", "Content-Type": "application/octet-stream"},
    data=EXE, binary=True, timeout=1800)
print("upload exe rc=", rc2, "err=", err2[:300], file=sys.stderr)
if rc2 != 0:
    print("EXE_UPLOAD_FAIL")
    sys.exit(1)

print("ALL_UPLOAD_OK")
