"""Sadachbia voice via Gemini TTS API (free AI Studio key in $GEMINI_API_KEY).

One request per SECTION (so section starts are exact); lines inside a section are aligned
with pause detection. Output: <out_dir>/voice.wav (48 kHz mono) + line_times.json (n_lines+1 values).

  python3 tools/tts_gemini.py specs/<id>.json build/<id>
"""
import base64
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np

VOICE = os.environ.get("REEL_VOICE", "Sadachbia")
MODELS = [m for m in os.environ.get("GEMINI_TTS_MODELS", "gemini-2.5-flash-preview-tts,gemini-2.5-flash-tts,gemini-2.5-pro-preview-tts").split(",") if m]
STYLE = os.environ.get("REEL_STYLE", "Read this in Hindi like an energetic young Indian Instagram reel creator, fast and punchy. "
                                     "Take a clear pause of about one second at every blank line between sentences")
MODE = os.environ.get("TTS_MODE", "reel")  # reel = 1 API call per reel (free-tier friendly), section = 1 call per section
SR_IN, SR = 24000, 48000
GAP = 0.12


def tts(text):
    key = os.environ["GEMINI_API_KEY"]
    body = {
        "contents": [{"parts": [{"text": f"{STYLE}:\n{text}"}]}],
        "generationConfig": {"responseModalities": ["AUDIO"],
                             "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": VOICE}}}},
    }
    last = None
    for model in MODELS:
        for attempt in range(5):
            req = urllib.request.Request(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                data=json.dumps(body).encode(), headers={"Content-Type": "application/json", "x-goog-api-key": key})
            try:
                with urllib.request.urlopen(req, timeout=180) as r:
                    data = json.load(r)
                b64 = data["candidates"][0]["content"]["parts"][0]["inlineData"]["data"]
                pcm = np.frombuffer(base64.b64decode(b64), dtype=np.int16).astype(np.float32) / 32768
                got, want = len(pcm) / 24000, len(text.replace(" ", "")) / 16.0
                if got < 0.6 * want:  # Gemini sometimes returns only the first part of a long script
                    last = f"{model}: truncated audio {got:.1f}s (expected ~{want:.0f}s)"
                    print(last, flush=True)
                    time.sleep(4)
                    continue
                return pcm
            except urllib.error.HTTPError as e:
                last = f"{model}: HTTP {e.code} {e.read()[:1500]!r}"
                if e.code == 429:
                    if "PerDay" in last or "per day" in last.lower() or "quota" in last.lower() and attempt >= 1:
                        break
                    time.sleep(25 * (attempt + 1))
                    continue
                if e.code in (500, 503):
                    time.sleep(5)
                    continue
                break
            except Exception as e:  # noqa
                last = f"{model}: {e}"
                time.sleep(3)
    raise RuntimeError(f"Gemini TTS failed: {last}")


def trim(x, thr=0.01):
    idx = np.where(np.abs(x) > thr)[0]
    if idx.size == 0:
        return x
    a, b = max(0, idx[0] - int(0.03 * SR_IN)), min(x.size, idx[-1] + int(0.08 * SR_IN))
    return x[a:b]


def pauses(x, sr, thr_db=-38, min_d=0.08):
    win = int(0.01 * sr)
    n = x.size // win
    rms = np.sqrt(np.mean(x[: n * win].reshape(n, win) ** 2, axis=1) + 1e-12)
    db = 20 * np.log10(rms)
    quiet = db < thr_db
    out, start = [], None
    for i, q in enumerate(quiet):
        if q and start is None:
            start = i
        if (not q or i == n - 1) and start is not None:
            if (i - start) * 0.01 >= min_d:
                out.append(((start + i) / 2 * 0.01, (i - start) * 0.01))
            start = None
    return out


