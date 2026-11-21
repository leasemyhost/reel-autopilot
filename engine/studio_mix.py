"""Studio-feel audio mix: voice polish + soft music bed (sidechain duck) + SFX + loudness.

Run from kit root:
  python3 scripts/studio_mix.py --video output/reel01_ai_website_voice.mp4 \
      --voice voiceover/voice_gemini.m4a --timings scripts/reel01/timings.json \
      --render scripts/reel01/render.py --out output/reel01_ai_website_studio.mp4
"""
import argparse
import importlib.util
import json
import subprocess
import tempfile
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SR = 48000

VOICE_CHAIN = ",".join([
    "highpass=f=75",
    "equalizer=f=120:t=q:w=0.9:g=3",       # chest / proximity warmth
    "equalizer=f=320:t=q:w=1.4:g=-3",      # mud cut
    "equalizer=f=900:t=q:w=1.5:g=-1",      # boxiness
    "equalizer=f=4200:t=q:w=1.2:g=2.5",    # presence / clarity
    "highshelf=f=11000:g=3",               # air
    "deesser=i=0.45:m=0.5:f=0.5",          # soften harsh s/sh
    "acompressor=threshold=-24dB:ratio=2.5:attack=12:release=120:makeup=2",
    "acompressor=threshold=-14dB:ratio=5:attack=3:release=60:makeup=2",
    "aecho=0.8:0.85:28|47:0.10|0.06",       # tiny booth ambience, not a hall
])


def pad_bed(total, bpm=96):
    """Soft lo-fi bed: warm chord pads + gentle kick + shaker. Khud synth kiya, copyright-free."""
    n = int(total * SR)
    t = np.arange(n) / SR
    beat = 60 / bpm
    bar = beat * 4
    chords = [[220.0, 261.6, 329.6], [174.6, 220.0, 261.6], [196.0, 246.9, 293.7], [164.8, 207.7, 246.9]]
    out = np.zeros((n, 2), np.float32)
    for k in range(int(total / bar) + 1):
        s, e = int(k * bar * SR), min(n, int((k + 1) * bar * SR))
        if s >= n:
            break
        tt = t[s:e] - k * bar
        env = np.minimum(1, tt / 0.6) * np.exp(-tt * 0.25)
        ch = chords[k % 4]
        for j, f in enumerate(ch):
            for det, pan in ((-0.4, 0.75), (0.4, 0.25)):
                w = np.sin(2 * np.pi * (f + det) * tt) + 0.25 * np.sin(2 * np.pi * 2 * (f + det) * tt)
                out[s:e, 0] += w * env * pan * 0.08
                out[s:e, 1] += w * env * (1 - pan) * 0.08
        sub = np.sin(2 * np.pi * ch[0] / 2 * tt) * env * 0.12
        out[s:e] += sub[:, None]
    kt = np.arange(int(0.3 * SR)) / SR
    kick = (np.sin(2 * np.pi * (90 * np.exp(-kt * 20) + 48) * kt) * np.exp(-kt * 9) * 0.55).astype(np.float32)
    rng = np.random.default_rng(5)
    st = np.arange(int(0.06 * SR)) / SR
    shaker = (rng.standard_normal(st.size) * np.exp(-st * 70) * 0.05).astype(np.float32)
    k = 0
    while k * beat < total:
        s = int(k * beat * SR)
        if k % 2 == 0:
            e = min(n, s + kick.size)
            out[s:e] += kick[: e - s, None]
        for sub_i in (0.5,):
            hs = int((k + sub_i) * beat * SR)
            if hs < n:
                he = min(n, hs + shaker.size)
                out[hs:he, 0] += shaker[: he - hs] * 0.8
                out[hs:he, 1] += shaker[: he - hs]
        k += 1
    fade = int(1.5 * SR)
    out[-fade:] *= np.linspace(1, 0, fade)[:, None]
    out[: int(0.3 * SR)] *= np.linspace(0, 1, int(0.3 * SR))[:, None]
    return out


def write_wav(path, x):
    x = np.clip(x, -0.98, 0.98)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())


def sfx_track(render_mod, starts, total):
    n = int(total * SR)
    out = np.zeros(n, np.float32)
    cache = {}

    def load(name):
        if name not in cache:
            x = render_mod.load_wav(name)
            cache[name] = np.interp(np.arange(0, x.size, 44100 / SR), np.arange(x.size), x).astype(np.float32)
        return cache[name]

    for i, sc in enumerate(render_mod.SCENES):
        for off, name in sc[4]:
            x = load(name)
            s = int((starts[i] + off) * SR)
            if s < n:
                e = min(n, s + x.size)
                out[s:e] += x[: e - s] * 0.22
        if sc[2] == "terminal":
            x = load("click")
            for k in np.arange(0, (starts[i + 1] - starts[i]) * 0.7, 0.09):
                s = int((starts[i] + k) * SR)
                if s < n:
                    out[s:s + x.size] += x[: min(x.size, n - s)] * 0.18
    return np.stack([out, out], 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--voice", required=True)
    ap.add_argument("--timings", required=True)
    ap.add_argument("--render", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    spec = importlib.util.spec_from_file_location("r", ROOT / a.render)
    r = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(r)
    durs = json.load(open(ROOT / a.timings))
    durs[-1] += 0.8
    starts = [0.0]
    for x in durs:
        starts.append(starts[-1] + x)
    total = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                  str(ROOT / a.video)], capture_output=True, text=True).stdout)

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        write_wav(td / "music.wav", pad_bed(total) * 0.55)
        write_wav(td / "sfx.wav", sfx_track(r, starts, total))
        fc = (
            f"[1:a]aresample={SR},{VOICE_CHAIN},pan=stereo|c0=c0|c1=c0,asplit=2[v][vkey];"
            "[2:a]volume=1.0[m];"
            "[m][vkey]sidechaincompress=threshold=0.02:ratio=6:attack=40:release=450:makeup=1[mduck];"
            "[3:a]volume=1.0[s];"
            "[v][mduck][s]amix=inputs=3:normalize=0:weights=1 0.9 1,"
            "loudnorm=I=-14:TP=-1.5:LRA=8[a]"
        )
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(ROOT / a.video), "-i", str(ROOT / a.voice),
               "-i", str(td / "music.wav"), "-i", str(td / "sfx.wav"), "-filter_complex", fc,
               "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-ar", str(SR),
               "-shortest", "-movflags", "+faststart", str(ROOT / a.out)]
        subprocess.run(cmd, check=True)
    print("done ->", a.out)


if __name__ == "__main__":
    main()
