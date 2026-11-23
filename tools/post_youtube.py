"""Upload a reel to YouTube as a Short (vertical, < 3 min). Uses scope youtube.upload only.
Env: YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN."""
import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path


def _req(url, data=None, headers=None, method=None):
    r = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(r, timeout=600) as resp:
            return resp.status, dict(resp.headers), resp.read()
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{method or 'GET'} {url.split('?')[0]} -> {e.code}: {e.read()[:600]!r}")


def access_token():
    body = urllib.parse.urlencode({
        "client_id": os.environ["YT_CLIENT_ID"], "client_secret": os.environ["YT_CLIENT_SECRET"],
        "refresh_token": os.environ["YT_REFRESH_TOKEN"], "grant_type": "refresh_token"}).encode()
    _, _, out = _req("https://oauth2.googleapis.com/token", body, {"Content-Type": "application/x-www-form-urlencoded"}, "POST")
    return json.loads(out)["access_token"]


def short_title(caption):
    first = next((l.strip() for l in caption.splitlines() if l.strip()), "AI trick")
    first = re.sub(r"#\S+", "", first).strip()
    t = (first[:85]).rstrip() + " #Shorts"
    return t[:100]


def upload_short(video, caption, tags=None):
    tok = access_token()
    meta = {
        "snippet": {"title": short_title(caption), "description": caption[:4900] + "\n\n#Shorts",
                    "tags": tags or ["AI tools", "AI Hindi", "ChatGPT", "Jayant Ke Guides"],
                    "categoryId": "28", "defaultLanguage": "hi", "defaultAudioLanguage": "hi"},
        "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False, "containsSyntheticMedia": False},
    }
    size = Path(video).stat().st_size
    _, h, _ = _req("https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
                   json.dumps(meta).encode(),
                   {"Authorization": f"Bearer {tok}", "Content-Type": "application/json; charset=UTF-8",
                    "X-Upload-Content-Type": "video/mp4", "X-Upload-Content-Length": str(size)}, "POST")
    loc = h.get("Location") or h.get("location")
    _, _, out = _req(loc, Path(video).read_bytes(), {"Content-Type": "video/mp4", "Content-Length": str(size)}, "PUT")
    v = json.loads(out)
    return v["id"], v.get("status", {}).get("privacyStatus"), f"https://youtube.com/shorts/{v['id']}"


if __name__ == "__main__":
    import sys
    print(upload_short(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "Test upload"))
