"""
د خبرونو اتومات روباټ — Ghora Graphics
له RSS فیډونو تازه خبرونه راټولوي او په ټلګرام چینل کې یې خپروي.
"""
import html
import json
import os
import re
import sys
import time
from datetime import datetime, timezone

import feedparser
import requests

from card import make_card
import fb

_CFG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
try:
    with open(_CFG_PATH, encoding="utf-8") as _f:
        _CFG = json.load(_f)
except (FileNotFoundError, json.JSONDecodeError):
    _CFG = {}


def setting(name):
    """لومړی GitHub Secrets، که نه وي نو config.json"""
    return (os.environ.get(name) or _CFG.get(name) or "").strip()


TOKEN = setting("TELEGRAM_BOT_TOKEN")
CHANNEL = setting("TELEGRAM_CHANNEL")          # لکه: @mynewschannel
SIGNATURE = setting("CHANNEL_SIGNATURE")       # د هر پوسټ په پای کې (اختیاري)
CARD_STYLE = setting("CARD_STYLE") or "1"   # 1-5، یا "auto" چې هر ځل بدل شي
FB_PAGE_NAME = setting("FB_PAGE_NAME")         # که څو پاڼې لرئ، د پاڼې نوم
HANDLE = setting("CARD_HANDLE") or ("t.me/" + CHANNEL.lstrip("@") if CHANNEL else "")  # پر کارت لیکل کېږي
MAX_PER_RUN = int(os.environ.get("MAX_PER_RUN", "5") or 5)        # په هر ځل څو خبرونه
GEMINI_KEY = setting("GEMINI_API_KEY")         # اختیاري: د AI لنډیز/ژباړې لپاره
GEMINI_MODELS = [m for m in [setting("GEMINI_MODEL"), "gemini-flash-latest", "gemini-3.8-flash", "gemini-flash-lite-latest"] if m]
DRY_RUN = os.environ.get("DRY_RUN") == "1"                        # یوازې ازموینه، نشر نه کوي

HERE = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(HERE, "posted.json")
FEEDS_FILE = os.path.join(HERE, "feeds.txt")
UA = {"User-Agent": "Mozilla/5.0 (GhoraNewsBot)"}


# ---------- مرستندویه ----------
def load_feeds():
    feeds = []
    with open(FEEDS_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "|" not in line:
                continue
            name, url = [p.strip() for p in line.split("|", 1)]
            feeds.append((name, url))
    return feeds


def load_state():
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"posted": []}


def save_state(state):
    state["posted"] = state["posted"][-3000:]
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=0)


def clean_text(raw, limit=350):
    text = re.sub(r"<[^>]+>", " ", raw or "")
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > limit:
        cut = text[:limit].rsplit(" ", 1)[0]
        text = cut + "…"
    return text


def find_image(entry):
    for key in ("media_content", "media_thumbnail"):
        for m in entry.get(key, []) or []:
            if m.get("url"):
                return m["url"]
    for enc in entry.get("enclosures", []) or []:
        if (enc.get("type") or "").startswith("image") and enc.get("href"):
            return enc["href"]
    texts = [entry.get("summary", "") or ""] + [c.get("value", "") for c in entry.get("content", []) or []]
    for tx in texts:
        m = re.search(r'<img[^>]+src=["\']([^"\']+)', tx)
        if m:
            return m.group(1)
    return None


def is_news(entry):
    """راډیويي/ویډیويي پروګرامونه او ډېر لنډ سرلیکونه پرېږدي."""
    for enc in entry.get("enclosures", []) or []:
        if (enc.get("type") or "").startswith(("audio", "video")):
            return False
    link = entry.get("link", "") or ""
    if any(x in link for x in ("/av/", "/audio/", "/video/", "/z/", "/podcast")):
        return False
    title = entry.get("title", "")
    if any(x in title for x in ("درسي ساعت", "د درس ساعت", "درس ساعت", "خبري ګړۍ", "ورځني خبرونه", "خبرونه -", "پروګرام")):
        return False
    return len(title.split()) >= 4


