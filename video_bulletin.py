"""
Bisram TV — سهارنی او ماښامنی ویډیويي خبري راپور (یوټیوب)

  python video_bulletin.py tick     هر ځل د خبرونو روباټ سره: ټلګرام ګوري، راپور چمتو کوي، Voice راټولوي
  python video_bulletin.py render   ویډیو جوړوي، یوټیوب ته یې پورته کوي او خبر ورکوي

د ټلګرام امرونه (یوازې مالک ته، @Tazakhabarbot کې):
  /start bisram   مالک ثبتول (یو ځل)
  /new            همدا اوس نوی راپور
  /status         څو برخې پاتې دي
  /redo 3         درېیمه برخه بیا ثبتول
  /build          چې ټولې ونه رسېږي هم، ویډیو جوړه کړه
  /cancel         اوسنی راپور لغوه
  /youtube        یوټیوب سره نښلول
"""
import json
import math
import os
import random
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone

import requests

import bot
import yt

HERE = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(HERE, "bulletin.json")      # یوازې tick یې لیکي
DONE_FILE = os.path.join(HERE, "bulletin_done.json")  # یوازې render یې لیکي
POSTED = os.path.join(HERE, "posted.json")
KEY = bot.TOKEN
N_NEWS = int(bot.setting("BULLETIN_NEWS") or 5)
SLOTS = {"morning": (7, 0, "سهارني"), "evening": (18, 0, "ماښامني")}
PS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
OWNER_CODE = "bisram"


def now_kabul():
    return datetime.now(timezone.utc) + timedelta(hours=4, minutes=30)


def ps_date(d=None):
    d = d or now_kabul()
    from card import PS_MONTHS
    return f"{d.day} {PS_MONTHS[d.month - 1]} {d.year}".translate(PS)


def load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save(st):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False, indent=1)


def tg(method, **data):
    files = data.pop("files", None)
    r = requests.post(f"https://api.telegram.org/bot{KEY}/{method}", data=data, files=files, timeout=60)
    return r.json()


def say(st, text, **kw):
    if st.get("owner"):
        return tg("sendMessage", chat_id=st["owner"], text=text, parse_mode="HTML", **kw)


# ---------------- د راپور چمتو کول ----------------
NARRATE = (
    "ته د «بسرام ټي وي» خبري ویاند لپاره متن لیکې. لاندې خبر د غږیز لوستلو لپاره "
    "په روانه، ساده او رسمي پښتو کې په ۴۰ تر ۶۵ ټکو کې ولیکه. جملې لنډې وي، چې په اسانۍ ولوستل شي. "
    "حقایق مه بدلوه، څه مه ورزیاتوه، خپل نظر مه ورکوه. یوازې متن ولیکه، بل هېڅ نه.\n\n"
)


def narration(item):
    text = f"سرلیک: {item['title']}\nمتن: {item.get('summary', '')}"
    try:
        out = bot._gemini(NARRATE + text) if bot.GEMINI_KEY else ""
        out = re.sub(r"[*#_]", "", out or "").strip()
        if 60 < len(out) < 900:
            return out
    except Exception as e:
        print("narration AI:", e)
    return f"{item['title']}. {item.get('summary', '')}"


def pick_news(hours=14):
    log = load(POSTED, {}).get("log", [])
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    fresh = [x for x in log if datetime.fromisoformat(x["t"]) >= since]
    fresh.sort(key=lambda x: (x.get("cat") == "کرکټ", bool(x.get("img")), x["t"]), reverse=True)
    out, seen = [], []
    for x in fresh:
        w = bot.title_words(x["title"])
        if any(len(w & s) / max(1, min(len(w), len(s))) >= 0.6 for s in seen):
            continue
        seen.append(w)
        out.append(x)
        if len(out) >= N_NEWS:
            break
    return out


