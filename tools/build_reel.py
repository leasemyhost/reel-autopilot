"""Render a reel from a JSON spec + voice + line times (reference style, engine2 + cards).

  python3 tools/build_reel.py specs/<id>.json build/<id>            # full -> build/<id>/reel.mp4
  python3 tools/build_reel.py specs/<id>.json build/<id> --preview  # key frames -> build/<id>/preview/
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import wave
from multiprocessing import Pool
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engine"))
import engine2 as E  # noqa: E402
from cards import CARDS  # noqa: E402
from engine2 import W, H, clamp, ease_back, ease_in_out, ease_out, prog  # noqa: E402

TOP_Y, BOT_Y = 345, 1395
ARROWS = [((300, 650), (760, 1150), (260, -60)), ((780, 640), (300, 1180), (-240, 40)), ((260, 700), (800, 1120), (220, 80)),
          ((820, 700), (260, 1100), (-260, -40)), ((300, 620), (780, 1160), (280, 20)), ((760, 660), (320, 1150), (-220, 60)),
          ((300, 700), (760, 1100), (240, -40)), ((780, 700), (300, 1120), (-240, 40))]

G = {}


def setup(spec, B):
    G["spec"], G["B"] = spec, B
    G["caps"] = [l["cap"] for l in spec["lines"]]
    G["secs"] = [(s["lines"][0], s["lines"][1], CARDS[s["card"]], s.get("params", {})) for s in spec["sections"]]
    G["starts"] = [B[a] for a, *_ in G["secs"]]
    E.HANDLE = spec.get("handle", os.environ.get("REEL_HANDLE", E.HANDLE))


def section_layer(si, t):
    B = G["B"]
    a, b, fn, p = G["secs"][si]
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    fn(layer, t, [B[k] for k in range(a, b + 2)], None, p)
    shift = 0.2 if si > 0 else 0.0
    E.draw_caption(layer, G["caps"][a], t, B[a] + shift, B[a + 1] - B[a] - shift, TOP_Y)
    for k in range(a + 1, b + 1):
        if B[k] - 0.05 <= t < (B[k + 1] if k < b else B[b + 1] + 1):
            E.draw_caption(layer, G["caps"][k], t, B[k], B[k + 1] - B[k], BOT_Y,
                           fade_out_at=(B[k + 1] - 0.15) if k < b else None)
    return layer


def render_frame(args):
    i, out_dir = args
    t = i / E.FPS
    starts, B = G["starts"], G["B"]
    frame = E.draw_background(t)
    si = max(k for k, s in enumerate(starts) if t >= s)
    T = starts[si]
    nxt = starts[si + 1] if si + 1 < len(starts) else None
    lay = section_layer(si, t)
    if nxt is not None and t >= nxt - 0.30:
        p = ease_in_out(prog(t, nxt - 0.30, 0.30))
        tl = E.transform_layer(lay, scale=1.02 - 0.12 * p, dy=-260 * p, rot=-5 * p, alpha=1 - p, blur=6 * p)
    elif si > 0 and t < T + 0.55:
        p = ease_back(prog(t, T + 0.12, 0.42), 1.2)
        a0, a1, _ = ARROWS[(si - 1) % len(ARROWS)]
        tl = E.transform_layer(lay, scale=0.55 + 0.45 * p, dx=(a1[0] - W / 2) * (1 - p), dy=(a1[1] - H / 2) * (1 - p),
                               rot=10 * (1 - p), alpha=clamp(p * 1.4), blur=5 * (1 - clamp(p * 1.3)))
    else:
        tl = E.transform_layer(lay, scale=1.0 + 0.02 * prog(t, T, (nxt or B[-1]) - T))
    if tl is not None:
        frame.alpha_composite(tl)
    for k in range(1, len(starts)):
        Tk = starts[k]
        if Tk - 0.2 <= t <= Tk + 0.6:
            a0, a1, bend = ARROWS[(k - 1) % len(ARROWS)]
            E.dashed_arrow(frame, a0, a1, bend, ease_out(prog(t, Tk - 0.2, 0.4)), alpha=1 - prog(t, Tk + 0.35, 0.25))
    frame.convert("RGB").save(out_dir / f"f_{i:05d}.png", compress_level=1)
    return i


def collect_events():
    B, ev = G["B"], []
    for si, (a, b, fn, p) in enumerate(G["secs"]):
        fn(None, 0, [B[k] for k in range(a, b + 2)], ev, p)
        for k in range(a, b + 1):
            st = B[k] + (0.2 if (k == a and si > 0) else 0)
            toks = E.parse_caption(G["caps"][k])
            ev += [(tm, "pop") for tm, (_, kw) in zip(E.word_times(toks, st, B[k + 1] - st), toks) if kw]
    for Tk in G["starts"][1:]:
        ev += [(Tk - 0.3, "whoosh"), (Tk + 0.12, "swoosh_in")]
    return ev


def write_wav(path, x, sr):
    x = np.clip(x, -0.98, 0.98)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((x * 32767).astype(np.int16).tobytes())


def init_worker(spec, B):
    setup(spec, B)


def make_cover(spec, B, out):
    """Reel thumbnail: dark bg + big hook text + the hero card. spec["cover"] uses caption syntax ([kw])."""
    text = spec.get("cover") or spec["lines"][0]["cap"]
    a, b, fn, p = G["secs"][0]
    t = B[b + 1] - 0.05  # hero card fully built
    img = E.draw_background(1.0)
    card = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    fn(card, t, [B[k] for k in range(a, b + 2)], None, p)
    card = E.transform_layer(card, scale=0.82, dy=270)
    img.alpha_composite(card)
    old = (E.KW_SIZE, E.TX_SIZE)
    E.KW_SIZE, E.TX_SIZE = 118, 78
    E.kw_box.cache_clear()
    top = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    E.draw_caption(top, text, 999, 0, 1, 470)
    img.alpha_composite(top)
    E.KW_SIZE, E.TX_SIZE = old
    E.kw_box.cache_clear()
    img.convert("RGB").save(out, quality=92)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("build")
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--jobs", type=int, default=os.cpu_count())
    ap.add_argument("--estimate", action="store_true", help="no voice yet: estimate line times from text length (preview only)")
    a = ap.parse_args()
    sys.path.insert(0, str(Path(__file__).parent))
    from spec_rules import ensure_outro
    spec = ensure_outro(json.load(open(a.spec)))
    bdir = Path(a.build)
    if a.estimate:
        bdir.mkdir(parents=True, exist_ok=True)
        B, t = [0.0], 0.0
        for l in spec["lines"]:
            t += max(1.2, len(l["hi"].replace(" ", "")) / 10.3)  # Sadachbia ~10.3 Devanagari chars/sec (measured)
            B.append(round(t, 2))
        json.dump(B, open(bdir / "line_times.json", "w"))
        if t > 45:
            print(f"WARNING: estimated {t:.0f}s > 45s - script chhota karo (Jayant ka niyam 30-45s)")
    B = json.load(open(bdir / "line_times.json"))
    assert len(B) == len(spec["lines"]) + 1, "line_times count mismatch"
    setup(spec, B)
    total = B[-1] + 0.9

    if a.preview:
        pdir = bdir / "preview"
        shutil.rmtree(pdir, ignore_errors=True)
        pdir.mkdir(parents=True)
        ts = []
        for lo, hi, *_ in G["secs"]:
            ts += [B[lo] + 0.3, (B[lo] + B[hi + 1]) / 2, B[hi + 1] - 0.35]
        for t in ts:
            render_frame((int(t * E.FPS), pdir))
        fs = sorted(pdir.glob("f_*.png"))
        sheet = Image.new("RGB", (6 * 270, ((len(fs) + 5) // 6) * 480), "white")
        for k, f in enumerate(fs):
            sheet.paste(Image.open(f).resize((270, 480)), ((k % 6) * 270, (k // 6) * 480))
        sheet.save(pdir / "sheet.png")
        make_cover(spec, B, pdir / "cover.jpg")
        print("preview ->", pdir / "sheet.png", "+ cover.jpg")
        return

    fdir = bdir / "frames"
    shutil.rmtree(fdir, ignore_errors=True)
    fdir.mkdir(parents=True)
    n = int(total * E.FPS)
    with Pool(a.jobs, initializer=init_worker, initargs=(spec, B)) as pool:
        for k, _ in enumerate(pool.imap_unordered(render_frame, [(i, fdir) for i in range(n)], chunksize=8)):
            if k % 300 == 0:
                print(f"  frames {k}/{n}", flush=True)
    from studio_mix import VOICE_CHAIN, pad_bed
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        write_wav(td / "sfx.wav", E.build_sfx_track(collect_events(), total), E.SR)
        write_wav(td / "music.wav", pad_bed(total) * 0.5, E.SR)
        fc = (f"[1:a]aresample={E.SR},{VOICE_CHAIN},pan=stereo|c0=c0|c1=c0,asplit=2[v][vk];"
              "[2:a][vk]sidechaincompress=threshold=0.02:ratio=6:attack=40:release=450[md];"
              "[v][md][3:a]amix=inputs=3:normalize=0:weights=1 0.85 1,loudnorm=I=-14:TP=-1.5:LRA=8[a]")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(E.FPS), "-i", str(fdir / "f_%05d.png"),
                        "-i", str(bdir / "voice.wav"), "-i", str(td / "music.wav"), "-i", str(td / "sfx.wav"),
                        "-filter_complex", fc, "-map", "0:v", "-map", "[a]", "-c:v", "libx264", "-preset", "medium",
                        "-crf", "20", "-pix_fmt", "yuv420p", "-profile:v", "high", "-c:a", "aac", "-b:a", "192k",
                        "-ar", str(E.SR), "-t", f"{total:.2f}", "-movflags", "+faststart", str(bdir / "reel.mp4")], check=True)
    shutil.rmtree(fdir)
    make_cover(spec, B, bdir / "cover.jpg")
    print("done ->", bdir / "reel.mp4", f"{total:.1f}s")


if __name__ == "__main__":
    main()