def _meta_tags(t):
    """د پاڼې ټول <meta> ټګونه (د خاصیتونو ترتیب هر ډول چې وي)."""
    out = {}
    for tag in re.findall(r"<meta\s[^>]*>", t, re.I):
        attrs = dict((k.lower(), v) for k, _, v in re.findall(r'([\w:-]+)\s*=\s*(["\'])(.*?)\2', tag))
        key = (attrs.get("property") or attrs.get("name") or "").lower()
        if key and "content" in attrs and key not in out:
            out[key] = html.unescape(attrs["content"])
    return out


def page_info(url):
    """د خبر له پاڼې لنډیز او انځورونه راخلي → (desc, [image urls])."""
    desc, imgs = "", []
    try:
        t = requests.get(url, headers=UA, timeout=20).text
        meta = _meta_tags(t)
        for k in ("og:description", "description", "twitter:description"):
            if meta.get(k):
                desc = clean_text(meta[k])
                break
        for k in ("og:image", "og:image:url", "og:image:secure_url", "twitter:image", "twitter:image:src"):
            if meta.get(k) and meta[k] not in imgs:
                imgs.append(meta[k])
        # د مقالې لومړی لوی انځور (که meta نه وي)
        for src in re.findall(r'<img[^>]+(?:data-src|src)=["\']([^"\']+\.(?:jpe?g|png|webp)[^"\']*)', t, re.I)[:6]:
            if not any(x in src.lower() for x in ("logo", "icon", "avatar", "banner", "ads")):
                imgs.append(requests.compat.urljoin(url, src))
    except Exception as e:
        print(f"  ⚠️ پاڼه خلاصه نه شوه: {e}")
    return desc, imgs


def download_image(urls, referer=None):
    """له لیست څخه لومړی سم انځور راښکته کوي؛ که ونه شو، None."""
    from io import BytesIO
    from PIL import Image
    if isinstance(urls, str):
        urls = [urls]
    headers = dict(UA)
    if referer:
        headers["Referer"] = referer
    for url in [u for u in urls if u]:
        try:
            r = requests.get(url, headers=headers, timeout=25)
            r.raise_for_status()
            im = Image.open(BytesIO(r.content)).convert("RGB")
            if im.width >= 250 and im.height >= 150:
                return im
        except Exception as e:
            print(f"  ⚠️ انځور راښکته نه شو: {str(e)[:80]}")
    print("  🖼️ انځور پیدا نه شو")
    return None


CRICKET_WORDS = ("کرکټ", "کریکټ", "کرېکټ", "کرکټ", "cricket", "ICC", "ACB", "T20", "ټي-ټوینټي",
                 "ټي ټوینټي", "ورلډ کپ", "نړیوال جام", "راشد خان", "نبي", "ګرباز", "ابراهیم زدران",
                 "اکرم", "لوبډله", "ویکټ", "منډې")


def is_cricket(entry):
    text = (entry.get("title", "") + " " + entry.get("summary", ""))[:600]
    return any(w.lower() in text.lower() for w in CRICKET_WORDS[:9]) or \
        sum(w in text for w in CRICKET_WORDS[9:]) >= 2


STOP = set("د په کې ته له او چې دې یې هم دا هغه یو پر سره څخه نه شو شوی شوې شوي کړ کړي کوي وايي ویل وویل "
             "یا تر باندې لپاره اړه کال ورځ نن".split())


def title_words(t):
    t = re.sub(r"[^\w\s]", " ", t or "")
    return {w for w in t.split() if len(w) > 1 and w not in STOP}


def is_duplicate(title, state):
    """که همدا خبر (له بلې سرچینې یا په بل ډول لیکل شوی) مخکې خپور شوی وي."""
    a = title_words(title)
    if len(a) < 2:
        return False
    for old in state.get("titles", [])[-250:]:
        b = set(old)
        if not b:
            continue
        common = len(a & b)
        if common / max(1, min(len(a), len(b))) >= 0.6 and common >= 2:
            return True
    return False


def remember_title(title, state):
    state.setdefault("titles", []).append(sorted(title_words(title)))
    state["titles"] = state["titles"][-400:]


