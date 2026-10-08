# -*- coding: utf-8 -*-
"""Senaryo JSON -> 1080x1920 Reels MP4 (Pillow + ffmpeg). Tüm şablonlar aynı görsel dili kullanır."""
import math, subprocess, tempfile, random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from .config import FONTS, CFG
from . import music

W, H, FPS = 1080, 1920, 30
SAFE_TOP, SAFE_BOT, SAFE_X = 230, 1520, 80   # Reels arayüzünün kapatmadığı alan
DARK = (14, 16, 20); WHITE = (255, 255, 255); RED = (230, 57, 70); GREEN = (46, 196, 110)
AMBER = (255, 176, 32); YEL = (255, 214, 10); BLUE = (80, 160, 255); GREY = (150, 156, 166)
GRASS = (34, 52, 38); ASPH = (52, 55, 60); LINE = (235, 235, 230); WALK = (92, 94, 98)
ACCENT = {"dogru_yanlis": RED, "teknik": BLUE, "quiz": YEL, "cevap": GREEN, "tehlike": AMBER,
          "challenge": (176, 120, 255), "efsane": (255, 120, 80), "ekipman": (120, 200, 255),
          "yorum_soru": (90, 210, 190), "mini_sinav": YEL}
ETIKET = {"dogru_yanlis": "DOĞRU / YANLIŞ", "teknik": "TEKNİK", "quiz": "SEN OLSAN?", "cevap": "CEVAP",
          "tehlike": "TEHLİKE AVI", "challenge": "CHALLENGE", "efsane": "EFSANE Mİ?", "ekipman": "EKİPMAN",
          "yorum_soru": "SİZ SORDUNUZ", "mini_sinav": "MİNİ SINAV"}

