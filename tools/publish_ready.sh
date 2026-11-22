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