def prepare(st, slot):
    items = pick_news()
    if len(items) < 2:
        say(st, "⚠️ د راپور لپاره کافي نوي خبرونه نشته (لږ تر لږه ۲ پکار دي).")
        return
    label = SLOTS.get(slot, (0, 0, ""))[2] or "ځانګړي"
    segs = []
    for i, it in enumerate(items):
        script = narration(it)
        if i == 0:
            script = (f"السلام علیکم! د بسرام ټي وي {label} خبرونو ته ښه راغلاست. "
                      f"نن {ps_date()} ده. لومړی خبر: ") + script
        if i == len(items) - 1:
            script += " دا وو د نن خبرونه. له موږ سره د ملګرتیا مننه، د الله په امان."
        segs.append({"title": it["title"], "script": script, "img": it.get("img"),
                     "source": it.get("source", ""), "cat": it.get("cat", "")})
    st["current"] = {"id": now_kabul().strftime("%Y%m%d-%H%M"), "slot": slot, "label": label,
                     "created": time.time(), "segs": segs, "voices": {}, "status": "waiting",
                     "redo": None}
    say(st, f"🎙️ <b>د بسرام ټي وي {label} ویډیويي خبرونه</b> — {ps_date()}\n\n"
            f"لاندې {len(segs)} برخې دي. هره برخه په <b>جلا Voice</b> کې ولولئ او د نمبر په ترتیب یې راولېږئ."
            f"\nکه یوه برخه بیا ثبتول غواړئ: <code>/redo 2</code>")
    for i, sg in enumerate(segs, 1):
        say(st, f"📰 <b>{str(i).translate(PS)}/{str(len(segs)).translate(PS)}</b> — {sg['title']}\n\n{sg['script']}")


