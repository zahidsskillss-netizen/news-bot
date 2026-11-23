"""
د هر خبر لپاره د Bisram TV کارت (انځور) جوړوي — ۵ ډیزاینونه.
ډیزاین په config.json کې د CARD_STYLE له لارې ټاکل کېږي (1 تر 5).
"""
import os
from datetime import datetime, timedelta, timezone

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")
W, H = 1080, 1080

BLUE = (33, 150, 243)
BLUE_DARK = (13, 71, 161)
NAVY = (10, 25, 60)
WHITE = (255, 255, 255)
YELLOW = (255, 202, 40)
RED = (229, 57, 53)
GREY = (70, 80, 100)

HEAD = "GhoraMarhey.ttf"      # سرلیک
BODY = "GhoraMessiri.ttf"     # لنډیز
LATIN = "Vazirmatn-Bold.ttf"  # پته (لاتین)

PS_MONTHS = ["جنوري", "فبروري", "مارچ", "اپرېل", "مې", "جون", "جولای",
             "اګست", "سپتمبر", "اکتوبر", "نومبر", "دسمبر"]


# ---------- مرستندویه ----------
def font(name, size):
    return ImageFont.truetype(os.path.join(ASSETS, name), size)


def tw(d, s, f):
    b = d.textbbox((0, 0), s, font=f, direction="rtl", language="ps")
    return b[2] - b[0]


def wrap(d, text, f, max_w):
    lines, cur = [], ""
    for word in text.split():
        test = (cur + " " + word).strip()
        if tw(d, test, f) <= max_w or not cur:
            cur = test
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def fit(d, text, fname, sizes, max_w, max_lines):
    for size in sizes:
        f = font(fname, size)
        lines = wrap(d, text, f, max_w)
        if len(lines) <= max_lines:
            return f, lines
    f = font(fname, sizes[-1])
    lines = wrap(d, text, f, max_w)[:max_lines]
    lines[-1] += " …"
    return f, lines


def rtl(d, xy, s, f, fill, anchor="ra"):
    d.text(xy, s, font=f, fill=fill, direction="rtl", language="ps", anchor=anchor)


def lines_block(d, lines, f, x, y, fill, gap, anchor="ma"):
    for ln in lines:
        rtl(d, (x, y), ln, f, fill, anchor)
        y += int(f.size * 1.25) + gap
    return y


def block_h(lines, f, gap):
    return len(lines) * (int(f.size * 1.25) + gap)


def logo(width):
    lg = Image.open(os.path.join(ASSETS, "logo.png")).convert("RGBA")
    return lg.resize((width, int(lg.height * width / lg.width)), Image.LANCZOS)


def logo_badge(width, pad=24, radius=28):
    """لوګو په شین بکس کې (د سپین شالید لپاره)."""
    lg = logo(width)
    badge = Image.new("RGBA", (lg.width + pad * 2, lg.height + pad * 2), (0, 0, 0, 0))
    ImageDraw.Draw(badge).rounded_rectangle((0, 0, badge.width - 1, badge.height - 1), radius, fill=BLUE)
    badge.paste(lg, (pad, pad), lg)
    return badge


def gradient(c1, c2, vertical=True):
    g = Image.linear_gradient("L").resize((W, H))
    if not vertical:
        g = g.rotate(90)
    return Image.composite(Image.new("RGB", (W, H), c2), Image.new("RGB", (W, H), c1), g)


def today():
    now = datetime.now(timezone.utc) + timedelta(hours=4, minutes=30)   # د کابل وخت
    return f"{now.day} {PS_MONTHS[now.month - 1]} {now.year}"


def footer(d, handle, bg=NAVY, fg=WHITE, date_fg=(180, 200, 230), h=110):
    d.rectangle((0, H - h, W, H), fill=bg)
    d.text((60, H - h / 2), handle, font=font(LATIN, 38), fill=fg, anchor="lm")
    rtl(d, (W - 60, H - h / 2), today(), font(BODY, 36), date_fg, "rm")


