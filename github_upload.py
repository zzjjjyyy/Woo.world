# -*- coding: utf-8 -*-
"""Upload the China atlas to zzjjjyyy/Woo.world under china-scenic-atlas/ via GitHub API.
Waits for the device-flow watcher to store a token, then creates one commit.
No token is written to logs.
"""
import os, json, base64, subprocess, time, hashlib

BASE = r"D:\DeepSeek Harness\artifacts"
SITE = r"D:\DeepSeek Harness\china-scenic-atlas"
TOKEN_FILE = os.path.join(BASE, "github_token.txt")
LOG = os.path.join(BASE, "github_upload.log")
TMP = os.path.join(BASE, "github_upload_tmp")
OWNER = "zzjjjyyy"
REPO = "Woo.world"
PREFIX = "china-scenic-atlas"
API = "https://api.github.com"
CURL = "curl.exe"
os.makedirs(TMP, exist_ok=True)

def log(msg):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(time.strftime("%H:%M:%S ") + str(msg) + "\n")

def token():
    for _ in range(1200):  # wait up to ~60 min for a manually supplied PAT
        if os.path.exists(TOKEN_FILE):
            t = open(TOKEN_FILE, encoding="utf-8").read().strip()
            if t:
                return t
        time.sleep(3)
    raise RuntimeError("token not found")

def api(method, path, body=None, max_time=180):
    out = os.path.join(TMP, "resp.json")
    if os.path.exists(out):
        os.remove(out)
    cmd = [CURL, "--ssl-no-revoke", "-sS", "-L", "--max-time", str(max_time),
           "-X", method, "-o", out,
           "-H", "Authorization: Bearer " + TOKEN_VALUE,
           "-H", "Accept: application/vnd.github+json",
           "-H", "X-GitHub-Api-Version: 2022-11-28",
           "-H", "User-Agent: dsh-atlas-upload"]
    if body is not None:
        bp = os.path.join(TMP, "body.json")
        with open(bp, "w", encoding="utf-8") as f:
            json.dump(body, f, ensure_ascii=False, separators=(",", ":"))
        cmd += ["--data-binary", "@" + bp]
    cmd.append(API + path)
    cp = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    raw = ""
    if os.path.exists(out):
        raw = open(out, encoding="utf-8", errors="replace").read()
    try:
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        data = {"_raw": raw[:500]}
    if cp.returncode != 0 or (isinstance(data, dict) and data.get("message") and "sha" not in data and "tree" not in data and "object" not in data):
        raise RuntimeError(f"{method} {path} failed rc={cp.returncode} data={data}")
    return data

def main():
    global TOKEN_VALUE
    log("uploader waiting for token")
    TOKEN_VALUE = token()
    log("token received")
    user = api("GET", "/user")
    log("authenticated as " + str(user.get("login")))
    repo = api("GET", f"/repos/{OWNER}/{REPO}")
    perms = repo.get("permissions") or {}
    log("repo permissions push=" + str(perms.get("push")) + " admin=" + str(perms.get("admin")))
    if not perms.get("push"):
        raise RuntimeError("token has no push permission on target repo / wrong account")
    ref = api("GET", f"/repos/{OWNER}/{REPO}/git/ref/heads/main")
    head = ref["object"]["sha"]
    commit = api("GET", f"/repos/{OWNER}/{REPO}/git/commits/{head}")
    base_tree = commit["tree"]["sha"]
    log("head=" + head[:10] + " base_tree=" + base_tree[:10])

    entries = []
    files = []
    for dp, dns, fns in os.walk(SITE):
        for fn in fns:
            full = os.path.join(dp, fn)
            rel = os.path.relpath(full, SITE).replace("\\", "/")
            files.append((full, rel))
    files.sort(key=lambda x: x[1])
    log("files=" + str(len(files)))
    total = sum(os.path.getsize(f) for f, _ in files)
    log("bytes=" + str(total))
    sha_before = hashlib.sha256(open(TOKEN_FILE, "rb").read()).hexdigest()
    for i, (full, rel) in enumerate(files):
        data = open(full, "rb").read()
        content = base64.b64encode(data).decode("ascii")
        # create blob (retry transient API errors)
        for attempt in range(4):
            try:
                res = api("POST", f"/repos/{OWNER}/{REPO}/git/blobs", {
                    "content": content, "encoding": "base64",
                })
                break
            except Exception as e:
                if attempt == 3:
                    raise
                log("blob retry " + rel + " " + str(e)[:120])
                time.sleep(4 * (attempt + 1))
        entries.append({
            "path": f"{PREFIX}/{rel}", "mode": "100644", "type": "blob", "sha": res["sha"],
        })
        if (i + 1) % 10 == 0 or (i + 1) == len(files):
            log(f"blob {i+1}/{len(files)} {rel}")
    tree = api("POST", f"/repos/{OWNER}/{REPO}/git/trees", {
        "base_tree": base_tree, "tree": entries,
    })
    log("new tree=" + tree["sha"][:10])
    new_commit = api("POST", f"/repos/{OWNER}/{REPO}/git/commits", {
        "message": "Add 山河志 · 中国三维地形旅游地图\n\n- 358 个 5A 景区静态数据\n- 真实 DEM 地形、分层设色、河湖水系与立体海岸\n- 景区详情、图集与主题视频模块\n- 本地预览脚本与数据说明",
        "tree": tree["sha"],
        "parents": [head],
    })
    log("new commit=" + new_commit["sha"][:10])
    api("PATCH", f"/repos/{OWNER}/{REPO}/git/refs/heads/main", {
        "sha": new_commit["sha"], "force": False,
    })
    log("ref updated -> main")
    # Verify the folder and one representative file exist in the new tree
    chk = api("GET", f"/repos/{OWNER}/{REPO}/contents/{PREFIX}/index.html?ref=main")
    log("verified " + str(chk.get("path")) + " size=" + str(chk.get("size")))
    with open(os.path.join(BASE, "github_upload_done.json"), "w", encoding="utf-8") as f:
        json.dump({
            "status": "success", "repo": f"{OWNER}/{REPO}", "folder": PREFIX,
            "commit": new_commit["sha"], "html_url": f"https://github.com/{OWNER}/{REPO}/tree/main/{PREFIX}",
            "file_count": len(files), "bytes": total,
        }, f, ensure_ascii=False, indent=2)
    log("DONE https://github.com/" + OWNER + "/" + REPO + "/tree/main/" + PREFIX)
    # Remove local token after success
    try:
        os.remove(TOKEN_FILE)
        log("local token removed")
    except Exception:
        pass

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log("FAILED " + repr(e))
