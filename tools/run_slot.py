"""GitHub Actions entrypoint: take the oldest pending spec for this slot -> Sadachbia voice -> render -> post -> archive.

  python3 tools/run_slot.py --slot morning|noon|evening [--no-post]
Pending specs live in specs/pending/<id>.json (written by the Claude scheduled run).
"""
import argparse
import datetime as dt
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))


def pick(slot):
    specs = sorted((ROOT / "specs/pending").glob("*.json"))
    same = [s for s in specs if json.load(open(s)).get("slot") == slot]
    return (same or specs or [None])[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slot", required=True)
    ap.add_argument("--no-post", action="store_true")
    a = ap.parse_args()
    sp = pick(a.slot)
    if not sp:
        print("no pending spec - nothing to do")
        return 0
    spec = json.load(open(sp))
    rid = sp.stem
    b = ROOT / "build" / rid
    print("== building", rid, spec.get("title"))
    subprocess.run([sys.executable, "tools/tts_gemini.py", str(sp), str(b)], check=True, cwd=ROOT)
    subprocess.run([sys.executable, "tools/build_reel.py", str(sp), str(b)], check=True, cwd=ROOT)
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height:format=duration",
                          "-of", "json", str(b / "reel.mp4")], capture_output=True, text=True, check=True).stdout
    info = json.loads(out)
    dur = float(info["format"]["duration"])
    assert any(s.get("width") == 1080 and s.get("height") == 1920 for s in info["streams"]), "bad size"
    assert any(s["codec_type"] == "audio" for s in info["streams"]), "no audio"
    assert 15 < dur < 90, f"bad duration {dur}"
    meta = {k: spec.get(k) for k in ("title", "topic", "hook", "slot", "sources")}
    meta.update(id=rid, duration=round(dur, 1), built_at=dt.datetime.utcnow().isoformat() + "Z")
    dest = ROOT / "posted" / rid
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "caption.txt").write_text(spec["caption"].strip() + "\n")
    shutil.copy(sp, dest / "spec.json")
    if a.no_post:
        meta["status"] = "built"
    else:
        from post_instagram import publish
        import os
        media_id, link = publish(b / "reel.mp4", spec["caption"].strip(), os.environ["IG_USER_ID"], os.environ["IG_ACCESS_TOKEN"])
        meta.update(status="posted", media_id=media_id, permalink=link, posted_at=dt.datetime.utcnow().isoformat() + "Z")
        print("posted:", media_id, link)
    json.dump(meta, open(dest / "meta.json", "w"), indent=2, ensure_ascii=False)
    sp.unlink()
    return 0


if __name__ == "__main__":
    sys.exit(main())
