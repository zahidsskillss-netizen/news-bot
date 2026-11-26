"""د لیکلي راپور لپاره ۸ Lower third ډیزاینونه — هر یو دوه کرښې متن اخلي.
draw(style, lines, frame_rgb) → RGBA overlay (1920x1080) چې پر انځور ایښودل کېږي.
"""
import os
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
A = os.path.join(HERE, "assets")
HEAD = os.path.join(A, "GhoraLalezar.ttf")
TEXT = os.path.join(A, "BahijTheSans-Bold.ttf")
SMALL = os.path.join(A, "GhoraMarhey.ttf")
W, H = 1920, 1080
TAG = "تازه خبر"

_fc = {}


def F(path, size):
    k = (path, size)
    if k not in _fc:
        _fc[k] = ImageFont.truetype(path, size, layout_engine=ImageFont.Layout.RAQM)
    return _fc[k]


def tw(text, font):
    return int(ImageDraw.Draw(Image.new("L", (1, 1))).textlength(text, font=font, direction="rtl", language="ps"))


def rtext(d, right, cy, text, font, fill):
    """ښي ته برابر متن، په عمودي منځ کې."""
    d.text((right, cy), text, font=font, fill=fill, anchor="rm", direction="rtl", language="ps")


def logo(w):
    from card import logo_clean
    return logo_clean(w)


def rrect(size, r, fill):
    im = Image.new("RGBA", size, (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), r, fill=fill)
    return im


def para(size, slant, fill):
    w, h = size
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(im).polygon([(slant, 0), (w, 0), (w - slant, h), (0, h)], fill=fill)
    return im


def hgrad(size, c1, c2):
    w, h = size
    g = Image.linear_gradient("L").rotate(90, expand=True).resize((w, h))
    return Image.composite(Image.new("RGBA", size, c2), Image.new("RGBA", size, c1), g)


def vgrad(size, c1, c2):
    g = Image.linear_gradient("L").resize(size)
    return Image.composite(Image.new("RGBA", size, c2), Image.new("RGBA", size, c1), g)


def mask_paste(dst, src, mask_img, xy):
    m = mask_img.split()[-1]
    dst.paste(src, xy, m)


def shadow(o, box, r=20, blur=18, alpha=140, off=(0, 10)):
    sh = Image.new("RGBA", o.size, (0, 0, 0, 0))
    x0, y0, x1, y1 = box
    ImageDraw.Draw(sh).rounded_rectangle((x0 + off[0], y0 + off[1], x1 + off[0], y1 + off[1]), r, fill=(0, 0, 0, alpha))
    o.alpha_composite(sh.filter(ImageFilter.GaussianBlur(blur)))


def two_lines(d, right, y1, y2, lines, font, fill):
    for y, ln in zip((y1, y2), lines):
        if ln:
            rtext(d, right, y, ln, font, fill)


