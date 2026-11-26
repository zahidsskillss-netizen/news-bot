"""د خبر متحرکه صحنه (د تلویزیوني سټوډیو بڼه) — د بصرام ټي وي رنګونه.
render(sg, photo, out, fps=30) → د صحنې اوږدوالی (ثانیې). غږ چوپ دی؛ موزیک وروسته پر ټوله ویډیو اچول کېږي.
"""
import math
import os
import subprocess

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
A = os.path.join(HERE, "assets")
HEAD = os.path.join(A, "GhoraLalezar.ttf")
TEXT = os.path.join(A, "BahijTheSans-Bold.ttf")
SMALL = os.path.join(A, "GhoraMarhey.ttf")
LATIN = os.path.join(A, "Vazirmatn-Bold.ttf") if os.path.exists(os.path.join(A, "Vazirmatn-Bold.ttf")) else HEAD
W, H = 1920, 1080

NAVY = (6, 14, 38)
NAVY2 = (10, 28, 90)
BLUE_D = (13, 71, 161)
BLUE = (33, 150, 243)
SKY = (120, 200, 255)
RED = (220, 24, 36)
YEL = (255, 196, 0)
ORG = (255, 150, 0)
WHITE = (255, 255, 255)

# ځایونه (د سرچینې ویډیو هنداره — ښي ته لوګو، چې پښتو ښي نه پیلېږي)
FR = (252, 106, 1668, 694)          # د انځور چوکاټ
PH = (260, 113, 1660, 687)          # انځور
BAND = (0, 695, W, 778)             # شینه پټۍ (تګونه)
BOX = (36, 778, 1536, 926)          # سپین متن بکس
LOGOBOX = (1566, 695, 1768, 928)
YBLOCK = (1768, 778, W, 928)
BOTTOM = (0, 928, W, H)
TXT_RIGHT, TXT_MAXW = 1500, 1290
TXT_SIZE = 54

_fc = {}


def F(path, size):
    k = (path, size)
    if k not in _fc:
        _fc[k] = ImageFont.truetype(path, size, layout_engine=ImageFont.Layout.RAQM)
    return _fc[k]


def tw(text, font):
    return int(ImageDraw.Draw(Image.new("L", (1, 1))).textlength(text, font=font, direction="rtl", language="ps"))


def vgrad(size, c1, c2):
    g = Image.linear_gradient("L").resize(size)
    return Image.composite(Image.new("RGBA", size, c2 + (255,)), Image.new("RGBA", size, c1 + (255,)), g)


def hgrad(size, c1, c2):
    g = Image.linear_gradient("L").rotate(90, expand=True).resize(size)
    return Image.composite(Image.new("RGBA", size, c2 + (255,)), Image.new("RGBA", size, c1 + (255,)), g)


def ease(x):
    x = min(1.0, max(0.0, x))
    return 1 - (1 - x) ** 3


def ease_back(x):
    x = min(1.0, max(0.0, x))
    c = 1.7
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


