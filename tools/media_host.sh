#!/usr/bin/env bash
# Put a video on the repo's public "media" release so Instagram can fetch it.  Usage: media_host.sh <file> <name>
# Prints the public URL. Needs a PUBLIC repo and GH_TOKEN with contents:write.
set -euo pipefail
R="${GITHUB_REPOSITORY}"
gh release view media -R "$R" >/dev/null 2>&1 || gh release create media -R "$R" --title media --notes "temporary reel files for Instagram upload" >/dev/null
cp "$1" "/tmp/$2"
gh release upload media "/tmp/$2" -R "$R" --clobber >/dev/null
echo "https://github.com/$R/releases/download/media/$2"
