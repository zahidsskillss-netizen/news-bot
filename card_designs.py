"""
د Bisram TV ۵ نوي ډیزاینونه (۶ تر ۱۰) — د زاهد د بېلګو له مخې، په پښتو (ښي-کیڼ) بڼه.
۶ ورځپاڼه · ۷ سپین کارت · ۸ براوزر · ۹ بشپړ انځور · ۱۰ خبرپاڼه
"""
import random

from PIL import Image, ImageDraw, ImageFilter

from card import (BLUE, BLUE_DARK, NAVY, WHITE, YELLOW, RED, GREY, HEAD, BODY, TEXT, LATIN, W, H,
                  font, tw, wrap, fit, rtl, block_h, logo_badge, logo_clean, cover, shade,
                  today)

INK = (20, 32, 60)
SOFT = (90, 100, 120)
PAPER = (247, 245, 239)
SKY = (214, 236, 252)


# ---------- مرستندویه ----------
def rounded_photo(photo, w, h, r=28):
    im = cover(photo, w, h).convert("RGBA")
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), r, fill=255)
    im.putalpha(m)
    return im


def placeholder(w, h):
    g = Image.linear_gradient("L").resize((w, h))
    return Image.composite(Image.new("RGB", (w, h), BLUE_DARK), Image.new("RGB", (w, h), BLUE), g)


def para(d, lines, f, x, y, fill, gap=10, anchor="ra"):
    for ln in lines:
        rtl(d, (x, y), ln, f, fill, anchor)
        y += int(f.size * 1.45) + gap
    return y


def shadow_box(img, box, radius=30, blur=22, alpha=70, offset=(0, 14)):
    x1, y1, x2, y2 = box
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((x1 + offset[0], y1 + offset[1], x2 + offset[0], y2 + offset[1]),
                                         radius, fill=(0, 0, 0, alpha))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(blur)))


def social_row(d, y, color, handle, x_right=W - 60, size=28):
    items = [("ټلګرام", handle), ("فیسبوک", "Bisram TV"), ("یوټیوب", "Bisram TV")]
    f, fl = font(BODY, size), font(LATIN, size)
    x = x_right
    for lab, val in items:
        rtl(d, (x, y), lab + ":", f, color, "rm")
        x -= tw(d, lab + ":", f) + 10
        vw = d.textbbox((0, 0), val, font=fl)[2]
        d.text((x - vw, y), val, font=fl, fill=color, anchor="lm")
        x -= vw + 46


