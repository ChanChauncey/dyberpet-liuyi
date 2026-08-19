import subprocess, json, sys, os

REPO = "ChanChauncey/dyberpet-liuyi"
EXE = r"C:\DyberPet\dist_logo_inst\LiuYi_Setup_v1.0.5.exe"
TAG = "v1.0.5"
BODY = (
    "LiuYi Desktop Pet v1.0.5\n\n"
    "- Fix import hook so that DyberPet submodules (e.g. DyberPet.settings) are loaded\n"
    "  from the loose source folder in the install directory after a differential update,\n"
    "  instead of from the frozen copy embedded in the exe.\n"
    "- This release is distributed as a full installer only; existing v1.0.4 users will\n"
    "  receive the full setup package automatically to replace the buggy executable.\n"
    "- Differential updates will be re-enabled starting from the next release.\n\n"
    "Download LiuYi_Setup_v1.0.5.exe and run it to install or upgrade."
)


def git_token():
    out = subprocess.run(
        ["git", "-c", "credential.helper=", "-c", "credential.helper=wincred", "credential", "fill"],
        input="protocol=https\nhost=github.com\n", capture_output=True, text=True,
    ).stdout
    for line in out.splitlines():
        if line.startswith("password="):
            return line[len("password="):]
    raise SystemExit("no token from wincred")


def curl(method, url, headers, data=None, binary=False, timeout=900):
    cmd = ["curl", "-sS", "-m", str(timeout), "-X", method, url]
    for k, v in headers.items():
        cmd += ["-H", f"{k}: {v}"]
    if data is not None:
        cmd += ["--data-binary", "@" + data] if binary else ["-d", data]
    r = subprocess.run(cmd, capture_output=True, text=(not binary))
    return r.returncode, r.stdout, r.stderr


if not os.path.isfile(EXE):
    raise SystemExit(f"EXE not found: {EXE}")
print("exe size:", os.path.getsize(EXE), file=sys.stderr)

tok = git_token()
print("token length:", len(tok), file=sys.stderr)
auth = {"Authorization": f"Bearer {tok}", "Accept": "application/vnd.github+json"}
api = f"https://api.github.com/repos/{REPO}/releases"

# 1) 找到并删除现有 v1.0.4 / v1.0.5 发布（避免同 tag 冲突，并移除旧增量包）
for old_tag in ["v1.0.4", "v1.0.5"]:
    print(f"=== lookup existing release {old_tag} ===", file=sys.stderr)
    rc, out, err = curl("GET", f"{api}/tags/{old_tag}", auth)
    print("lookup rc=", rc, "err=", err[:200], file=sys.stderr)
    if rc == 0 and out.strip():
        try:
            rel = json.loads(out)
            rid = rel.get("id")
            if rid:
                print("deleting existing release id=", rid, file=sys.stderr)
                d_rc, d_out, d_err = curl("DELETE", f"{api}/{rid}", auth)
                print("delete release rc=", d_rc, "err=", d_err[:200], file=sys.stderr)
        except Exception as e:
            print("parse existing release failed:", e, file=sys.stderr)

    print(f"=== delete existing tag {old_tag} ===", file=sys.stderr)
    t_rc, t_out, t_err = curl("DELETE", f"https://api.github.com/repos/{REPO}/git/refs/tags/{old_tag}", auth)
    print("delete tag rc=", t_rc, "err=", t_err[:200], file=sys.stderr)

# 2) 重新创建 v1.0.5 发布
print("=== creating release ===", file=sys.stderr)
rc, out, err = curl("POST", api, auth, json.dumps({
    "tag_name": TAG, "name": TAG, "body": BODY,
    "draft": False, "prerelease": False,
}))
print("create rc=", rc, "err=", err[:200], file=sys.stderr)
if rc != 0:
    print("CREATE_FAILED")
    sys.exit(1)
rel = json.loads(out)
print("release id=", rel.get("id"), file=sys.stderr)
up = rel["upload_url"].split("{")[0]

# 3) 上传完整安装包（约 247MB，可能耗时）
print("=== uploading LiuYi_Setup_v1.0.5.exe ===", file=sys.stderr)
asset_url = up + "?name=LiuYi_Setup_v1.0.5.exe"
rc2, out2, err2 = curl("POST", asset_url,
    {"Authorization": f"Bearer {tok}", "Content-Type": "application/octet-stream"},
    data=EXE, binary=True, timeout=1800)
print("upload exe rc=", rc2, "err=", err2[:300], file=sys.stderr)
print("upload exe resp=", out2[:300], file=sys.stderr)

print("DONE")
