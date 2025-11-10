import requests
import feedparser
import re
import os
import json
import time
import asyncio
import threading
import http.server
import socketserver
from bs4 import BeautifulSoup
from datetime import datetime
from telegram.ext import ApplicationBuilder, CommandHandler

def keep_alive():
    PORT = 8080
    Handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        httpd.serve_forever()

threading.Thread(target=keep_alive, daemon=True).start()

BOT_TOKEN = "8574839052:AAF-DXQhtnXeY3r2Oc8oiz1WiDA1Hru7EPI"  # вставь сюда токен
CHAT_ID = "1400522756"

RSS_OR_SEARCH_URLS = [
    "https://www.olx.ua/uk/list/q-lego%20lord%20of%20rings/?min_id=905847219",
    "https://www.olx.ua/uk/detskiy-mir/igrushki/konstruktory/q-lego%20%D1%87%D0%B5%D0%BB%D0%BE%D0%B2%D0%B5%D1%87%D0%BA%D0%B8/",
    "https://www.olx.ua/uk/list/q-lego%20%D1%85%D0%BE%D0%B1%D0%B1%D0%B8%D1%82/",
    "https://www.olx.ua/uk/list/q-lego%20hobbit/",
    "https://www.olx.ua/uk/list/q-lego%20%D0%B2%D0%BB%D0%B0%D1%81%D1%82%D0%B5%D0%BB%D0%B8%D0%BD%20%D0%BA%D0%BE%D0%BB%D0%B5%D1%86/",
    "https://www.olx.ua/uk/detskiy-mir/igrushki/konstruktory/q-lego%20%D0%BC%D0%B8%D0%BD%D1%96%D1%84%D1%96%D0%B3%D1%83%D1%80%D0%BA%D0%B8/"
]

KEYWORDS = [
    "lord of the rings", "the hobbit", "lotr", "hobbit", "rings", "tolkien",
    "aragorn", "gandalf", "legolas", "frodo", "sam", "sauron", "saruman",
    "орки", "гобіт", "володар", "перснів", "смауг", "мордoр"
]

MIN_PRICE = None
MAX_PRICE = None
CHECK_INTERVAL = 60
STATE_FILE = "seen.json"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

def load_seen():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()

def save_seen(seen):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(list(seen), f, ensure_ascii=False)

def send_telegram(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "disable_web_page_preview": False}
    try:
        r = requests.post(url, data=payload, timeout=10)
        return r.ok
    except Exception as e:
        print("Telegram send error:", e)
        return False

def log_to_telegram(message):
    send_telegram(f"⚠️ Лог бота:\n{message}")

async def start(update, context):
    await update.message.reply_text("👋 Привіт! Бот запущений і моніторить оголошення на OLX.")

async def check_status(update, context):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="🤖 Бот активний та працює стабільно!")

def entry_passes_filters(title, price):
    s = title.lower()
    if MIN_PRICE and price and price < MIN_PRICE:
        return False
    if MAX_PRICE and price and price > MAX_PRICE:
        return False
    return any(k.lower() in s for k in KEYWORDS)

def try_rss_parse(url):
    feed = feedparser.parse(url)
    items = []
    if feed and getattr(feed, "entries", None):
        for e in feed.entries:
            uid = e.get("id") or e.get("link")
            title = e.get("title", "")
            link = e.get("link", "")
            summary = e.get("summary", "")
            price = None
            m = re.search(r"(\d[\d\s,]*)\s*грн", (title + " " + summary))
            if m:
                price = int(re.sub(r"[^\d]", "", m.group(1)))
            items.append({"id": uid, "title": title, "link": link, "price": price})
    return items

def parse_html_search(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")
        ads = []
        for a in soup.select('a[href*="/d/"]'):
            link = a.get('href')
            title = a.get_text(separator=" ", strip=True)
            if not link or not title:
                continue
            if link.startswith("/"):
                link = "https://www.olx.ua" + link
            uid = link
            price = None
            cont = a.find_parent()
            text_block = cont.get_text(" ", strip=True) if cont else title
            m = re.search(r"(\d[\d\s,]*)\s*грн", text_block)
            if m:
                price = int(re.sub(r"[^\d]", "", m.group(1)))
            ads.append({"id": uid, "title": title, "link": link, "price": price})
        unique = {item['id']: item for item in ads if item['id']}
        return list(unique.values())
    except Exception as e:
        log_to_telegram(f"HTML parse error: {e}")
        return []

def format_message(item):
    t = item.get("title") or "Без назви"
    p = item.get("price")
    pr = f"{p} грн" if p else "Ціна не вказана"
    l = item.get("link")
    pub = datetime.now().strftime("%Y-%m-%d %H:%M")
    return f"{t}\n{pr}\n{l}\n{pub}"

async def monitor_loop():
    send_telegram("🚀 OLX-бот запущений і працює.")
    seen = load_seen()
    print("🔍 Моніторинг запущено...")

    while True:
        try:
            for url in RSS_OR_SEARCH_URLS:
                print(f"Перевіряю: {url}")
                items = try_rss_parse(url)
                if not items:
                    items = parse_html_search(url)
                for it in items:
                    uid = it.get("id") or it.get("link")
                    if not uid or not entry_passes_filters(it.get("title", ""), it.get("price")):
                        continue
                    if uid not in seen:
                        msg = format_message(it)
                        if send_telegram(msg):
                            seen.add(uid)
                            print("✅ Відправлено:", it.get("title"))
                        else:
                            log_to_telegram(f"❌ Помилка відправки: {it.get('title')}")
                save_seen(seen)
        except Exception as e:
            log_to_telegram(f"Main loop error: {e}")
        await asyncio.sleep(CHECK_INTERVAL)

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", check_status))

    asyncio.create_task(monitor_loop())
    print("✅ Telegram bot started.")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