_fc = {}
def F(sz, bold=True):
    k = (sz, bold)
    if k not in _fc:
        _fc[k] = ImageFont.truetype(str(FONTS / ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf")), sz)
    return _fc[k]

def clamp(v, a=0.0, b=1.0): return max(a, min(b, v))
def ease(t): t = clamp(t); return t * t * (3 - 2 * t)
def seg(t, a, b): return ease((t - a) / (b - a)) if b > a else float(t >= a)
def lerp(a, b, k): return a + (b - a) * k

def read_time(text, lo=2.2, hi=6.5):
    return clamp(1.0 + len(str(text).split()) * 0.36, lo, hi)

def wrap(text, font, width, d=None):
    d = d or ImageDraw.Draw(Image.new("RGB", (1, 1)))
    lines = []
    for para in str(text).split("\n"):
        cur = ""
        for w in para.split():
            t = (cur + " " + w).strip()
            if d.textlength(t, font=font) <= width: cur = t
            else:
                if cur: lines.append(cur)
                cur = w
        lines.append(cur)
    return lines

def fit_text(text, width, max_lines, start, minimum=34, bold=True):
    sz = start
    while sz > minimum:
        lines = wrap(text, F(sz, bold), width)
        if len(lines) <= max_lines: return F(sz, bold), lines
        sz -= 4
    return F(minimum, bold), wrap(text, F(minimum, bold), width)

# ---------------- sprite'lar ----------------
def _sprite(w, h): return Image.new("RGBA", (w, h), (0, 0, 0, 0))

def car_sprite(color=(70, 120, 200), w=130, h=250):
    im = _sprite(w + 12, h + 14); d = ImageDraw.Draw(im)
    d.rounded_rectangle([8, 12, w + 8, h + 12], 30, fill=(20, 22, 26, 150))
    d.rounded_rectangle([0, 0, w, h], 30, fill=color)
    dk = tuple(int(c * 0.35) for c in color)
    d.rounded_rectangle([14, 46, w - 14, 92], 10, fill=dk)
    d.rounded_rectangle([16, h - 72, w - 16, h - 38], 9, fill=dk)
    for sx in (24, w - 24):
        d.ellipse([sx - 12, 4, sx + 12, 18], fill=(255, 245, 200))
        d.rounded_rectangle([sx - 12, h - 10, sx + 12, h - 2], 3, fill=(200, 30, 30))
    return im

def truck_sprite(w=140, h=290):
    im = _sprite(w + 12, h + 14); d = ImageDraw.Draw(im)
    d.rounded_rectangle([8, 12, w + 8, h + 12], 16, fill=(20, 22, 26, 150))
    d.rounded_rectangle([5, 0, w - 5, 82], 20, fill=(225, 225, 220))
    d.rounded_rectangle([20, 40, w - 20, 72], 8, fill=(25, 35, 55))
    d.rounded_rectangle([0, 88, w, h], 10, fill=(205, 200, 190))
    for k in range(1, 5):
        y = 88 + k * (h - 88) / 5; d.line([12, y, w - 12, y], fill=(180, 175, 165), width=3)
    return im

def bus_sprite(w=150, h=420):
    im = _sprite(w + 12, h + 14); d = ImageDraw.Draw(im)
    d.rounded_rectangle([8, 12, w + 8, h + 12], 18, fill=(20, 22, 26, 150))
    d.rounded_rectangle([0, 0, w, h], 18, fill=(40, 150, 110))
    d.rounded_rectangle([12, 14, w - 12, 60], 8, fill=(25, 35, 55))
    for k in range(6): d.rounded_rectangle([w - 18, 80 + k * 52, w - 6, 120 + k * 52], 3, fill=(25, 35, 55))
    return im

def moto_sprite(color=(200, 30, 40), head_ang=0):
    im = _sprite(150, 240); d = ImageDraw.Draw(im); cx, cy = 75, 120
    d.rounded_rectangle([cx - 22, cy - 102, cx + 26, cy + 112], 22, fill=(20, 22, 26, 140))
    d.rounded_rectangle([cx - 11, cy - 110, cx + 11, cy - 68], 10, fill=(20, 20, 22))
    d.rounded_rectangle([cx - 13, cy + 58, cx + 13, cy + 110], 11, fill=(20, 20, 22))
    d.rounded_rectangle([cx - 27, cy - 74, cx + 27, cy + 64], 24, fill=color)
    d.line([cx - 56, cy - 58, cx + 56, cy - 58], fill=(25, 25, 28), width=9)
    for sx in (-1, 1):
        d.ellipse([cx + sx * 64 - 11, cy - 76, cx + sx * 64 + 11, cy - 56], fill=(180, 190, 200), outline=(25, 25, 28), width=3)
    d.rounded_rectangle([cx - 38, cy - 26, cx + 38, cy + 10], 16, fill=(30, 34, 40))
    d.ellipse([cx - 27, cy - 45, cx + 27, cy + 9], fill=(240, 240, 240), outline=(20, 20, 20), width=4)
    base = -90 - head_ang
    d.arc([cx - 27, cy - 45, cx + 27, cy + 9], base - 45, base + 45, fill=(20, 20, 24), width=11)
    return im

def ped_sprite(color=(240, 180, 60), s=1.0):
    r = int(26 * s); im = _sprite(int(90 * s), int(70 * s)); d = ImageDraw.Draw(im)
    cx, cy = im.width // 2, im.height // 2
    d.rounded_rectangle([cx - int(38 * s), cy - int(14 * s), cx + int(38 * s), cy + int(14 * s)], int(12 * s), fill=color)
    d.ellipse([cx - r // 1.4, cy - r // 1.4, cx + r // 1.4, cy + r // 1.4], fill=(60, 40, 30))
    return im

def bike_sprite():
    im = _sprite(70, 170); d = ImageDraw.Draw(im)
    d.rounded_rectangle([28, 4, 42, 50], 7, fill=(20, 20, 22)); d.rounded_rectangle([28, 118, 42, 166], 7, fill=(20, 20, 22))
    d.line([35, 40, 35, 130], fill=(60, 180, 220), width=8); d.line([10, 48, 60, 48], fill=(25, 25, 28), width=6)
    d.ellipse([20, 66, 50, 96], fill=(240, 200, 60))
    return im

def ball_sprite():
    im = _sprite(40, 40); d = ImageDraw.Draw(im); d.ellipse([2, 2, 38, 38], fill=(240, 60, 60), outline=WHITE, width=4); return im

def cone_sprite(s=1.0):
    r = int(20 * s); im = _sprite(2 * r + 6, 2 * r + 6); d = ImageDraw.Draw(im); c = r + 3
    d.ellipse([c - r, c - r, c + r, c + r], fill=(255, 120, 20)); d.ellipse([c - r * .55, c - r * .55, c + r * .55, c + r * .55], fill=WHITE)
    d.ellipse([c - r * .3, c - r * .3, c + r * .3, c + r * .3], fill=(255, 120, 20)); return im

CAR_COLORS = [(70, 120, 200), (200, 200, 205), (40, 40, 45), (170, 40, 40), (90, 140, 90), (220, 180, 60)]

def paste_c(img, sp, cx, cy, rot=0, alpha=1.0):
    if rot: sp = sp.rotate(rot, expand=True, resample=Image.BICUBIC)
    if alpha < 1:
        sp = sp.copy(); a = sp.getchannel("A").point(lambda v: int(v * alpha)); sp.putalpha(a)
    img.alpha_composite(sp, (int(cx - sp.width / 2), int(cy - sp.height / 2)))

# ---------------- arka planlar ----------------
def road_simple(t, dim=0):
    img = Image.new("RGBA", (W, H), GRASS + (255,)); d = ImageDraw.Draw(img)
    L, R, MID = 240, 840, 540
    d.rectangle([L, 0, R, H], fill=ASPH)
    d.rectangle([L + 18, 0, L + 28, H], fill=LINE); d.rectangle([R - 28, 0, R - 18, H], fill=LINE)
    off = (t * 700) % 240; y = -240 + off
    while y < H: d.rectangle([MID - 6, y, MID + 6, y + 120], fill=LINE); y += 240
    off2 = (t * 700) % 420; y = -420 + off2
    while y < H:
        for x in (110, 970):
            d.ellipse([x - 46, y - 46, x + 46, y + 46], fill=(28, 70, 40)); d.ellipse([x - 30, y - 30, x + 30, y + 30], fill=(40, 92, 52))
        y += 420
    if dim: img.alpha_composite(Image.new("RGBA", (W, H), DARK + (dim,)))
    return img

# Sahne (kuşbakışı, sağ trafik): kaldırım | park | sol şerit | sağ şerit | park | kaldırım
X = {"kaldirim_sol": 55, "sol_park": 185, "sol": 400, "sag": 680, "sag_park": 895, "kaldirim_sag": 1025}

def scene_base(sc, t=0.0):
    img = Image.new("RGBA", (W, H), WALK + (255,)); d = ImageDraw.Draw(img)
    d.rectangle([110, 0, 970, H], fill=ASPH)
    for x in (110, 966): d.rectangle([x, 0, x + 4, H], fill=(200, 200, 200))
    d.rectangle([258, 0, 264, H], fill=(210, 210, 205)); d.rectangle([816, 0, 822, H], fill=(210, 210, 205))
    off = (t * 120) % 200
    for y0 in range(-200, H, 200): d.rectangle([536, y0 + off, 544, y0 + off + 100], fill=LINE)
    yz = sc.get("yaya_gecidi")
    kv = sc.get("kavsak")
    if kv:
        ky = int(H * float(kv if isinstance(kv, (int, float)) and not isinstance(kv, bool) else 0.42))
        d.rectangle([0, ky - 150, W, ky + 150], fill=ASPH)
        for x0 in range(0, 110, 60): pass
        d.rectangle([0, ky - 4, 110, ky + 4], fill=LINE); d.rectangle([970, ky - 4, W, ky + 4], fill=LINE)
    if yz:
        yy = int(H * float(yz if isinstance(yz, (int, float)) and not isinstance(yz, bool) else 0.3))
        for x0 in range(270, 815, 70): d.rectangle([x0, yy - 60, x0 + 40, yy + 60], fill=(235, 235, 230))
    yz_ = sc.get("yuzey")
    if yz_ in ("islak", "yaprak", "cakil", "mazot"):
        rnd = random.Random(7); ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
        if yz_ == "islak": od.rectangle([262, 0, 818, H], fill=(120, 160, 220, 40))
        for _ in range(260 if yz_ != "islak" else 60):
            x, y = rnd.randint(270, 810), rnd.randint(0, H)
            if yz_ == "yaprak": od.ellipse([x, y, x + 16, y + 10], fill=(200, 120, 40, 200))
            elif yz_ == "cakil": od.ellipse([x, y, x + 6, y + 6], fill=(170, 165, 150, 220))
            elif yz_ == "mazot": od.ellipse([x, y, x + 60, y + 24], fill=(120, 60, 160, 60))
            else: od.line([x, y, x, y + 30], fill=(200, 220, 255, 90), width=2)
        img.alpha_composite(ov)
    return img

def obj_sprite(o, k):
    tip = o.get("tip", "araba")
    if tip in ("araba", "park", "yan_yol_araba"): return car_sprite(CAR_COLORS[k % len(CAR_COLORS)])
    if tip == "kamyon": return truck_sprite()
    if tip == "otobus": return bus_sprite()
    if tip == "motosiklet": return moto_sprite((40, 90, 200))
    if tip == "yaya": return ped_sprite()
    if tip == "cocuk": return ped_sprite((80, 200, 240), 0.75)
    if tip == "bisiklet": return bike_sprite()
    if tip == "top": return ball_sprite()
    return car_sprite(CAR_COLORS[k % len(CAR_COLORS)])

def place(o):
    s = o.get("serit", "sag"); y = 480 + clamp(float(o.get("y", 0.4))) * 760
    rot = 0
    if s.startswith("yan_yol"):
        x = 160 if s == "yan_yol_sol" else 920; rot = -90 if s == "yan_yol_sol" else 90
    else:
        x = X.get(s, X["sag"])
        if s == "sol" and o.get("tip") not in ("yaya", "cocuk", "top"): rot = 180  # karşı yön
    if o.get("tip") in ("yaya", "cocuk") and s in ("sol", "sag"): rot = 0
    return x, y, rot

def draw_scene(img, sc, ego=True, ego_head=0):
    objs = sc.get("ogeler", [])[:8]
    pos = []
    for k, o in enumerate(objs):
        x, y, rot = place(o); paste_c(img, obj_sprite(o, k), x, y, rot); pos.append((x, y))
    if ego: paste_c(img, moto_sprite(head_ang=ego_head), X["sag"], SAFE_BOT - 120)
    return pos

# ---------------- UI öğeleri (önceden render edilip kompozit edilir) ----------------
def card(text, width=900, size=60, fg=WHITE, bg=(22, 26, 32, 235), max_lines=5, pad=34, bold=True, align="center", radius=34, stripe=None):
    f, lines = fit_text(text, width - 2 * pad, max_lines, size, bold=bold)
    lh = int(f.size * 1.22); h = lh * len(lines) + 2 * pad
    im = _sprite(width, h); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, width - 1, h - 1], radius, fill=bg)
    if stripe: d.rounded_rectangle([0, 0, 14, h - 1], 7, fill=stripe)
    for i, ln in enumerate(lines):
        tw = d.textlength(ln, font=f)
        x = (width - tw) / 2 if align == "center" else pad + (14 if stripe else 0)
        d.text((x, pad + i * lh), ln, font=f, fill=fg)
    return im

def pill(text, bg, fg=WHITE, size=56):
    f = F(size); d0 = ImageDraw.Draw(Image.new("RGB", (1, 1))); tw = d0.textlength(text, font=f)
    w, h = int(tw + 70), int(size * 1.7); im = _sprite(w, h); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w - 1, h - 1], h // 2, fill=bg); d.text(((w - tw) / 2, (h - size * 1.15) / 2), text, font=f, fill=fg)
    return im

def big_text(text, size=96, fg=WHITE, width=940, max_lines=4, stroke=7):
    f, lines = fit_text(text, width, max_lines, size)
    lh = int(f.size * 1.18); im = _sprite(W, lh * len(lines) + 30); d = ImageDraw.Draw(im)
    for i, ln in enumerate(lines):
        tw = d.textlength(ln, font=f, )
        d.text(((W - tw) / 2, 10 + i * lh), ln, font=f, fill=fg, stroke_width=stroke, stroke_fill=DARK)
    return im

def steps_card(items, color, width=900, size=50, title=None):
    pad = 32; f = F(size); lh = int(size * 1.25); d0 = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    blocks = []
    for i, it in enumerate(items):
        ff, ls = fit_text(it, width - 2 * pad - 90, 3, size)
        blocks.append((ff, ls))
    th = (int(size * 1.4) + 18) if title else 0
    h = pad * 2 + th + sum(int(b[0].size * 1.25) * len(b[1]) + 22 for b in blocks)
    im = _sprite(width, h); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, width - 1, h - 1], 34, fill=(22, 26, 32, 235))
    y = pad
    if title:
        d.text((pad, y), title, font=F(int(size * 1.05)), fill=color); y += th
    for i, (ff, ls) in enumerate(blocks):
        d.ellipse([pad, y, pad + 64, y + 64], fill=color); n = str(i + 1)
        d.text((pad + 32 - d.textlength(n, font=F(40)) / 2, y + 8), n, font=F(40), fill=DARK)
        for j, ln in enumerate(ls): d.text((pad + 90, y + 4 + j * int(ff.size * 1.25)), ln, font=ff, fill=WHITE)
        y += int(ff.size * 1.25) * len(ls) + 22
    return im

