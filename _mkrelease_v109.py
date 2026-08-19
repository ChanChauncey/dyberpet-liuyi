import subprocess, json, sys, os

REPO = "ChanChauncey/dyberpet-liuyi"
TAG = "v1.0.9"
EXE = r"C:\DyberPet\dist_logo_inst\LiuYi_Setup_v1.0.9.exe"
SRC = r"C:\DyberPet\DyberPet_source.zip"
NAME = "六一桌宠 v1.0.9"
BODY = """## 六一桌宠 v1.0.9

### 修复 1：点击小猫「掉两个只进一个」
- **根因**：掉落信号 `addItem_toInven` 同时连到了「老背包」和「新 Dashboard 背包」两个槽，一次点击被两处各自随机选物，于是弹出两个掉落通知，但老背包只新增了一个，另一个进了用户没注意到的 Dashboard 背包。同样的问题还会导致金币通知翻倍、好感度升级奖励翻倍。
- **修复**：断开 Dashboard 背包对掉落/金币/升级奖励信号的监听，只保留老背包处理。顺手统一了两处背包的物品合并计数逻辑。

### 修复 2：更新时不再弹黑框
- **根因**：桌宠内点「立即更新」、装在受保护目录（如 `C:\\Program Files`）时，增量覆盖 `DyberPet/` 无写权限会走 UAC 提权，原本用 `cmd /c robocopy` 复制补丁，提权后的控制台窗口被设为可见 → 弹黑框。
- **修复**：`ShellExecuteEx` 的 `nShow` 改为 `SW_HIDE`，提权后的控制台静默执行，UAC 同意/取消的系统弹窗不受影响。

### 升级方式
- 从 v1.0.5/v1.0.6/v1.0.7/v1.0.8 升级：点「立即更新」下载约 247KB 增量源码包覆盖 `DyberPet/`，几秒完成。
- 想体验**安装向导**的全部优化，请重新运行本完整安装包（覆盖安装即可）。
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

# 清理已存在的 v1.0.9（release + tag），保证干净重建
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

# 上传完整安装包
print("=== uploading LiuYi_Setup_v1.0.9.exe ===", file=sys.stderr)
asset_url = up + "?name=LiuYi_Setup_v1.0.9.exe"
rc2, out2, err2 = curl("POST", asset_url,
    {"Authorization": f"Bearer {tok}", "Content-Type": "application/octet-stream"},
    data=EXE, binary=True, timeout=1800)
print("upload exe rc=", rc2, "err=", err2[:300], file=sys.stderr)
if rc2 != 0:
    print("EXE_UPLOAD_FAIL")
    sys.exit(1)

# 上传增量源码包
print("=== uploading DyberPet_source.zip ===", file=sys.stderr)
asset_url2 = up + "?name=DyberPet_source.zip"
rc3, out3, err3 = curl("POST", asset_url2,
    {"Authorization": f"Bearer {tok}", "Content-Type": "application/octet-stream"},
    data=SRC, binary=True, timeout=600)
print("upload src rc=", rc3, "err=", err3[:300], file=sys.stderr)
if rc3 != 0:
    print("SRC_UPLOAD_FAIL")
    sys.exit(1)

print("ALL_UPLOAD_OK")
