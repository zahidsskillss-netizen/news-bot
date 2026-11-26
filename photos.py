"""د هر خبر لپاره څو انځورونه: د خبر له پاڼې، او که کم وو، له Wikimedia Commons (وړیا، قانوني انځورونه)."""
import re

import requests

import bot

UA = {"User-Agent": "BisramTV-NewsBot/1.0 (https://t.me/bisramtv)"}
BAD = re.compile(r"nude|naked|erotic|sex|bikini|lingerie|alcohol|wine|beer|casino|tattoo|concert|"
                 r"logo|map|flag_of|coat_of_arms|diagram|chart|svg|icon|signature|document|scan", re.I)

KW_PROMPT = (
    "Give 2 short English image-search queries (2-4 words each) for real photos that illustrate this "
    "Pashto news story: the place, building, landscape, object or general topic (for example "
    "'Kabul city street', 'Amu Darya river', 'Afghanistan cricket stadium', 'wheat harvest Afghanistan'). "
    "Do NOT use names of people. One query per line, nothing else.\n\n"
)


def keywords(sg):
    try:
        out = bot._gemini(KW_PROMPT + f"{sg.get('title', '')}\n{sg.get('summary', '')[:500]}") if bot.GEMINI_KEY else ""
    except Exception as e:
        print("keywords AI:", e)
        out = ""
    qs = [re.sub(r"[^A-Za-z0-9 \-]", "", q).strip() for q in (out or "").splitlines()]
    return [q for q in qs if 2 < len(q) < 60][:2]


def commons(query, n=4):
    """Wikimedia Commons → د انځورونو URL (۱۶۰۰px)."""
    try:
        r = requests.get("https://commons.wikimedia.org/w/api.php", headers=UA, timeout=20, params={
            "action": "query", "format": "json", "generator": "search", "gsrnamespace": 6,
            "gsrsearch": f"{query} filetype:bitmap", "gsrlimit": 15,
            "prop": "imageinfo", "iiprop": "url|size|mime", "iiurlwidth": 1600})
        pages = sorted((r.json().get("query") or {}).get("pages", {}).values(), key=lambda p: p.get("index", 99))
    except Exception as e:
        print("commons:", e)
        return []
    out = []
    for p in pages:
        ii = (p.get("imageinfo") or [{}])[0]
        if BAD.search(p.get("title", "")) or ii.get("mime") not in ("image/jpeg", "image/png", "image/webp"):
            continue
        w, h = ii.get("width", 0), ii.get("height", 0)
        if w < 900 or h < 500 or not (1.1 < w / max(1, h) < 2.4):      # پراخ (landscape) انځورونه
            continue
        out.append(ii.get("thumburl") or ii.get("url"))
        if len(out) >= n:
            break
    return out


def _ahash(im):
    import numpy as np
    a = np.asarray(im.convert("L").resize((12, 12)), dtype=np.float32)
    return (a > a.mean()).flatten()


def gather(sg, want=4):
    """د یوه خبر انځورونه (PIL) — لومړی د خبر خپل، بیا Commons. ورته انځورونه نه تکرارېږي."""
    urls = [u for u in ([sg.get("img")] + list(sg.get("imgs") or [])) if u]
    ims, hashes = [], []

    def add(url, referer=None):
        im = bot.download_image([url], referer=referer)
        if im is None or im.width < 400:
            return
        h = _ahash(im)
        if any((h != x).mean() < 0.12 for x in hashes):          # همغه انځور په بل اندازه
            return
        hashes.append(h)
        ims.append(im)

    for u in dict.fromkeys(urls):
        if len(ims) >= want:
            break
        add(u, sg.get("link"))
    if len(ims) < 3:
        for q in keywords(sg):
            for u in commons(q):
                if len(ims) >= want:
                    break
                add(u)
            if len(ims) >= want:
                break
    print(f"  🖼️ {len(ims)} انځورونه: {sg.get('title', '')[:40]}")
    return ims
