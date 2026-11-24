"""
فیسبوک پاڼې ته اتومات نشر.
د فیسبوک معلومات په fb_secret.enc کې کوډ شوي (encrypted) دي؛ کیلي یې د روباټ Token دی
چې یوازې په GitHub Secrets کې شته، نو په Public repo کې هم خوندي دي.
"""
import base64
import hashlib
import json
import os

import requests
from cryptography.fernet import Fernet, InvalidToken

HERE = os.path.dirname(os.path.abspath(__file__))
SECRET_FILE = os.path.join(HERE, "fb_secret.enc")   # App ID, App Secret, User Token
PAGE_FILE = os.path.join(HERE, "fb_page.enc")       # د پاڼې دایمي Token (پخپله جوړېږي)
API = "https://graph.facebook.com/v23.0"


def _fernet(key_source):
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(key_source.encode()).digest()))


def encrypt_to(path, data, key_source):
    with open(path, "wb") as f:
        f.write(_fernet(key_source).encrypt(json.dumps(data).encode()))


def _decrypt(path, key_source):
    try:
        with open(path, "rb") as f:
            return json.loads(_fernet(key_source).decrypt(f.read()))
    except (FileNotFoundError, InvalidToken, ValueError):
        return None


def get_page(key_source, page_name=""):
    """(page_id, page_token, page_name) ورکوي، یا None."""
    page = _decrypt(PAGE_FILE, key_source)
    if page:
        return page["id"], page["token"], page.get("name", "")

    sec = _decrypt(SECRET_FILE, key_source)
    if not sec:
        return None
    # ۱) لنډمهاله Token → اوږدمهاله
    r = requests.get(f"{API}/oauth/access_token", params={
        "grant_type": "fb_exchange_token", "client_id": sec["app_id"],
        "client_secret": sec["app_secret"], "fb_exchange_token": sec["user_token"]}, timeout=30).json()
    long_token = r.get("access_token")
    if not long_token:
        print(f"❌ فیسبوک: Token بدل نه شو: {(r.get('error') or {}).get('message')}")
        return None
    # ۲) د پاڼې دایمي Token
    r = requests.get(f"{API}/me/accounts", params={
        "access_token": long_token, "fields": "id,name,access_token", "limit": 100}, timeout=30).json()
    pages = r.get("data") or []
    if not pages:
        print(f"❌ فیسبوک: هېڅ پاڼه پیدا نه شوه: {(r.get('error') or {}).get('message', '')}")
        return None
    print("📘 فیسبوک پاڼې: " + "، ".join(p["name"] for p in pages))
    chosen = next((p for p in pages if page_name and page_name.lower() in p["name"].lower()), pages[0])
    encrypt_to(PAGE_FILE, {"id": chosen["id"], "token": chosen["access_token"], "name": chosen["name"]}, key_source)
    print(f"✅ فیسبوک پاڼه وټاکل شوه: {chosen['name']}")
    return chosen["id"], chosen["access_token"], chosen["name"]


def reconnect(key_source, user_token, page_name=""):
    """نوی User Token → اوږدمهاله → د پاڼې نوی Token. (ok, پیغام) ورکوي."""
    sec = _decrypt(SECRET_FILE, key_source)
    if not sec:
        return False, "د App معلومات نشته"
    sec["user_token"] = user_token
    old_page = PAGE_FILE + ".bak"
    if os.path.exists(PAGE_FILE):
        os.replace(PAGE_FILE, old_page)
    encrypt_to(SECRET_FILE, sec, key_source)
    page = get_page(key_source, page_name)
    if not page:
        if os.path.exists(old_page):
            os.replace(old_page, PAGE_FILE)
        return False, "Token سم نه و، یا پاڼې ته اجازه نه وه ورکړل شوې"
    if os.path.exists(old_page):
        os.remove(old_page)
    return True, page[2]


def post_photo(page_id, token, image_path, caption):
    with open(image_path, "rb") as f:
        r = requests.post(f"{API}/{page_id}/photos",
                          data={"message": caption, "access_token": token},
                          files={"source": f}, timeout=90).json()
    if r.get("id"):
        return True
    print(f"  ❌ فیسبوک تېروتنه: {(r.get('error') or {}).get('message')}")
    return False
