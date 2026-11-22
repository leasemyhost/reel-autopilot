"""Reel engine v2 - reference style (paper bg, blurred orange flowers, word-by-word captions,
Figma-style keyword boxes, macOS UI cards, cursor, coins, dashed-arrow transitions, SFX per event).

Reel scripts import this and define SECTIONS + per-section draw functions.
"""
import math
import random
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
FONTS = ROOT / "assets/fonts"
W, H, FPS = 1080, 1920, 30

BG = (13, 14, 19)          # dark theme (Jayant: 'background dark use karo')
GRID = (25, 27, 34)
CAP_INK = (246, 244, 240)  # caption text on dark bg
ORANGE = (217, 98, 43)
FLOWER = (242, 138, 96)
INK = (31, 31, 36)
GREY = (110, 110, 118)
LIGHT = (250, 248, 245)
CREAM = (252, 246, 238)
DARK = (27, 31, 44)
DARK2 = (38, 43, 58)
GREEN = (34, 165, 91)
RED = (222, 64, 52)
WHITE = (255, 255, 255)

HANDLE = "Jayant Ke Guides"


# ------------------------------------------------------------------ easing
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease_out(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def ease_in_out(x):
    x = clamp(x)
    return 3 * x * x - 2 * x * x * x


def ease_back(x, s=1.7):
    x = clamp(x)
    return 1 + (s + 1) * (x - 1) ** 3 + s * (x - 1) ** 2


def prog(t, start, dur):
    return clamp((t - start) / dur)


# ------------------------------------------------------------------ fonts
@lru_cache(maxsize=256)
def sans(size, weight="Medium"):
    f = ImageFont.truetype(str(FONTS / "DMSans.ttf"), size)
    try:
        f.set_variation_by_name(weight)
    except Exception:
        pass
    return f


@lru_cache(maxsize=64)
def serif(size):
    return ImageFont.truetype(str(FONTS / "Lora-BoldItalic.ttf"), size)


@lru_cache(maxsize=64)
def mono(size, bold=False):
    return ImageFont.truetype(str(FONTS / ("JetBrainsMono-Bold.ttf" if bold else "JetBrainsMono-Regular.ttf")), size)


# ------------------------------------------------------------------ background
@lru_cache(maxsize=1)
def background():
    """Dark gradient bg: deep indigo top -> near-black bottom + soft orange/blue glows + faint grid."""
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    v = (yy / H)[..., None]
    top, bot = np.array([30, 22, 52], np.float32), np.array([9, 10, 16], np.float32)
    arr = top * (1 - v) + bot * v

    def glow(cx, cy, r, col, k):
        g = np.exp(-(((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * r * r)))[..., None]
        return g * np.array(col, np.float32) * k

    arr += glow(W * 0.92, H * 0.08, 520, (217, 98, 43), 0.30)   # warm orange, top-right
    arr += glow(W * 0.05, H * 0.62, 600, (60, 80, 200), 0.22)   # cool blue, left-middle
    arr += glow(W * 0.85, H * 0.95, 480, (217, 98, 43), 0.14)   # warm, bottom-right
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")
    grid = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(grid)
    for x in range(0, W, 54):
        d.line([x, 0, x, H], fill=(255, 255, 255, 9), width=1)
    for y in range(0, H, 54):
        d.line([0, y, W, y], fill=(255, 255, 255, 9), width=1)
    img = img.convert("RGBA")
    img.alpha_composite(grid)
    rng = np.random.default_rng(1)
    a = np.asarray(img).astype(np.float32)
    a[..., :3] += rng.normal(0, 2.0, (H, W, 1))
    vig = 1 - 0.22 * (((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    a[..., :3] *= vig[..., None]
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGBA")


@lru_cache(maxsize=4)
def flower_sprite(size=400, blur=7):
    s = size * 2
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = s / 2
    petals = 16
    w = int(s * 0.06)
    for i in range(petals):
        a = 2 * math.pi * i / petals + 0.1
        L = s * 0.46 * (0.9 + 0.1 * math.sin(i * 2.7))
        x1, y1 = c + L * math.cos(a), c + L * math.sin(a)
        x0, y0 = c + s * 0.08 * math.cos(a), c + s * 0.08 * math.sin(a)
        d.line([x0, y0, x1, y1], fill=FLOWER + (255,), width=w)
        for (px, py) in ((x0, y0), (x1, y1)):
            d.ellipse([px - w / 2, py - w / 2, px + w / 2, py + w / 2], fill=FLOWER + (255,))
    d.ellipse([c - s * 0.11, c - s * 0.11, c + s * 0.11, c + s * 0.11], fill=FLOWER + (255,))
    im = im.resize((size, size), Image.LANCZOS).filter(ImageFilter.GaussianBlur(blur))
    a = im.split()[3].point(lambda v: int(v * 0.8))
    im.putalpha(a)
    return im


FLOWERS = []  # Jayant: side flowers nahi chahiye


def draw_background(t):
    img = background().copy()
    fs = flower_sprite()
    for i, (cx, cy, sc, dirn) in enumerate(FLOWERS):
        sp = fs.rotate(dirn * t * 7 + i * 20, resample=Image.BICUBIC)
        if sc != 1:
            sp = sp.resize((int(sp.width * sc), int(sp.height * sc)), Image.BICUBIC)
        img.alpha_composite(sp, (int(cx - sp.width / 2), int(cy - sp.height / 2)))
    d = ImageDraw.Draw(img)
    d.text((W / 2, 1795), HANDLE, font=sans(26, "Regular"), fill=(120, 122, 132), anchor="mm")
    return img


# ------------------------------------------------------------------ sprites
def shadowed(sprite, radius=36, offset=18, alpha=60, blur=28):
    pad = blur * 2 + offset
    w, h = sprite.size
    out = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
    a = sprite.split()[3].point(lambda v: alpha if v > 0 else 0)
    sh = Image.new("RGBA", sprite.size, (40, 30, 20, 0))
    sh.putalpha(a)
    tmp = Image.new("RGBA", out.size, (0, 0, 0, 0))
    tmp.alpha_composite(sh, (pad, pad + offset))
    tmp = tmp.filter(ImageFilter.GaussianBlur(blur))
    out.alpha_composite(tmp)
    out.alpha_composite(sprite, (pad, pad))
    return out


def rrect(w, h, r, fill, outline=None, width=2):
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle([0, 0, w - 1, h - 1], radius=r, fill=fill, outline=outline, width=width)
    return im


def window(w, h, title="", dark=False, radius=30):
    """macOS-style window. Returns (img, content_top_y)."""
    fill = DARK + (255,) if dark else (247, 246, 244, 255)
    im = rrect(w, h, radius, fill, outline=(60, 66, 84, 255) if dark else (222, 218, 212, 255), width=2)
    d = ImageDraw.Draw(im)
    for i, c in enumerate([(255, 95, 87), (254, 188, 46), (40, 200, 64)]):
        d.ellipse([28 + i * 34, 26, 48 + i * 34, 46], fill=c)
    if title:
        f = mono(22)
        tw = d.textlength(title, font=f)
        if dark:
            d.text((w / 2, 36), title, font=f, fill=(140, 146, 165), anchor="mm")
        else:
            d.rounded_rectangle([w / 2 - tw / 2 - 18, 18, w / 2 + tw / 2 + 18, 54], radius=18, fill=WHITE, outline=(225, 220, 214))
            d.text((w / 2, 36), title, font=f, fill=GREY, anchor="mm")
    return im, 72


def label_pill(text):
    f = mono(24, bold=True)
    tw = int(ImageDraw.Draw(Image.new("RGB", (1, 1))).textlength(text, font=f))
    im = rrect(tw + 44, 50, 25, (28, 28, 34, 255))
    ImageDraw.Draw(im).text(((tw + 44) / 2, 25), text, font=f, fill=WHITE, anchor="mm")
    return im


def pill(text, bg, fg, size=28, pad=26, h=56, weight="Bold", outline=None):
    f = sans(size, weight)
    tick = "✓" in text
    text = text.replace("✓", "").strip()
    tw = int(ImageDraw.Draw(Image.new("RGB", (1, 1))).textlength(text, font=f))
    extra = int(size * 1.1) if tick else 0
    im = rrect(tw + pad * 2 + extra, h, h // 2, bg, outline=outline, width=2)
    d = ImageDraw.Draw(im)
    d.text((pad, h / 2), text, font=f, fill=fg, anchor="lm")
    if tick:
        cx, r = pad + tw + extra * 0.6, size * 0.42
        d.line([cx - r * 0.7, h / 2, cx - r * 0.15, h / 2 + r * 0.55, cx + r * 0.8, h / 2 - r * 0.6], fill=fg, width=max(3, size // 8))
    return im


def check_icon(d, cx, cy, r, color=GREEN, fg=WHITE):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)
    d.line([cx - r * 0.45, cy + r * 0.02, cx - r * 0.1, cy + r * 0.38, cx + r * 0.5, cy - r * 0.35], fill=fg, width=max(3, int(r * 0.28)), joint="curve")


def cross_icon(d, cx, cy, r, color=RED, fg=WHITE):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)
    k = r * 0.4
    d.line([cx - k, cy - k, cx + k, cy + k], fill=fg, width=max(3, int(r * 0.26)))
    d.line([cx - k, cy + k, cx + k, cy - k], fill=fg, width=max(3, int(r * 0.26)))


@lru_cache(maxsize=4)
def coin_sprite(size=64, symbol="₹"):
    s = size * 3
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([4, 4, s - 4, s - 4], fill=(214, 120, 40))
    d.ellipse([16, 16, s - 16, s - 16], fill=(240, 160, 60), outline=(204, 110, 34), width=6)
    d.text((s / 2, s / 2 + 4), symbol, font=sans(int(s * 0.5), "Bold"), fill=(150, 70, 20), anchor="mm")
    return shadowed(im.resize((size, size), Image.LANCZOS), offset=5, blur=6, alpha=70)


def star(d, cx, cy, r, color=ORANGE):
    pts = []
    for i in range(8):
        a = math.pi / 4 * i
        rr = r if i % 2 == 0 else r * 0.3
        pts.append((cx + rr * math.sin(a), cy - rr * math.cos(a)))
    d.polygon(pts, fill=color)


@lru_cache(maxsize=1)
def cursor_sprite():
    s = 3
    im = Image.new("RGBA", (40 * s, 56 * s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    pts = [(2, 2), (2, 42), (12, 32), (19, 49), (26, 46), (19, 30), (33, 30)]
    pts = [(x * s, y * s) for x, y in pts]
    d.polygon(pts, fill=(20, 20, 20), outline=WHITE)
    d.line(pts + [pts[0]], fill=WHITE, width=2 * s)
    return shadowed(im.resize((40, 56), Image.LANCZOS), offset=4, blur=4, alpha=80)


def paste(layer, sprite, cx, cy, scale=1.0, alpha=1.0, rot=0.0):
    """Paste sprite centered at (cx, cy) with scale/alpha/rotation."""
    if alpha <= 0.01 or scale <= 0.01:
        return
    sp = sprite
    if abs(scale - 1) > 1e-3:
        sp = sp.resize((max(1, int(sp.width * scale)), max(1, int(sp.height * scale))), Image.BILINEAR)
    if abs(rot) > 0.05:
        sp = sp.rotate(rot, resample=Image.BICUBIC, expand=True)
    if alpha < 0.999:
        a = sp.split()[3].point(lambda v: int(v * alpha))
        sp = sp.copy()
        sp.putalpha(a)
    layer.alpha_composite(sp, (int(cx - sp.width / 2), int(cy - sp.height / 2))) if (
        cx - sp.width / 2 >= 0 and cy - sp.height / 2 >= 0 and cx + sp.width / 2 <= layer.width and cy + sp.height / 2 <= layer.height
    ) else _paste_clip(layer, sp, int(cx - sp.width / 2), int(cy - sp.height / 2))


def _paste_clip(layer, sp, x, y):
    tmp = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    tmp.paste(sp, (x, y), sp)
    layer.alpha_composite(tmp)


def pop_in(t, start, dur=0.35):
    """returns (scale, alpha) for a pop-in animation."""
    p = prog(t, start, dur)
    return (0.6 + 0.4 * ease_back(p)) if p > 0 else 0, ease_out(p * 1.6)


# ------------------------------------------------------------------ captions
def parse_caption(text):
    toks = []
    for raw in text.split():
        if raw.startswith("[") and raw.endswith("]"):
            toks.append((raw[1:-1], True))
        else:
            toks.append((raw, False))
    return toks


_meas = ImageDraw.Draw(Image.new("RGB", (1, 1)))
KW_SIZE, TX_SIZE = 80, 54   # bade, bold - phone pe door se padhne layak


def kw_runs(word):
    """Split keyword into (text, font) runs - Lora lacks the rupee sign."""
    runs, cur = [], ""
    for ch in word:
        if ch == "₹":
            if cur:
                runs.append((cur, serif(KW_SIZE)))
                cur = ""
            runs.append(("₹", sans(KW_SIZE - 6, "Bold")))
        else:
            cur += ch
    if cur:
        runs.append((cur, serif(KW_SIZE)))
    return runs


def tok_width(word, kw):
    if kw:
        return sum(_meas.textlength(s, font=f) for s, f in kw_runs(word)) + 36
    return _meas.textlength(word, font=sans(TX_SIZE, "Bold"))


def layout(toks, maxw=980):
    rows, cur, cw = [], [], 0
    gap_n, gap_k = 14, 8
    for i, (w, kw) in enumerate(toks):
        tw = tok_width(w, kw)
        g = (gap_k if kw and cur and cur[-1][1] else gap_n) if cur else 0
        if cur and cw + g + tw > maxw:
            rows.append(cur)
            cur, cw = [], 0
            g = 0
        cur.append((w, kw, i, tw, g))
        cw += g + tw
    if cur:
        rows.append(cur)
    return rows


@lru_cache(maxsize=512)
def kw_box(word):
    runs = kw_runs(word)
    tw = int(sum(_meas.textlength(s, font=f) for s, f in runs))
    bw, bh = tw + 40, 108
    im = Image.new("RGBA", (bw + 16, bh + 16), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    o = 8
    d.rectangle([o, o, o + bw, o + bh], fill=CREAM + (255,), outline=ORANGE + (255,), width=3)
    x = o + 18
    for s, f in runs:
        d.text((x, o + bh / 2 + 2), s, font=f, fill=ORANGE, anchor="lm")
        x += _meas.textlength(s, font=f)
    for hx, hy in [(o, o), (o + bw, o), (o, o + bh), (o + bw, o + bh)]:
        d.rectangle([hx - 6, hy - 6, hx + 6, hy + 6], fill=WHITE, outline=ORANGE, width=2)
    return im


def word_times(toks, start, dur):
    """Reveal time per token spread over 85% of line duration by character weight."""
    weights = [len(w) + 2 for w, _ in toks]
    tot = sum(weights)
    out, acc = [], 0
    for wgt in weights:
        out.append(start + dur * 0.85 * acc / tot)
        acc += wgt
    return out


def draw_caption(layer, text, t, start, dur, cy, fade_out_at=None):
    """Word-by-word caption; returns list of keyword pop times (for SFX)."""
    toks = parse_caption(text)
    times = word_times(toks, start, dur)
    rows = layout(toks)
    row_h = [112 if any(k for _, k, *_ in r) else 74 for r in rows]
    total_h = sum(row_h) + 6 * (len(rows) - 1)
    y = cy - total_h / 2
    alpha_all = 1.0
    if fade_out_at is not None:
        alpha_all = 1 - prog(t, fade_out_at, 0.2)
    d = ImageDraw.Draw(layer)
    for r, rh in zip(rows, row_h):
        rw = sum(g + tw for _, _, _, tw, g in r)
        x = W / 2 - rw / 2
        for w, kw, i, tw, g in r:
            x += g
            p = prog(t, times[i], 0.22)
            if p > 0 and alpha_all > 0:
                a = ease_out(p) * alpha_all
                if kw:
                    s, _ = pop_in(t, times[i], 0.32)
                    paste(layer, kw_box(w), x + tw / 2, y + rh / 2, scale=s, alpha=a, rot=(1 - ease_out(p)) * -6)
                else:
                    dy = (1 - ease_out(p)) * 14
                    col = tuple(int(BG[k] + (CAP_INK[k] - BG[k]) * a) for k in range(3))
                    d.text((x, y + rh / 2 + dy), w, font=sans(TX_SIZE, "Bold"), fill=col, anchor="lm")
            x += tw
        y += rh + 6
    return [times[i] for i, (_, k) in enumerate(toks) if k]


# ------------------------------------------------------------------ transitions
def dashed_arrow(layer, p0, p1, bend, prog_draw, alpha=1.0):
    if prog_draw <= 0 or alpha <= 0:
        return
    d = ImageDraw.Draw(layer)
    (x0, y0), (x1, y1) = p0, p1
    mx, my = (x0 + x1) / 2 + bend[0], (y0 + y1) / 2 + bend[1]
    n = 90
    pts = []
    for i in range(n + 1):
        u = i / n * prog_draw
        x = (1 - u) ** 2 * x0 + 2 * (1 - u) * u * mx + u * u * x1
        y = (1 - u) ** 2 * y0 + 2 * (1 - u) * u * my + u * u * y1
        pts.append((x, y))
    col = ORANGE + (int(220 * alpha),)
    for i in range(0, len(pts) - 1, 2):
        d.line([pts[i], pts[i + 1]], fill=col, width=5)
    if prog_draw > 0.98:
        (ax, ay), (bx, by) = pts[-3], pts[-1]
        ang = math.atan2(by - ay, bx - ax)
        L = 26
        d.polygon([(bx, by), (bx - L * math.cos(ang - 0.45), by - L * math.sin(ang - 0.45)),
                   (bx - L * math.cos(ang + 0.45), by - L * math.sin(ang + 0.45))], fill=col)


def transform_layer(layer, scale=1.0, dx=0, dy=0, rot=0.0, alpha=1.0, blur=0):
    if alpha <= 0.01:
        return None
    out = layer
    if abs(scale - 1) > 1e-3 or abs(rot) > 0.05 or dx or dy:
        out = layer.transform(layer.size, Image.AFFINE, _affine(scale, dx, dy, rot), resample=Image.BILINEAR)
    if blur > 0.5:
        out = out.filter(ImageFilter.GaussianBlur(blur))
    if alpha < 0.999:
        a = out.split()[3].point(lambda v: int(v * alpha))
        out = out.copy()
        out.putalpha(a)
    return out


def _affine(scale, dx, dy, rot):
    a = math.radians(rot)
    cos, sin = math.cos(a) / scale, math.sin(a) / scale
    cx, cy = W / 2 + dx, H / 2 + dy
    # inverse mapping: output (x,y) -> input
    return (cos, sin, W / 2 - cos * cx - sin * cy,
            -sin, cos, H / 2 + sin * cx - cos * cy)


# ------------------------------------------------------------------ SFX synthesis (48 kHz)
SR = 48000


def _t(sec):
    return np.arange(int(SR * sec)) / SR


def _norm(x, g=0.8):
    return (x / (np.max(np.abs(x)) + 1e-9) * g).astype(np.float32)


def _bandnoise(n, lo, hi, rng):
    x = rng.standard_normal(n)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(n, 1 / SR)
    X[(f < lo) | (f > hi)] = 0
    return np.fft.irfft(X, n)


def make_sfx():
    rng = np.random.default_rng(11)
    s = {}
    t = _t(0.5)
    n = t.size
    sweep = np.concatenate([_bandnoise(n, 200 + 1500 * k / 8, 900 + 4000 * k / 8, rng)[k * n // 8:(k + 1) * n // 8] for k in range(8)])
    env = np.sin(np.pi * np.clip(t / 0.5, 0, 1)) ** 1.6
    s["whoosh"] = _norm(sweep[:n] * env, 0.55)
    t = _t(0.12)
    f = 520 * np.exp(-t * 28) + 240
    s["pop"] = _norm(np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 38) + 0.3 * rng.standard_normal(t.size) * np.exp(-t * 400), 0.6)
    t = _t(0.02)
    s["tick"] = _norm(_bandnoise(t.size, 1800, 6000, rng) * np.exp(-t * 300), 0.35)
    keys = []
    for k in range(6):
        tt = _t(0.035)
        keys.append(_norm(_bandnoise(tt.size, 1200 + k * 200, 5200, rng) * np.exp(-tt * 180), 0.3 + 0.04 * k))
    s["keys"] = keys
    t = _t(0.06)
    c = _bandnoise(t.size, 1500, 7000, rng) * np.exp(-t * 260)
    c[int(0.028 * SR):] += _bandnoise(t.size - int(0.028 * SR), 1500, 7000, rng) * np.exp(-t[: t.size - int(0.028 * SR)] * 300) * 0.6
    s["click"] = _norm(c, 0.45)
    t = _t(0.9)
    bell = sum(a * np.sin(2 * np.pi * fr * t) * np.exp(-t * dec) for fr, a, dec in [(1318.5, 1, 5), (2637, 0.35, 8), (3951, 0.15, 11)])
    bell2 = np.zeros_like(bell)
    off = int(0.09 * SR)
    bell2[off:] = sum(a * np.sin(2 * np.pi * fr * t[:-off]) * np.exp(-t[:-off] * dec) for fr, a, dec in [(1975.5, 1, 5), (3951, 0.3, 9)])
    s["ding"] = _norm(bell + bell2, 0.42)
    t = _t(0.4)
    s["coin"] = _norm(np.sin(2 * np.pi * 2637 * t) * np.exp(-t * 9) + 0.7 * np.sin(2 * np.pi * 3520 * t) * np.exp(-t * 12), 0.3)
    t = _t(0.22)
    s["swoosh_in"] = _norm(_bandnoise(t.size, 600, 5000, rng) * (t / 0.22) ** 2 * np.exp(-((t - 0.18) * 18) ** 2), 0.35)
    return s


def build_sfx_track(events, total):
    """events: list of (time, name). Returns stereo float32 array."""
    lib = make_sfx()
    n = int(total * SR)
    out = np.zeros((n, 2), np.float32)
    rng = random.Random(4)
    for tm, name in sorted(events):
        x = lib[name]
        if isinstance(x, list):
            x = rng.choice(x)
        s = int(tm * SR)
        if s < 0 or s >= n:
            continue
        e = min(n, s + x.size)
        pan = 0.5 if name not in ("whoosh",) else 0.5
        out[s:e, 0] += x[: e - s] * (1 - pan) * 2 * 0.5 + x[: e - s] * 0.5
        out[s:e, 1] += x[: e - s] * pan * 2 * 0.5 + x[: e - s] * 0.5
    return out * 0.55
