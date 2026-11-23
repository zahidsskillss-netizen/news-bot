"""د هرې سرچینې د انځور ازموینه (نشر نه کوي)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import feedparser, requests, bot
for name, url in bot.load_feeds():
    f = feedparser.parse(requests.get(url, headers=bot.UA, timeout=30).content)
    for e in f.entries[:3]:
        _, imgs = bot.page_info(e.get("link"))
        im = bot.download_image(imgs + [bot.find_image(e)], referer=e.get("link"))
        print("IMG", name, "|", (e.get("title") or "")[:40], "|", len(imgs), "|", im.size if im else None)