# ---------------- ټلګرام: امرونه او Voice ----------------
def handle(st, msg):
    chat = msg.get("chat", {}).get("id")
    text = (msg.get("text") or "").strip()
    if text.startswith("/start"):
        if OWNER_CODE in text.lower() and not st.get("owner"):
            st["owner"] = chat
            say(st, "✅ تاسو د بسرام ټي وي د ویډیويي راپور مالک ثبت شوئ.\n"
                    "هره ورځ سهار ۷ او ماښام ۶ بجې به د خبرونو متن درته راشي.\n"
                    "همدا اوس د ازموینې لپاره: /new")
        return
    if chat != st.get("owner"):
        return
    cur = st.get("current")
    if text == "/new":
        prepare(st, "manual")
    elif text == "/status":
        if not cur:
            say(st, "اوس هېڅ راپور روان نه دی. نوی: /new")
        else:
            got = sorted(int(k) for k in cur["voices"])
            miss = [i for i in range(1, len(cur["segs"]) + 1) if i not in got]
            say(st, f"وضعیت: {cur['status']}\nترلاسه: {got}\nپاتې: {miss or 'هېڅ'}")
    elif text.startswith("/redo"):
        m = re.search(r"\d+", text.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")))
        if cur and m and 1 <= int(m.group()) <= len(cur["segs"]):
            cur["redo"] = int(m.group())
            sg = cur["segs"][cur["redo"] - 1]
            say(st, f"🔁 د {cur['redo']} برخې نوی Voice راولېږئ:\n\n{sg['script']}")
    elif text == "/build":
        if cur and cur["voices"]:
            cur["status"] = "ready"
    elif text == "/cancel":
        st["current"] = None
        say(st, "❌ راپور لغوه شو.")
    elif text == "/youtube":
        try:
            dev = yt.start_device(KEY)
        except Exception as e:
            dev = None
            print("device:", e)
        if not dev:
            say(st, "⚠️ د یوټیوب Client لا نه دی ورکړل شوی، یا تېروتنه وشوه.")
        else:
            st["yt_device"] = dev
            say(st, f"🔑 <b>یوټیوب سره نښلول</b>\n\n۱. دا لینک خلاص کړئ: {dev['verification_url']}\n"
                    f"۲. دا کوډ ولیکئ: <code>{dev['user_code']}</code>\n"
                    f"۳. د یوټیوب چینل Gmail وټاکئ او <b>Allow</b> ووهئ.\n\n"
                    f"(که «Google hasn't verified this app» ولیکل شو: Advanced ← Go to Bisram News)")
    elif (msg.get("voice") or msg.get("audio")) and cur and cur["status"] == "waiting":
        f = msg.get("voice") or msg.get("audio")
        n = len(cur["segs"])
        idx = cur.pop("redo", None) or next((i for i in range(1, n + 1) if str(i) not in cur["voices"]), None)
        cur["redo"] = None
        if not idx:
            say(st, "ټولې برخې دمخه ترلاسه شوې. د بیا ثبتولو لپاره: /redo 2")
            return
        cur["voices"][str(idx)] = {"file_id": f["file_id"], "dur": f.get("duration", 0)}
        left = [i for i in range(1, n + 1) if str(i) not in cur["voices"]]
        if left:
            say(st, f"✅ {str(idx).translate(PS)} برخه ترلاسه شوه. اوس <b>{str(left[0]).translate(PS)}</b> برخه راولېږئ.")
        else:
            cur["status"] = "ready"
            say(st, "✅ ټولې برخې ترلاسه شوې! ویډیو جوړېږي… (۵ تر ۱۰ دقیقې)")


def tick():
    if not KEY:
        return
    st = load(STATE_FILE, {"offset": 0, "owner": None, "current": None, "done": []})
    res = tg("getUpdates", offset=st.get("offset", 0), timeout=0, allowed_updates='["message"]')
    if not res.get("ok"):
        print("getUpdates:", res)
        wh = tg("getWebhookInfo")
        print("webhook:", (wh.get("result") or {}).get("url"))
    else:
        print("updates:", len(res.get("result", [])))
    for u in res.get("result", []):
        st["offset"] = u["update_id"] + 1
        if u.get("message"):
            try:
                handle(st, u["message"])
            except Exception as e:
                print("handle error:", e)
    # یوټیوب اجازه
    dev = st.get("yt_device")
    if dev:
        try:
            ok = yt.poll_device(KEY, dev)
        except Exception as e:
            ok = None
            print("poll:", e)
        if ok:
            st["yt_device"] = None
            say(st, "✅ یوټیوب وصل شو! له اوس وروسته ویډیوګانې پخپله اپلوډ کېږي.")
        elif ok is False:
            st["yt_device"] = None
            say(st, "⚠️ د یوټیوب اجازې وخت تېر شو. بیا: /youtube")
    # سهار او ماښام
    k = now_kabul()
    for slot, (hh, mm, _) in SLOTS.items():
        tag = f"{k:%Y-%m-%d}-{slot}"
        start = k.replace(hour=hh, minute=mm, second=0, microsecond=0)
        if st.get("owner") and start <= k < start + timedelta(hours=2) and tag not in st.get("done", []):
            st.setdefault("done", []).append(tag)
            st["done"] = st["done"][-20:]
            cur = st.get("current")
            if cur and cur["status"] == "waiting" and cur["voices"]:
                say(st, "ℹ️ تېر راپور نیمګړی پاتې شو. نوی راپور راغی.")
            prepare(st, slot)
    cur = st.get("current")
    done = load(DONE_FILE, {})
    if cur and cur["id"] in done and cur["status"] != "done":
        cur["status"] = "done"
        cur["video"] = done[cur["id"]]
    if cur and cur["status"] == "ready":
        cur["status"] = "rendering"
        cur["render_started"] = time.time()
        save(st)
        subprocess.run(["gh", "workflow", "run", "bulletin.yml", "--ref", "main"], check=False)
    elif cur and cur["status"] == "rendering" and time.time() - cur.get("render_started", 0) > 3600:
        cur["status"] = "ready"     # که ودرېد، بیا هڅه
    save(st)


# ---------------- ویډیو جوړول ----------------
W, H, FPS = 1920, 1080, 30
WORK = "/tmp/bulletin"


def ff(*args):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args], check=True)


def dur(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                         capture_output=True, text=True).stdout.strip()
    return float(out or 0)


def tg_download(file_id, out):
    r = tg("getFile", file_id=file_id)
    path = r["result"]["file_path"]
    with open(out, "wb") as f:
        f.write(requests.get(f"https://api.telegram.org/file/bot{KEY}/{path}", timeout=120).content)
    return out