def entry_time(entry):
    t = entry.get("published_parsed") or entry.get("updated_parsed")
    return time.mktime(t) if t else 0


# ---------- AI ----------
GH_TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()            # په GitHub Actions کې پخپله شته
GH_MODEL = os.environ.get("GH_MODEL", "openai/gpt-4.1-mini").strip()

PROMPT = (
    "ته د «بسرام ټي وي» خبري چینل لیکوال یې. لاندې خبر په بشپړه توګه په خپلو نویو ټکو او "
    "نوې جملې جوړښت سره په روانه، سمه پښتو کې بیا ولیکه. د اصلي متن جملې مه کاپي کوه. "
    "که خبر په بله ژبه وي، پښتو ته یې وژباړه. حقایق، نومونه او شمېرې مه بدلوه، "
    "هېڅ شی ورته مه زیاتوه، خپل نظر مه ورکوه، او د خبري اژانس نوم مه یادوه. "
    "د متن د نشتوالي یا کمښت په اړه هېڅ مه لیکه؛ یوازې له موجودو معلوماتو کار واخله.\n"
    "په دیني موضوعاتو کې درناوی وساته.\n"
    "همدارنګه وټاکه:\n"
    "- ډول: که دا ریښتینی خبر وي «خبر» ولیکه؛ که درس، پروګرام، اعلان، مرکه‌یي خپرونه، "
    "ورځنۍ لنډیز، سرګرمي یا بل شی وي «نه» ولیکه.\n"
    "- اسلامي: که خبر له اسلامي اصولو سره په ټکر کې وي (لکه شراب، قمار، فحشا، نڅا، کنسرټونه، د موسیقۍ محفلونه، نوې سندرې یا البومونه، "
    "بې‌حیا سرګرمي، یا د دین سپکاوی) «نامناسب» ولیکه، که نه «مناسب».\n"
    "- برخه: یوه کلمه — سیاست، اقتصاد، امنیت، ټولنه، کرکټ، سپورت، روغتیا، ټکنالوژي، نړۍ، نور.\n"
    "ځواب یوازې په دې بڼه ورکړه:\n"
    "ډول: خبر/نه\n"
    "اسلامي: مناسب/نامناسب\n"
    "برخه: ...\n"
    "سرلیک: (تر ۱۴ ټکو لنډ)\n"
    "لنډیز: (۲ یا ۳ لنډې جملې)\n\n"
)


def _parse(out):
    t = re.search(r"سرلیک\s*[:：]\s*(.+)", out)
    s = re.search(r"لنډیز\s*[:：]\s*(.+)", out, re.S)
    k = re.search(r"ډول\s*[:：]\s*(\S+)", out)
    i = re.search(r"اسلامي\s*[:：]\s*(\S+)", out)
    c = re.search(r"برخه\s*[:：]\s*(\S+)", out)
    if t and s:
        if k and "نه" in k.group(1):
            return "SKIP:خبر نه دی"
        if i and "نامناسب" in i.group(1):
            return "SKIP:اسلامي اصول"
        cat = c.group(1).strip("*") if c else ""
        return t.group(1).strip().strip("*"), s.group(1).strip().strip("*"), cat
    return None


def _github_models(prompt):
    r = requests.post(
        "https://models.github.ai/inference/chat/completions",
        headers={"Authorization": f"Bearer {GH_TOKEN}", "Content-Type": "application/json",
                 "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"},
        json={"model": GH_MODEL, "messages": [{"role": "user", "content": prompt}],
              "temperature": 0.7},
        timeout=60,
    )
    if r.status_code != 200 or not r.text.strip().startswith("{"):
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")
    return r.json()["choices"][0]["message"]["content"]


