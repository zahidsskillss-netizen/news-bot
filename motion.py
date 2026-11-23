"""
Bisram TV — موشن ګرافیک: Intro، Outro او Lower third
ټول انیمیشنونه په کوډ جوړېږي (Pillow + NumPy + OpenCV) او په FFmpeg ویډیو کېږي.
"""
import math
import os
import random
import subprocess
import wave

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")
W, H, FPS = 1920, 1080, 30

BLUE = (33, 150, 243)
BLUE_L = (100, 190, 255)
BLUE_D = (13, 71, 161)
NAVY = (6, 14, 38)
RED = (229, 57, 53)
WHITE = (255, 255, 255)
YELLOW = (255, 202, 40)

HEAD = os.path.join(ASSETS, "GhoraLalezar.ttf")
BODY = os.path.join(ASSETS, "GhoraMarhey.ttf")
LATIN = os.path.join(ASSETS, "Vazirmatn-Bold.ttf")
PS_MONTHS = ["جنوري", "فبروري", "مارچ", "اپرېل", "مې", "جون", "جولای",
             "اګست", "سپتمبر", "اکتوبر", "نومبر", "دسمبر"]


# ================= اسانتیاوې =================
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def prog(t, start, dur):
    return clamp((t - start) / dur)


def ease_out_cubic(x):
    return 1 - (1 - x) ** 3


def ease_in_out(x):
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def ease_out_back(x, s=1.70158):
    x -= 1
    return 1 + (s + 1) * x ** 3 + s * x ** 2


def ease_out_expo(x):
    return 1 if x >= 1 else 1 - 2 ** (-10 * x)


def font(path, size):
    return ImageFont.truetype(path, size)


def text_layer(text, path, size, color=WHITE, rtl=True, pad=20, shadow=False):
    """متن په یوه شفافه RGBA انځور کې."""
    f = font(path, size)
    kw = {"direction": "rtl", "language": "ps"} if rtl else {}
    tmp = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    b = tmp.textbbox((0, 0), text, font=f, **kw)
    w, h = b[2] - b[0] + pad * 2, b[3] - b[1] + pad * 2
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if shadow:
        d.text((pad - b[0] + 3, pad - b[1] + 4), text, font=f, fill=(0, 0, 0, 140), **kw)
        im = im.filter(ImageFilter.GaussianBlur(4))
        d = ImageDraw.Draw(im)
    d.text((pad - b[0], pad - b[1]), text, font=f, fill=color, **kw)
    return im


def kabul_date():
    from datetime import datetime, timedelta, timezone
    n = datetime.now(timezone.utc) + timedelta(hours=4, minutes=30)
    return f"{n.day} {PS_MONTHS[n.month - 1]} {n.year}"


def to_np(im):
    return np.asarray(im.convert("RGBA")).astype(np.float32) / 255.0


def over(dst, src):
    """src (RGBA float) د dst (RGB float) پر سر."""
    a = src[..., 3:4]
    dst[..., :3] = src[..., :3] * a + dst[..., :3] * (1 - a)
    return dst


def add_glow(frame, layer, strength=0.9, radius=31):
    """د رڼا ځلا (bloom)."""
    rgb = layer[..., :3] * layer[..., 3:4]
    g = cv2.GaussianBlur(rgb, (0, 0), radius)
    frame[..., :3] = np.clip(frame[..., :3] + g * strength, 0, 1)
    return frame


# ================= 3D =================
def project(points, cx, cy, focal=1400):
    out = []
    for x, y, z in points:
        s = focal / (focal + z)
        out.append((cx + x * s, cy + y * s))
    return np.float32(out)


def rot(p, ay, ax=0.0, az=0.0):
    x, y, z = p
    # Y محور
    c, s = math.cos(ay), math.sin(ay)
    x, z = x * c + z * s, -x * s + z * c
    # X محور
    c, s = math.cos(ax), math.sin(ax)
    y, z = y * c - z * s, y * s + z * c
    # Z محور
    c, s = math.cos(az), math.sin(az)
    x, y = x * c - y * s, x * s + y * c
    return x, y, z


