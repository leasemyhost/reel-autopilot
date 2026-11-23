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
    done = ROOT / "posted" / r["id"] / "meta.json"
    if done.exists():
        meta.update(json.load(open(done)))
    tok = os.environ["IG_ACCESS_TOKEN"]
    # main account (@jayantkeguidess) + optional second account (@jayantkeguides), same time
    targets = [("", os.environ["IG_USER_ID"])]
    if os.environ.get("IG_USER_ID_2"):
        targets.append(("_2", os.environ["IG_USER_ID_2"]))
    failed = 0
    for sfx, uid in targets:
        if meta.get("permalink" + sfx):
            print(f"already posted{sfx}:", meta["permalink" + sfx])
            continue
        try:
            media_id, link = publish(video, r["caption"], uid, tok)
            meta.update({"media_id" + sfx: media_id, "permalink" + sfx: link})
            if not sfx:
                meta.update(status="posted", posted_at=dt.datetime.utcnow().isoformat() + "Z")
            print(f"posted{sfx}:", media_id, link)
        except Exception as e:
            failed += 1
            meta["error" + sfx] = str(e)[:300]
            print(f"FAILED{sfx}:", e)
    if os.environ.get("YT_REFRESH_TOKEN") and not meta.get("youtube_url"):
        try:
            from post_youtube import upload_short
            vid, privacy, url = upload_short(video, r["caption"])
            meta.update(youtube_id=vid, youtube_url=url, youtube_privacy=privacy)
            print("posted_yt:", url, privacy)
        except Exception as e:
            meta["error_yt"] = str(e)[:300]
            print("FAILED_yt:", e)
    if os.environ.get("FB_PAGE_ID") and os.environ.get("FB_PAGE_TOKEN"):
        try:
            meta["fb_video_id"] = publish_facebook_reel(video, r["caption"], os.environ["FB_PAGE_ID"], os.environ["FB_PAGE_TOKEN"])
        except Exception as e:
            meta["fb_error"] = str(e)[:300]
    dest = ROOT / "posted" / r["id"]
    dest.mkdir(parents=True, exist_ok=True)
    json.dump(meta, open(dest / "meta.json", "w"), indent=2, ensure_ascii=False)
    return 1 if not meta.get("permalink") else 0


if __name__ == "__main__":
    sys.exit(main())
