import subprocess, json, sys, os

REPO = "ChanChauncey/dyberpet-liuyi"
OLD_ASSET_ID = 511763559
RELEASE_ID = 369356951
EXE = r"C:\Users\76215\Desktop\LiuYi_Setup.exe"

def git_token():
    out = subprocess.run(
        ["git", "-c", "credential.helper=", "-c", "credential.helper=wincred", "credential", "fill"],
        input="protocol=https\nhost=github.com\n", capture_output=True, text=True,
    ).stdout
    for line in out.splitlines():
        if line.startswith("password="):
            return line[len("password="):]
    raise SystemExit("no token")

def curl(method, url, headers, data=None, binary=False, timeout=600):
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

print("=== delete old asset", OLD_ASSET_ID, "===", file=sys.stderr)
rc, out, err = curl("DELETE",
    f"https://api.github.com/repos/{REPO}/releases/assets/{OLD_ASSET_ID}", auth)
print("delete rc=", rc, "err=", err[:200], file=sys.stderr)

print("=== upload new asset ===", file=sys.stderr)
asset_url = f"https://uploads.github.com/repos/{REPO}/releases/{RELEASE_ID}/assets?name=LiuYi_Setup.exe"
rc2, out2, err2 = curl("POST", asset_url,
    {"Authorization": f"Bearer {tok}", "Content-Type": "application/octet-stream"},
    data=EXE, binary=True, timeout=600)
print("upload rc=", rc2, "err=", err2[:300], file=sys.stderr)
print("upload resp=", out2[:200], file=sys.stderr)
print("DONE")
