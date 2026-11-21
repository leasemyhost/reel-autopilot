"""Reusable animated card library for engine2 reels.

Every card: fn(layer, t, L, ev, p)
  layer : RGBA canvas (None when collecting events)
  t     : current time (s)
  L     : absolute start times of the section's lines + section end  (len = n_lines + 1)
  ev    : list to append (time, sfx_name) when collecting events, else None
  p     : params dict from the spec
Cards only use the area between y=480 and y=1270 (captions live above/below).
"""
import math
from functools import lru_cache

from PIL import Image, ImageDraw

import engine2 as E
from engine2 import (CREAM, DARK, DARK2, GREEN, GREY, INK, ORANGE, RED, WHITE, check_icon, coin_sprite,
                     cross_icon, cursor_sprite, ease_back, ease_in_out, ease_out, label_pill, mono, paste, pill,
                     pop_in, prog, rrect, sans, shadowed, window)

CY = 880


# ------------------------------------------------------------------ helpers
@lru_cache(maxsize=32)
def sh_window(w, h, title, dark=False):
    im, _ = window(w, h, title, dark)
    return shadowed(im)


@lru_cache(maxsize=64)
def sh_card(w, h, border=None):
    return shadowed(rrect(w, h, 24, (255, 255, 255, 255), outline=border or (226, 221, 215, 255), width=3 if border else 2))


def lerp(a, b, q):
    return a + (b - a) * q


def fmt_num(v, style="inr"):
    v = int(round(v))
    if style == "inr":
        s = str(abs(v))
        if len(s) > 3:
            last3, rest = s[-3:], s[:-3]
            parts = []
            while len(rest) > 2:
                parts.insert(0, rest[-2:])
                rest = rest[:-2]
            if rest:
                parts.insert(0, rest)
            s = ",".join(parts) + "," + last3
        return "₹" + s
    if style == "usd":
        return "$" + f"{v:,}"
    if style == "pct":
        return f"{v}%"
    if style == "k":
        return f"{v / 1000:.1f}K" if v >= 1000 else str(v)
    return f"{v:,}"


def fit_text(d, text, size, maxw, weight="Bold"):
    while size > 16 and d.textlength(text, font=sans(size, weight)) > maxw:
        size -= 2
    return sans(size, weight)


def coins(layer, t, start, spots, symbol="₹"):
    for i, (x, y) in enumerate(spots):
        s, a = pop_in(t, start + i * 0.12, 0.35)
        if a > 0:
            paste(layer, coin_sprite(64, symbol), x, y + math.sin(t * 2.2 + i) * 8, scale=s, alpha=a,
                  rot=math.sin(t * 1.5 + i) * 10)


def sparkles(layer, t, start, spots):
    d = ImageDraw.Draw(layer)
    for i, (x, y) in enumerate(spots):
        q = prog(t, start + i * 0.2, 0.3)
        if q > 0:
            E.star(d, x, y, 14 * ease_back(q) * (0.85 + 0.15 * math.sin(t * 5 + i)))


def cursor(layer, x, y, click_t=None, t=0):
    paste(layer, cursor_sprite(), x + 14, y + 22)
    if click_t is not None and 0 <= t - click_t < 0.35:
        q = (t - click_t) / 0.35
        r = 18 + 40 * q
        ImageDraw.Draw(layer).ellipse([x - r, y - r, x + r, y + r], outline=ORANGE + (int(200 * (1 - q)),), width=4)


def at(L, spec, default=0.0):
    """Resolve a time spec: number = seconds after section start; 'l2+0.3' = line 2 start + 0.3."""
    if spec is None:
        return L[0] + default
    if isinstance(spec, (int, float)):
        return L[0] + spec
    s = str(spec)
    if s.startswith("l"):
        k, _, off = s[1:].partition("+")
        return L[min(int(k), len(L) - 1)] + (float(off) if off else 0.0)
    return L[0] + float(s)


def maybe_label(layer, t, L, p, y=500):
    if p.get("label"):
        paste(layer, label_pill(p["label"].upper()), 540, y, *pop_in(t, L[0], 0.3))
        return True
    return False