def plane(img_np, cx, cy, scale=1.0, ay=0.0, ax=0.0, az=0.0, z=0.0, zoff=0.0):
    """یو انځور په 3D فضا کې څرخوي او پر کینوس یې پروجکټ کوي → RGBA float (W×H)."""
    h, w = img_np.shape[:2]
    hw, hh = w * scale / 2, h * scale / 2
    corners = [(-hw, -hh, zoff), (hw, -hh, zoff), (hw, hh, zoff), (-hw, hh, zoff)]
    pts = []
    for p in corners:
        x, y, zz = rot(p, ay, ax, az)
        pts.append((x, y, zz + z))
    dst = project(pts, cx, cy)
    src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    M = cv2.getPerspectiveTransform(src, dst)
    return cv2.warpPerspective(img_np, M, (W, H), flags=cv2.INTER_LINEAR,
                               borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))


def extruded(frame, img_np, cx, cy, scale, ay, ax=0.0, z=0.0, depth=60, layers=14,
             side=(10, 40, 110)):
    """3D ایستل شوی (extruded) شی: شاته تیاره پاڼې، مخې ته اصلي مخ."""
    sil = img_np.copy()
    sil[..., 0], sil[..., 1], sil[..., 2] = side[0] / 255, side[1] / 255, side[2] / 255
    for i in range(layers, 0, -1):
        k = i / layers
        lay = sil.copy()
        lay[..., :3] *= (0.55 + 0.45 * (1 - k))
        frame = over(frame, plane(lay, cx, cy, scale, ay, ax, 0, z, zoff=depth * k))
    front = plane(img_np, cx, cy, scale, ay, ax, 0, z)
    return over(frame, front), front


def light_sweep(layer, pos, width=0.12, angle=0.35, intensity=0.85):
    """د رڼا یوه کږه پټۍ چې د شي پر مخ تېرېږي (pos: 0→1)."""
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    u = (xx / W + yy / H * angle) / (1 + angle)
    band = np.exp(-((u - pos) ** 2) / (2 * width ** 2)) * intensity
    out = layer.copy()
    out[..., :3] = np.clip(out[..., :3] + band[..., None], 0, 1)
    return out


_YY, _XX = None, None


def sweep_fast(frame, mask, pos, width=0.08, angle=0.35, intensity=0.8):
    global _YY, _XX
    if _YY is None:
        _YY, _XX = np.mgrid[0:H, 0:W].astype(np.float32)
    u = (_XX / W + _YY / H * angle) / (1 + angle)
    band = np.exp(-((u - pos) ** 2) / (2 * width ** 2)) * intensity
    frame[..., :3] = np.clip(frame[..., :3] + (band * mask)[..., None], 0, 1)
    return frame


# ================= شالید (د سټوډیو فضا) =================
class Studio:
    def __init__(self, seed=7):
        rnd = random.Random(seed)
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        r = np.sqrt(((xx - W / 2) / W) ** 2 + ((yy - H * 0.42) / H) ** 2)
        base = np.zeros((H, W, 3), np.float32)
        c1, c2 = np.array(BLUE_D) / 255 * 0.55, np.array(NAVY) / 255
        k = np.clip(r * 1.6, 0, 1)[..., None]
        self.base = c1 * (1 - k) + c2 * k
        self.parts = [(rnd.random() * W, rnd.random() * H, rnd.uniform(0.3, 1.0),
                       rnd.uniform(1, 3.2), rnd.random() * 6.28) for _ in range(90)]
        self.vignette = np.clip(1.15 - r * 0.9, 0.35, 1)[..., None]

    def frame(self, t, cam=0.0):
        f = self.base.copy()
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        # 3D شبکه (د سټوډیو فرش)
        horizon, cx = H * 0.60, W / 2
        speed = (t * 0.55) % 1
        for i in range(14):
            zf = ((i + speed) / 14)
            y = horizon + (H - horizon) * zf ** 2.2
            a = int(90 * zf)
            d.line((0, y, W, y), fill=(60, 150, 255, a), width=2)
        for i in range(-14, 15):
            x2 = cx + i * 260 + cam * 120
            d.line((cx + i * 18, horizon, x2, H), fill=(60, 150, 255, 55), width=2)
        # د رڼا ستنې
        for i, xb in enumerate((0.18, 0.5, 0.82)):
            x = W * xb + math.sin(t * 0.7 + i * 2) * 120
            d.polygon([(x - 30, 0), (x + 30, 0), (x + 260, horizon), (x - 260, horizon)],
                      fill=(80, 170, 255, 16))
        ov = ov.filter(ImageFilter.GaussianBlur(1.2))
        f = over(f, to_np(ov))
        # ذرات (د ژوري سره)
        pl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        pd = ImageDraw.Draw(pl)
        for (x, y, dep, sz, ph) in self.parts:
            xx = (x + t * 40 * dep + cam * 60 * dep) % W
            yy = (y - t * 25 * dep) % H
            a = int(120 * dep * (0.6 + 0.4 * math.sin(t * 2 + ph)))
            r = sz * dep
            pd.ellipse((xx - r, yy - r, xx + r, yy + r), fill=(150, 210, 255, a))
        pl_np = to_np(pl)
        f = over(f, pl_np)
        f = add_glow(f, pl_np, 0.8, 6)
        f[..., :3] *= self.vignette
        return f


