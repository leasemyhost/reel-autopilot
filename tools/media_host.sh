#!/usr/bin/env bash
# Put a video on the repo's public "media" release so Instagram can fetch it.  Usage: media_host.sh <file> <name>
# Prints the public URL. Needs a PUBLIC repo and GH_TOKEN with contents:write.
set -euo pipefail
R="${GITHUB_REPOSITORY}"; REL="${RELEASE:-media}"
gh release view "$REL" -R "$R" >/dev/null 2>&1 || gh release create "$REL" -R "$R" --title "$REL" --notes "reel files" >/dev/null
cp "$1" "/tmp/$2"
gh release upload "$REL" "/tmp/$2" -R "$R" --clobber >/dev/null
echo "https://github.com/$R/releases/download/$REL/$2"