def frame_border(img, color, width=20):
    ImageDraw.Draw(img).rectangle([0, 0, W - 1, H - 1], outline=color, width=width)

class Timeline:
    """Zamanlı öğeler: (görsel, x_merkez, y_üst, t0, t1, giriş)"""
    def __init__(self): self.items = []; self.dur = 0; self.hooks = []; self.sfx = []
    def add(self, im, t0, t1, y, x=W / 2, anim="up", sfx=None):
        self.items.append((im, x, y, t0, t1, anim)); self.dur = max(self.dur, t1)
        if sfx is not False:
            self.sfx.append((t0, sfx or ("impact" if anim == "pop" else "whoosh")))
    def fx(self, t, kind): self.sfx.append((t, kind))
    def at(self, fn): self.hooks.append(fn)
    def compose(self, img, t):
        for im, x, y, t0, t1, anim in self.items:
            if t < t0 or t > t1: continue
            a = min(seg(t, t0, t0 + 0.25), 1 - seg(t, t1 - 0.2, t1))
            if a <= 0: continue
            dy = (1 - seg(t, t0, t0 + 0.3)) * 50 if anim == "up" else 0
            sc = 1 + (1 - seg(t, t0, t0 + 0.18)) * 0.25 if anim == "pop" else 1
            sp = im if sc == 1 else im.resize((int(im.width * sc), int(im.height * sc)))
            paste_c(img, sp, x, y + dy + sp.height / 2, 0, a)

