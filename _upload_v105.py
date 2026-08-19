import subprocess, json, sys, os

REPO = "ChanChauncey/dyberpet-liuyi"
EXE = r"C:\DyberPet\dist_logo_inst\LiuYi_Setup_v1.0.5.exe"
TAG = "v1.0.5"


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

# 找到已存在的 v1.0.5 发布（前面创建过但 asset 上传失败，release 已存在）
rc, out, err = curl("GET", f"{api}/tags/{TAG}", auth)
print("lookup rc=", rc, "err=", err[:200], file=sys.stderr)
rel = json.loads(out)
rid = rel["id"]
print("release id=", rid, file=sys.stderr)

# 若已有同名 asset 先删掉，避免重复
for a in rel.get("assets", []):
    name = a.get("name")
    print("existing asset:", name, file=sys.stderr)
    d_rc, _, d_err = curl("DELETE", f"{api}/assets/{a['id']}", auth)
    print("  delete rc=", d_rc, d_err[:120], file=sys.stderr)

up = rel["upload_url"].split("{")[0]
print("upload_url:", up, file=sys.stderr)

print("=== uploading LiuYi_Setup_v1.0.5.exe ===", file=sys.stderr)
asset_url = up + "?name=LiuYi_Setup_v1.0.5.exe"
rc2, out2, err2 = curl("POST", asset_url,
    {"Authorization": f"Bearer {tok}", "Content-Type": "application/octet-stream"},
    data=EXE, binary=True, timeout=1800)
print("upload exe rc=", rc2, "err=", err2[:300], file=sys.stderr)
print("upload exe resp=", out2[:300], file=sys.stderr)

if rc2 == 0:
    print("UPLOAD_OK")
else:
    print("UPLOAD_FAIL")
    sys.exit(1)
