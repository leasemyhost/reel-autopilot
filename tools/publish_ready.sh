#!/usr/bin/env bash
# Host ready/<id>/reel.mp4 + fresh cover on the public media release, then post to Instagram.
set -euo pipefail
V=$(ls ready/*/reel.mp4 | head -1); D=$(dirname "$V"); ID=$(basename "$D")
# thumbnail post-time pe dobara banta hai, taaki posted/<id>/spec.json mein cover badalne se naya lage
if [ -f "posted/$ID/spec.json" ]; then
  pip install -q pillow numpy fonttools 2>/dev/null || true
  python3 tools/build_reel.py "posted/$ID/spec.json" "/tmp/cover-$ID" --cover-only "$D/cover.jpg" || true
fi
export PUBLIC_VIDEO_URL=$(tools/media_host.sh "$V" "$ID.mp4")
if [ -f "$D/cover.jpg" ]; then export PUBLIC_COVER_URL=$(tools/media_host.sh "$D/cover.jpg" "$ID-cover.jpg"); fi
python3 tools/post_ready.py ready

# YouTube manual upload ke liye: video + title/description 'youtube' release mein (7 din rehta hai)
if [ -f "posted/$ID/meta.json" ] && grep -q '"permalink"' "posted/$ID/meta.json"; then
  python3 - "$D/ready.json" > "/tmp/$ID-youtube.txt" <<'PY'
import json, re, sys
r = json.load(open(sys.argv[1])); cap = r["caption"]
first = next((l.strip() for l in cap.splitlines() if l.strip()), "AI trick")
print("TITLE:\n" + (re.sub(r"#\S+", "", first).strip()[:85] + " #Shorts") + "\n\nDESCRIPTION:\n" + cap + "\n\n#Shorts")
PY
  YV=$(RELEASE=youtube tools/media_host.sh "$V" "$ID.mp4") || true
  YT=$(RELEASE=youtube tools/media_host.sh "/tmp/$ID-youtube.txt" "$ID-youtube.txt") || true
  echo "yt_download: $YV"
  echo "yt_text: $YT"
fi