def progress(img, t, dur, color):
    d = ImageDraw.Draw(img); d.rectangle([0, 0, W, 10], fill=(40, 44, 50)); d.rectangle([0, 0, int(W * clamp(t / dur)), 10], fill=color)

def brand(img, sablon):
    d = ImageDraw.Draw(img); h = CFG["hesap"]["handle"]
    f = F(30); tw = d.textlength(h, font=f); d.text(((W - tw) / 2, 196), h, font=f, fill=(255, 255, 255, 210))
    lab = ETIKET.get(sablon, "")
    if lab: paste_c(img, pill(lab, ACCENT.get(sablon, WHITE) + (255,), DARK, 36), W / 2, 150)

# ---------------- şablonlar ----------------
def hook_section(tl, s, t0=0.0, dur=1.8):
    tl.add(big_text(s.get("kanca", ""), 92), t0, t0 + dur, 760, anim="pop")
    tl.fx(t0 + dur - 0.05, "whoosh")
    return t0 + dur

def cta_section(tl, t0, text="Kaydet, sürüşten önce tekrar izle"):
    tl.add(card(text, 860, 50, fg=DARK, bg=YEL + (245,)), t0, t0 + 2.4, 1250)
    return t0 + 2.4

def build_dogru_yanlis(s):
    tl = Timeline(); t = hook_section(tl, s)
    y = s.get("yanlis", {}); dgr = s.get("dogru", {})
    tl.add(pill("✗  YANLIŞ", RED + (255,)), t, t + 4.6, 300, sfx="buzz")
    d1 = read_time(y.get("durum", "")); tl.add(card(y.get("durum", ""), 900, 54, stripe=RED), t + 0.2, t + 4.6, 420)
    tl.add(big_text(y.get("sonuc", "RAMAK KALA!"), 80, RED), t + 0.2 + d1 * 0.6, t + 4.6, 900, anim="pop")
    tl.fx(t + 0.2 + d1 * 0.6 - 0.35, "screech"); tl.fx(t + 0.2 + d1 * 0.6 - 0.9, "riser")
    red_win = (t, t + 4.6); t += 4.6
    adim = dgr.get("adimlar", [])[:4]
    dd = 1.2 + 1.5 * len(adim)
    tl.add(pill("✓  DOĞRU", GREEN + (255,)), t, t + dd, 300, sfx="ding")
    tl.add(steps_card(adim, GREEN, 900, 50), t + 0.2, t + dd, 420)
    green_win = (t, t + dd); t += dd
    tl.add(card(s.get("kural", ""), 900, 62, fg=DARK, bg=WHITE + (245,)), t, t + read_time(s.get("kural", "")) + 0.5, 700, anim="pop")
    t += read_time(s.get("kural", "")) + 0.5
    t = cta_section(tl, t)
    sc = s.get("sahne") or {}
    def bg(img, tt):
        if sc.get("ogeler"):
            base = scene_base(sc, tt); draw_scene(base, sc); img.alpha_composite(base)
            img.alpha_composite(Image.new("RGBA", (W, H), DARK + (110,)))
        else:
            img.alpha_composite(road_simple(tt, 120))
        if red_win[0] <= tt < red_win[1]: frame_border(img, RED)
        if green_win[0] <= tt < green_win[1]: frame_border(img, GREEN)
    return tl, t, bg

def build_teknik(s):
    tl = Timeline(); t = hook_section(tl, s)
    tl.add(card(s.get("baslik", ""), 900, 64, stripe=BLUE), t, t + 99, 300)
    h = s.get("hata", ""); dh = read_time(h) + 0.4
    tl.add(pill("✗  YAYGIN HATA", RED + (255,), size=44), t + 0.2, t + dh, 560, sfx="buzz")
    tl.add(card(h, 900, 50), t + 0.3, t + dh, 680); t += dh
    adim = s.get("adimlar", [])[:4]; dd = 1.0 + 1.6 * len(adim)
    tl.add(steps_card(adim, BLUE, 900, 48, "Doğru teknik"), t, t + dd, 560); t += dd
    ip = s.get("ipucu", ""); di = read_time(ip) + 0.4
    tl.add(card("İpucu: " + ip, 900, 54, fg=DARK, bg=WHITE + (245,)), t, t + di, 700, anim="pop"); t += di
    t = cta_section(tl, t, "Bir sonraki antrenmanda dene")
    end = t; tl.items = [(im, x, y, t0, min(t1, end), a) for im, x, y, t0, t1, a in tl.items]
    def bg(img, tt): img.alpha_composite(road_simple(tt, 150))
    return tl, t, bg

