"""Upload a video to Instagram as a REELS container and wait for FINISHED - never publishes."""
import os, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from post_instagram import HOST, VER, api
tok, uid = os.environ["IG_ACCESS_TOKEN"], os.environ["IG_USER_ID"]
video = Path(sys.argv[1])
base = f"https://{HOST}/{VER}"
c = api("POST", f"{base}/{uid}/media", {"media_type": "REELS", "upload_type": "resumable", "caption": "upload test (not published)", "access_token": tok})
print("container:", c.get("id"), "uri:", "yes" if c.get("uri") else "no")
uri = c.get("uri") or f"https://rupload.facebook.com/ig-api-upload/{VER}/{c['id']}"
r = api("POST", uri, headers={"Authorization": f"OAuth {tok}", "offset": "0", "file_size": str(video.stat().st_size)}, data=video.read_bytes())
print("upload:", r)
for _ in range(40):
    st = api("GET", f"{base}/{c['id']}", {"fields": "status_code,status", "access_token": tok})
    print("status:", st.get("status_code"), st.get("status", ""))
    if st.get("status_code") in ("FINISHED", "ERROR", "EXPIRED"):
        break
    time.sleep(10)
print("RESULT:", st.get("status_code"), "- NOT published (test only)")