def write_rgba_clip(path, frames_fn, n):
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba",
                          "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "qtrle", path],
                         stdin=subprocess.PIPE)
    import numpy as np
    for i in range(n):
        p.stdin.write((np.clip(frames_fn(i / FPS), 0, 1) * 255).astype("uint8").tobytes())
    p.stdin.close()
    p.wait()


def segment(i, sg, voice_wav, photo, out):
    import numpy as np
    from PIL import Image
    import motion as m
    from card import cover
    vd = dur(voice_wav)
    D = round(vd + 1.4, 2)
    d = f"{WORK}/s{i}"
    os.makedirs(d, exist_ok=True)
    # شالید: انځور (cover) + لاندې تیاره + کیڼ پاس لوګو
    bgimg = cover(photo, int(W * 1.15), int(H * 1.15)) if photo else None
    if bgimg is None:
        g = Image.linear_gradient("L").resize((int(W * 1.15), int(H * 1.15)))
        bgimg = Image.composite(Image.new("RGB", g.size, (13, 71, 161)), Image.new("RGB", g.size, (33, 150, 243)), g)
    bgimg.save(f"{d}/bg.jpg", quality=93)
    yy = np.linspace(0, 1, H)[:, None]
    a = (np.clip((yy - 0.5) / 0.5, 0, 1) ** 1.6 * 200).astype("uint8")
    shade = np.zeros((H, W, 4), "uint8")
    shade[..., 3] = np.repeat(a, W, axis=1)
    over = Image.fromarray(shade, "RGBA")
    from card import logo_clean
    lg = logo_clean(250)
    over.alpha_composite(lg, (40, 30))
    over.save(f"{d}/over.png")
    # Lower third: ننوتل، درېدل، وتل
    lt = m.LowerThird(sg["title"], "تازه خبر", sub=f"سرچینه: {sg['source']}" if sg.get("source") else "Bisram TV")
    n_in = int(1.7 * FPS)
    write_rgba_clip(f"{d}/lt_in.mov", lambda t: lt.frame(t, 100), n_in)
    hold = (np.clip(lt.frame(1.8, 100), 0, 1) * 255).astype("uint8")
    Image.fromarray(hold, "RGBA").save(f"{d}/lt_hold.png")
    n_out = int(0.8 * FPS)
    write_rgba_clip(f"{d}/lt_out.mov", lambda t: lt.frame(10 - 0.8 + t, 10), n_out)
    # شاته موزیک (ډېر ورو)
    mus = f"{d}/music.wav"
    m.write_wav(mus, m.pad(D + 0.5, random.choice((98, 110, 123))) * 0.5)
    t_out = max(1.8, D - 0.8)
    dx = random.choice((-1, 1))
    xexpr = f"(iw-{W})/2+{dx}*(iw-{W})/2*(t/{D}-0.5)"
    flt = (
        f"[0:v]crop={W}:{H}:'{xexpr}':'(ih-{H})/2+(ih-{H})/4*(t/{D}-0.5)',fps={FPS},format=rgba[bg];"
        f"[bg][1:v]overlay=0:0[b1];"
        f"[b1][2:v]overlay=0:0:enable='lt(t,1.7)'[b2];"
        f"[b2][3:v]overlay=0:0:enable='between(t,1.7,{t_out})'[b3];"
        f"[4:v]setpts=PTS+{t_out}/TB[lo];[b3][lo]overlay=0:0:enable='gte(t,{t_out})':eof_action=pass[b4];"
        f"[b4]fade=t=in:st=0:d=0.3,fade=t=out:st={D - 0.3}:d=0.3,format=yuv420p[v];"
        f"[5:a]adelay=500|500,loudnorm=I=-16:TP=-1.5:LRA=11[va];[6:a]volume=0.10[mu];"
        f"[va][mu]amix=inputs=2:duration=longest:normalize=0,atrim=0:{D},afade=t=out:st={D - 0.4}:d=0.4[a]"
    )
    ff("-loop", "1", "-t", str(D), "-i", f"{d}/bg.jpg", "-loop", "1", "-t", str(D), "-i", f"{d}/over.png",
       "-i", f"{d}/lt_in.mov", "-loop", "1", "-t", str(D), "-i", f"{d}/lt_hold.png", "-i", f"{d}/lt_out.mov",
       "-i", voice_wav, "-i", mus, "-filter_complex", flt, "-map", "[v]", "-map", "[a]",
       "-t", str(D), "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-r", str(FPS),
       "-video_track_timescale", "15360",
       "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", out)
    return dur(out)