def build_quiz(s, reveal=False):
    tl = Timeline(); t = hook_section(tl, s, dur=1.5)
    q = s.get("soru", ""); dq = read_time(q) + 0.6
    tl.add(card(q, 900, 54), t, t + 99, 300)
    t += 0.4
    ops = s.get("secenekler", {}); keys = [k for k in ("A", "B", "C") if k in ops]
    ys = 300 + 40 + card(q, 900, 54).height + 20
    cards = {}
    for i, k in enumerate(keys):
        cards[k] = card(f"{k})  {ops[k]}", 900, 48, align="left", stripe=YEL)
    yy = ys
    for i, k in enumerate(keys):
        tl.add(cards[k], t + 0.3 * (i + 1), t + 99, yy); yy += cards[k].height + 18
    t += dq + 0.3 * len(keys)
    if not reveal:
        for k_ in range(3): tl.fx(t - 3 + k_, "tick")
        tl.add(big_text("Cevabını yorumla", 70, YEL), t, t + 3.0, yy + 40, anim="pop")
        tl.add(card("Çözüm yarın", 600, 48, fg=DARK, bg=YEL + (245,)), t + 0.4, t + 3.0, yy + 200)
        t += 3.0
    else:
        dk = s.get("dogru", keys[0] if keys else "A")
        yy2 = ys
        for k in keys:
            if k == dk: tl.add(card(f"✓  {k})  {ops[k]}", 900, 48, fg=DARK, bg=GREEN + (250,), align="left"), t, t + 99, yy2, anim="pop", sfx="ding")
            yy2 += cards[k].height + 18
        t += 1.6
        q_end = t
        ac = s.get("aciklama", [])[:3]; da = 1.0 + sum(read_time(a, 1.6, 4.0) for a in ac)
        k_ = s.get("kural", ""); dk_ = read_time(k_) + 0.4
        sc_ = steps_card(ac, GREEN, 900, 46, "Neden?")
        tl.add(sc_, t, t + da + dk_, 300)
        t += da
        tl.add(card(k_, 900, 58, fg=DARK, bg=WHITE + (245,)), t, t + dk_, 300 + sc_.height + 40, anim="pop"); t += dk_
        tl.items = [(im, x, y, t0, (q_end if (t1 > 90 and t0 < q_end) else t1), a) for im, x, y, t0, t1, a in tl.items]
    end = t
    tl.items = [(im, x, y, t0, min(t1, end), a) for im, x, y, t0, t1, a in tl.items]
    sc = s.get("sahne") or {}
    def bg(img, tt):
        if sc.get("ogeler"):
            base = scene_base(sc, 0); draw_scene(base, sc); img.alpha_composite(base)
            img.alpha_composite(Image.new("RGBA", (W, H), DARK + (150,)))
        else: img.alpha_composite(road_simple(0 if reveal else tt, 150))
    return tl, end, bg

def build_cevap(s): return build_quiz(s, reveal=True)

def build_tehlike(s):
    tl = Timeline(); sc = s.get("sahne") or {"ogeler": []}
    objs = sc.get("ogeler", [])[:8]
    hz = [(i, o) for i, o in enumerate(objs) if o.get("tehlike")]
    t = 0.0
    tl.add(big_text(s.get("kanca", "Kaç tehlike var?"), 80), 0, 2.2, 300, anim="pop")
    tl.add(card("3 saniye düşün…", 560, 46, fg=DARK, bg=YEL + (245,)), 2.2, 4.4, 300)
    for k_ in range(3): tl.fx(2.4 + k_ * 0.66, "tick")
    t = 4.4; marks = []
    for n, (i, o) in enumerate(hz[:5]):
        x, y, _ = place(o); tm = t + n * 2.0
        marks.append((tm, x, y, n + 1))
        tl.add(card(f"{n + 1}. {o['tehlike']}", 900, 46, stripe=AMBER, align="left"), tm, tm + 2.0, 260, sfx="impact")
        if o.get("tip") in ("araba", "yan_yol_araba", "kamyon", "otobus"): tl.fx(tm + 0.1, "horn")
    t += 2.0 * len(hz[:5])
    tl.add(card(f"{len(hz[:5])} tehlike. Kaçını buldun? Yorumla", 900, 52, fg=DARK, bg=AMBER + (245,)), t, t + 2.4, 260, anim="pop")
    kap = s.get("kapanis", "")
    if kap: tl.add(card(kap, 900, 50), t + 0.3, t + 2.4, 470)
    t += 2.4
    base0 = scene_base(sc, 0); draw_scene(base0, sc)
    def bg(img, tt):
        img.alpha_composite(base0)
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
        for tm, x, y, n in marks:
            if tt < tm: continue
            k = seg(tt, tm, tm + 0.35); r = 110 + 12 * math.sin(tt * 6)
            od.ellipse([x - r, y - r, x + r, y + r], outline=AMBER + (int(255 * k),), width=10)
            od.ellipse([x + r * 0.55, y - r - 10, x + r * 0.55 + 66, y - r + 56], fill=AMBER + (int(255 * k),))
            od.text((x + r * 0.55 + 33 - ImageDraw.Draw(ov).textlength(str(n), font=F(44)) / 2, y - r - 2), str(n), font=F(44), fill=DARK + (int(255 * k),))
        img.alpha_composite(ov)
    return tl, t, bg