def pill(d, cx, cy, text, f, bg, fg, padx=34, h=64):
    w = tw(d, text, f)
    d.rounded_rectangle((cx - w / 2 - padx, cy - h / 2, cx + w / 2 + padx, cy + h / 2), radius=h / 2, fill=bg)
    rtl(d, (cx, cy), text, f, fg, "mm")


# ---------- ۱: کلاسیک (شین شالید، سپین پانل) ----------
def style1(title, summary, handle):
    img = gradient(BLUE, BLUE_DARK)
    d = ImageDraw.Draw(img)
    lg = logo(330)
    img.paste(lg, ((W - lg.width) // 2, 55), lg)
    pill(d, W / 2, 265, "تازه خبر", font(HEAD, 36), YELLOW, NAVY)

    x1, y1, x2, y2 = 60, 330, W - 60, 930
    d.rounded_rectangle((x1, y1, x2, y2), radius=36, fill=WHITE)
    inner = x2 - x1 - 100
    tf, tl = fit(d, title, HEAD, [70, 62, 56, 50, 44], inner, 4)
    sf, sl = fit(d, summary, BODY, [38, 34, 31], inner, 3) if summary else (None, [])
    total = block_h(tl, tf, 6) + (60 + block_h(sl, sf, 4) if sl else 0)
    y = y1 + ((y2 - y1) - total) / 2
    y = lines_block(d, tl, tf, W / 2, y, NAVY, 6)
    if sl:
        y += 34
        d.line((W / 2 - 60, y, W / 2 + 60, y), fill=BLUE, width=5)
        lines_block(d, sl, sf, W / 2, y + 26, GREY, 4)
    footer(d, handle, h=100)
    return img


# ---------- ۲: عاجل خبر (تور شالید، سور نښه) ----------
def style2(title, summary, handle):
    img = gradient((8, 18, 45), (20, 45, 100))
    d = ImageDraw.Draw(img)
    lg = logo(260)
    img.paste(lg, (60, 55), lg)
    f = font(HEAD, 42)
    w = tw(d, "عاجل خبر", f)
    d.rectangle((W - 60 - w - 70, 75, W - 60, 155), fill=RED)
    rtl(d, (W - 95, 115), "عاجل خبر", f, WHITE, "rm")
    d.rectangle((0, 250, W, 258), fill=BLUE)

    inner = W - 160
    tf, tl = fit(d, title, HEAD, [80, 72, 64, 56, 50], inner, 4)
    sf, sl = fit(d, summary, BODY, [38, 34, 31], inner - 40, 3) if summary else (None, [])
    total = block_h(tl, tf, 10) + (60 + block_h(sl, sf, 6) if sl else 0)
    y = 300 + ((H - 120 - 300) - total) / 2
    y = lines_block(d, tl, tf, W - 80, y, WHITE, 10, "ra")
    if sl:
        d.rectangle((W - 80 - 8, y + 20, W - 80, y + 20 + block_h(sl, sf, 6)), fill=YELLOW)
        lines_block(d, sl, sf, W - 110, y + 20, (200, 215, 240), 6, "ra")
    footer(d, handle, bg=RED, date_fg=WHITE, h=100)
    return img


# ---------- ۳: سپین او ساده ----------
def style3(title, summary, handle):
    img = Image.new("RGB", (W, H), WHITE)
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, W, 18), fill=BLUE)
    bd = logo_badge(250)
    img.paste(bd, ((W - bd.width) // 2, 70), bd)
    pill(d, W / 2, 300, "خبر", font(HEAD, 34), (227, 242, 253), BLUE_DARK, padx=40, h=58)

    inner = W - 180
    tf, tl = fit(d, title, HEAD, [76, 68, 60, 54, 48], inner, 4)
    sf, sl = fit(d, summary, BODY, [38, 34, 31], inner, 3) if summary else (None, [])
    total = block_h(tl, tf, 8) + (70 + block_h(sl, sf, 4) if sl else 0)
    y = 360 + ((H - 110 - 360) - total) / 2
    y = lines_block(d, tl, tf, W / 2, y, NAVY, 8)
    if sl:
        y += 34
        for i, c in enumerate([BLUE, YELLOW, BLUE]):
            d.ellipse((W / 2 - 40 + i * 30, y, W / 2 - 26 + i * 30, y + 14), fill=c)
        lines_block(d, sl, sf, W / 2, y + 40, GREY, 4)
    footer(d, handle, bg=BLUE, date_fg=WHITE, h=100)
    return img


# ---------- ۴: کږه پرې کرښه (د لوګو په څېر) ----------
def style4(title, summary, handle):
    img = Image.new("RGB", (W, H), WHITE)
    top = gradient(BLUE, BLUE_DARK, vertical=False)
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).polygon([(0, 0), (W, 0), (W, 330), (0, 420)], fill=255)
    img.paste(top, (0, 0), mask)
    d = ImageDraw.Draw(img)
    d.polygon([(0, 420), (W, 330), (W, 345), (0, 435)], fill=NAVY)
    lg = logo(360)
    img.paste(lg, ((W - lg.width) // 2, 80), lg)

    inner = W - 160
    tf, tl = fit(d, title, HEAD, [72, 64, 58, 52, 46], inner, 4)
    sf, sl = fit(d, summary, BODY, [36, 33, 30], inner, 3) if summary else (None, [])
    total = block_h(tl, tf, 8) + (50 + block_h(sl, sf, 4) if sl else 0)
    y = 470 + ((H - 100 - 470) - total) / 2
    y = lines_block(d, tl, tf, W / 2, y, NAVY, 8)
    if sl:
        lines_block(d, sl, sf, W / 2, y + 30, GREY, 4)
    footer(d, handle, h=90)
    return img


# ---------- ۵: د سرلیک پټۍ (هره کرښه په جلا بکس کې) ----------
def style5(title, summary, handle):
    img = gradient(BLUE, (25, 118, 210))
    d = ImageDraw.Draw(img)
    for i in range(-H, W, 70):
        d.line((i, H, i + H, 0), fill=(41, 160, 250), width=18)
    lg = logo(300)
    img.paste(lg, ((W - lg.width) // 2, 60), lg)

    inner = W - 200
    tf, tl = fit(d, title, HEAD, [70, 62, 56, 50], inner, 4)
    lh = int(tf.size * 1.25) + 28
    sf, sl = fit(d, summary, BODY, [36, 33, 30], W - 220, 3) if summary else (None, [])
    total = len(tl) * lh + (40 + block_h(sl, sf, 4) + 40 if sl else 0)
    y = 300 + ((H - 110 - 300) - total) / 2
    for ln in tl:
        w = tw(d, ln, tf)
        d.rectangle((W / 2 - w / 2 - 28, y, W / 2 + w / 2 + 28, y + lh - 12), fill=WHITE)
        rtl(d, (W / 2, y + (lh - 12) / 2), ln, tf, NAVY, "mm")
        y += lh
    if sl:
        y += 30
        box_h = block_h(sl, sf, 4) + 36
        d.rectangle((80, y, W - 80, y + box_h), fill=NAVY)
        lines_block(d, sl, sf, W / 2, y + 16, WHITE, 4)
    footer(d, handle, bg=YELLOW, fg=NAVY, date_fg=NAVY, h=100)
    return img


STYLES = {1: style1, 2: style2, 3: style3, 4: style4, 5: style5}


def make_card(title, summary, handle, out_path, style=1):
    try:
        style = int(style)
    except (TypeError, ValueError):
        style = 1
    img = STYLES.get(style, style1)(title, summary or "", handle)
    img.save(out_path, "JPEG", quality=92)
    return out_path


if __name__ == "__main__":
    t = "د کاپ۳۱ اقلیمي ناسته له هوکړې پرته پای ته ورسېده"
    s = "د ملګرو ملتونو د اقلیمي بدلون غونډه پرته له دې چې ګډې پرېکړې ته ورسېږي، پای ته ورسېده او هېوادونو په راتلونکو ګامونو هوکړه ونه کړه."
    for n in STYLES:
        make_card(t, s, "t.me/bisramtv", f"/tmp/design_{n}.jpg", n)
    print("ok")
