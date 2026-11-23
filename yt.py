"""
یوټیوب: اجازه (OAuth Device flow — په موبایل اسانه) او د ویډیو اپلوډ.
ټول معلومات کوډ شوي (encrypted) ساتل کېږي؛ کیلي یې د روباټ Token دی.
"""
import json
import os
import time

import requests

import fb   # د کوډ کولو مرستندویه (encrypt_to / _decrypt)

HERE = os.path.dirname(os.path.abspath(__file__))
CLIENT_FILE = os.path.join(HERE, "yt_client.enc")   # Client ID + Secret
TOKEN_FILE = os.path.join(HERE, "yt_token.enc")     # Refresh token
SCOPE = "https://www.googleapis.com/auth/youtube"


def client(key):
    return fb._decrypt(CLIENT_FILE, key)


def connected(key):
    return bool(fb._decrypt(TOKEN_FILE, key))


def start_device(key):
    c = client(key)
    if not c:
        return None
    r = requests.post("https://oauth2.googleapis.com/device/code",
                      data={"client_id": c["client_id"], "scope": SCOPE}, timeout=30).json()
    if "device_code" not in r:
        raise RuntimeError(r)
    r["started"] = time.time()
    return r


def poll_device(key, dev):
    """که زاهد اجازه ورکړې وي، Token ساتي → True؛ انتظار → None؛ پای → False."""
    c = client(key)
    if time.time() - dev.get("started", 0) > dev.get("expires_in", 1800):
        return False
    r = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": c["client_id"], "client_secret": c["client_secret"],
        "device_code": dev["device_code"],
        "grant_type": "urn:ietf:params:oauth:grant-type:device_code"}, timeout=30).json()
    if r.get("refresh_token"):
        fb.encrypt_to(TOKEN_FILE, {"refresh_token": r["refresh_token"]}, key)
        return True
    if r.get("error") in ("authorization_pending", "slow_down"):
        return None
    print("YouTube auth:", r)
    return False


def access_token(key):
    c, t = client(key), fb._decrypt(TOKEN_FILE, key)
    r = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": c["client_id"], "client_secret": c["client_secret"],
        "refresh_token": t["refresh_token"], "grant_type": "refresh_token"}, timeout=30).json()
    if "access_token" not in r:
        raise RuntimeError(f"YouTube token: {r}")
    return r["access_token"]


def upload(key, path, title, description, tags, privacy="public", thumb=None):
    tok = access_token(key)
    meta = {"snippet": {"title": title[:100], "description": description[:4900],
                        "tags": tags[:30], "categoryId": "25", "defaultLanguage": "ps",
                        "defaultAudioLanguage": "ps"},
            "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False}}
    size = os.path.getsize(path)
    r = requests.post("https://www.googleapis.com/upload/youtube/v3/videos",
                      params={"uploadType": "resumable", "part": "snippet,status"},
                      headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json",
                               "X-Upload-Content-Type": "video/mp4",
                               "X-Upload-Content-Length": str(size)},
                      data=json.dumps(meta), timeout=60)
    r.raise_for_status()
    url = r.headers["Location"]
    with open(path, "rb") as f:
        r = requests.put(url, data=f, headers={"Content-Type": "video/mp4"}, timeout=1800)
    r.raise_for_status()
    vid = r.json()["id"]
    if thumb:
        try:
            with open(thumb, "rb") as f:
                t = requests.post("https://www.googleapis.com/upload/youtube/v3/thumbnails/set",
                                  params={"videoId": vid}, headers={"Authorization": f"Bearer {tok}",
                                                                    "Content-Type": "image/jpeg"},
                                  data=f.read(), timeout=120)
            if t.status_code != 200:
                print("thumbnail:", t.status_code, t.text[:200])
        except Exception as e:
            print("thumbnail error:", e)
    return vid, r.json().get("status", {}).get("privacyStatus")
