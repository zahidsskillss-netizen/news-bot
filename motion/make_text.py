"""د ۳D صحنو لپاره پښتو متن انځورونه (Blender پښتو توري نه شي جوړولای)."""
import os, sys
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

def text_png(text, font, size, out, color=(255, 255, 255, 255), pad=40):
    f = ImageFont.truetype(os.path.join(ROOT, "assets", font), size)
    d = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    rtl = any("؀" <= c <= "ۿ" for c in text)
    kw = dict(direction="rtl", language="ps") if rtl else {}
    b = d.textbbox((0, 0), text, font=f, **kw)
    im = Image.new("RGBA", (b[2] - b[0] + pad * 2, b[3] - b[1] + pad * 2), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((pad - b[0], pad - b[1]), text, font=f, fill=color, **kw)
    im.save(out)
    return im.size

if __name__ == "__main__":
    A = os.path.join(HERE, "assets")
    print(text_png("د ورځې خبرونه", "GhoraMarhey.ttf", 220, os.path.join(A, "t_daily.png")))
    print(text_png("زموږ چینل سبسکرایب کړئ", "GhoraMarhey.ttf", 170, os.path.join(A, "t_sub.png")))
    print(text_png("t.me/bisramtv", "Vazirmatn-Bold.ttf", 130, os.path.join(A, "t_handle.png")))
    print(text_png("SUBSCRIBE", "Vazirmatn-ExtraBold.ttf", 150, os.path.join(A, "t_subscribe.png")))
    print(text_png("مننه چې زموږ سره یاست", "GhoraMessiri.ttf", 130, os.path.join(A, "t_thanks.png")))
    print(text_png("عاجل", "GhoraMarhey.ttf", 200, os.path.join(A, "t_ajel.png")))