# ---------------- 1: کلاسیک تلویزیوني (سور/ژېړ/شین) ----------------
def s1(lines, frame, source):
    o = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(o)
    # لاندې سور پټۍ
    o.alpha_composite(vgrad((W, 70), (220, 20, 30, 255), (150, 0, 10, 255)), (0, H - 70))
    rtext(d, W - 40, H - 35, "Bisram TV  •  t.me/bisramtv", F(SMALL, 30), (255, 255, 255))
    # سپین بکس
    x0, x1, y0, y1 = 120, W - 330, H - 300, H - 85
    shadow(o, (x0, y0, x1, y1), r=4)
    o.alpha_composite(vgrad((x1 - x0, y1 - y0), (255, 255, 255, 255), (222, 226, 235, 255)), (x0, y0))
    d.rectangle((x0, y0, x1, y0 + 6), fill=(20, 40, 140))
    # تګ: ژېړ + شین
    t = F(HEAD, 40)
    o.alpha_composite(para((300, 62), 0, (255, 196, 0, 255)), (x1 - 300, y0 - 62))
    rtext(d, x1 - 20, y0 - 30, TAG, t, (150, 0, 0))
    o.alpha_composite(para((230, 62), 0, (20, 40, 140, 255)), (x1 - 530, y0 - 62))
    d.text((x1 - 415, y0 - 30), "NEWS", font=F(os.path.join(A, "Vazirmatn-Bold.ttf") if os.path.exists(os.path.join(A, "Vazirmatn-Bold.ttf")) else HEAD, 36), fill="white", anchor="mm")
    two_lines(d, x1 - 30, y0 + 62, y0 + 160, lines, F(TEXT, 56), (15, 20, 40))
    # لوګو بکس
    bx = W - 320
    o.alpha_composite(vgrad((290, y1 - y0 + 62), (190, 0, 10, 255), (110, 0, 0, 255)), (bx + 10, y0 - 62))
    lg = logo(240)
    o.alpha_composite(lg, (bx + 10 + (290 - lg.width) // 2, y0 + 10))
    d.rounded_rectangle((bx + 95, y1 - 60, bx + 215, y1 - 20), 6, fill=(255, 255, 255))
    d.text((bx + 155, y1 - 40), "LIVE", font=F(HEAD, 30) if not os.path.exists(os.path.join(A, "Vazirmatn-Bold.ttf")) else F(os.path.join(A, "Vazirmatn-Bold.ttf"), 28), fill=(200, 0, 0), anchor="mm")
    return o


# ---------------- 2: Liquid Glass (روښانه شیشه) ----------------
def s2(lines, frame, source):
    o = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    x0, y0, x1, y1 = 110, H - 320, W - 110, H - 70
    box = (x0, y0, x1, y1)
    shadow(o, box, r=48, blur=30, alpha=120)
    glass = frame.crop(box).filter(ImageFilter.GaussianBlur(28)).convert("RGBA")
    glass.alpha_composite(Image.new("RGBA", glass.size, (255, 255, 255, 120)))
    glass.alpha_composite(vgrad(glass.size, (255, 255, 255, 90), (255, 255, 255, 0)))
    m = rrect(glass.size, 48, (0, 0, 0, 255))
    mask_paste(o, glass, m, (x0, y0))
    d = ImageDraw.Draw(o)
    d.rounded_rectangle(box, 48, outline=(255, 255, 255, 230), width=3)
    d.rounded_rectangle((x0 + 4, y0 + 4, x1 - 4, y1 - 4), 45, outline=(255, 255, 255, 60), width=2)
    # تګ کپسول
    t = F(HEAD, 38)
    w = tw(TAG, t) + 60
    o.alpha_composite(rrect((w, 60), 30, (0, 122, 255, 255)), (x1 - 40 - w, y0 + 26))
    rtext(d, x1 - 70, y0 + 54, TAG, t, "white")
    lg = logo(200)
    o.alpha_composite(lg, (x0 + 40, y0 + 22))
    two_lines(d, x1 - 50, y0 + 135, y0 + 205, lines, F(TEXT, 54), (20, 24, 40))
    return o


# ---------------- 3: تیاره ځلانده کپسول (Glow pill) ----------------
def s3(lines, frame, source):
    o = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    x0, y0, x1, y1 = 140, H - 300, W - 140, H - 80
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glow).rounded_rectangle((x0, y0, x1, y1), 110, outline=(80, 200, 255, 255), width=14)
    o.alpha_composite(glow.filter(ImageFilter.GaussianBlur(22)))
    body = vgrad((x1 - x0, y1 - y0), (12, 30, 70, 235), (4, 10, 30, 245))
    mask_paste(o, body, rrect(body.size, 110, (0, 0, 0, 255)), (x0, y0))
    d = ImageDraw.Draw(o)
    d.rounded_rectangle((x0, y0, x1, y1), 110, outline=(140, 225, 255, 255), width=3)
    # پاس ځلا کرښه
    hl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(hl).line((x0 + 160, y0 + 2, x1 - 160, y0 + 2), fill=(255, 255, 255, 255), width=4)
    o.alpha_composite(hl.filter(ImageFilter.GaussianBlur(3)))
    t = F(HEAD, 40)
    rtext(d, x1 - 140, y0 + 52, TAG, t, (110, 215, 255))
    d.ellipse((x1 - 128, y0 + 44, x1 - 112, y0 + 60), fill=(110, 215, 255))
    two_lines(d, x1 - 110, y0 + 120, y0 + 185, lines, F(TEXT, 54), "white")
    lg = logo(210)
    o.alpha_composite(lg, (x0 + 80, y0 + (y1 - y0 - lg.height) // 2))
    return o


# ---------------- 4: شین کږ سلیب + سور تګ ----------------
def s4(lines, frame, source):
    o = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    y0, y1 = H - 290, H - 70
    sl = 60
    o.alpha_composite(para((W - 120, y1 - y0), sl, (0, 0, 0, 90)), (70, y0 + 12))
    slab = hgrad((W - 120, y1 - y0), (10, 50, 160, 245), (0, 120, 230, 245))
    mask_paste(o, slab, para(slab.size, sl, (0, 0, 0, 255)), (60, y0))
    d = ImageDraw.Draw(o)
    acc = para((W - 120, 10), 3, (255, 200, 0, 255))
    o.alpha_composite(acc, (60 + sl - 3, y0))
    t = F(HEAD, 40)
    w = tw(TAG, t) + 70
    o.alpha_composite(para((w, 64), 22, (225, 25, 35, 255)), (W - 110 - w, y0 - 54))
    rtext(d, W - 140, y0 - 22, TAG, t, "white")
    two_lines(d, W - 150, y0 + 78, y0 + 160, lines, F(TEXT, 56), "white")
    lg = logo(220)
    o.alpha_composite(lg, (150, y0 + (y1 - y0 - lg.height) // 2))
    d.line((420, y0 + 40, 420, y1 - 40), fill=(255, 255, 255, 120), width=2)
    return o


# ---------------- 5: سرلیک پټۍ + سپین بکس ----------------
def s5(lines, frame, source):
    o = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    x0, x1 = 100, W - 100
    y0 = H - 330
    shadow(o, (x0, y0, x1, H - 60), r=18)
    top = hgrad((x1 - x0, 74), (6, 14, 38, 255), (20, 50, 120, 255))
    mask_paste(o, top, rrect(top.size, 18, (0, 0, 0, 255)).crop((0, 0, x1 - x0, 74)), (x0, y0))
    o.alpha_composite(Image.new("RGBA", (x1 - x0, 20), (20, 50, 120, 255)).crop((0, 0, x1 - x0, 20)), (x0, y0 + 60))
    d = ImageDraw.Draw(o)
    d.rectangle((x0, y0 + 60, x1, y0 + 74), fill=(20, 50, 120))
    white = rrect((x1 - x0, H - 60 - (y0 + 74)), 18, (255, 255, 255, 250))
    o.alpha_composite(white, (x0, y0 + 74))
    d.rectangle((x0, y0 + 74, x1, y0 + 94), fill=(255, 255, 255, 250))
    d.rectangle((x1 - 12, y0 + 74, x1, H - 78), fill=(230, 30, 40))
    rtext(d, x1 - 40, y0 + 38, TAG, F(HEAD, 40), (255, 205, 0))
    d.text((x0 + 40, y0 + 38), "Bisram TV", font=F(HEAD, 34), fill="white", anchor="lm")
    two_lines(d, x1 - 50, y0 + 140, y0 + 215, lines, F(TEXT, 56), (10, 20, 45))
    return o


# ---------------- 6: لږ تیاره شفافه + ژېړه کرښه (Minimal) ----------------
def s6(lines, frame, source):
    o = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    y0, y1 = H - 300, H - 60
    o.alpha_composite(hgrad((W, y1 - y0), (0, 0, 0, 0), (0, 0, 0, 200)), (0, y0))
    o.alpha_composite(Image.new("RGBA", (W, H - y1), (0, 0, 0, 200)), (0, y1))
    d = ImageDraw.Draw(o)
    d.rectangle((W - 120, y0 + 30, W - 110, y1 - 30), fill=(255, 200, 0))
    rtext(d, W - 150, y0 + 55, TAG, F(HEAD, 42), (255, 200, 0))
    two_lines(d, W - 150, y0 + 130, y0 + 200, lines, F(TEXT, 58), "white")
    lg = logo(200)
    o.alpha_composite(lg, (60, y1 - lg.height - 10))
    return o


# ---------------- 7: ټول پلن نیوز بار ----------------
def s7(lines, frame, source):
    o = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    y0 = H - 280
    o.alpha_composite(vgrad((W, H - y0), (8, 20, 60, 235), (2, 6, 20, 250)), (0, y0))
    d = ImageDraw.Draw(o)
    d.rectangle((0, y0, W, y0 + 6), fill=(0, 160, 255))
    d.rectangle((0, H - 56, W, H), fill=(230, 30, 40))
    rtext(d, W - 40, H - 28, "بصرام ټي وي  •  t.me/bisramtv", F(SMALL, 30), "white")
    # کړۍ لوګو
    c = Image.new("RGBA", (230, 230), (0, 0, 0, 0))
    ImageDraw.Draw(c).ellipse((0, 0, 229, 229), fill=(8, 22, 64, 255), outline=(0, 160, 255, 255), width=8)
    lg = logo(180)
    c.alpha_composite(lg, ((230 - lg.width) // 2, (230 - lg.height) // 2))
    o.alpha_composite(c, (W - 270, y0 - 90))
    t = F(HEAD, 40)
    w = tw(TAG, t) + 60
    o.alpha_composite(rrect((w, 58), 8, (0, 160, 255, 255)), (W - 300 - w, y0 - 40))
    rtext(d, W - 330, y0 - 11, TAG, t, "white")
    two_lines(d, W - 300, y0 + 75, y0 + 150, lines, F(TEXT, 56), "white")
    return o


# ---------------- 8: درې اړخیز پاڼې (Layered 3D) ----------------
def s8(lines, frame, source):
    o = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    y0, y1 = H - 300, H - 80
    sl = 40
    o.alpha_composite(para((W - 200, y1 - y0), sl, (225, 25, 35, 255)), (110, y0 + 18))
    o.alpha_composite(para((W - 200, y1 - y0), sl, (0, 90, 200, 255)), (95, y0 + 9))
    shadow(o, (80, y0, W - 120, y1), r=0, blur=14, alpha=110)
    white = vgrad((W - 200, y1 - y0), (255, 255, 255, 255), (232, 236, 244, 255))
    mask_paste(o, white, para(white.size, sl, (0, 0, 0, 255)), (80, y0))
    d = ImageDraw.Draw(o)
    t = F(HEAD, 40)
    w = tw(TAG, t) + 80
    o.alpha_composite(para((w, 62), 20, (6, 14, 38, 255)), (W - 140 - w, y0 - 50))
    rtext(d, W - 175, y0 - 19, TAG, t, (255, 205, 0))
    two_lines(d, W - 190, y0 + 72, y0 + 152, lines, F(TEXT, 56), (10, 20, 45))
    # کیڼ اړخ ته د لوګو تیاره برخه
    nav = para((360, y1 - y0), sl, (6, 14, 38, 255))
    o.alpha_composite(nav, (80, y0))
    lg = logo(230)
    o.alpha_composite(lg, (80 + (360 - lg.width) // 2, y0 + (y1 - y0 - lg.height) // 2))
    return o


STYLES = {1: s1, 2: s2, 3: s3, 4: s4, 5: s5, 6: s6, 7: s7, 8: s8}
# د هر ډیزاین لپاره د یوې کرښې اعظمي پلنوالی (پکسل)
MAXW = {1: 1380, 2: 1450, 3: 1180, 4: 1280, 5: 1560, 6: 1420, 7: 1480, 8: 1220}


def draw(style, lines, frame, source=""):
    return STYLES[int(style)](lines, frame, source)
