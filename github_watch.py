# -*- coding: utf-8 -*-
"""Wait for GitHub device authorization and store the token locally (no token in logs)."""
import json, subprocess, time, os

BASE = r"D:\DeepSeek Harness\artifacts"
DEVICE = os.path.join(BASE, "github_device.json")
TOKEN = os.path.join(BASE, "github_token.txt")
LOG = os.path.join(BASE, "github_watch.log")
CURL = "curl.exe"

def log(msg):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(time.strftime("%H:%M:%S ") + msg + "\n")

dev = json.load(open(DEVICE, encoding="utf-8"))
client = dev["client_id"]
device = dev["device_code"]
expires_at = dev["expires_at"]
log("watcher start")
interval = 5
while True:
    # check expiry using ISO time without extra deps
    try:
        from datetime import datetime, timezone
        exp = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        if datetime.now(timezone.utc) >= exp:
            log("authorization code expired")
            break
    except Exception:
        pass
    time.sleep(interval)
    try:
        cp = subprocess.run([
            CURL, "--ssl-no-revoke", "-sS", "-L", "--max-time", "25",
            "-X", "POST", "-H", "Accept: application/json",
            "-H", "User-Agent: dsh-github-upload",
            "-d", f"client_id={client}&device_code={device}&grant_type=urn:ietf:params:oauth:grant-type:device_code",
            "https://github.com/login/oauth/access_token",
        ], capture_output=True, text=True, encoding="utf-8", errors="replace")
        raw = (cp.stdout or "").strip()
        data = json.loads(raw) if raw.startswith("{") else {}
    except Exception as e:
        log("poll error " + repr(e))
        interval = min(15, interval + 2)
        continue
    if data.get("access_token"):
        with open(TOKEN, "w", encoding="utf-8", newline="") as f:
            f.write(data["access_token"])
        log("authorized; token stored; scope=" + str(data.get("scope")))
        break
    err = data.get("error")
    if err == "authorization_pending":
        continue
    if err == "slow_down":
        interval = min(20, interval + 5)
        log("slow_down; interval=" + str(interval))
        continue
    if err:
        log("auth stopped: " + str(err) + " " + str(data.get("error_description", "")))
        break
log("watcher exit")
