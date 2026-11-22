#!/usr/bin/env bash
# Host ready/<id>/reel.mp4 (+ cover.jpg) on the public media release, then post to Instagram.
set -euo pipefail
V=$(ls ready/*/reel.mp4 | head -1); D=$(dirname "$V"); ID=$(basename "$D")
export PUBLIC_VIDEO_URL=$(tools/media_host.sh "$V" "$ID.mp4")
if [ -f "$D/cover.jpg" ]; then export PUBLIC_COVER_URL=$(tools/media_host.sh "$D/cover.jpg" "$ID-cover.jpg"); fi
python3 tools/post_ready.py ready