@lru_cache(maxsize=8)
def phone_sprite(title="SHARMA", subtitle="BAKERY", cta="Order on WhatsApp", line="Fresh cakes daily"):
    w, h = 300, 560
    im = rrect(w, h, 46, (24, 24, 28, 255))
    sc = rrect(w - 24, h - 24, 36, (255, 255, 255, 255))
    d = ImageDraw.Draw(sc)
    d.rounded_rectangle([0, 0, w - 25, 150], radius=36, fill=(214, 108, 60))
    d.rectangle([0, 60, w - 25, 150], fill=(214, 108, 60))
    d.text(((w - 24) / 2, 80), title[:12], font=sans(30, "Black"), fill=WHITE, anchor="mm")
    d.text(((w - 24) / 2, 114), subtitle[:16], font=sans(22, "Bold"), fill=(255, 225, 205), anchor="mm")
    d.rounded_rectangle([22, 172, w - 47, 300], radius=18, fill=(250, 228, 205))
    for cx, col in [(70, (226, 140, 96)), (138, (240, 190, 120)), (206, (200, 110, 80))]:
        d.ellipse([cx - 32, 205, cx + 32, 269], fill=col)
    d.text((22, 330), line[:22], font=sans(22, "Bold"), fill=INK)
    for k in range(3):
        d.rounded_rectangle([22, 370 + k * 34, w - 47 - k * 40, 388 + k * 34], radius=9, fill=(236, 233, 229))
    d.rounded_rectangle([22, 470, w - 47, 516], radius=23, fill=GREEN)
    d.text(((w - 24) / 2, 493), cta[:20], font=sans(19, "Bold"), fill=WHITE, anchor="mm")
    im.alpha_composite(sc, (12, 12))
    return shadowed(im)


# ------------------------------------------------------------------ 1. hero
def hero(layer, t, L, ev, p):
    """params: window, title, subtitle, badge, stat_label, stat_from, stat_to, stat_style, stat_at,
    stat_chip, checklist_title, items[3], check_at, phone{title,subtitle,cta,line}, coin_symbol"""
    T = L[0]
    items = p.get("items", [])[:4]
    stat_at = at(L, p.get("stat_at", "l1"))
    check_at = at(L, p.get("check_at", "l2+0.25"))
    if ev is not None:
        ev += [(T + 0.05, "pop"), (T + 0.35, "swoosh_in"), (T + 0.55, "pop"), (T + 0.75, "pop")]
        ev += [(stat_at + k * 0.5, "coin") for k in range(3)] + [(check_at + k * 0.45, "ding") for k in range(len(items))]
        return
    s, a = pop_in(t, T, 0.4)
    paste(layer, sh_window(920, 660, p.get("window", "claude-code")), 540, CY, scale=s, alpha=a)
    if t < T + 0.25:
        return
    d = ImageDraw.Draw(layer)
    x0, y0 = 80, CY - 330
    d.rounded_rectangle([x0 + 36, y0 + 92, x0 + 92, y0 + 148], radius=14, fill=ORANGE)
    E.star(d, x0 + 64, y0 + 120, 18, color=WHITE)
    d.text((x0 + 112, y0 + 104), p.get("title", ""), font=fit_text(d, p.get("title", ""), 34, 520), fill=INK, anchor="lm")
    d.text((x0 + 112, y0 + 138), p.get("subtitle", ""), font=sans(22, "Regular"), fill=GREY, anchor="lm")
    if p.get("badge"):
        paste(layer, pill(p["badge"], (255, 244, 236, 255), ORANGE, size=22, h=46, outline=ORANGE + (255,)), x0 + 780, y0 + 120)
    s2, a2 = pop_in(t, T + 0.35, 0.4)
    ph = p.get("phone", {})
    paste(layer, phone_sprite(ph.get("title", "MY"), ph.get("subtitle", "BUSINESS"), ph.get("cta", "Contact on WhatsApp"),
                              ph.get("line", "Online in 15 min")), x0 + 220, y0 + 440, scale=0.82 * s2, alpha=a2, rot=(1 - a2) * 8)
    s3, a3 = pop_in(t, T + 0.55, 0.35)
    paste(layer, sh_card(440, 220), x0 + 650, y0 + 330, scale=s3, alpha=a3)
    if a3 > 0.9:
        d.text((x0 + 455, y0 + 262), p.get("stat_label", "").upper(), font=mono(20), fill=GREY, anchor="lm")
        v = lerp(p.get("stat_from", 0), p.get("stat_to", 0), ease_out(prog(t, stat_at, 1.2)))
        d.text((x0 + 455, y0 + 325), fmt_num(v, p.get("stat_style", "inr")), font=sans(64, "Bold"), fill=INK, anchor="lm")
        if p.get("stat_chip") and t > stat_at + 1.2:
            paste(layer, pill(p["stat_chip"], (225, 246, 233, 255), GREEN, size=20, h=40), x0 + 540, y0 + 392,
                  scale=ease_back(prog(t, stat_at + 1.2, 0.3)))
    s4, a4 = pop_in(t, T + 0.75, 0.35)
    paste(layer, sh_card(440, 230, border=ORANGE + (255,)), x0 + 650, y0 + 560, scale=s4, alpha=a4)
    if a4 > 0.9:
        d.text((x0 + 455, y0 + 480), p.get("checklist_title", "").upper(), font=mono(20, True), fill=ORANGE, anchor="lm")
        for k, item in enumerate(items[:3]):
            yy = y0 + 528 + k * 50
            done = t > check_at + k * 0.45
            if done:
                check_icon(d, x0 + 470, yy, 14)
            else:
                d.ellipse([x0 + 456, yy - 14, x0 + 484, yy + 14], outline=(200, 196, 190), width=3)
            d.text((x0 + 498, yy), item, font=fit_text(d, item, 25, 360, "Bold" if done else "Medium"),
                   fill=INK if done else GREY, anchor="lm")
    coins(layer, t, T + 0.9, [(95, 575), (985, 560), (90, 1200), (990, 1215)], p.get("coin_symbol", "₹"))
    sparkles(layer, t, T + 1.1, [(1010, 760), (70, 900)])