def align_lines(x, sr, lines):
    """Return boundaries inside a section chunk for len(lines) lines (len+1 values)."""
    dur = x.size / sr
    if len(lines) == 1:
        return [0.0, dur]
    ps = [p for p in pauses(x, sr) if 0.25 < p[0] < dur - 0.25]
    w = [len(re.sub(r"\s", "", l)) for l in lines]
    tot, acc, exp = sum(w), 0, []
    for v in w[:-1]:
        acc += v
        exp.append(dur * acc / tot)
    n, m = len(exp), len(ps)
    INF = 1e9
    dp = [[INF] * (m + 1) for _ in range(n + 1)]
    bk = [[None] * (m + 1) for _ in range(n + 1)]
    for j in range(m + 1):
        dp[0][j] = 0
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            skip = dp[i][j - 1]
            take = dp[i - 1][j - 1] + abs(ps[j - 1][0] - exp[i - 1]) - 2.5 * ps[j - 1][1]
            dp[i][j], bk[i][j] = (take, True) if take < skip else (skip, False)
    if m < n or dp[n][m] >= INF:
        return [0.0] + exp + [dur]
    i, j, ch = n, m, []
    while i > 0:
        if bk[i][j]:
            ch.append(ps[j - 1][0])
            i -= 1
        j -= 1
    return [0.0] + ch[::-1] + [dur]


def main():
    spec = json.load(open(sys.argv[1]))
    out = Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    lines = [l["hi"] for l in spec["lines"]]
    chunks, bounds, t0 = [], [], 0.0
    groups = [tuple(sec["lines"]) for sec in spec["sections"]] if MODE == "section" else [(0, len(lines) - 1)]
    for a, b in groups:
        text = "\n\n".join(lines[a:b + 1])
        x = trim(tts(text))
        bb = align_lines(x, SR_IN, lines[a:b + 1])
        bounds += [t0 + v for v in bb[:-1]]
        chunks.append(x)
        chunks.append(np.zeros(int(GAP * SR_IN), np.float32))
        t0 += x.size / SR_IN + GAP
        if len(groups) > 1:
            time.sleep(float(os.environ.get("TTS_SLEEP", "4")))
    bounds.append(t0)
    voice = np.concatenate(chunks)
    # refine with whisper word timestamps when available (GitHub Actions); pause-DP bounds stay as fallback
    if os.environ.get("ALIGN_WHISPER", "1") == "1":
        try:
            import soundfile  # noqa: F401
        except Exception:
            pass
        try:
            from align_whisper import line_starts
            tmpw = out / "voice_16k.wav"
            raw16 = out / "v16.raw"
            (voice * 32767).astype(np.int16).tofile(raw16)
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "s16le", "-ar", str(SR_IN), "-ac", "1", "-i", str(raw16),
                            "-ar", "16000", str(tmpw)], check=True)
            raw16.unlink()
            ws = line_starts(tmpw, lines)
            if ws:
                refined = [0.0]
                for i in range(1, len(lines)):
                    w = ws[i]
                    # whisper word start sits just after the pause; keep it unless it disagrees wildly with order
                    if w is not None and refined[-1] + 0.4 < w < t0 - 0.3:
                        refined.append(round(max(0.0, w - 0.08), 3))
                    else:
                        refined.append(max(bounds[i], refined[-1] + 0.4))
                refined.append(t0)
                print("whisper alignment used; max shift", round(max(abs(a - b) for a, b in zip(refined, bounds)), 2))
                bounds = refined
            tmpw.unlink(missing_ok=True)
        except Exception as e:  # noqa
            print("whisper alignment skipped:", e)
    raw = out / "voice_24k.raw"
    (voice * 32767).astype(np.int16).tofile(raw)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "s16le", "-ar", str(SR_IN), "-ac", "1", "-i", str(raw),
                    "-ar", str(SR), str(out / "voice.wav")], check=True)
    raw.unlink()
    json.dump([round(v, 3) for v in bounds], open(out / "line_times.json", "w"))
    print(f"voice {t0:.1f}s, {len(lines)} lines -> {out}")


if __name__ == "__main__":
    main()
