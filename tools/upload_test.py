"""Container tests (never publishes). Args: name=url pairs. For each: classic video_url and resumable file_url."""
import os, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from post_instagram import HOST, VER, api
tok, uid = os.environ["IG_ACCESS_TOKEN"], os.environ["IG_USER_ID"]
base = f"https://{HOST}/{VER}"

def wait(cid):
    for _ in range(30):
        st = api("GET", f"{base}/{cid}", {"fields": "status_code,status", "access_token": tok})
        if st.get("status_code") in ("FINISHED", "ERROR", "EXPIRED"): return st
        time.sleep(10)
    return st

for arg in sys.argv[1:]:
    name, url = arg.split("=", 1)
    try:
        c = api("POST", f"{base}/{uid}/media", {"media_type": "REELS", "video_url": url, "caption": "test", "access_token": tok})
        print(name, "video_url ->", wait(c["id"]))
    except Exception as e: print(name, "video_url err", e)
    try:
        c = api("POST", f"{base}/{uid}/media", {"media_type": "REELS", "upload_type": "resumable", "caption": "test", "access_token": tok})
        api("POST", c["uri"], headers={"Authorization": f"OAuth {tok}", "file_url": url})
        print(name, "file_url ->", wait(c["id"]))
    except Exception as e: print(name, "file_url err", str(e)[:300])
print("DONE - nothing published")
