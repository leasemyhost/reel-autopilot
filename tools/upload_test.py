"""Make an IG REELS container from PUBLIC_VIDEO_URL via rupload file_url and wait for FINISHED. Never publishes."""
import os, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from post_instagram import HOST, VER, api
tok, uid, url = os.environ["IG_ACCESS_TOKEN"], os.environ["IG_USER_ID"], os.environ["PUBLIC_VIDEO_URL"]
base = f"https://{HOST}/{VER}"
c = api("POST", f"{base}/{uid}/media", {"media_type": "REELS", "upload_type": "resumable", "caption": "test", "access_token": tok})
print("upload:", api("POST", c["uri"], headers={"Authorization": f"OAuth {tok}", "file_url": url}))
for _ in range(40):
    st = api("GET", f"{base}/{c['id']}", {"fields": "status_code,status", "access_token": tok})
    print("status:", st.get("status_code"), st.get("status", ""))
    if st.get("status_code") in ("FINISHED", "ERROR", "EXPIRED"):
        break
    time.sleep(10)
print("RESULT:", st.get("status_code"), "- NOT published")
sys.exit(0 if st.get("status_code") == "FINISHED" else 1)