def normalize(src, out):
    ff("-i", src, "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},format=yuv420p",
       "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-video_track_timescale", "15360",
       "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", out)
    return dur(out)


def thumbnail(cur, photo, out):
    from PIL import Image, ImageDraw
    from card import cover, logo_clean, font, HEAD, tw, rtl, fit, shade
    TW, TH = 1280, 720
    img = (cover(photo, TW, TH) if photo else Image.new("RGB", (TW, TH), (13, 71, 161))).convert("RGBA")
    img.alpha_composite(shade(TW, 460, 0, 235), (0, TH - 460))
    d = ImageDraw.Draw(img)
    lg = logo_clean(260)
    img.alpha_composite(lg, (24, 18))
    lab = f"{cur['label']} خبرونه"
    f = font(HEAD, 92)
    w = tw(d, lab, f)
    d.rounded_rectangle((TW - 50 - w - 50, 40, TW - 50, 170), 18, fill=(229, 57, 53))
    rtl(d, (TW - 75, 104), lab, f, (255, 255, 255), "rm")
    tf, tl = fit(d, cur["segs"][0]["title"], HEAD, [74, 66, 58], TW - 100, 2)
    y = TH - 70 - len(tl) * int(tf.size * 1.25)
    for ln in tl:
        rtl(d, (TW - 50, y), ln, tf, (255, 255, 255))
        y += int(tf.size * 1.25)
    rtl(d, (TW - 50, TH - 60), ps_date(), font(HEAD, 40), (255, 202, 40))
    img.convert("RGB").save(out, quality=92)
    return out


def ts(sec):
    sec = int(sec)
    return f"{sec // 60:02d}:{sec % 60:02d}"