# --- challenge: ölçülü koni düzenleri ---
def layout_points(lay):
    tip = lay.get("tip", "slalom"); g = lambda k, v: float(lay.get(k, v))
    cones, path, dims = [], [], []
    if tip in ("slalom", "ofset"):
        n = int(g("koni", 6)); a = g("aralik_m", 6); o = g("ofset_m", 1.5) if tip == "ofset" else 0
        for i in range(n): cones.append(((o if i % 2 else -o) if o else 0, i * a))
        for k in range(0, 101):
            yy = -a * 0.8 + k / 100 * (a * (n - 1) + a * 1.6); xx = 1.6 * math.sin((yy / a) * math.pi + math.pi / 2) + (0 if not o else 0)
            path.append((xx, yy))
        dims.append(("v", cones[0], cones[1], f"{a:g} m"))
        if o: dims.append(("h", (-o, 0), (o, a), f"{2 * o:g} m"))
    elif tip in ("u_donus", "kutu"):
        w_ = g("genislik_m", 6); l_ = g("uzunluk_m", 12)
        for p in [(-w_ / 2, 0), (w_ / 2, 0), (-w_ / 2, l_), (w_ / 2, l_), (-w_ / 2, l_ / 2), (w_ / 2, l_ / 2)]: cones.append(p)
        for k in range(0, 101):
            u = k / 100
            if u < 0.4: path.append((-w_ / 4, u / 0.4 * l_ * 0.8))
            elif u < 0.6: ang = math.pi * (u - 0.4) / 0.2; path.append((-w_ / 4 * math.cos(ang), l_ * 0.8 + w_ / 4 * math.sin(ang)))
            else: path.append((w_ / 4, l_ * 0.8 - (u - 0.6) / 0.4 * l_ * 0.8))
        dims += [("h", (-w_ / 2, 0), (w_ / 2, 0), f"{w_:g} m"), ("v", (w_ / 2, 0), (w_ / 2, l_), f"{l_:g} m")]
    elif tip == "sekiz":
        dd = g("mesafe_m", 10); cones += [(0, 0), (0, dd)]
        for k in range(0, 201):
            u = 2 * math.pi * k / 200; path.append((dd * 0.45 * math.sin(2 * u) / 1.0, dd / 2 + dd * 0.85 * math.sin(u) / 1.0 * 0.75))
        dims.append(("v", (0, 0), (0, dd), f"{dd:g} m"))
    elif tip == "fren":
        d1 = g("fren_noktasi_m", 20); L = g("durma_kutusu_m", 4); w_ = 3
        cones += [(-w_ / 2, d1), (w_ / 2, d1), (-w_ / 2, d1 + L), (w_ / 2, d1 + L), (-w_ / 2, 0), (w_ / 2, 0)]
        for k in range(101): path.append((0, (d1 + L * 0.6) * k / 100))
        dims += [("v", (w_ / 2, 0), (w_ / 2, d1), f"{d1:g} m"), ("v", (-w_ / 2, d1), (-w_ / 2, d1 + L), f"{L:g} m")]
    elif tip == "koridor":
        w_ = g("genislik_m", 1); L = g("uzunluk_m", 15); n = 6
        for i in range(n): cones += [(-w_ / 2 - 0.3, i * L / (n - 1)), (w_ / 2 + 0.3, i * L / (n - 1))]
        for k in range(101): path.append((0, L * k / 100))
        dims += [("h", (-w_ / 2 - 0.3, 0), (w_ / 2 + 0.3, 0), f"{w_:g} m"), ("v", (w_ / 2 + 0.3, 0), (w_ / 2 + 0.3, L), f"{L:g} m")]
    else:  # spiral / daire
        r = g("yaricap_m", 6); n = int(g("koni", 8))
        for i in range(n): a = 2 * math.pi * i / n; cones.append((r * math.cos(a), r + r * math.sin(a)))
        for k in range(201):
            a = 2 * math.pi * k / 200 * 2; rr = r * 0.8 * (1 - 0.35 * k / 200); path.append((rr * math.cos(a), r + rr * math.sin(a)))
        dims.append(("h", (-r, r), (r, r), f"Ø {2 * r:g} m"))
    return cones, path, dims

def build_challenge(s):
    tl = Timeline(); t = hook_section(tl, s, dur=1.8)
    lay = s.get("duzen", {"tip": "slalom"})
    cones, path, dims = layout_points(lay)
    xs = [p[0] for p in cones + path]; ys = [p[1] for p in cones + path]
    bw, bh = 760, 520; spanx = max(max(xs) - min(xs), 1); spany = max(max(ys) - min(ys), 1)
    sc_ = min(bw / spanx, bh / spany) * 0.85; cx0 = (max(xs) + min(xs)) / 2; cy0 = (max(ys) + min(ys)) / 2
    oy = 480 + bh / 2 + 20
    def P(p): return (W / 2 + (p[0] - cx0) * sc_, oy - (p[1] - cy0) * sc_)
    tl.add(card(s.get("baslik", ""), 900, 58, stripe=ACCENT["challenge"]), t, t + 99, 260)
    seviye = s.get("seviye", "")
    if seviye: tl.add(pill(seviye, ACCENT["challenge"] + (255,), DARK, 38), t + 0.2, t + 99, 410, x=W / 2)
    t_d = t; t += 3.5
    kur = s.get("kurallar", [])[:3]; dk = 1.0 + sum(read_time(k, 1.6, 4) for k in kur)
    tl.add(steps_card(kur, ACCENT["challenge"], 900, 44, "Kurallar"), t, t + dk, 1080); t += dk
    t = cta_section(tl, t, "Denediğinde yorumla: kaçıncı denemede yaptın?")
    end = t
    tl.items = [(im, x, y, t0, min(t1, end), a) for im, x, y, t0, t1, a in tl.items]
    cone = cone_sprite(0.7)
    def bg(img, tt):
        img.alpha_composite(Image.new("RGBA", (W, H), (44, 47, 52, 255)))
        d = ImageDraw.Draw(img)
        for gx in range(0, W, 90): d.line([gx, 0, gx, H], fill=(52, 55, 60), width=2)
        for gy in range(0, H, 90): d.line([0, gy, W, gy], fill=(52, 55, 60), width=2)
        if tt < t_d: return
        k = seg(tt, t_d, t_d + 2.4)
        pts = [P(p) for p in path]; m = int(len(pts) * k)
        for i in range(0, max(m - 1, 0), 2): d.line([pts[i], pts[i + 1]], fill=(255, 255, 255), width=5)
        for p in cones: paste_c(img, cone, *P(p))
        if 0 < m < len(pts): paste_c(img, moto_sprite().resize((75, 120)), pts[m - 1][0], pts[m - 1][1])
        for kind, a, b, lab in dims:
            A, B = P(a), P(b)
            if kind == "v": A = (A[0] + 70, A[1]); B = (B[0] + 70, B[1])
            else: A = (A[0], A[1] + 60); B = (B[0], B[1] + 60)
            d.line([A, B], fill=YEL, width=5)
            for q in (A, B): d.ellipse([q[0] - 8, q[1] - 8, q[0] + 8, q[1] + 8], fill=YEL)
            mx, my = (A[0] + B[0]) / 2, (A[1] + B[1]) / 2
            paste_c(img, pill(lab, DARK + (230,), YEL, 34), mx + (60 if kind == "v" else 0), my)
    return tl, end, bg