def _gemini(prompt):
    last = None
    for model in GEMINI_MODELS * 2:
        for cfg in ({"thinkingConfig": {"thinkingLevel": "low"}}, {}):
            try:
                r = requests.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                    headers={"x-goog-api-key": GEMINI_KEY, "Content-Type": "application/json"},
                    json={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": cfg},
                    timeout=50,
                )
            except requests.RequestException as e:
                last = f"{model}: {e.__class__.__name__}"
                break
            if r.status_code == 200:
                parts = r.json()["candidates"][0]["content"]["parts"]
                return "".join(p.get("text", "") for p in parts if not p.get("thought"))
            last = f"{model}: HTTP {r.status_code}: {r.text[:200]}"
            if r.status_code in (401, 403):
                raise RuntimeError(last)
            if r.status_code != 400:
                break
        time.sleep(3)
    raise RuntimeError(last)


def ai_rewrite(title, summary):
    """خبر په نویو ټکو بیا لیکي. که ناکام شي، None ورکوي."""
    prompt = PROMPT + f"سرلیک: {title}\nمتن: {summary}"
    for name, fn, ok in (("Gemini", _gemini, GEMINI_KEY),):
        if not ok:
            continue
        try:
            res = _parse(fn(prompt))
            if res:
                return res
            print(f"  ⚠️ {name}: ځواب سم نه و")
        except Exception as e:
            print(f"  ⚠️ {name} AI ناکام شو: {e}")
    return None


# ---------- ټلګرام ----------
def tg(method, data, files=None):
    url = f"https://api.telegram.org/bot{TOKEN}/{method}"
    for _ in range(3):
        r = requests.post(url, data=data, files=files, timeout=60)
        if files:
            for f in files.values():
                f.seek(0)
        res = r.json()
        if res.get("ok"):
            return True
        wait = (res.get("parameters") or {}).get("retry_after")
        if wait:
            time.sleep(int(wait) + 1)
            continue
        print(f"  ❌ ټلګرام تېروتنه ({method}): {res.get('description')}")
        return False
    return False


def fb_caption(title, summary, source=None):
    parts = [title]
    if summary:
        parts.append(summary)
    if source:
        parts.append(f"سرچینه: {source}")
    parts.append(f"📢 ټلګرام: {HANDLE}")
    return "\n\n".join(parts)


def build_message(title, summary, source=None, link=None):
    parts = [f"<b>{html.escape(title)}</b>"]
    if summary:
        parts.append(html.escape(summary))
    if source and link:
        parts.append(f"📰 سرچینه: {html.escape(source)}\n🔗 <a href=\"{html.escape(link)}\">بشپړ خبر</a>")
    if SIGNATURE:
        parts.append(html.escape(SIGNATURE))
    return "\n\n".join(parts)


def publish(text, card_path=None, image_url=None):
    if DRY_RUN:
        print("---- (DRY RUN) ----\n" + text + f"\n[کارت: {card_path}]\n")
        return True
    if card_path and len(text) <= 1024:
        with open(card_path, "rb") as f:
            if tg("sendPhoto", {"chat_id": CHANNEL, "caption": text, "parse_mode": "HTML"},
                  files={"photo": f}):
                return True
    if image_url and len(text) <= 1024:
        if tg("sendPhoto", {"chat_id": CHANNEL, "photo": image_url, "caption": text, "parse_mode": "HTML"}):
            return True
    return tg("sendMessage", {"chat_id": CHANNEL, "text": text, "parse_mode": "HTML",
                              "disable_web_page_preview": "true"})


FB = None