# ================= لوګو =================
_LOGO = None


def logo_np(width):
    global _LOGO
    if _LOGO is None:
        _LOGO = Image.open(os.path.join(ASSETS, "logo.png")).convert("RGBA")
    lg = _LOGO.resize((width, int(_LOGO.height * width / _LOGO.width)), Image.LANCZOS)
    return to_np(lg)


def logo3d_tile_np(width=330, radius=22):
    """د زاهد 3D لوګو (د دېوال موک‌اپ) — ګرد کونجونه او شنه څنډه."""
    src = Image.open(os.path.join(ASSETS, "logo3d.jpg")).convert("RGB")
    crop = src.crop((95, 215, 865, 640))
    hgt = int(width * crop.height / crop.width)
    crop = crop.resize((width, hgt), Image.LANCZOS)
    tile = Image.new("RGBA", (width, hgt), (0, 0, 0, 0))
    mask = Image.new("L", (width, hgt), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, width - 1, hgt - 1), radius, fill=255)
    tile.paste(crop, (0, 0), mask)
    ImageDraw.Draw(tile).rounded_rectangle((1, 1, width - 2, hgt - 2), radius,
                                           outline=BLUE + (255,), width=5)
    return to_np(tile)


def logo_card_np(width, pad_ratio=0.16, radius=48):
    """لوګو په شین کارت کې — لکه اصلي لوګو (تور برخه هم ښکاري)."""
    lg = Image.open(os.path.join(ASSETS, "logo.png")).convert("RGBA")
    inner = int(width * (1 - 2 * pad_ratio))
    lg = lg.resize((inner, int(lg.height * inner / lg.width)), Image.LANCZOS)
    h = lg.height + int(width * pad_ratio * 1.3)
    card = Image.new("RGBA", (width, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(card)
    d.rounded_rectangle((0, 0, width - 1, h - 1), radius, fill=BLUE + (255,))
    # نرۍ ځلنده څنډه
    d.rounded_rectangle((3, 3, width - 4, h - 4), radius - 3, outline=(140, 205, 255, 255), width=3)
    card.alpha_composite(lg, ((width - lg.width) // 2, (h - lg.height) // 2))
    return to_np(card)


def panel_np(w, h, color, slant=0.0, radius=0, alpha=255):
    """کږ (parallelogram) پانل — د لوګو د کږې کرښې په څېر."""
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    s = int(h * slant)
    d.polygon([(s, 0), (w, 0), (w - s, h), (0, h)], fill=color + (alpha,))
    return to_np(im)


# ================= INTRO =================
def intro_frame(t, studio, title="د بسرام ټي وي خبري خپرونه", dur=6.0):
    cam = ease_in_out(prog(t, 0, dur))
    f = studio.frame(t, cam)

    # ۱) کږې شنې پاڼې په 3D کې راننوځي (0 → 1.6)
    slabs = [(-1, 0.00, BLUE, -170), (1, 0.12, BLUE_D, 0), (-1, 0.24, RED, 170)]
    for i, (side, st, col, yo) in enumerate(slabs):
        p = ease_out_expo(prog(t, st, 1.0))
        out_p = ease_in_out(prog(t, 2.2 + i * 0.08, 0.7))
        if p <= 0 or out_p >= 1:
            continue
        slab = panel_np(1500, 120, col, slant=1.2, alpha=235)
        x = W / 2 + side * (1 - p) * 2400 - side * out_p * 2600
        f = over(f, plane(slab, x, H / 2 + yo, 1.0, ay=side * (1 - p) * 0.9, ax=0.15,
                          z=300 * (1 - p)))

    # ۲) 3D لوګو چې څرخي او راښکاري (1.0 → 3.2)
    lp = prog(t, 1.0, 1.6)
    if lp > 0:
        e = ease_out_back(lp, 1.2)
        lg = logo_card_np(760)
        ay = (1 - e) * 1.25 + math.sin(t * 0.9) * 0.06 * prog(t, 2.6, 1)
        ax = -0.12 * (1 - e)
        z = 900 * (1 - ease_out_cubic(lp))
        lg_a = lg.copy()
        lg_a[..., 3] *= clamp(lp * 2.5)
        f, front = extruded(f, lg_a, W / 2, H * 0.40, 1.0, ay, ax, z, depth=60, layers=16,
                            side=(10, 60, 150))
        f = add_glow(f, front, 0.12 * clamp(lp * 2), 30)
        # د رڼا پټۍ په لوګو
        sp = prog(t, 2.5, 0.9)
        if 0 < sp < 1:
            f = sweep_fast(f, front[..., 3], -0.1 + sp * 1.3, 0.05, 0.4, 0.9)

    # ۳) سره پټۍ او سرلیک (3.0 → 4.2)
    bp = ease_out_expo(prog(t, 3.0, 0.9))
    if bp > 0:
        bw = int(980 * bp) + 2
        bar = panel_np(bw, 92, RED, slant=0.6)
        f = over(f, plane(bar, W / 2, H * 0.72, 1.0))
        tp = ease_out_cubic(prog(t, 3.35, 0.7))
        if tp > 0:
            tl = to_np(text_layer(title, HEAD, 58, WHITE))
            tl[..., 3] *= tp
            f = over(f, plane(tl, W / 2, H * 0.72 + 40 * (1 - tp), 1.0))
    dp = ease_out_cubic(prog(t, 3.7, 0.7))
    if dp > 0:
        dl = to_np(text_layer(kabul_date(), BODY, 40, (200, 225, 255)))
        dl[..., 3] *= dp
        f = over(f, plane(dl, W / 2, H * 0.81 + 30 * (1 - dp), 1.0))

    # ۴) سپینه رڼا او وتل (5.4 → 6)
    fl = prog(t, dur - 0.55, 0.55)
    if fl > 0:
        f[..., :3] = f[..., :3] * (1 - fl) + fl * np.array([1, 1, 1]) * (1 - fl * 0.0)
    fi = 1 - prog(t, 0, 0.35)
    if fi > 0:
        f[..., :3] *= (1 - fi)
    return f


# ================= OUTRO =================
def outro_frame(t, studio, dur=7.0):
    f = studio.frame(t + 10, 0.3 * math.sin(t * 0.4))
    fi = clamp(1 - t / 0.5)
    lp = ease_out_back(prog(t, 0.2, 1.2), 1.1)
    if lp > 0:
        lg = logo_card_np(560)
        ay = (1 - lp) * -1.1 + math.sin(t * 0.8) * 0.1
        f, front = extruded(f, lg, W / 2, H * 0.30, 1.0, ay, -0.05, 500 * (1 - lp),
                            depth=50, layers=14, side=(10, 60, 150))
        f = add_glow(f, front, 0.1, 26)
        sp = (t * 0.35) % 1.6
        f = sweep_fast(f, front[..., 3], -0.1 + sp, 0.05, 0.4, 0.7)

    tp = ease_out_cubic(prog(t, 1.2, 0.8))
    if tp > 0:
        tl = to_np(text_layer("د کتلو مننه", HEAD, 76, WHITE, shadow=True))
        tl[..., 3] *= tp
        f = over(f, plane(tl, W / 2, H * 0.53 + 50 * (1 - tp), 1.0))

    # سبسکرایب تڼۍ + زنګ
    bp = prog(t, 2.0, 0.9)
    if bp > 0:
        e = ease_out_back(bp, 2.0)
        click = prog(t, 3.4, 0.25)
        pressed = click > 0
        btn = Image.new("RGBA", (560, 120), (0, 0, 0, 0))
        d = ImageDraw.Draw(btn)
        col = (90, 90, 100) if pressed else RED
        d.rounded_rectangle((0, 0, 559, 119), 60, fill=col + (255,))
        txt = "سبسکرایب شو ✓" if pressed else "سبسکرایب کړئ"
        fnt = font(HEAD, 54)
        d.text((280, 58), txt.replace(" ✓", ""), font=fnt, fill=WHITE, anchor="mm",
               direction="rtl", language="ps")
        b_np = to_np(btn)
        sc = e * (1 - 0.08 * math.sin(clamp(click) * math.pi))
        f = over(f, plane(b_np, W / 2 - 60, H * 0.68, sc, ay=(1 - e) * 0.8))
        # زنګ
        gp = ease_out_back(prog(t, 3.8, 0.6), 2.2)
        if gp > 0:
            bell = Image.new("RGBA", (120, 120), (0, 0, 0, 0))
            bd = ImageDraw.Draw(bell)
            bd.ellipse((0, 0, 119, 119), fill=WHITE + (255,))
            bd.pieslice((30, 22, 90, 92), 180, 360, fill=RED + (255,))
            bd.rectangle((30, 56, 90, 80), fill=RED + (255,))
            bd.polygon([(24, 80), (96, 80), (90, 70), (30, 70)], fill=RED + (255,))
            bd.ellipse((52, 82, 68, 98), fill=RED + (255,))
            wob = math.sin(t * 18) * 0.35 * (1 - prog(t, 4.0, 1.2))
            f = over(f, plane(to_np(bell), W / 2 + 300, H * 0.68, gp, az=wob))

    # ټولنیزې پاڼې
    for i, (lab, val) in enumerate((("ټلګرام", "t.me/bisramtv"), ("فیسبوک", "Bisram TV"))):
        sp = ease_out_expo(prog(t, 4.4 + i * 0.2, 0.8))
        if sp <= 0:
            continue
        x = W / 2 + (-330 if i == 0 else 330)
        card = Image.new("RGBA", (560, 110), (0, 0, 0, 0))
        cd = ImageDraw.Draw(card)
        cd.rounded_rectangle((0, 0, 559, 109), 24, fill=(255, 255, 255, 30),
                             outline=(120, 190, 255, 160), width=2)
        cd.ellipse((452, 20, 522, 90), fill=BLUE + (255,))
        cd.text((487, 56), lab[0], font=font(HEAD, 40), fill=WHITE, anchor="mm",
                direction="rtl", language="ps")
        cd.text((420, 36), lab, font=font(BODY, 28), fill=(170, 210, 255), anchor="ra",
                direction="rtl", language="ps")
        cd.text((36, 58), val, font=font(LATIN, 38), fill=WHITE, anchor="lm")
        c_np = to_np(card)
        c_np[..., 3] *= sp
        f = over(f, plane(c_np, x, H * 0.86 + 60 * (1 - sp), 1.0, ax=(1 - sp) * 0.8))

    if fi > 0:
        f[..., :3] *= (1 - fi)
    fo = prog(t, dur - 0.6, 0.6)
    if fo > 0:
        f[..., :3] *= (1 - fo)
    return f


# ================= LOWER THIRD =================
LW = 330   # د 3D لوګو پلن والی په Lower third کې


class LowerThird:
    """د خبر لپاره 3D Lower third (RGBA). duration کې: ننوتل، درېدل، وتل."""

    def __init__(self, headline, tag="خبر", sub="Bisram TV", max_w=1300):
        self.lines = 1
        for size in (60, 56, 52, 48):
            hl = text_layer(headline, HEAD, size, NAVY)
            if hl.width <= max_w:
                break
        else:   # دوه کرښې
            words = headline.split()
            best = None
            for i in range(1, len(words)):
                a, b = " ".join(words[:i]), " ".join(words[i:])
                la, lb = text_layer(a, HEAD, 50, NAVY, pad=8), text_layer(b, HEAD, 50, NAVY, pad=8)
                wmax = max(la.width, lb.width)
                if best is None or wmax < best[0]:
                    best = (wmax, la, lb)
            _, la, lb = best
            hl = Image.new("RGBA", (max(la.width, lb.width), la.height + lb.height - 6), (0, 0, 0, 0))
            hl.alpha_composite(la, (hl.width - la.width, 0))
            hl.alpha_composite(lb, (hl.width - lb.width, la.height - 6))
            self.lines = 2
        self.head = to_np(hl)
        self.tag = to_np(text_layer(tag, HEAD, 50, WHITE))
        self.sub = to_np(text_layer(f"{sub}  •  {kabul_date()}", BODY, 32, WHITE))
        self.logo = logo3d_tile_np(LW)
        self.bw = max(900, min(1500, self.head.shape[1] + 120))
        self.bh = 120 if self.lines == 1 else 190

    def frame(self, t, dur):
        out_t = prog(t, dur - 0.8, 0.8)
        f = np.zeros((H, W, 4), np.float32)

        def put(layer, x, y, s=1.0, ay=0.0, ax=0.0, alpha=1.0):
            nonlocal f
            lay = layer.copy()
            lay[..., 3] *= alpha
            src = plane(lay, x, y, s, ay, ax)
            a = src[..., 3:4]
            f[..., :3] = src[..., :3] * a + f[..., :3] * (1 - a)
            f[..., 3:4] = a + f[..., 3:4] * (1 - a)

        right = W - 90
        base_y = H - 190
        oe = ease_in_out(out_t)

        # لوګو بکس (3D څرخېدل)
        p = ease_out_back(prog(t, 0.0, 0.7), 1.4)
        if p > 0:
            b = self.logo
            put(b, right - LW / 2, base_y + 40, 1.0, ay=(1 - p) * 1.4 + oe * 1.4, alpha=1 - oe)

        # سره نښه
        p2 = ease_out_expo(prog(t, 0.2, 0.6))
        if p2 > 0:
            tw = self.tag.shape[1] + 50
            tag_bg = panel_np(tw, 84, RED, slant=0.45)
            x = right - LW - 20 - tw / 2 + (1 - p2) * 300 + oe * 300
            ty = base_y - 68 - (self.bh - 120)
            put(tag_bg, x, ty, alpha=(1 - oe) * clamp(p2 * 3))
            put(self.tag, x, ty + 2, alpha=(1 - oe) * clamp(p2 * 3))

        # اصلي سپینه پټۍ (له ښي نه کیڼ ته پرانیستل کېږي)
        p3 = ease_out_expo(prog(t, 0.35, 0.8))
        if p3 > 0:
            w = max(2, int(self.bw * p3 * (1 - oe)))
            bar = panel_np(w, self.bh, WHITE, slant=0.5 * 120 / self.bh)
            put(bar, right - LW - 15 - w / 2, base_y + 25 - (self.bh - 120) / 2, ay=-0.05)
            tp = ease_out_cubic(prog(t, 0.65, 0.6))
            if tp > 0:
                hx = right - LW - 50 - self.head.shape[1] / 2
                fade = 1 - prog(t, dur - 0.95, 0.3)
                put(self.head, hx + 60 * (1 - tp), base_y + 25 - (self.bh - 120) / 2,
                    alpha=tp * fade)
            sw = prog(t, 1.2, 0.8)
            if 0 < sw < 1:
                f = sweep_fast(f, f[..., 3], 1.1 - sw * 1.3, 0.035, 0.6, 0.5)

        # لاندې شنه پټۍ
        p4 = ease_out_expo(prog(t, 0.6, 0.7))
        if p4 > 0:
            sw_ = self.sub.shape[1] + 60
            w = max(2, int(sw_ * p4 * (1 - oe)))
            strip = panel_np(w, 58, BLUE_D, slant=0.5)
            put(strip, right - LW - 15 - w / 2 - 30, base_y + 112)
            put(self.sub, right - LW - 15 - sw_ / 2 - 30, base_y + 112, alpha=clamp(p4 * 2) * (1 - oe))
        return f


# ================= غږ (Sound design) =================
SR = 44100


def _env(n, a, d):
    e = np.ones(n)
    ai = int(a * SR)
    e[:ai] = np.linspace(0, 1, ai) if ai else 1
    e[ai:] = np.exp(-np.linspace(0, d, n - ai))
    return e


def whoosh(dur=0.8, up=True):
    n = int(dur * SR)
    noise = np.random.randn(n)
    sweep = np.linspace(0.02, 0.35, n) if up else np.linspace(0.35, 0.02, n)
    out = np.zeros(n)
    y = 0.0
    for i in range(n):
        y += sweep[i] * (noise[i] - y)
        out[i] = y
    env = np.sin(np.linspace(0, math.pi, n)) ** 2
    return out * env * 0.9


def impact(dur=1.6):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    freq = 55 + 70 * np.exp(-tt * 9)
    boom = np.sin(2 * math.pi * np.cumsum(freq) / SR) * np.exp(-tt * 2.8)
    hit = np.random.randn(n) * np.exp(-tt * 30) * 0.35
    return (boom + hit) * 0.9


def shimmer(dur=1.5):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    s = sum(np.sin(2 * math.pi * f * tt) for f in (880, 1320, 1760, 2640)) / 4
    return s * np.exp(-tt * 2.2) * np.minimum(1, tt * 20) * 0.25


def pad(dur, root=110):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    chord = sum(np.sin(2 * math.pi * root * r * tt + np.sin(tt * 0.7 * k))
                for k, r in enumerate((1, 1.5, 2, 2.52)))
    env = np.minimum(1, tt / 1.0) * np.minimum(1, (dur - tt) / 1.2)
    return chord / 4 * env * 0.22


def mix(dur, events):
    buf = np.zeros(int(dur * SR) + SR)
    for at, snd in events:
        i = int(at * SR)
        buf[i:i + len(snd)] += snd[:len(buf) - i]
    buf = buf[:int(dur * SR)]
    buf /= max(1e-6, np.abs(buf).max()) / 0.85
    return buf


def write_wav(path, sig):
    st = (np.clip(sig, -1, 1) * 32767).astype(np.int16)
    st = np.repeat(st[:, None], 2, axis=1)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(st.tobytes())


# ================= رنډر =================
def render(path, frame_fn, dur, audio=None, alpha=False):
    n = int(dur * FPS)
    if alpha:   # MOV (ProRes 4444) د شفافیت سره
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba",
               "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "prores_ks",
               "-profile:v", "4444", "-pix_fmt", "yuva444p10le", path]
    else:
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
               "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-"]
        if audio:
            cmd += ["-i", audio, "-c:a", "aac", "-b:a", "192k", "-shortest"]
        cmd += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
                "-pix_fmt", "yuv420p", path]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(n):
        fr = frame_fn(i / FPS)
        if alpha:
            data = (np.clip(fr, 0, 1) * 255).astype(np.uint8)
        else:
            data = (np.clip(fr[..., :3], 0, 1) * 255).astype(np.uint8)
        p.stdin.write(data.tobytes())
    p.stdin.close()
    p.wait()


def build_intro(path, title="د بسرام ټي وي خبري خپرونه"):
    dur = 6.0
    st = Studio(3)
    wav = path + ".wav"
    write_wav(wav, mix(dur, [(0, pad(dur)), (0.0, whoosh(0.9)), (0.9, whoosh(0.7)),
                             (1.6, impact()), (2.5, shimmer()), (3.0, whoosh(0.5)),
                             (3.2, impact(1.0) * 0.5), (5.3, whoosh(0.7))]))
    render(path, lambda t: intro_frame(t, st, title, dur), dur, wav)
    os.remove(wav)


def build_outro(path):
    dur = 7.0
    st = Studio(5)
    wav = path + ".wav"
    write_wav(wav, mix(dur, [(0, pad(dur, 98)), (0.2, whoosh(0.9)), (1.2, impact(1.2) * 0.6),
                             (2.0, whoosh(0.5)), (3.4, shimmer(0.8)), (3.8, shimmer(1.2)),
                             (4.4, whoosh(0.6)), (4.6, whoosh(0.6))]))
    render(path, lambda t: outro_frame(t, st, dur), dur, wav)
    os.remove(wav)


# ================= د زاهد Intro (Veo) + د خبر انځور په شین سکرین کې =================
INTRO_STUDIO = os.path.join(ASSETS, "intro_studio.mp4")


def _order_quad(pts):
    pts = np.float32(pts).reshape(-1, 2)
    s, d = pts.sum(1), np.diff(pts, axis=1).ravel()
    return np.float32([pts[np.argmin(s)], pts[np.argmin(d)], pts[np.argmax(s)], pts[np.argmax(d)]])


def _screen_quad(frame_bgr):
    b, g, r = [frame_bgr[..., k].astype(np.int16) for k in range(3)]
    mask = ((g > 140) & (g > r + 55) & (g > b + 55)).astype(np.uint8) * 255
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return None
    c = max(cnts, key=cv2.contourArea)
    area = cv2.contourArea(c)
    x, y, w, h = cv2.boundingRect(c)
    if area < 150000 or area / (w * h) < 0.85:     # یوازې پوره شین سکرین (نه د رڼا ځلا)
        return None
    approx = cv2.approxPolyDP(cv2.convexHull(c), 0.02 * cv2.arcLength(c, True), True)
    if len(approx) == 4:
        return _order_quad(approx)
    return np.float32([[x, y], [x + w, y], [x + w, y + h], [x, y + h]])


def studio_intro(photo, out_path, src=INTRO_STUDIO):
    """د زاهد Intro ویډیو کې شین سکرین د خبر په انځور بدلوي (photo: PIL یا None)."""
    cap = cv2.VideoCapture(src)
    fps = cap.get(cv2.CAP_PROP_FPS) or 24
    w, h = int(cap.get(3)), int(cap.get(4))
    ph = None
    if photo is not None:
        ph = cv2.cvtColor(np.asarray(photo.convert("RGB")), cv2.COLOR_RGB2BGR)
    tmp = out_path + ".v.mp4"
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgr24",
                          "-s", f"{w}x{h}", "-r", str(fps), "-i", "-", "-c:v", "libx264",
                          "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", tmp],
                         stdin=subprocess.PIPE)
    while True:
        ok, f = cap.read()
        if not ok:
            break
        q = _screen_quad(f) if ph is not None else None
        if q is not None:
            # انځور د سکرین اندازې ته (cover) او بیا perspective
            qw = np.linalg.norm(q[1] - q[0]); qh = np.linalg.norm(q[3] - q[0])
            sh, sw = ph.shape[:2]
            r = max(qw / sw, qh / sh)
            cw, ch = qw / r, qh / r
            x0, y0 = (sw - cw) / 2, (sh - ch) / 2
            M = cv2.getPerspectiveTransform(
                np.float32([[x0, y0], [x0 + cw, y0], [x0 + cw, y0 + ch], [x0, y0 + ch]]), q)
            warped = cv2.warpPerspective(ph, M, (w, h))
            ff = f.astype(np.float32)
            b, g, rr = ff[..., 0], ff[..., 1], ff[..., 2]
            a = np.clip((g - np.maximum(rr, b) - 35) / 70, 0, 1)
            inside = np.zeros((h, w), np.uint8)
            cv2.fillConvexPoly(inside, np.int32(cv2.convexHull(q)), 1)
            inside = cv2.dilate(inside, np.ones((15, 15), np.uint8)).astype(np.float32)
            a = cv2.GaussianBlur(a * inside, (0, 0), 1.2)[..., None]
            # د شنې رڼا لرې کول (despill) په څنډو کې
            ff[..., 1] = np.where(inside > 0, np.minimum(g, np.maximum(rr, b) + 10), g)
            out = ff * (1 - a) + warped.astype(np.float32) * a
            # د فرش انعکاس: پاتې شنه برخه د انځور په تیاره، سرچپه انعکاس ډکه شي
            mx = np.maximum(np.maximum(rr, b), 1)
            a2 = np.clip((g / mx - 1.5) / 0.7, 0, 1) * (g > 45) * (1 - inside)
            if a2.sum() > 2000:
                ys, xs = np.where(a2 > 0.5)
                if len(ys):
                    rx0, rx1, ry0, ry1 = xs.min(), xs.max(), ys.min(), ys.max()
                    refl = cv2.flip(cv2.resize(ph, (max(2, rx1 - rx0), max(2, int((rx1 - rx0) * sh / sw)))), 0)
                    refl = cv2.GaussianBlur(refl, (0, 0), 3).astype(np.float32) * 0.45
                    canvas = np.zeros_like(ff)
                    hh = min(refl.shape[0], h - ry0)
                    canvas[ry0:ry0 + hh, rx0:rx0 + refl.shape[1]] = refl[:hh]
                    a2 = cv2.GaussianBlur(a2, (0, 0), 1.5)[..., None]
                    out[..., 1] = np.where(a2[..., 0] > 0, np.minimum(out[..., 1], np.maximum(out[..., 0], out[..., 2]) + 10), out[..., 1])
                    out = out * (1 - a2) + canvas * a2
            f = out.clip(0, 255).astype(np.uint8)
        p.stdin.write(f.tobytes())
    p.stdin.close(); p.wait(); cap.release()
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", tmp, "-i", src, "-map", "0:v",
                    "-map", "1:a?", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest",
                    out_path], check=True)
    os.remove(tmp)
    return out_path