def build_efsane(s):
    tl = Timeline(); t = 0
    tl.add(pill("EFSANE Mİ, GERÇEK Mİ?", ACCENT["efsane"] + (255,), DARK, 46), 0, 99, 330)
    iddia = s.get("iddia", ""); tl.add(big_text(f"“{iddia}”", 84), 0.3, 99, 520, anim="pop")
    t = 0.3 + read_time(iddia) + 0.3
    tl.add(card("Sence? 3… 2… 1…", 620, 50, fg=DARK, bg=YEL + (245,)), t, t + 2.4, 1000)
    for k_ in range(3): tl.fx(t + 0.2 + k_ * 0.75, "tick")
    t += 2.4
    hk = str(s.get("hukum", "EFSANE")).upper(); col = {"EFSANE": RED, "GERÇEK": GREEN}.get(hk, AMBER)
    tl.add(pill(hk, col + (255,), WHITE, 110), t, 99, 900, anim="pop"); tl.fx(t, "buzz" if hk == "EFSANE" else "ding"); t += 1.0
    ac = s.get("aciklama", [])[:3]; da = 1.0 + sum(read_time(a, 1.8, 4.5) for a in ac)
    tl.add(steps_card(ac, col, 900, 44), t, t + da, 1090); t += da
    t = cta_section(tl, t, "Bunu bilmeyen bir arkadaşına gönder")
    end = t; tl.items = [(im, x, y, t0, min(t1, end), a) for im, x, y, t0, t1, a in tl.items]
    def bg(img, tt): img.alpha_composite(road_simple(tt, 170))
    return tl, end, bg

def build_ekipman(s):
    tl = Timeline(); t = hook_section(tl, s, dur=1.6)
    tl.add(card(s.get("baslik", ""), 900, 62, stripe=ACCENT["ekipman"]), t, 99, 300)
    m = s.get("maddeler", [])[:4]; dm = 1.0 + sum(read_time(x, 1.8, 4.5) for x in m)
    tl.add(steps_card(m, ACCENT["ekipman"], 900, 46, "Kontrol listesi"), t + 0.4, 99, 500); t += 0.4 + dm
    ip = s.get("ipucu", "")
    if ip:
        di = read_time(ip) + 0.4; tl.add(card("İpucu: " + ip, 900, 50, fg=DARK, bg=WHITE + (245,)), t, t + di, 1200, anim="pop"); t += di
    t = cta_section(tl, t)
    end = t; tl.items = [(im, x, y, t0, min(t1, end), a) for im, x, y, t0, t1, a in tl.items]
    def bg(img, tt): img.alpha_composite(road_simple(tt, 175))
    return tl, end, bg

def build_yorum_soru(s):
    tl = Timeline(); t = hook_section(tl, s, dur=1.6)
    q = s.get("soru", "")
    im = card(q, 900, 50, align="left", bg=(245, 245, 245, 250), fg=(20, 20, 20))
    hd = card("Bir takipçimiz sordu:", 900, 36, align="left", bg=(0, 0, 0, 0), fg=(200, 200, 200), pad=10)
    tl.add(hd, t, 99, 300); tl.add(im, t + 0.1, 99, 360); t += read_time(q) + 0.6
    cv = s.get("cevap", [])[:3]; dc = 1.0 + sum(read_time(x, 1.8, 4.5) for x in cv)
    tl.add(steps_card(cv, ACCENT["yorum_soru"], 900, 46, "Cevap"), t, 99, 380 + im.height + 30); t += dc
    t = cta_section(tl, t, "Sorunu yorumlara yaz, Pazar videosu olabilir")
    end = t; tl.items = [(im_, x, y, t0, min(t1, end), a) for im_, x, y, t0, t1, a in tl.items]
    def bg(img, tt): img.alpha_composite(road_simple(tt, 175))
    return tl, end, bg

def build_mini_sinav(s):
    tl = Timeline(); t = hook_section(tl, s, dur=1.8)
    for i, q in enumerate(s.get("sorular", [])[:3]):
        dq = read_time(q.get("s", "")) + 1.2; dc = read_time(q.get("c", ""), 1.6, 4)
        tl.add(pill(f"SORU {i + 1}/3", YEL + (255,), DARK, 40), t, t + dq + dc, 300)
        tl.add(card(q.get("s", ""), 900, 54), t, t + dq + dc, 420)
        tl.add(card("✓ " + q.get("c", ""), 900, 50, fg=DARK, bg=GREEN + (245,)), t + dq, t + dq + dc, 820, anim="pop", sfx="ding")
        t += dq + dc
    t = cta_section(tl, t, "Kaç doğru yaptın? Yorumla")
    def bg(img, tt): img.alpha_composite(road_simple(tt, 170))
    return tl, t, bg

BUILDERS = {"dogru_yanlis": build_dogru_yanlis, "teknik": build_teknik, "quiz": build_quiz, "cevap": build_cevap,
            "tehlike": build_tehlike, "challenge": build_challenge, "efsane": build_efsane, "ekipman": build_ekipman,
            "yorum_soru": build_yorum_soru, "mini_sinav": build_mini_sinav}

