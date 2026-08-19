import subprocess, json, sys, os

REPO = "ChanChauncey/dyberpet-liuyi"
EXE = r"C:\Users\76215\Desktop\LiuYi_Setup.exe"
TAG = "v1.0.4"
BODY = (
    "LiuYi Desktop Pet v1.0.4\n\n"
    "- Check for updates, then ask to confirm before downloading/installing\n"
    "- On confirm: auto-download with progress, silent install, auto-restart, data kept\n"
    "- Installer detects a running instance and can close it for you before installing\n"
    "- Check-update result shown at top of window; current version shown in About\n\n"
    "Download LiuYi_Setup.exe to install."
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

tok = git_token()
print("token length:", len(tok), file=sys.stderr)
auth = {"Authorization": f"Bearer {tok}", "Accept": "application/vnd.github+json"}
api = f"https://api.github.com/repos/{REPO}/releases"

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
asset_url = up + "?name=LiuYi_Setup.exe"
print("asset_url=", asset_url, file=sys.stderr)

print("=== uploading asset (may take a while) ===", file=sys.stderr)
rc2, out2, err2 = curl("POST", asset_url,
    {"Authorization": f"Bearer {tok}", "Content-Type": "application/octet-stream"},
    data=EXE, binary=True, timeout=900)
print("upload rc=", rc2, "err=", err2[:300], file=sys.stderr)
print("upload resp=", out2[:300], file=sys.stderr)
print("DONE")
