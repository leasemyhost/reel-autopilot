"""Publish the next ready reel from queue/ to Instagram via the official Graph API (resumable upload).

Env (GitHub Actions secrets):
  IG_USER_ID        Instagram professional account id
  IG_ACCESS_TOKEN   long-lived token (instagram_business_content_publish)
  IG_GRAPH_HOST     graph.instagram.com (Instagram Login, default) or graph.facebook.com (Facebook Login)
  IG_API_VERSION    default v22.0
Usage: python3 tools/post_instagram.py [--slot morning|noon|evening] [--dry-run]
"""
import argparse
import datetime as dt
import json
import os
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOST = os.environ.get("IG_GRAPH_HOST", "graph.instagram.com")
VER = os.environ.get("IG_API_VERSION", "v22.0")


def api(method, url, params=None, headers=None, data=None):
    if params:
        url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, method=method, data=data, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{method} {url.split('?')[0]} -> {e.code}: {e.read()[:500]!r}")


def upload_binary(uri, video, tok):
    """POST the raw file to the rupload uri. urllib defaults to form-urlencoded, which rupload rejects."""
    size = video.stat().st_size
    return api("POST", uri, headers={"Authorization": f"OAuth {tok}", "offset": "0", "file_size": str(size),
                                     "Content-Type": "application/octet-stream",
                                     "Content-Length": str(size)}, data=video.read_bytes())


def next_item(slot=None):
    items = []
    for meta in sorted((ROOT / "queue").glob("*/meta.json")):
        m = json.load(open(meta))
        if m.get("status") == "ready" and not m.get("skip"):
            items.append((m.get("slot") != slot, m.get("created", ""), meta.parent, m))
    items.sort(key=lambda x: (x[0], x[1]))
    return items[0][2:] if items else (None, None)


def publish(video, caption, uid, tok, video_url=None):
    base = f"https://{HOST}/{VER}"
    video_url = video_url or os.environ.get("PUBLIC_VIDEO_URL")
    if video_url:  # tested: classic video_url is reliable with the system-user token
        c = api("POST", f"{base}/{uid}/media", {"media_type": "REELS", "video_url": video_url, "caption": caption,
                                               "share_to_feed": "true", "access_token": tok})
        cid = c["id"]
    else:
        c = api("POST", f"{base}/{uid}/media", {"media_type": "REELS", "upload_type": "resumable", "caption": caption,
                                               "share_to_feed": "true", "access_token": tok})
        cid = c["id"]
        upload_binary(c.get("uri") or f"https://rupload.facebook.com/ig-api-upload/{VER}/{cid}", video, tok)
    for _ in range(60):
        st = api("GET", f"{base}/{cid}", {"fields": "status_code,status", "access_token": tok})
        if st.get("status_code") == "FINISHED":
            break
        if st.get("status_code") in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"container {cid} failed: {st}")
        time.sleep(10)
    else:
        raise RuntimeError("processing timeout")
    r = api("POST", f"{base}/{uid}/media_publish", {"creation_id": cid, "access_token": tok})
    media_id = r["id"]
    try:
        link = api("GET", f"{base}/{media_id}", {"fields": "permalink", "access_token": tok}).get("permalink")
    except Exception:
        link = None
    return media_id, link


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slot")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    folder, m = next_item(a.slot)
    if not folder:
        print("queue empty - nothing to post")
        return 0
    caption = (folder / "caption.txt").read_text().strip()
    video = folder / "reel.mp4"
    print(f"posting {folder.name}: {m.get('title')}")
    if a.dry_run:
        print(caption[:300])
        return 0
    media_id, link = publish(video, caption, os.environ["IG_USER_ID"], os.environ["IG_ACCESS_TOKEN"])
    m.update(status="posted", media_id=media_id, permalink=link, posted_at=dt.datetime.utcnow().isoformat() + "Z")
    dest = ROOT / "posted" / folder.name
    dest.mkdir(parents=True, exist_ok=True)
    json.dump(m, open(dest / "meta.json", "w"), indent=2, ensure_ascii=False)
    shutil.copy(folder / "caption.txt", dest / "caption.txt")
    shutil.rmtree(folder)  # video removed after posting to keep the repo small
    print("posted:", media_id, link)
    return 0


if __name__ == "__main__":
    sys.exit(main())


def publish_facebook_reel(video, caption, page_id, page_token):
    """Facebook Page Reels API: start -> binary upload -> finish (published)."""
    base = f"https://graph.facebook.com/{VER}"
    st = api("POST", f"{base}/{page_id}/video_reels", {"upload_phase": "start", "access_token": page_token})
    vid = st["video_id"]
    up = st.get("upload_url") or f"https://rupload.facebook.com/video-upload/{VER}/{vid}"
    api("POST", up, headers={"Authorization": f"OAuth {page_token}", "offset": "0", "file_size": str(video.stat().st_size)},
        data=video.read_bytes())
    api("POST", f"{base}/{page_id}/video_reels", {"upload_phase": "finish", "video_id": vid, "video_state": "PUBLISHED",
                                                  "description": caption, "access_token": page_token})
    return vid