def render(script, out_path, seed=0):
    sablon = script["sablon"]
    tl, dur, bg = BUILDERS[sablon](script)
    dur = clamp(dur + 0.4, 6.0, 60.0); n = int(dur * FPS)
    out_path = Path(out_path); out_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        wav = Path(td) / "m.wav"; music.make(wav, dur, seed=seed, events=tl.sfx)
        p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                              "-r", str(FPS), "-i", "-", "-i", str(wav), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-profile:v", "high",
                              "-crf", "20", "-preset", "medium", "-af", "loudnorm=I=-12:TP=-1.5:LRA=9", "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-shortest",
                              "-movflags", "+faststart", str(out_path)], stdin=subprocess.PIPE)
        for i in range(n):
            t = i / FPS
            img = Image.new("RGBA", (W, H), DARK + (255,))
            bg(img, t); tl.compose(img, t); progress(img, t, dur, ACCENT.get(sablon, WHITE)); brand(img, sablon)
            p.stdin.write(img.convert("RGB").tobytes())
        p.stdin.close()
        if p.wait() != 0: raise RuntimeError("ffmpeg başarısız")
    return out_path, dur

def add_music(video_in, out_path, seed=0):
    """Hazır (premade) videoya müzik ekler."""
    dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(video_in)]).decode().strip())
    with tempfile.TemporaryDirectory() as td:
        wav = Path(td) / "m.wav"; music.make(wav, dur, seed=seed)
        subprocess.check_call(["ffmpeg", "-y", "-loglevel", "error", "-i", str(video_in), "-i", str(wav), "-map", "0:v:0", "-map", "1:a:0",
                               "-c:v", "copy", "-af", "loudnorm=I=-12:TP=-1.5:LRA=9", "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-shortest", "-movflags", "+faststart", str(out_path)])
    return out_path, dur

def still(script, t, path):
    tl, dur, bg = BUILDERS[script["sablon"]](script)
    img = Image.new("RGBA", (W, H), DARK + (255,)); bg(img, t); tl.compose(img, t); progress(img, t, dur, ACCENT.get(script["sablon"], WHITE)); brand(img, script["sablon"])
    img.convert("RGB").save(path); return dur


# ---------------- kapak görseli ----------------
KAPAK_ROZET = {"dogru_yanlis": "ÇOĞU SÜRÜCÜ BUNU YANLIŞ YAPIYOR", "teknik": "ÇOĞU SÜRÜCÜ BUNU BİLMİYOR",
               "quiz": "SEN OLSAN NE YAPARDIN?", "cevap": "DOĞRU CEVAP ŞAŞIRTABİLİR", "tehlike": "KAÇ TEHLİKE GÖRÜYORSUN?",
               "challenge": "YAPABİLİR MİSİN?", "efsane": "EFSANE Mİ, GERÇEK Mİ?", "ekipman": "BUNU KONTROL ETMEDEN BİNME",
               "yorum_soru": "EN ÇOK SORULAN SORU", "mini_sinav": "3 SORU: KAÇINI BİLİRSİN?"}
KAPAK_AN = {"dogru_yanlis": 0.32, "quiz": 0.62, "cevap": 0.55, "tehlike": 0.78, "challenge": 0.45, "efsane": 0.55}
KAPAK_SIMGE = {"quiz": "?", "tehlike": "!", "dogru_yanlis": "!", "efsane": "?", "mini_sinav": "?", "challenge": "!"}


def tr_upper(t):
    return str(t).replace("i", "İ").replace("ı", "I").upper()


def cover(script, path):
    """Merak uyandıran kapak: videonun en çarpıcı anından bulanık arka plan + dev başlık. Metin, profil ızgarasındaki
    3:4 ve akıştaki 1:1 kırpma içinde kalır."""
    from PIL import ImageFilter
    sb = script["sablon"]
    tl, dur, bg = BUILDERS[sb](script)
    t = dur * KAPAK_AN.get(sb, 0.5)
    img = Image.new("RGBA", (W, H), DARK + (255,)); bg(img, t); tl.compose(img, t)
    img = img.filter(ImageFilter.GaussianBlur(7))
    img.alpha_composite(Image.new("RGBA", (W, H), DARK + (150,)))
    acc = ACCENT.get(sb, RED)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W - 1, H - 1], outline=acc, width=26)
    # rozet
    rz = KAPAK_ROZET.get(sb, "")
    if rz:
        p = pill(rz, YEL + (255,), DARK, 46); paste_c(img, p, W / 2, 500)
    # başlık
    head = tr_upper(script.get("kapak") or script.get("kanca") or script.get("baslik") or "")
    words = head.split()
    if len(words) > 7: head = " ".join(words[:7]) + "…"
    f, lines = fit_text(head, 940, 4, 132, minimum=72)
    lh = int(f.size * 1.12); y0 = 880 - lh * len(lines) / 2
    for i, ln in enumerate(lines):
        tw = d.textlength(ln, font=f)
        col = YEL if i == len(lines) - 1 else WHITE
        d.text(((W - tw) / 2, y0 + i * lh), ln, font=f, fill=col, stroke_width=10, stroke_fill=DARK)
    # simge
    sm = KAPAK_SIMGE.get(sb)
    if sm:
        cx, cy, r = W - 190, 330, 95
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=RED, outline=WHITE, width=10)
        fs = F(150); tw = d.textlength(sm, font=fs); d.text((cx - tw / 2, cy - 95), sm, font=fs, fill=WHITE)
    # alt çağrı
    cta = card("SONUNA KADAR İZLE ▶", 900, 54, fg=WHITE, bg=RED + (255,), pad=26, max_lines=1)
    paste_c(img, cta, W / 2, 1300)
    hd = CFG["hesap"]["handle"]; fh = F(40); tw = d.textlength(hd, font=fh)
    d.text(((W - tw) / 2, 1420), hd, font=fh, fill=(255, 255, 255), stroke_width=4, stroke_fill=DARK)
    img.convert("RGB").save(path, "JPEG", quality=90)
    return path
