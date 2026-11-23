"""د ۶–۱۰ ډیزاینونو ازموینه: د ورځې ۵ تازه خبرونه، هر یو په یو ډیزاین کې (نشر نه کېږي)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import feedparser, requests
import bot
from card_designs import DESIGNS

items = []
for name, url in bot.load_feeds():
    try:
        f = feedparser.parse(requests.get(url, headers=bot.UA, timeout=30).content)
        for e in f.entries[:6]:
            if bot.is_news(e):
                items.append((name, e))
    except Exception as ex:
        print("feed fail", name, ex)
os.makedirs("preview", exist_ok=True)
n = 6
for name, e in items:
    if n > 10:
        break
    link = e.get("link")
    title = bot.clean_text(e.get("title", ""), 200)
    summary = bot.clean_text(e.get("summary", ""))
    desc, img = bot.page_info(link)
    if len(summary) < 40:
        summary = desc or summary
    photo = bot.download_image(img or bot.find_image(e))
    r = bot.ai_rewrite(title, summary)
    if not r or isinstance(r, str):
        print("skip", title[:40], r)
        continue
    t, s, _ = r
    DESIGNS[n](t, s, "t.me/bisramtv", photo, name).save(f"preview/design_{n}.jpg", quality=92)
    print("ok", n, t)
    n += 1