def render():
    import motion as m
    st = load(STATE_FILE, {})
    cur = st.get("current")
    if not cur or cur.get("status") not in ("rendering", "ready") or cur["id"] in load(DONE_FILE, {}):
        print("هېڅ راپور د جوړېدو لپاره نشته")
        return
    os.makedirs(WORK, exist_ok=True)
    say(st, "🎬 ویډیو جوړېږي…")
    parts, chapters, t = [], [], 0.0
    segs = [(i, sg) for i, sg in enumerate(cur["segs"], 1) if str(i) in cur["voices"]]
    photos = {}
    for i, sg in segs:
        photos[i] = bot.download_image([sg.get("img")]) if sg.get("img") else None
    # ۱) Intro: د لومړي خبر انځور په شین سکرین کې
    first_photo = next((photos[i] for i, _ in segs if photos.get(i)), None)
    m.studio_intro(first_photo, f"{WORK}/intro_raw.mp4")
    t += normalize(f"{WORK}/intro_raw.mp4", f"{WORK}/p0.mp4")
    parts.append(f"{WORK}/p0.mp4")
    chapters.append(("00:00", "پیل"))
    # ۲) هر خبر
    for i, sg in segs:
        ogg = tg_download(cur["voices"][str(i)]["file_id"], f"{WORK}/v{i}.ogg")
        wav = f"{WORK}/v{i}.wav"
        ff("-i", ogg, "-ar", "48000", "-ac", "2", wav)
        chapters.append((ts(t), sg["title"]))
        t += segment(i, sg, wav, photos.get(i), f"{WORK}/p{i}.mp4")
        parts.append(f"{WORK}/p{i}.mp4")
        print("segment", i, "ok")
    # ۳) Outro
    t += normalize(os.path.join(HERE, "assets", "outro.mp4"), f"{WORK}/pz.mp4")
    parts.append(f"{WORK}/pz.mp4")
    with open(f"{WORK}/list.txt", "w") as f:
        f.write("".join(f"file '{p}'\n" for p in parts))
    final = f"{WORK}/bisram_{cur['id']}.mp4"
    ff("-f", "concat", "-safe", "0", "-i", f"{WORK}/list.txt", "-c", "copy", "-movflags", "+faststart", final)
    thumb = thumbnail(cur, first_photo, f"{WORK}/thumb.jpg")

    # ۴) سرلیک، Description، Tags، Hashtags
    title = f"بسرام ټي وي | {cur['label']} خبرونه | {ps_date()} — {cur['segs'][0]['title']}"
    cats = {sg.get("cat") for _, sg in segs if sg.get("cat")}
    hashtags = ["#بسرام_ټي_وي", "#پښتو_خبرونه", "#افغانستان", "#تازه_خبرونه"] + \
               [f"#{c}" for c in cats if c and c != "نور"][:3]
    desc = (f"د بسرام ټي وي {cur['label']} خبرونه — {ps_date()}\n\n"
            "په دې خپرونه کې:\n" + "\n".join(f"{a} {b}" for a, b in chapters) +
            f"\n\n📢 ټلګرام: https://t.me/bisramtv\n📘 فیسبوک: Bisram TV\n\n"
            "زموږ چینل سبسکرایب کړئ او د زنګ تڼۍ ووهئ، چې هره ورځ تازه خبرونه ترلاسه کړئ.\n\n" +
            " ".join(hashtags))
    tags = ["بسرام ټي وي", "Bisram TV", "پښتو خبرونه", "افغانستان خبرونه", "تازه خبرونه", "Pashto news",
            "Afghanistan news", f"{cur['label']} خبرونه"] + [c for c in cats if c and c != "نور"]
    # ۵) اپلوډ
    link = None
    if yt.connected(KEY):
        try:
            vid, priv = yt.upload(KEY, final, title, desc, tags, "public", thumb)
            link = f"https://youtu.be/{vid}"
            note = "" if priv == "public" else \
                "\n\n⚠️ یوټیوب ویډیو Private کړه (پروژه لا تایید شوې نه ده). په YouTube Studio کې یې Public کړئ."
            say(st, f"✅ ویډیو یوټیوب ته پورته شوه:\n{link}{note}")
        except Exception as e:
            print("upload error:", e)
            say(st, f"⚠️ یوټیوب ته پورته نه شوه: {str(e)[:300]}")
    else:
        say(st, "ℹ️ یوټیوب لا وصل نه دی (/youtube). ویډیو درته دلته لېږم.")
    # ویډیو مالک ته (که له ۵۰MB کمه وي)
    if os.path.getsize(final) < 49 * 1024 * 1024:
        with open(final, "rb") as f:
            tg("sendVideo", chat_id=st["owner"], caption=title[:1000], supports_streaming="true",
               files={"video": f})
    else:
        small = f"{WORK}/small.mp4"
        ff("-i", final, "-vf", "scale=854:480", "-c:v", "libx264", "-preset", "veryfast", "-crf", "30",
           "-c:a", "aac", "-b:a", "96k", small)
        if os.path.getsize(small) < 49 * 1024 * 1024:
            with open(small, "rb") as f:
                tg("sendVideo", chat_id=st["owner"], caption="(کوچنۍ نسخه) " + title[:900],
                   supports_streaming="true", files={"video": f})
    # په چینل کې خبر
    if link:
        with open(thumb, "rb") as f:
            tg("sendPhoto", chat_id=bot.CHANNEL, caption=f"🎬 <b>{cur['label']} ویډیويي خبرونه</b> — {ps_date()}\n\n"
               f"▶️ {link}\n\n📢 @bisramtv", parse_mode="HTML", files={"photo": f})
    done = load(DONE_FILE, {})
    done[cur["id"]] = link
    with open(DONE_FILE, "w", encoding="utf-8") as f:
        json.dump(dict(list(done.items())[-30:]), f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "tick"
    {"tick": tick, "render": render}[cmd]()