# ---------- ۶: ورځپاڼه ----------
def style6(title, summary, handle, photo, source):
    img = Image.new("RGBA", (W, H), PAPER + (255,))
    rnd = random.Random(3)
    nd = ImageDraw.Draw(img)
    for _ in range(9000):   # د کاغذ دانې
        x, y = rnd.randrange(W), rnd.randrange(H)
        c = rnd.randint(225, 240)
        nd.point((x, y), fill=(c, c - 2, c - 8, 255))
    d = ImageDraw.Draw(img)

    bd = logo_badge(250, pad=16, radius=16)
    img.alpha_composite(bd, ((W - bd.width) // 2, 34))
    rtl(d, (W - 50, 60), "خبري څانګه", font(HEAD, 30), BLUE_DARK)
    rtl(d, (W - 50, 102), "Bisram TV", font(LATIN, 24), SOFT)
    d.text((50, 62), today(), font=font(BODY, 28), fill=BLUE_DARK, direction="rtl",
           language="ps", anchor="la")
    d.text((50, 104), handle, font=font(LATIN, 24), fill=SOFT, anchor="la")
    y = 34 + bd.height + 16
    d.line((50, y, W - 50, y), fill=BLUE_DARK, width=3)
    tag = "د ورځې مهم خبرونه، لنډ، سم او بې‌پرې"
    rtl(d, (W / 2, y + 12), tag, font(BODY, 30), BLUE_DARK, "ma")
    y += 62
    d.line((50, y, W - 50, y), fill=BLUE_DARK, width=1)

    py = y + 22
    pw, ph = W - 100, 470
    d.rectangle((50 - 7, py - 7, 50 + pw + 7, py + ph + 7), fill=BLUE_DARK)
    pic = cover(photo, pw, ph) if photo else placeholder(pw, ph)
    img.paste(pic, (50, py))
    if source:
        sf = font(BODY, 24)
        sw = tw(d, "سرچینه: " + source, sf)
        d.rectangle((50, py + ph - 46, 50 + sw + 40, py + ph), fill=(*BLUE_DARK, 255))
        rtl(d, (50 + sw + 20, py + ph - 23), "سرچینه: " + source, sf, WHITE, "rm")

    y = py + ph + 26
    tf, tl = fit(d, title, HEAD, [58, 52, 48, 44], W - 110, 2)
    for ln in tl:
        rtl(d, (W - 55, y), ln, tf, BLUE_DARK)
        y += int(tf.size * 1.3)
    y += 4
    room = (H - 70 - 14) - y
    if summary and room > 40:
        sf = font(BODY, 28)
        n = max(1, int(room // (int(28 * 1.45) + 2)))
        sf, sl = fit(d, summary, TEXT, [28, 26], W - 110, min(3, n))
        para(d, sl, sf, W - 55, y, INK, 2)

    d.rectangle((0, H - 70, W, H), fill=BLUE_DARK)
    social_row(d, H - 35, WHITE, handle, size=26)
    return img.convert("RGB")


# ---------- ۷: سپین کارت ----------
def style7(title, summary, handle, photo, source):
    img = Image.new("RGBA", (W, H), (233, 236, 240, 255))
    shadow_box(img, (45, 45, W - 45, H - 45), 8, 20, 60)
    d = ImageDraw.Draw(img)
    d.rectangle((45, 45, W - 45, H - 45), fill=WHITE)

    bd = logo_badge(170, pad=12, radius=14)
    img.alpha_composite(bd, (W - 85 - bd.width, 80))
    for i, ch in enumerate(("f", "t", "y")):
        cx = 115 + i * 62
        d.ellipse((cx - 24, 100, cx + 24, 148), outline=INK, width=3)
        d.text((cx, 124), ch, font=font(LATIN, 26), fill=INK, anchor="mm")

    rtl(d, (W / 2, 200), "تازه خبر", font(BODY, 36), SOFT, "ma")
    tf, tl = fit(d, title, HEAD, [62, 56, 50, 46], W - 220, 2)
    y = 252
    for ln in tl:
        rtl(d, (W / 2, y), ln, tf, BLUE_DARK, "ma")
        y += int(tf.size * 1.28)
    if summary:
        sf, sl = fit(d, "«" + summary + "»", TEXT, [28, 26], W - 260, 2)
        y = para(d, sl, sf, W / 2, y + 4, INK, 0, "ma")
    d.text((165, 318), "‹", font=font(LATIN, 50), fill=INK, anchor="mm")
    d.text((W - 165, 318), "›", font=font(LATIN, 50), fill=INK, anchor="mm")

    # انځور: ګرد چوکاټ، شنې کونجي او نقطه لرونکی شالید
    px, pw = 170, W - 340
    py = max(y + 70, 540)
    ph = min(330, H - 190 - py)
    for yy in range(py - 60, py + ph + 60, 16):
        for xx in range(px - 80, px + pw + 80, 16):
            dist = ((xx - W / 2) / (pw * 0.8)) ** 2 + ((yy - (py + ph / 2)) / (ph * 0.9)) ** 2
            if dist < 1:
                r = 3.5 * (1 - dist)
                d.ellipse((xx - r, yy - r, xx + r, yy + r), fill=(200, 228, 250))
    d.rounded_rectangle((px - 26, py - 26, px + 200, py - 14), 6, fill=BLUE)
    d.rounded_rectangle((px - 26, py - 26, px - 14, py + 150), 6, fill=BLUE)
    d.rounded_rectangle((px + pw - 200, py + ph + 14, px + pw + 26, py + ph + 26), 6, fill=BLUE)
    d.rounded_rectangle((px + pw + 14, py + ph - 150, px + pw + 26, py + ph + 26), 6, fill=BLUE)
    d.rounded_rectangle((px - 10, py - 10, px + pw + 10, py + ph + 10), 40, outline=INK, width=3)
    d.ellipse((px + pw - 4, py - 16, px + pw + 16, py + 4), fill=INK)
    d.ellipse((px - 16, py + ph - 4, px + 4, py + ph + 16), fill=INK)
    pic = rounded_photo(photo, pw, ph, 32) if photo else rounded_photo(placeholder(pw, ph), pw, ph, 32)
    img.alpha_composite(pic, (px, py))
    if source:
        rtl(d, (px + pw - 16, py + ph - 14), source, font(BODY, 20), (240, 240, 240), "rd")

    by = H - 120
    rtl(d, (W - 90, by - 20), "نېټه", font(BODY, 24), SOFT, "ra")
    rtl(d, (W - 90, by + 12), today(), font(BODY, 28), INK, "ra")
    f = font(HEAD, 34)
    bw = tw(d, "نور ولولئ", f) + 70
    d.rounded_rectangle((W / 2 - bw / 2, by - 12, W / 2 + bw / 2, by + 52), 32, outline=BLUE, width=4)
    rtl(d, (W / 2, by + 20), "نور ولولئ", f, BLUE_DARK, "mm")
    d.text((90, by - 18), "ټلګرام", font=font(BODY, 24), fill=SOFT, direction="rtl", language="ps", anchor="la")
    d.text((90, by + 14), handle, font=font(LATIN, 28), fill=INK, anchor="la")
    return img.convert("RGB")


# ---------- ۸: براوزر ----------
def style8(title, summary, handle, photo, source):
    g = Image.linear_gradient("L").resize((W, H)).rotate(35)
    img = Image.composite(Image.new("RGB", (W, H), (25, 110, 200)), Image.new("RGB", (W, H), (70, 175, 245)), g).convert("RGBA")
    d = ImageDraw.Draw(img)
    for i in range(-H, W, 90):
        d.line((i, H, i + H * 0.6, 0), fill=(110, 195, 250, 255), width=2)
    # د براوزر پټۍ
    d.rounded_rectangle((70, 60, W - 70, 150), 45, fill=SKY)
    # ← → ⟳ (په لاس انځور شوي)
    for x0, sgn in ((130, -1), (205, 1)):
        d.line((x0 - 22, 105, x0 + 22, 105), fill=INK, width=5)
        tip = x0 + 22 * sgn
        d.line((tip, 105, tip - 14 * sgn, 91), fill=INK, width=5)
        d.line((tip, 105, tip - 14 * sgn, 119), fill=INK, width=5)
    d.arc((262, 83, 306, 127), 40, 330, fill=INK, width=5)
    d.polygon([(300, 76), (312, 96), (290, 96)], fill=INK)
    d.rounded_rectangle((350, 74, W - 90, 136), 31, fill=WHITE)
    d.rounded_rectangle((382, 94, 398, 116), 3, fill=INK)
    d.arc((380, 82, 400, 104), 180, 360, fill=INK, width=3)
    d.text((418, 105), handle, font=font(LATIN, 32), fill=INK, anchor="lm")

    # کارت
    cx1, cy1, cx2, cy2 = 70, 185, W - 70, H - 60
    d.rounded_rectangle((cx1, cy1, cx2, cy2), 50, fill=SKY + (255,))
    pw, ph = cx2 - cx1 - 50, 470
    px, py = cx1 + 25, cy1 + 25
    d.rounded_rectangle((px - 6, py - 6, px + pw + 6, py + ph + 6), 40, fill=WHITE)
    pic = rounded_photo(photo, pw, ph, 36) if photo else rounded_photo(placeholder(pw, ph), pw, ph, 36)
    img.alpha_composite(pic, (px, py))
    if not photo:   # انځور نه وي: لوی لوګو په منځ کې
        big = logo_clean(300)
        img.alpha_composite(big, (px + (pw - big.width) // 2, py + (ph - big.height) // 2 + 30))
    else:           # د چینل لوګو: د انځور چپ پورته کونج
        bug = logo_clean(200)
        img.alpha_composite(bug, (px + 18, py + 14))
    # «ژوندی / تازه خبر» نښه
    s1, s2 = font(HEAD, 30), font(HEAD, 62)
    x2 = px + pw - 40
    w2 = tw(d, "تازه خبر", s2) + 50
    sticker = Image.new("RGBA", (w2 + 20, 150), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sticker)
    sd.polygon([(w2 - 120, 0), (w2 + 10, 0), (w2, 44), (w2 - 130, 44)], fill=BLUE + (255,))
    sd.text((w2 - 60, 22), "LIVE", font=font(LATIN, 28), fill=WHITE, anchor="mm")
    sd.polygon([(20, 52), (w2 + 20, 52), (w2, 140), (0, 140)], fill=WHITE + (255,))
    sd.text((w2 / 2 + 10, 96), "تازه خبر", font=s2, fill=BLUE_DARK, anchor="mm", direction="rtl", language="ps")
    img.alpha_composite(sticker, (x2 - sticker.width, py + 30))
    if source:   # سرچینه: کوچنی متن په تور شالید
        sf_ = font(BODY, 16)
        sw = tw(d, source, sf_)
        bx, by = px + 20, py + ph - 20 - 28
        d.rounded_rectangle((bx, by, bx + sw + 20, by + 28), 7, fill=(0, 0, 0, 170))
        rtl(d, (bx + 10 + sw, by + 14), source, sf_, (235, 235, 235), "rm")

    # سرلیک او متن (پرته له «تازه خبر» او «نور ولولئ»)
    tx = cx2 - 40
    y = py + ph + 26
    tf, tl = fit(d, title, HEAD, [46, 42, 38], pw - 40, 2)
    for ln in tl:
        rtl(d, (tx, y), ln, tf, INK)
        y += int(tf.size * 1.3)
    date_y = cy2 - 44
    room = (date_y - 24) - (y + 6)
    if summary and room > 30:
        # تل درې کرښې (که ځای کم وي، فونټ کوچنی کېږي)
        for size in (28, 26, 24, 22):
            if 3 * int(size * 1.45) <= room:
                break
        sf, sl = fit(d, summary, TEXT, [size, max(20, size - 2)], pw - 40, 3)
        para(d, sl, sf, tx, y + 6, (30, 40, 62), 0)
    # نېټه: تر ټولو لاندې
    d.line((cx1 + 40, date_y - 14, cx2 - 40, date_y - 14), fill=(185, 210, 232), width=2)
    rtl(d, (tx, date_y + 8), today(), font(BODY, 26), SOFT, "rm")
    d.text((cx1 + 40, date_y + 8), handle, font=font(LATIN, 26), fill=SOFT, anchor="lm")
    return img.convert("RGB")


# ---------- ۹: بشپړ انځور ----------
def style9(title, summary, handle, photo, source):
    img = (cover(photo, W, H) if photo else placeholder(W, H)).convert("RGBA")
    img.alpha_composite(shade(W, 380, 200, 0), (0, 0))
    img.alpha_composite(shade(W, 620, 0, 245), (0, H - 620))
    blk = Image.new("RGBA", (W, 200), (8, 18, 45, 245))
    img.alpha_composite(blk, (0, H - 200))
    d = ImageDraw.Draw(img)

    f = font(HEAD, 120)
    a, b = "تازه", " خبرونه"
    wa, wb = tw(d, a, f), tw(d, b, f)
    x0 = (W + wa + wb) / 2
    rtl(d, (x0, 70), a, f, RED)
    rtl(d, (x0 - wa, 70), b, f, WHITE)
    pf = font(BODY, 40)
    pw_ = tw(d, "بسرام ټي وي", pf) + 60
    d.rounded_rectangle((x0 - wa - wb + 10, 230, x0 - wa - wb + 10 + pw_, 292), 10, fill=(240, 80, 80))
    rtl(d, (x0 - wa - wb + 10 + pw_ / 2, 261), "بسرام ټي وي", pf, WHITE, "mm")
    lg = logo_clean(170)
    img.alpha_composite(lg, (40, 40))

    tf, tl = fit(d, title, HEAD, [76, 68, 62, 56], W - 140, 3)
    y = H - 210 - len(tl) * int(tf.size * 1.25)
    for i, ln in enumerate(tl):
        rtl(d, (W - 70, y), ln, tf, RED if i == len(tl) - 1 and len(tl) > 1 else WHITE)
        y += int(tf.size * 1.25)
    if source:
        rtl(d, (70, H - 175), "انځور: " + source, font(BODY, 24), (190, 200, 220), "la")
    social_row(d, H - 95, WHITE, handle, x_right=W - 70, size=28)
    rtl(d, (W / 2, H - 40), today(), font(BODY, 24), (170, 190, 220), "mm")
    return img.convert("RGB")


# ---------- ۱۰: خبرپاڼه ----------
def style10(title, summary, handle, photo, source):
    img = Image.composite(Image.new("RGB", (W, H), (20, 90, 180)), Image.new("RGB", (W, H), (60, 160, 240)),
                          Image.linear_gradient("L").resize((W, H))).convert("RGBA")
    d = ImageDraw.Draw(img)
    lg = logo_clean(190)
    img.alpha_composite(lg, (W - 60 - lg.width, 28))
    d.rounded_rectangle((60, 46, 440, 104), 12, fill=WHITE)
    d.text((86, 75), handle, font=font(LATIN, 28), fill=INK, anchor="lm")
    d.ellipse((396, 60, 420, 84), outline=INK, width=3)
    d.line((416, 80, 428, 92), fill=INK, width=4)

    sx1, sy1, sx2, sy2 = 70, 140, W - 70, H - 95
    shadow_box(img, (sx1, sy1, sx2, sy2), 0, 26, 110, (0, 18))
    d.rectangle((sx1, sy1, sx2, sy2), fill=WHITE)
    # د پاڼې اوښتی کونج (ښي پاس)
    c = 150
    d.polygon([(sx2 - c, sy1), (sx2, sy1), (sx2, sy1 + c)], fill=(20, 90, 180))
    d.polygon([(sx2 - c, sy1), (sx2, sy1 + c), (sx2 - c + 10, sy1 + c - 10)], fill=(225, 228, 232))
    d.line((sx2 - c, sy1, sx2, sy1 + c), fill=(200, 205, 212), width=2)

    y = sy1 + 50
    rtl(d, (sx2 - c - 20, y), "خبرپاڼه", font(BODY, 28), INK)
    d.text((sx1 + 45, y + 4), today(), font=font(BODY, 26), fill=INK, anchor="la",
           direction="rtl", language="ps")
    y += 52
    d.line((sx1 + 45, y, sx2 - 45, y), fill=INK, width=4)
    d.line((sx1 + 45, y + 10, sx2 - 45, y + 10), fill=INK, width=2)
    rtl(d, (W / 2, y + 18), "بسرام خبرونه", font(HEAD, 92), INK, "ma")
    y += 150
    d.line((sx1 + 45, y, sx2 - 45, y), fill=INK, width=3)

    pw = sx2 - sx1 - 90
    tf0, tl0 = fit(d, title, HEAD, [48, 44, 40], pw, 2)
    ph = 340 if len(tl0) == 1 else 300
    py = y + 26
    pic = cover(photo, pw, ph) if photo else placeholder(pw, ph)
    img.paste(pic, (sx1 + 45, py))
    d.rounded_rectangle((sx1 + 45, py + ph + 6, sx1 + 45 + pw, py + ph + 24), 9, outline=INK, width=3)
    if source:
        rtl(d, (sx1 + 60, py + ph - 14), source, font(BODY, 20), WHITE, "ld")

    y = py + ph + 44
    tf, tl = fit(d, title, HEAD, [48, 44, 40], pw, 2)
    for ln in tl:
        rtl(d, (sx2 - 45, y), ln, tf, INK)
        y += int(tf.size * 1.3)
    room = (sy2 - 30) - (y + 4)
    if summary and room > 34:
        n = max(1, int(room // int(26 * 1.45)))
        sf, sl = fit(d, summary, TEXT, [26, 24], pw, min(3, n))
        para(d, sl, sf, sx2 - 45, y + 4, (60, 65, 80), 0)

    social_row(d, H - 48, WHITE, handle, x_right=W - 70, size=28)
    return img.convert("RGB")


DESIGNS = {6: style6, 7: style7, 8: style8, 9: style9, 10: style10}
