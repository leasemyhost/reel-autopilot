"""Post a reel that build.yml rendered 2h earlier.  python3 tools/post_ready.py ready/
Reads ready/<id>/{reel.mp4,ready.json}, publishes to Instagram, updates posted/<id>/meta.json."""
import datetime as dt
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from post_instagram import publish, publish_facebook_reel  # noqa: E402


def main():
    rdir = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / "ready")
    items = sorted(rdir.glob("*/ready.json"))
    if not items:
        print("no ready reel")
        return 2
    r = json.load(open(items[0]))
    video = items[0].parent / "reel.mp4"
    meta = r["meta"]
    media_id, link = publish(video, r["caption"], os.environ["IG_USER_ID"], os.environ["IG_ACCESS_TOKEN"])
    meta.update(status="posted", media_id=media_id, permalink=link, posted_at=dt.datetime.utcnow().isoformat() + "Z")
    print("posted:", media_id, link)
    if os.environ.get("FB_PAGE_ID") and os.environ.get("FB_PAGE_TOKEN"):
        try:
            meta["fb_video_id"] = publish_facebook_reel(video, r["caption"], os.environ["FB_PAGE_ID"], os.environ["FB_PAGE_TOKEN"])
        except Exception as e:
            meta["fb_error"] = str(e)[:300]
    dest = ROOT / "posted" / r["id"]
    dest.mkdir(parents=True, exist_ok=True)
    json.dump(meta, open(dest / "meta.json", "w"), indent=2, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
