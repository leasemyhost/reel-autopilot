"""Try several ways to get a video into an IG REELS container. Never publishes."""
import os, sys, time, json, urllib.request, urllib.error
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from post_instagram import HOST, VER, api
tok, uid = os.environ["IG_ACCESS_TOKEN"], os.environ["IG_USER_ID"]
video = Path(sys.argv[1]); size = video.stat().st_size
base = f"https://{HOST}/{VER}"
RAW = "https://raw.githubusercontent.com/leasemyhost/reel-autopilot/main/tests/sample.mp4"

def raw_post(url, headers, data=None):
    req = urllib.request.Request(url, method="POST", data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=300) as r: return r.status, r.read()[:300]
    except urllib.error.HTTPError as e: return e.code, e.read()[:300]

def wait(cid):
    for _ in range(30):
        st = api("GET", f"{base}/{cid}", {"fields": "status_code,status", "access_token": tok})
        if st.get("status_code") in ("FINISHED", "ERROR", "EXPIRED"): return st
        time.sleep(10)
    return st

def container(**extra):
    return api("POST", f"{base}/{uid}/media", {"media_type": "REELS", "caption": "test", "access_token": tok, **extra})

try:
    s = urllib.request.urlopen(urllib.request.Request(RAW, method="HEAD"), timeout=30).status
except Exception as e: s = str(e)
print("raw github url public?:", s)

# A: resumable, bare headers
c = container(upload_type="resumable"); print("A uri:", c.get("uri"))
print("A upload:", raw_post(c["uri"], {"Authorization": f"OAuth {tok}", "offset": "0", "file_size": str(size)}, video.read_bytes()))
# B: resumable, file_url header (rupload fetches the public url)
c = container(upload_type="resumable")
print("B upload:", raw_post(c["uri"], {"Authorization": f"OAuth {tok}", "file_url": RAW}))
print("B status:", wait(c["id"]))
# C: classic video_url
try:
    c = container(video_url=RAW); print("C status:", wait(c["id"]))
except Exception as e: print("C err:", e)
print("DONE - nothing published")