# ------------------------------------------------------------------ 2. list_scan
def list_scan(layer, t, L, ev, p):
    """params: window, heading, items[{name, initial, from, to, flip_at}], counter_fmt '{n}/10 online',
    search{text, at, tag}"""
    T = L[0]
    items = p.get("items", [])[:10]
    flips = [(i, at(L, it.get("flip_at"))) for i, it in enumerate(items) if it.get("flip_at") is not None]
    srch = p.get("search")
    if ev is not None:
        ev += [(T + 0.4 + k * 0.16, "tick") for k in range(len(items))] + [(ft, "ding") for _, ft in flips]
        if srch:
            st = at(L, srch.get("at", "l2"))
            ev += [(st + 0.1 + k * 0.08, "keys") for k in range(min(16, len(srch.get("text", ""))))]
            if srch.get("tag"):
                ev += [(st + 1.4, "pop")]
        return
    s, a = pop_in(t, T, 0.4)
    paste(layer, sh_window(920, 690, p.get("window", "scan")), 540, CY, scale=s, alpha=a)
    if t < T + 0.3:
        return
    d = ImageDraw.Draw(layer)
    x0, y0 = 80, CY - 345
    d.text((x0 + 40, y0 + 100), p.get("heading", ""), font=fit_text(d, p.get("heading", ""), 28, 560), fill=INK, anchor="lm")
    n_on = sum(1 for i, ft in flips if t > ft)
    if p.get("counter_fmt"):
        d.text((x0 + 880, y0 + 100), p["counter_fmt"].format(n=n_on), font=mono(24, True), fill=GREEN if n_on else RED, anchor="rm")
    two_col = len(items) > 5
    for i, it in enumerate(items):
        c, r = (i % 2, i // 2) if two_col else (0, i)
        cw = 405 if two_col else 840
        cx, cy = x0 + 40 + c * 425, y0 + 140 + r * 82
        q0 = prog(t, T + 0.4 + i * 0.16, 0.25)
        if q0 <= 0:
            continue
        dx = (1 - ease_back(q0)) * 40
        d.rounded_rectangle([cx + dx, cy, cx + cw + dx, cy + 68], radius=16, fill=WHITE, outline=(228, 223, 217), width=2)
        d.ellipse([cx + 14 + dx, cy + 12, cx + 58 + dx, cy + 56], fill=(255, 236, 224))
        d.text((cx + 36 + dx, cy + 34), it.get("initial", it["name"][:1]), font=sans(22, "Bold"), fill=ORANGE, anchor="mm")
        d.text((cx + 72 + dx, cy + 34), it["name"], font=fit_text(d, it["name"], 23, cw - 200), fill=INK, anchor="lm")
        flipped = it.get("flip_at") is not None and t > at(L, it["flip_at"])
        tag = it.get("to", "Done") if flipped else it.get("from", "")
        if tag:
            good = flipped
            col, bg = (GREEN, (225, 246, 233)) if good else (RED, (253, 232, 229))
            tw = d.textlength(tag, font=sans(18, "Bold"))
            d.rounded_rectangle([cx + cw - 15 - tw - 24 + dx, cy + 20, cx + cw - 15 + dx, cy + 48], radius=14, fill=bg)
            d.text((cx + cw - 27 + dx, cy + 34), tag, font=sans(18, "Bold"), fill=col, anchor="rm")
    if srch:
        st = at(L, srch.get("at", "l2"))
        if t > st:
            by = y0 + 580
            d.rounded_rectangle([x0 + 40, by, x0 + 880, by + 70], radius=35, fill=WHITE, outline=(220, 215, 210), width=2)
            d.ellipse([x0 + 64, by + 22, x0 + 90, by + 48], outline=GREY, width=4)
            d.line([x0 + 86, by + 44, x0 + 98, by + 56], fill=GREY, width=4)
            q = srch.get("text", "")
            n = int(len(q) * prog(t, st + 0.1, 1.1))
            d.text((x0 + 120, by + 35), q[:n] + ("|" if int(t * 3) % 2 else ""), font=sans(28, "Medium"), fill=INK, anchor="lm")
            if srch.get("tag") and t > st + 1.4:
                paste(layer, pill(srch["tag"], ORANGE + (255,), WHITE, size=22, h=44), x0 + 740, by + 35,
                      scale=ease_back(prog(t, st + 1.4, 0.3)))


# ------------------------------------------------------------------ 3. terminal
def terminal(layer, t, L, ev, p):
    """params: label, window, prompts[{text, at}], results[{text, at}], cards[{title, sub, chip, green}]"""
    T = L[0]
    prompts = p.get("prompts", [])[:3]
    results = p.get("results", [])[:4]
    cards_ = p.get("cards", [])[:2]
    if ev is not None:
        ev += [(T + 0.05, "pop")]
        for pr in prompts:
            st = at(L, pr.get("at"), 0.4)
            ev += [(st + k * 0.07, "keys") for k in range(min(20, len(pr["text"])))]
        ev += [(at(L, r.get("at")), "ding") for r in results] + [(T + 0.9 + k * 0.15, "pop") for k in range(len(cards_))]
        return
    has_label = maybe_label(layer, t, L, p, 500)
    wy = 790 if has_label else 760
    s, a = pop_in(t, T + 0.1, 0.4)
    paste(layer, sh_window(920, 460, p.get("window", "terminal"), dark=True), 540, wy, scale=s, alpha=a)
    d = ImageDraw.Draw(layer)
    if t > T + 0.4:
        x0, y0 = 80, wy - 230
        yy = y0 + 110
        for k, pr in enumerate(prompts):
            st = at(L, pr.get("at"), 0.4)
            if t < st:
                continue
            nxt = at(L, prompts[k + 1].get("at"), 0.4) if k + 1 < len(prompts) else st + 1.6
            n = int(len(pr["text"]) * prog(t, st, max(0.6, (nxt - st) * 0.8)))
            if k == 0:
                d.rounded_rectangle([x0 + 30, yy - 32, x0 + 890, yy + 32], radius=14, fill=(45, 51, 68))
                d.rounded_rectangle([x0 + 44, yy - 20, x0 + 84, yy + 20], radius=10, fill=ORANGE)
                E.star(d, x0 + 64, yy, 13, color=WHITE)
            col = (235, 236, 240) if k == 0 else (120, 222, 160)
            txt = pr["text"][:n] + ("▌" if n < len(pr["text"]) and int(t * 4) % 2 else "")
            d.text((x0 + 104, yy), txt, font=mono(24), fill=col, anchor="lm")
            yy += 62
        yy += 8
        for r in results:
            if t > at(L, r.get("at")):
                check_icon(d, x0 + 58, yy, 14, color=(120, 222, 160), fg=DARK)
                d.text((x0 + 80, yy), r["text"], font=mono(23), fill=(200, 204, 214), anchor="lm")
                yy += 44
    for k, c in enumerate(cards_):
        cx = 315 + k * 450
        sc, al = pop_in(t, T + 0.9 + k * 0.15, 0.35)
        paste(layer, sh_card(430, 190, border=GREEN + (255,) if c.get("green") else None), cx, 1155, scale=sc, alpha=al)
        if al > 0.9:
            if c.get("chip"):
                paste(layer, pill(c["chip"], (GREEN if c.get("green") else ORANGE) + (255,), WHITE, size=28, h=58, pad=30), cx, 1115)
                d.text((cx, 1175), c.get("title", ""), font=fit_text(d, c.get("title", ""), 25, 390), fill=INK, anchor="mm")
                d.text((cx, 1207), c.get("sub", ""), font=sans(19, "Medium"), fill=GREEN if c.get("green") else GREY, anchor="mm")
            else:
                d.text((cx, 1130), c.get("title", ""), font=fit_text(d, c.get("title", ""), 28, 390), fill=INK, anchor="mm")
                d.text((cx, 1172), c.get("sub", ""), font=sans(21, "Regular"), fill=GREY, anchor="mm")


# ------------------------------------------------------------------ 4. chat
def chat(layer, t, L, ev, p):
    """params: label, phone{...}, contact, status, messages[{text, mine, at}], stamp, stamp_at"""
    T = L[0]
    msgs = p.get("messages", [])[:5]
    stamp_at = at(L, p.get("stamp_at"), (L[-1] - L[0]) - 0.6)
    if ev is not None:
        ev += [(T + 0.05, "pop"), (T + 0.3, "swoosh_in"), (T + 0.5, "pop")] + [(at(L, m.get("at")), "pop") for m in msgs]
        if p.get("stamp"):
            ev += [(stamp_at, "ding")]
        return
    maybe_label(layer, t, L, p, 500)
    ph = p.get("phone", {})
    s, a = pop_in(t, T + 0.3, 0.4)
    paste(layer, phone_sprite(ph.get("title", "MY"), ph.get("subtitle", "BUSINESS"), ph.get("cta", "Contact on WhatsApp"),
                              ph.get("line", "Online in 15 min")), 300, CY + 30, scale=s, alpha=a, rot=(1 - a) * -10)
    s2, a2 = pop_in(t, T + 0.5, 0.4)
    paste(layer, sh_card(520, 560), 745, CY + 30, scale=s2, alpha=a2)
    if a2 < 0.9:
        return
    d = ImageDraw.Draw(layer)
    x0, y0 = 485, CY - 250
    d.ellipse([x0 + 24, y0 + 22, x0 + 74, y0 + 72], fill=(225, 246, 233))
    d.text((x0 + 49, y0 + 47), p.get("contact", "C")[:1], font=sans(24, "Bold"), fill=GREEN, anchor="mm")
    d.text((x0 + 90, y0 + 36), p.get("contact", "Customer"), font=sans(25, "Bold"), fill=INK, anchor="lm")
    d.text((x0 + 90, y0 + 64), p.get("status", "online"), font=sans(18, "Regular"), fill=GREEN, anchor="lm")
    d.line([x0 + 20, y0 + 90, x0 + 500, y0 + 90], fill=(236, 232, 226), width=2)
    yy = y0 + 120
    for m in msgs:
        q0 = prog(t, at(L, m.get("at")), 0.25)
        if q0 <= 0:
            continue
        f = sans(22, "Medium")
        txt = m["text"]
        while d.textlength(txt, font=f) > 420 and len(txt) > 4:
            txt = txt[:-2]
        bw = d.textlength(txt, font=f) + 36
        if m.get("mine"):
            bx1, bx0, fill = x0 + 490, x0 + 490 - bw, (220, 248, 198)
        else:
            bx0, bx1, fill = x0 + 22, x0 + 22 + bw, (243, 241, 238)
        off = (1 - ease_back(q0)) * 20
        d.rounded_rectangle([bx0, yy + off, bx1, yy + 56 + off], radius=18, fill=fill)
        d.text(((bx0 + bx1) / 2, yy + 28 + off), txt, font=f, fill=INK, anchor="mm")
        yy += 72
    if p.get("stamp") and t > stamp_at:
        paste(layer, pill(p["stamp"], GREEN + (255,), WHITE, size=34, h=72, pad=40), x0 + 260, y0 + 470,
              scale=ease_back(prog(t, stamp_at, 0.35)), rot=-8)


# ------------------------------------------------------------------ 5. stats
def stats(layer, t, L, ev, p):
    """params: window, label, start_value, end_value, style, grow_at, bars, bar_label_fmt '{n} clients',
    footer, chip, chip_at, coin_symbol"""
    T = L[0]
    nb = int(p.get("bars", 10))
    g0 = at(L, p.get("grow_at", "l1+0.1"))
    g1 = at(L, p.get("grow_end", "l2-0.2")) if p.get("grow_end") else (L[2] - 0.2 if len(L) > 2 else L[-1] - 0.4)
    g1 = max(g1, g0 + 0.8)
    bar_t = [g0 + k * (g1 - g0) / nb for k in range(nb)]
    chip_at = at(L, p.get("chip_at", "l2+0.2"))
    if ev is not None:
        ev += [(T + 0.05, "pop")] + [(T + 0.4 + k * 0.25, "coin") for k in range(3)] + [(b, "tick") for b in bar_t]
        ev += [(g1, "ding")] + ([(chip_at, "pop")] if p.get("chip") else [])
        return
    s, a = pop_in(t, T, 0.4)
    paste(layer, sh_window(920, 680, p.get("window", "dashboard"), dark=True), 540, CY, scale=s, alpha=a)
    if t < T + 0.35:
        return
    d = ImageDraw.Draw(layer)
    x0, y0 = 80, CY - 340
    d.text((x0 + 44, y0 + 110), p.get("label", "").upper(), font=mono(22, True), fill=(150, 156, 175), anchor="lm")
    sv, evv = p.get("start_value", 0), p.get("end_value", 100)
    v = sv * ease_out(prog(t, T + 0.3, 1.0))
    if t > g0:
        v = sv + (evv - sv) * ease_in_out(prog(t, g0, g1 - g0))
    d.text((x0 + 44, y0 + 190), fmt_num(v, p.get("style", "inr")), font=sans(92, "Bold"), fill=WHITE, anchor="lm")
    nc = max(1, sum(1 for b in bar_t if t > b)) if t > g0 else 1
    if p.get("bar_label_fmt"):
        d.text((x0 + 876, y0 + 190), p["bar_label_fmt"].format(n=nc), font=sans(30, "Bold"), fill=(120, 222, 160), anchor="rm")
    base = y0 + 560
    bw = min(56, int(780 / nb) - 20)
    for k in range(nb):
        bx = x0 + 60 + k * (820 / nb)
        on = (k == 0 and t > T + 0.3) or (t > bar_t[k] and t > g0)
        if on:
            h = 200 * ease_back(prog(t, T + 0.3 if k == 0 else bar_t[k], 0.3)) + 40 * (k / max(1, nb - 1))
            d.rounded_rectangle([bx, base - h, bx + bw, base], radius=10, fill=ORANGE)
        else:
            d.rounded_rectangle([bx, base - 18, bx + bw, base], radius=8, fill=DARK2)
    d.line([x0 + 44, base + 10, x0 + 876, base + 10], fill=(60, 66, 84), width=2)
    d.text((x0 + 44, base + 50), p.get("footer", ""), font=mono(22), fill=(150, 156, 175), anchor="lm")
    if p.get("chip") and t > chip_at:
        paste(layer, pill(p["chip"], (225, 246, 233, 255), GREEN, size=26, h=60), 540, CY + 410, scale=ease_back(prog(t, chip_at, 0.35)))
    coins(layer, t, T + 0.4, [(110, 560), (980, 600), (1000, 1180)], p.get("coin_symbol", "₹"))


# ------------------------------------------------------------------ 6. crosses
def crosses(layer, t, L, ev, p):
    """params: items[{title, sub}] (3), cross_at[3], final{title, sub, bar_label, at}"""
    T = L[0]
    items = p.get("items", [])[:3]
    seg = (L[1] - L[0]) if len(L) > 2 else (L[-1] - L[0]) * 0.6
    cts = [at(L, c) for c in p.get("cross_at", [])] or [T + seg * f for f in (0.28, 0.55, 0.82)][:len(items)]
    fin = p.get("final")
    fin_at = at(L, fin.get("at", "l1")) if fin else None
    if ev is not None:
        ev += [(T + 0.05 + k * 0.12, "pop") for k in range(len(items))] + [(c, "click") for c in cts]
        if fin:
            ev += [(fin_at + 0.05, "swoosh_in"), (fin_at + 0.3, "pop"), (L[-1] - 0.5, "ding")]
        return
    d = ImageDraw.Draw(layer)
    for k, it in enumerate(items):
        cx = 210 + k * 330
        s, a = pop_in(t, T + k * 0.12, 0.35)
        paste(layer, sh_card(290, 260), cx, 680, scale=s, alpha=a)
        if a > 0.9:
            f = fit_text(d, it["title"], 38, 250)
            d.text((cx, 650), it["title"], font=f, fill=INK, anchor="mm")
            d.text((cx, 698), it.get("sub", ""), font=fit_text(d, it.get("sub", ""), 22, 250, "Medium"), fill=GREY, anchor="mm")
            if k < len(cts) and t > cts[k]:
                q = ease_back(prog(t, cts[k], 0.3))
                cross_icon(d, cx + 110, 575, max(1, 30 * q))
                w2 = min(120, d.textlength(it["title"], font=f) / 2 + 8) * ease_out(prog(t, cts[k], 0.25))
                d.line([cx - w2, 650, cx + w2, 650], fill=RED, width=6)
    if fin and t > fin_at:
        s, a = pop_in(t, fin_at + 0.05, 0.4)
        paste(layer, sh_window(760, 380, "", dark=True), 540, 1070, scale=s, alpha=a)
        if a > 0.9:
            d.rounded_rectangle([250, 960, 410, 1060], radius=10, fill=(60, 66, 84), outline=(120, 126, 145), width=3)
            d.rounded_rectangle([225, 1060, 435, 1078], radius=8, fill=(120, 126, 145))
            E.star(d, 330, 1010, 22, color=ORANGE)
            d.text((470, 990), fin.get("title", ""), font=fit_text(d, fin.get("title", ""), 38, 380), fill=WHITE, anchor="lm")
            d.text((470, 1036), fin.get("sub", ""), font=sans(28, "Medium"), fill=(150, 156, 175), anchor="lm")
            d.text((250, 1130), fin.get("bar_label", "").upper(), font=mono(22, True), fill=(150, 156, 175), anchor="lm")
            hp = ease_in_out(prog(t, fin_at + 0.5, max(0.8, L[-1] - fin_at - 1.0)))
            d.rounded_rectangle([400, 1120, 830, 1142], radius=11, fill=DARK2)
            d.rounded_rectangle([400, 1120, 400 + 430 * hp, 1142], radius=11, fill=GREEN)
            d.text((850, 1131), f"{int(hp * 100)}%", font=mono(22, True), fill=(120, 222, 160), anchor="lm")


# ------------------------------------------------------------------ 7. compare
def compare(layer, t, L, ev, p):
    """params: left{title, lines[]}, right{title, lines[]}, right_at, verdict"""
    T = L[0]
    lt, rt = p.get("left", {}), p.get("right", {})
    r_at = at(L, p.get("right_at", "l1"))
    if ev is not None:
        ev += [(T + 0.05, "pop")] + [(T + 0.4 + k * 0.3, "tick") for k in range(len(lt.get("lines", [])))]
        ev += [(r_at, "swoosh_in"), (r_at + 0.1, "pop")] + [(r_at + 0.4 + k * 0.3, "ding") for k in range(len(rt.get("lines", [])))]
        if p.get("verdict"):
            ev += [(L[-1] - 0.7, "pop")]
        return
    d = ImageDraw.Draw(layer)
    for side, (cx, data, good, st) in enumerate([(300, lt, False, T), (780, rt, True, r_at)]):
        s, a = pop_in(t, st, 0.4)
        paste(layer, sh_card(440, 600, border=(GREEN if good else RED) + (255,)), cx, CY, scale=s, alpha=a, rot=(1 - a) * (6 if good else -6))
        if a < 0.9:
            continue
        col = GREEN if good else RED
        d.rounded_rectangle([cx - 190, CY - 270, cx + 190, CY - 200], radius=35, fill=col)
        d.text((cx, CY - 235), data.get("title", ""), font=fit_text(d, data.get("title", ""), 30, 340), fill=WHITE, anchor="mm")
        for k, ln in enumerate(data.get("lines", [])[:5]):
            if t > st + 0.4 + k * 0.3:
                yy = CY - 140 + k * 82
                (check_icon if good else cross_icon)(d, cx - 170, yy, 18)
                d.text((cx - 138, yy), ln, font=fit_text(d, ln, 25, 320, "Bold"), fill=INK, anchor="lm")
    if p.get("verdict") and t > L[-1] - 0.7:
        paste(layer, shadowed(pill(p["verdict"], ORANGE + (255,), WHITE, size=34, h=76, pad=40), offset=8, blur=12),
              540, CY + 330, scale=ease_back(prog(t, L[-1] - 0.7, 0.35)))


# ------------------------------------------------------------------ 8. steps
def steps(layer, t, L, ev, p):
    """params: window, items[{title, sub, at}]  - numbered rows that appear & tick"""
    T = L[0]
    items = p.get("items", [])[:5]
    times = [at(L, it.get("at"), 0.4 + k * 0.5) for k, it in enumerate(items)]
    if ev is not None:
        ev += [(T + 0.05, "pop")] + [(tm, "pop") for tm in times] + [(tm + 0.5, "ding") for tm in times]
        return
    s, a = pop_in(t, T, 0.4)
    h = 140 + 110 * len(items)
    paste(layer, sh_window(920, h, p.get("window", "step-by-step")), 540, CY, scale=s, alpha=a)
    d = ImageDraw.Draw(layer)
    y0 = CY - h / 2 + 90
    for k, (it, tm) in enumerate(zip(items, times)):
        q = prog(t, tm, 0.3)
        if q <= 0:
            continue
        dx = (1 - ease_back(q)) * 60
        yy = y0 + k * 110
        d.rounded_rectangle([120 + dx, yy, 960 + dx, yy + 92], radius=20, fill=WHITE, outline=(228, 223, 217), width=2)
        d.rounded_rectangle([140 + dx, yy + 18, 196 + dx, yy + 74], radius=14, fill=ORANGE if t < tm + 0.5 else GREEN)
        d.text((168 + dx, yy + 46), f"{k + 1:02d}", font=mono(24, True), fill=WHITE, anchor="mm")
        d.text((220 + dx, yy + 32), it["title"], font=fit_text(d, it["title"], 28, 600), fill=INK, anchor="lm")
        d.text((220 + dx, yy + 64), it.get("sub", ""), font=sans(20, "Regular"), fill=GREY, anchor="lm")
        if t > tm + 0.5:
            check_icon(d, 920 + dx, yy + 46, 18)


# ------------------------------------------------------------------ 9. big_number
def big_number(layer, t, L, ev, p):
    """params: label, from, to, style, sub, chips[]"""
    T = L[0]
    chips = p.get("chips", [])[:3]
    if ev is not None:
        ev += [(T + 0.05, "pop")] + [(T + 0.3 + k * 0.3, "coin") for k in range(4)] + [(T + 1.4 + k * 0.25, "pop") for k in range(len(chips))]
        return
    s, a = pop_in(t, T, 0.4)
    paste(layer, sh_card(900, 520), 540, CY - 40, scale=s, alpha=a)
    if a < 0.9:
        return
    d = ImageDraw.Draw(layer)
    d.text((540, CY - 230), p.get("label", "").upper(), font=mono(26, True), fill=GREY, anchor="mm")
    v = lerp(p.get("from", 0), p.get("to", 0), ease_out(prog(t, T + 0.3, 1.2)))
    d.text((540, CY - 90), fmt_num(v, p.get("style", "plain")), font=sans(150, "Bold"), fill=ORANGE, anchor="mm")
    d.text((540, CY + 40), p.get("sub", ""), font=fit_text(d, p.get("sub", ""), 32, 780, "Medium"), fill=INK, anchor="mm")
    for k, c in enumerate(chips):
        paste(layer, pill(c, (243, 241, 238, 255), INK, size=24, h=52, weight="SemiBold"), 240 + k * 300, CY + 300,
              *pop_in(t, T + 1.4 + k * 0.25, 0.3))
    coins(layer, t, T + 0.3, [(110, 560), (980, 560), (120, 1180), (970, 1200)], p.get("coin_symbol", "₹"))


# ------------------------------------------------------------------ 10. cta
def cta(layer, t, L, ev, p):
    """params: keyword, name, initials, dm_text, dm_sub"""
    T = L[0]
    kw = p.get("keyword", "GUIDE").upper()
    follow_t, type_t, post_t = T + 0.9, T + 1.4, T + 2.0
    dm_t = L[1] + 0.2 if len(L) > 2 else T + 2.6
    if ev is not None:
        ev += [(T + 0.05, "pop"), (T + 0.25, "pop"), (follow_t, "click"), (follow_t + 0.05, "ding")]
        ev += [(type_t + k * 0.08, "keys") for k in range(len(kw))] + [(post_t, "click"), (post_t + 0.1, "pop"),
                                                                       (dm_t, "swoosh_in"), (dm_t + 0.3, "ding")]
        return
    s, a = pop_in(t, T, 0.35)
    paste(layer, shadowed(pill(kw, ORANGE + (255,), WHITE, size=56, h=110, pad=60), offset=10, blur=14), 540, 600, scale=s, alpha=a)
    s2, a2 = pop_in(t, T + 0.25, 0.4)
    paste(layer, sh_card(900, 260), 540, 860, scale=s2, alpha=a2)
    d = ImageDraw.Draw(layer)
    if a2 > 0.9:
        d.ellipse([130, 760, 200, 830], fill=ORANGE)
        d.text((165, 795), p.get("initials", "JK"), font=sans(28, "Bold"), fill=WHITE, anchor="mm")
        d.text((220, 778), p.get("name", E.HANDLE), font=sans(30, "Bold"), fill=INK, anchor="lm")
        d.text((220, 814), f"Step 1: Follow · Step 2: Comment {kw}", font=fit_text(d, f"Step 1: Follow · Step 2: Comment {kw}", 20, 520, "Regular"),
               fill=GREY, anchor="lm")
        following = t > follow_t
        paste(layer, pill("Following ✓" if following else "Follow", (GREEN if following else (0, 149, 246)) + (255,), WHITE, size=22, h=48), 880, 795)
        d.rounded_rectangle([130, 870, 950, 940], radius=35, fill=(246, 244, 241))
        d.rounded_rectangle([146, 884, 188, 926], radius=12, fill=(214, 41, 118))
        d.rounded_rectangle([156, 894, 178, 916], radius=7, outline=WHITE, width=3)
        n = int(len(kw) * prog(t, type_t, 0.6))
        d.text((206, 905), kw[:n] + ("|" if int(t * 3) % 2 and t < post_t else ""), font=sans(28, "Bold"), fill=INK, anchor="lm")
        paste(layer, pill("Post", ORANGE + (255,), WHITE, size=22, h=46), 890, 905)
        if t < follow_t:
            q = ease_in_out(prog(t, T + 0.4, follow_t - T - 0.4))
            cursor(layer, lerp(700, 880, q), lerp(1000, 800, q))
        elif t < post_t:
            q = ease_in_out(prog(t, type_t, post_t - type_t))
            cursor(layer, lerp(880, 890, q), lerp(800, 908, q), click_t=follow_t, t=t)
        else:
            cursor(layer, 890, 908, click_t=post_t, t=t)
            for k in range(3):
                q = prog(t, post_t + k * 0.12, 0.9)
                if 0 < q < 1:
                    y, x, r = 760 - 120 * q, 870 + math.sin(q * 6 + k) * 30, 16 * (1 - q * 0.4)
                    col = (232, 64, 90, int(255 * (1 - q)))
                    d.ellipse([x - r, y - r, x, y], fill=col)
                    d.ellipse([x, y - r, x + r, y], fill=col)
                    d.polygon([(x - r, y - r / 2), (x + r, y - r / 2), (x, y + r * 0.9)], fill=col)
    s3, a3 = pop_in(t, dm_t, 0.4)
    paste(layer, sh_card(900, 150, border=GREEN + (255,)), 540, 1120 + (1 - a3) * 60, scale=s3, alpha=a3)
    if a3 > 0.9:
        d.rounded_rectangle([140, 1080, 230, 1118], radius=19, fill=GREEN)
        d.text((185, 1099), "DM", font=sans(20, "Bold"), fill=WHITE, anchor="mm")
        d.text((250, 1099), p.get("dm_text", "Guide bhej diya"), font=fit_text(d, p.get("dm_text", ""), 28, 640), fill=INK, anchor="lm")
        d.text((140, 1150), p.get("dm_sub", "Comment karo, seedha DM mein milega"), font=sans(21, "Regular"), fill=GREY, anchor="lm")
        check_icon(d, 930, 1120, 22)


CARDS = {"hero": hero, "list_scan": list_scan, "terminal": terminal, "chat": chat, "stats": stats,
         "crosses": crosses, "compare": compare, "steps": steps, "big_number": big_number, "cta": cta}
