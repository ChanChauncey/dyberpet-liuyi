import subprocess, json, sys, os

REPO = "ChanChauncey/dyberpet-liuyi"
TAG = "v1.0.8"
EXE = r"C:\DyberPet\dist_logo_inst\LiuYi_Setup_v1.0.8.exe"
SRC = r"C:\DyberPet\DyberPet_source.zip"
NAME = "六一桌宠 v1.0.8"
BODY = """## 六一桌宠 v1.0.8

### 修复：点击小猫掉落物异常
- **点击小猫只掉 1 个物品**：此前一次点击偶发触发两次 `patpat()`（鼠标 release 事件重复触发 / 快速双击），导致掉出 2 个东西、但背包只新增 1 个（第二个通知被合并）。
- 已加入 **200ms 防抖**：同一次点击在 200ms 内只响应第一次，后面的重复触发直接忽略。
- 同时修正了背包 `add_items()` 的物品合并逻辑，确保多物品计数准确、与掉落通知一一对应。

### 升级方式
- 从 v1.0.5/v1.0.6/v1.0.7 升级：点「立即更新」下载约 247KB 增量源码包覆盖 `DyberPet/`，几秒完成。
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

# 清理已存在的 v1.0.8（release + tag），保证干净重建
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
print("=== uploading LiuYi_Setup_v1.0.8.exe ===", file=sys.stderr)
asset_url = up + "?name=LiuYi_Setup_v1.0.8.exe"
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