# ---------------- ثابتې برخې (یو ځل جوړېږي) ----------------
def side_texture():
    """شین شالید د خواوو لپاره: رڼا کرښې، کږې پټۍ — پلن، چې وخوځېږي."""
    tex = vgrad((W + 600, 600), BLUE, BLUE_D).convert("RGBA")
    d = ImageDraw.Draw(tex)
    rng = np.random.default_rng(3)
    lay = Image.new("RGBA", tex.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(lay)
    for k in range(26):
        x = int(rng.uniform(0, tex.width))
        w = int(rng.uniform(20, 120))
        a = int(rng.uniform(25, 80))
        ld.polygon([(x, 0), (x + w, 0), (x + w - 260, 600), (x - 260, 600)], fill=(255, 255, 255, a))
    tex.alpha_composite(lay.filter(ImageFilter.GaussianBlur(10)))
    for k in range(8):
        x = int(rng.uniform(0, tex.width))
        d.line((x, 0, x - 140, 600), fill=(200, 235, 255, 150), width=2)
    for y in (180, 430):
        for x in range(0, tex.width, 26):
            d.line((x, y + (x % 60) // 10, x + 12, y + (x % 60) // 10), fill=(220, 240, 255, 140), width=2)
    # ژېړ رڼا لاندې
    glow = Image.new("RGBA", tex.size, (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse((-200, 380, tex.width + 200, 900), fill=(255, 200, 60, 70))
    tex.alpha_composite(glow.filter(ImageFilter.GaussianBlur(60)))
    return tex


def logo_tile():
    p = os.path.join(A, "logo3d.jpg")
    if os.path.exists(p):
        im = Image.open(p).convert("RGB")
        bw, bh = LOGOBOX[2] - LOGOBOX[0], 143
        s = max(bw / im.width, bh / im.height)
        im = im.resize((int(im.width * s) + 1, int(im.height * s) + 1))
        x0, y0 = (im.width - bw) // 2, (im.height - bh) // 2
        return im.crop((x0, y0, x0 + bw, y0 + bh)).convert("RGBA")
    from card import logo_clean
    t = vgrad((LOGOBOX[2] - LOGOBOX[0], 143), NAVY2, NAVY)
    lg = logo_clean(180)
    t.alpha_composite(lg, ((t.width - lg.width) // 2, (t.height - lg.height) // 2))
    return t


def tag_img(text, size, bg, fg, w, h, font=HEAD):
    im = Image.new("RGBA", (w, h), bg + (255,))
    im.alpha_composite(vgrad((w, h // 2), tuple(min(255, c + 30) for c in bg), bg), (0, 0))
    d = ImageDraw.Draw(im)
    d.text((w // 2, h // 2 - size // 10), text, font=F(font, size), fill=fg, anchor="mm", direction="rtl", language="ps")
    return im


def text_lines_img(lines, title):
    """دوه کرښې متن (هره کلمه جلا، چې یو یو ښکاره شي): [(word_img, x, y)] د BOX په نسبت."""
    font = F(HEAD if title else TEXT, TXT_SIZE + (4 if title else 0))
    col = NAVY2 if title else (12, 18, 36)
    out = []
    cys = [42, 108] if len(lines) == 2 else [75]
    for li, (ln, cy) in enumerate(zip(lines, cys)):
        words = ln.split()
        x = TXT_RIGHT - BOX[0]
        sp = tw(" ", font)
        for w in words:                       # ښي نه کیڼ ته
            ww = tw(w, font)
            im = Image.new("RGBA", (ww + 20, 90), (0, 0, 0, 0))
            ImageDraw.Draw(im).text((ww + 10, 45), w, font=font, fill=col, anchor="rm",
                                    direction="rtl", language="ps")
            out.append((im, x - ww - 10, cy - 45, li))
            x -= ww + sp
    return out


def paginate(text, title=False):
    """متن په دوه-کرښیزو پاڼو وېشي."""
    font = F(HEAD if title else TEXT, TXT_SIZE + (4 if title else 0))
    pages, lines, cur = [], [], []
    for w in text.split():
        if cur and tw(" ".join(cur + [w]), font) > TXT_MAXW:
            lines.append(" ".join(cur))
            cur = []
            if len(lines) == 2:
                pages.append(lines)
                lines = []
        cur.append(w)
    if cur:
        lines.append(" ".join(cur))
    if lines:
        pages.append(lines)
    return pages


class Scene:
    def __init__(self, sg, fps=30):
        self.fps = fps
        self.sg = sg
        self.tex = side_texture()
        self.tile = logo_tile()
        self.static = self._static()
        self.tag_red = tag_img("تازه", 56, RED, WHITE, 408, 77)
        self.tag_yel = tag_img("خبر", 56, YEL, NAVY, 417, 77)
        self.badge_y = tag_img("تازه", 40, YEL, NAVY, 240, 50)
        self.badge_r = tag_img("خبر", 40, RED, WHITE, 240, 50)
        self.live = Image.new("RGBA", (LOGOBOX[2] - LOGOBOX[0], 40), (0, 0, 0, 255))
        ImageDraw.Draw(self.live).text((self.live.width // 2 + 12, 20), "LIVE", font=F(LATIN, 30), fill=WHITE, anchor="mm")
        labels = ["Bisram TV", "HD", "#1", "t.me/bisramtv"]
        self.labels = []
        for lb in labels:
            im = Image.new("RGBA", (LOGOBOX[2] - LOGOBOX[0], 50), (255, 255, 255, 255))
            fz = 30 if len(lb) < 12 else 22
            ImageDraw.Draw(im).text((im.width // 2, 26), lb, font=F(LATIN, fz), fill=NAVY2, anchor="mm")
            self.labels.append(im)
        src = sg.get("source") or "Bisram TV"
        info = f"سرچینه: {src}"
        self.info = Image.new("RGBA", (640, 70), (0, 0, 0, 0))
        ImageDraw.Draw(self.info).text((620, 38), info, font=F(SMALL, 32), fill=(200, 225, 255), anchor="rm",
                                       direction="rtl", language="ps")
        # پاڼې او وختونه
        title = (sg.get("title") or "").strip()
        body = (sg.get("summary") or "").strip()
        self.pages = [(p, True) for p in paginate(title, True)] + [(p, False) for p in paginate(body)]
        self.page_words = [text_lines_img(p, t) for p, t in self.pages]
        self.t0 = 1.1
        self.times = []
        t = self.t0
        for k, words in enumerate(self.page_words):
            n = len(words)
            reveal = n * 0.30
            hold = n * 0.22 + (1.6 if k == 0 else 1.0)
            self.times.append((t, t + reveal, t + reveal + hold))
            t += reveal + hold
        self.D = round(t + 0.4, 2)

    def _static(self):
        o = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(o)
        # پاس پټۍ
        o.alpha_composite(vgrad((W, 33), BLUE_D, NAVY2), (0, 0))
        o.alpha_composite(vgrad((W, 8), NAVY, NAVY), (0, 98))
        # د انځور چوکاټ
        d.rectangle(FR, fill=NAVY)
        # لاندې شینه پټۍ
        o.alpha_composite(hgrad((W, BAND[3] - BAND[1]), NAVY2, BLUE_D), (0, BAND[1]))
        # سپین بکس
        o.alpha_composite(vgrad((BOX[2] - BOX[0], BOX[3] - BOX[1]), (250, 250, 252), (222, 226, 236)), (BOX[0], BOX[1]))
        d.rectangle((BOX[0] + 50, BOX[3] - 5, BOX[2] - 40, BOX[3] - 2), fill=(255, 255, 255))
        d.rectangle((0, BOX[1], BOX[0], BOX[3]), fill=ORG)
        d.rectangle((BOX[2], BOX[1], LOGOBOX[0], BOX[3]), fill=ORG)
        # ژېړ بلاک
        yb = vgrad((YBLOCK[2] - YBLOCK[0], YBLOCK[3] - YBLOCK[1]), (255, 225, 60), (255, 170, 0))
        rr = Image.new("RGBA", yb.size, (0, 0, 0, 0))
        ImageDraw.Draw(rr).ellipse((10, 10, 260, 260), outline=(255, 255, 255, 90), width=14)
        yb.alpha_composite(rr.filter(ImageFilter.GaussianBlur(3)))
        o.alpha_composite(yb, (YBLOCK[0], YBLOCK[1]))
        # لاندې پټۍ
        o.alpha_composite(vgrad((W, H - BOTTOM[1]), BLUE, (6, 40, 120)), (0, BOTTOM[1]))
        d.rectangle((0, BOTTOM[1], W, BOTTOM[1] + 4), fill=(140, 210, 255))
        d.text((W - 60, 1004), "t.me/bisramtv  •  بصرام ټي وي", font=F(SMALL, 34), fill=(230, 242, 255),
               anchor="rm", direction="rtl", language="ps")
        return o

    # ---------- یو چوکاټ ----------
    def frame(self, t):
        f = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        # د خواوو شین متحرک شالید
        off = int((t * 40) % 600)
        crop = self.tex.crop((off, 0, off + W, 600)).resize((W, H - 106 - 0))
        side = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        side.paste(crop, (0, 106))
        f.alpha_composite(side)
        f.alpha_composite(self.static)
        # د انځور سوری (شفاف) — انځور له ffmpeg نه لاندې راځي
        intro = ease(t / 0.7)
        hole = Image.new("L", (W, H), 255)
        cx, cy = (PH[0] + PH[2]) / 2, (PH[1] + PH[3]) / 2
        s = 0.6 + 0.4 * intro
        hw, hh = (PH[2] - PH[0]) / 2 * s, (PH[3] - PH[1]) / 2 * s
        ImageDraw.Draw(hole).rectangle((cx - hw, cy - hh, cx + hw, cy + hh), fill=0)
        a = np.array(f)
        a[..., 3] = np.minimum(a[..., 3], np.array(hole))
        f = Image.fromarray(a, "RGBA")
        d = ImageDraw.Draw(f)
        # د چوکاټ ځلا کرښه (پاس) چې تېرېږي
        gx = int(PH[0] + ((t * 0.35) % 1.0) * (PH[2] - PH[0]))
        d.line((gx - 160, FR[1] + 2, gx + 160, FR[1] + 2), fill=(190, 230, 255), width=3)
        # پاس بار: LIVE (کیڼ)، ژېړ، غشی (ښي)
        top_in = ease((t - 0.1) / 0.6)
        ty = int(33 - 70 * (1 - top_in))
        bar = Image.new("RGBA", (W, 65), (0, 0, 0, 0))
        bd = ImageDraw.Draw(bar)
        bar.alpha_composite(vgrad((223, 65), (240, 40, 50), (180, 10, 20)), (0, 0))
        bd.text((112, 34), "LIVE", font=F(LATIN, 40), fill=WHITE, anchor="mm")
        if int(t * 2) % 2 == 0:
            bd.ellipse((20, 26, 36, 42), fill=WHITE)
        bd.rectangle((223, 0, 253, 65), fill=NAVY2)
        yl = hgrad((1499, 65), (255, 160, 0), (255, 225, 40))
        bar.alpha_composite(yl, (253, 0))
        sx = int(((t * 0.5) % 1.4 - 0.2) * 1499)
        sh = Image.new("RGBA", (1499, 65), (0, 0, 0, 0))
        ImageDraw.Draw(sh).polygon([(sx, 0), (sx + 90, 0), (sx + 50, 65), (sx - 40, 65)], fill=(255, 255, 255, 120))
        bar.alpha_composite(sh.filter(ImageFilter.GaussianBlur(6)), (253, 0))
        bar.alpha_composite(vgrad((78, 65), BLUE_D, NAVY2), (1752, 0))
        ax = 1800 - int(8 * math.sin(t * 6))
        bd.polygon([(ax + 12, 18), (ax - 12, 33), (ax + 12, 48)], fill=WHITE)
        bar.alpha_composite(vgrad((90, 65), BLUE, BLUE_D), (1830, 0))
        f.alpha_composite(bar, (0, ty))
        # تګونه (ښي نه راننوځي)
        p = ease_back((t - 0.25) / 0.6)
        if p > 0:
            xr = 1125 + int(500 * (1 - p))
            p2 = ease_back((t - 0.4) / 0.6)
            if p2 > 0:
                f.alpha_composite(self.tag_yel, (708 + int(600 * (1 - p2)), 698))
            f.alpha_composite(self.tag_red, (xr, 698))
            # ځلا چې پر تګونو تېرېږي
            gx = int(((t * 0.4) % 1.5) * 1100)
            gl = Image.new("RGBA", (830, 77), (0, 0, 0, 0))
            ImageDraw.Draw(gl).polygon([(gx - 300, 0), (gx - 220, 0), (gx - 260, 77), (gx - 340, 77)],
                                       fill=(255, 255, 255, 150))
            f.alpha_composite(gl.filter(ImageFilter.GaussianBlur(5)), (708, 698))
        f.alpha_composite(self.info, (40, 700))
        # لوګو بکس
        lb = self.labels[int(t / 2.5) % len(self.labels)]
        f.alpha_composite(lb, (LOGOBOX[0], LOGOBOX[1]))
        f.alpha_composite(self.tile, (LOGOBOX[0], LOGOBOX[1] + 50))
        f.alpha_composite(self.live, (LOGOBOX[0], LOGOBOX[3] - 40))
        if int(t * 2) % 2 == 0:
            ImageDraw.Draw(f).ellipse((LOGOBOX[0] + 48, LOGOBOX[3] - 28, LOGOBOX[0] + 62, LOGOBOX[3] - 14), fill=RED)
        # کږې لښتې (کیڼ لوري)
        sk = Image.new("RGBA", (180, 260), (0, 0, 0, 0))
        sd = ImageDraw.Draw(sk)
        for k, (c, x0) in enumerate(((BLUE, 30), (YEL, 70), (RED, 110))):
            yo = int(14 * math.sin(t * 3 + k))
            sd.polygon([(x0 + 40, 10 + yo), (x0 + 58, 16 + yo), (x0 + 8, 200 + yo), (x0 - 10, 194 + yo)], fill=c + (255,))
        f.alpha_composite(sk, (0, 690))
        # لاندې رڼا ټکي چې ځغلي
        d = ImageDraw.Draw(f)
        for k in range(14):
            x = int((k * 151 + t * 260) % (W + 200)) - 100
            d.rounded_rectangle((x, 1066, x + 40 + (k % 3) * 20, 1071), 3, fill=(220, 240, 255, 230))
            x2 = W - int((k * 173 + t * 200) % (W + 200))
            d.rounded_rectangle((x2, 8, x2 + 30 + (k % 2) * 20, 12), 2, fill=(255, 255, 255, 200))
        # بیج (کیڼ لاندې)
        bp = ease_back((t - 0.6) / 0.5)
        if bp > 0:
            f.alpha_composite(self.badge_y, (60, 954 + int(40 * (1 - bp))))
            f.alpha_composite(self.badge_r, (60, 1004 + int(40 * (1 - bp))))
        # متن (کلمه په کلمه)
        self._text(f, t)
        # د ټولې صحنې ننوتل (سپین فلش نه، یوازې د کتار پرانیستل)
        if t < 0.35:
            a = np.array(f)
            a[..., 3] = (a[..., 3] * (t / 0.35)).astype(np.uint8)
            f = Image.fromarray(a, "RGBA")
        return f

    def _text(self, f, t):
        k = next((j for j, (a, r, e) in enumerate(self.times) if a <= t < e), None)
        if k is None:
            k = len(self.times) - 1 if t >= self.times[-1][2] else None
        if k is None:
            return
        a, r, e = self.times[k]
        words = self.page_words[k]
        n = len(words)
        out_p = 0.0 if k == len(self.times) - 1 else max(0.0, (t - (e - 0.25)) / 0.25)
        for wi, (im, x, y, li) in enumerate(words):
            st = a + (r - a) * wi / max(1, n)
            p = ease((t - st) / 0.22)
            if p <= 0:
                continue
            al = p * (1 - out_p)
            if al <= 0:
                continue
            w = im.copy()
            if al < 1:
                arr = np.array(w)
                arr[..., 3] = (arr[..., 3] * al).astype(np.uint8)
                w = Image.fromarray(arr, "RGBA")
            dy = int(18 * (1 - p)) - int(20 * out_p)
            f.alpha_composite(w, (BOX[0] + x, BOX[1] + y + dy))


def render(sg, photo, out, fps=30):
    """صحنه جوړوي: انځور په چوکاټ کې (ورو زوم)، پاس یې ټول متحرک ګرافیک."""
    sc = Scene(sg, fps)
    D = sc.D
    n = int(round(D * fps))
    tmp = out + ".photo.jpg"
    pw, ph = PH[2] - PH[0], PH[3] - PH[1]
    if photo is None:                       # انځور نشته: شین شالید او لوی لوګو
        from card import logo_clean
        photo = side_texture().crop((0, 0, pw, ph)).resize((pw, ph))
        lg = logo_clean(560)
        photo.alpha_composite(lg, ((pw - lg.width) // 2, (ph - lg.height) // 2))
        photo = photo.convert("RGB")
    from card import cover
    cover(photo, int(pw * 1.12), int(ph * 1.12)).save(tmp, quality=93)
    flt = (f"[1:v]scale={int(pw * 1.12)}:{int(ph * 1.12)},"
           f"crop={pw}:{ph}:'(iw-{pw})/2*(1-t/{D})':'(ih-{ph})/2*(t/{D})',"
           f"pad={W}:{H}:{PH[0]}:{PH[1]}:color=0x061026,fps={fps}[bg];"
           f"[bg][0:v]overlay=0:0:format=auto,format=yuv420p[v]")
    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r", str(fps), "-i", "-",
           "-loop", "1", "-t", str(D), "-i", tmp,
           "-f", "lavfi", "-t", str(D), "-i", "anullsrc=r=48000:cl=stereo",
           "-filter_complex", flt, "-map", "[v]", "-map", "2:a", "-t", str(D),
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-r", str(fps),
           "-video_track_timescale", "15360", "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "2", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(n):
        p.stdin.write(sc.frame(i / fps).tobytes())
    p.stdin.close()
    if p.wait() != 0:
        raise RuntimeError("scene render failed")
    os.remove(tmp)
    return D