# ---------- اصلي کار ----------
def main():
    if not DRY_RUN and (not TOKEN or not CHANNEL):
        sys.exit("TELEGRAM_BOT_TOKEN او TELEGRAM_CHANNEL په Secrets کې ورکړئ.")

    if not DRY_RUN:
        me = requests.get(f"https://api.telegram.org/bot{TOKEN}/getMe", timeout=20).json()
        if not me.get("ok"):
            sys.exit(f"❌ د روباټ Token سم نه دی: {me.get('description')}")
        print(f"🤖 روباټ: @{me['result']['username']} | AI: {'هو' if GEMINI_KEY else 'نه'}")

    global FB
    FB = fb.get_page(TOKEN, FB_PAGE_NAME) if (TOKEN and not DRY_RUN) else None
    if FB:
        print(f"📘 فیسبوک: {FB[2]}")

    state = load_state()
    seen = set(state["posted"])
    first_run = not state["posted"]
    items = []

    for name, url in load_feeds():
        try:
            r = requests.get(url, headers=UA, timeout=30)
            r.raise_for_status()
            feed = feedparser.parse(r.content)
            print(f"✅ {name}: {len(feed.entries)} خبرونه")
        except Exception as e:
            print(f"⚠️ {name} راونه رسېد: {e}")
            continue
        for e in feed.entries:
            if not is_news(e):
                continue
            link = e.get("link") or e.get("id")
            if link and link not in seen:
                items.append((entry_time(e), name, e, link))

    # کرکټ ته لومړیتوب، بیا نوي خبرونه لومړی
    items.sort(key=lambda x: (is_cricket(x[2]), x[0]), reverse=True)
    to_post = items[:MAX_PER_RUN]
    print(f"\n🆕 نوي خبرونه: {len(items)} — اوس خپرېږي: {len(to_post)}")

    for _, name, e, link in reversed(to_post):         # زوړ لومړی، چې نوی په سر کې پاتې شي
        title = clean_text(e.get("title", ""), 200)
        if is_duplicate(title, state):
            print(f"  ♻️ دا خبر مخکې خپور شوی، پرېښودل شو: {title[:50]}")
            state["posted"].append(link)
            continue
        summary = clean_text(e.get("summary", ""))
        if summary == title:
            summary = ""
        page_desc, page_img = page_info(link)
        if len(summary) < 40:
            summary = page_desc or summary
        if not summary:
            print(f"  ⏭️ متن نه لري، پرېښودل شو: {title[:50]}")
            state["posted"].append(link)
            continue
        photo = download_image(page_img + [find_image(e)], referer=link)
        rewritten = ai_rewrite(title, summary)
        if isinstance(rewritten, str):          # خبر نه دی، یا له اسلامي اصولو سره سمون نه لري
            print(f"  ⏭️ پرېښودل شو ({rewritten[5:]}): {title[:50]}")
            state["posted"].append(link)
            continue
        if not rewritten:
            # AI نه وي نو د خبر ډول او اسلامي اصول نه شو کتلای — راتلونکي ځل بیا کوشش
            print(f"  ⏸️ AI ځواب ورنه کړ، وروسته: {title[:50]}")
            continue
        orig_title = title
        title, summary, category = rewritten
        if is_duplicate(title, state):
            print(f"  ♻️ ورته خبر مخکې خپور شوی، پرېښودل شو: {title[:50]}")
            state["posted"].append(link)
            continue
        n = len(state["posted"])
        style = (n % 5) + 1 if CARD_STYLE == "auto" else CARD_STYLE
        card_path = os.path.join("/tmp", f"card_{n}.jpg")
        # په متن کې سرچینه نشته؛ یوازې په انځور کې ډېر کوچنی نوم
        card = make_card(title, summary, HANDLE, card_path, style, photo=photo, source=name)
        ok = publish(build_message(title, summary), card_path=card)
        fb_text = fb_caption(title, summary)
        if ok and FB and not DRY_RUN:
            if fb.post_photo(FB[0], FB[1], card, fb_text):
                print("  📘 فیسبوک ته هم ولېږل شو")
        if ok:
            state["posted"].append(link)
            remember_title(orig_title, state)
            remember_title(title, state)
            save_state(state) if not DRY_RUN else None    # سمدستي ساتل، چې بیا خپور نه شي
            print(f"  📤 {title[:60]}")
        time.sleep(3)

    # پاتې زاړه خبرونه هم «لیدل شوي» ګڼو چې بیا را نه شي
    for _, _, _, link in items[MAX_PER_RUN:]:
        state["posted"].append(link)
    if first_run:
        print("ℹ️ لومړی ځل: یوازې تر ټولو تازه خبرونه خپاره شول.")

    state["last_run"] = datetime.now(timezone.utc).isoformat()
    if not DRY_RUN:
        save_state(state)


if __name__ == "__main__":
    main()
