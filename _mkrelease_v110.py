import subprocess, json, sys, os

REPO = "ChanChauncey/dyberpet-liuyi"
TAG = "v1.0.10"
EXE = r"C:\DyberPet\dist_logo_inst\LiuYi_Setup_v1.0.10.exe"
SRC = r"C:\DyberPet\DyberPet_source.zip"
NAME = "六一桌宠 v1.0.10"
BODY = """## 六一桌宠 v1.0.10

### 修复：v1.0.9 增量更新后仍「掉两个只进一个」
- **根因**：v1.0.9 把重复连接改在 `run_DyberPet.py` 里，但 `run_DyberPet.py` 是冻结在 `六一桌宠.exe` 里的入口文件，**不在增量更新包 `DyberPet_source.zip` 的覆盖范围内**。所以老用户用「立即更新」升到 v1.0.9 后，版本号虽然变了，但旧连接仍在，掉落/金币/升级奖励仍被两个背包各处理一次。
- **修复**：在**可被增量覆盖**的 `DyberPet/Dashboard/DashboardUI.py` 里加运行时修复：等 Dashboard 初始化、老入口点把信号连上之后，再异步断开 Dashboard 背包对 `addItem_toInven` / `addCoins` / `fvlvl_changed_main_inve` 的重复监听。这样老用户走增量升级也能真正修好。
- 同时保留 `run_DyberPet.py` 里的注释版清理（新装用户不再产生重复连接）。

### 仍包含 v1.0.9 的另外两项修复
- 点击小猫掉落物去重（断 Dashboard 背包重复监听）。
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

# 清理已存在的 v1.0.10（release + tag），保证干净重建
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
print("=== uploading LiuYi_Setup_v1.0.10.exe ===", file=sys.stderr)
asset_url = up + "?name=LiuYi_Setup_v1.0.10.exe"
rc2, out2, err2 = curl("POST", asset_url,
    {"Authorization": f"Bearer {tok}", "Content-Type": "application/octet-stream"},
    data=EXE, binary=True, timeout=1800)
print("upload exe rc=", rc2, "err=", err2[:300], file=sys.stderr)
if rc2 != 0:
    print("EXE_UPLOAD_FAIL")
    sys.exit(1)

print("ALL_UPLOAD_OK")
