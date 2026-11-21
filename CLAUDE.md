# reel-autopilot

Instagram reel factory for "Jayant Ke Guides". Read `PLAYBOOK.md` before doing anything - it is the full procedure.

- Engine: `engine/engine2.py` (style primitives), `engine/cards.py` (10 animated card types), `engine/studio_mix.py` (voice chain + music bed)
- Tools: `tools/tts_gemini.py` (Sadachbia voice), `tools/build_reel.py` (render), `tools/post_instagram.py` + `tools/insights.py` (run in GitHub Actions only)
- Setup in a fresh session: `pip install --break-system-packages pillow numpy fonttools` and make sure `ffmpeg` exists.
- Voice is always Gemini **Sadachbia**. Narration text (`hi`) is pure Devanagari Hindi.
- Never commit `build/`. Claude runs only add `specs/pending/<id>.json` + `data/` updates; GitHub Actions builds and posts (IG + FB Page).
- Reply to the user in Hinglish.
