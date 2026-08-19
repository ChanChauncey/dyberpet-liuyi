import subprocess, json, sys, os

REPO = "ChanChauncey/dyberpet-liuyi"
TAG = "v1.0.7"
EXE = r"C:\DyberPet\dist_logo_inst\LiuYi_Setup_v1.0.7.exe"
SRC = r"C:\DyberPet\DyberPet_source.zip"
NAME = "六一桌宠 v1.0.7"
BODY = """## 六一桌宠 v1.0.7

### 安装向导优化
- **默认勾选「开机自动启动」**，安装后 Windows 登录即自动运行（仍可在安装界面取消）。
- **去除开始菜单选项的多余括号文案**：「创建开始菜单快捷方式」不再显示「(含卸载)」说明。
- **安装过程中隐藏「上一步」与「取消」按钮**：必须等待安装完成，避免中途取消导致目录半覆盖。
- **消除黑框**：安装向导检测/关闭正在运行的旧实例时，不再弹出控制台黑窗口。

### 设置优化
- **设置页「开机自动启动」开关改为中文**：卡片标题由「Auto-Start at Boot」改为「开机自动启动」，副标题改为「Windows 启动时自动运行六一桌宠」，与安装程序保持一致。
- **新增「开机自动启动」开关**（设置 → Mode）：状态与安装时的选择同步，切换即写入/删除注册表自启项。
- **「自动锁定」默认开启**：新装用户默认勾选（锁屏时暂停 HP/好感度变化）。

### 升级方式
- 从 v1.0.5/v1.0.6 升级：点「立即更新」下载约 247KB 增量源码包覆盖 `DyberPet/`，几秒完成。
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

# 清理已存在的 v1.0.7（release + tag），保证干净重建
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
print("=== uploading LiuYi_Setup_v1.0.7.exe ===", file=sys.stderr)
asset_url = up + "?name=LiuYi_Setup_v1.0.7.exe"
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
