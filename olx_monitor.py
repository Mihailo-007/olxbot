import requests
import feedparser
import re
import os
import json
import requests
import feedparser
import re
import os
import json
import time
from bs4 import BeautifulSoup
from datetime import datetime
import threading
import http.server
import socketserver
from telegram.ext import Updater, CommandHandler

# 🔹 Простий веб-сервер (щоб Render не засинав)
def keep_alive():
    PORT = 8080
    Handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        httpd.serve_forever()

threading.Thread(target=keep_alive, daemon=True).start()

# 🔹 НАЛАШТУВАННЯ
BOT_TOKEN = "8574839052:AAF-DXQhtnXeY3r2Oc8oiz1WiDA1Hru7EPI"  # <--- СЮДИ ВСТАВ СВІЙ ТОКЕН
CHAT_ID = "1400522756"

# 🔹 Посилання для моніторингу
RSS_OR_SEARCH_URLS = [
    "https://www.olx.ua/uk/list/q-lego%20lord%20of%20rings/?min_id=905847219&reason=observed_search&search%5Border%5D=created_at%3Adesc",
    "https://www.olx.ua/uk/detskiy-mir/igrushki/konstruktory/q-%D0%BB%D0%B5%D0%B3%D0%BE%20%D1%87%D0%B5%D0%BB%D0%BE%D0%B2%D0%B5%D1%87%D0%BA%D0%B8/?currency=UAH&min_id=905749210&reason=observed_search&search%5Border%5D=relevance%3Adesc",
    "https://www.olx.ua/uk/list/q-lego%20%D1%85%D0%BE%D0%B1%D0%B1%D0%B8%D1%82/?min_id=905454579&reason=observed_search&search%5Border%5D=relevance%3Adesc",
    "https://www.olx.ua/uk/list/q-lego%20hobbit/?min_id=905836648&reason=observed_search&search%5Border%5D=relevance%3Adesc",
    "https://www.olx.ua/uk/list/q-lego%20%D0%B2%D0%BB%D0%B0%D1%81%D1%82%D0%B5%D0%BB%D0%B8%D0%BD%20%D0%BA%D0%BE%D0%BB%D0%B5%D1%86/?min_id=905107950&reason=observed_search&search%5Border%5D=relevance%3Adesc",
    "https://www.olx.ua/uk/detskiy-mir/igrushki/konstruktory/q-lego%20%D0%BC%D0%B8%D0%BD%D0%B8%D1%84%D0%B8%D0%B3%D1%83%D1%80%D0%BA%D0%B8/?min_id=905836648&reason=observed_search"
]

# 🔹 Ключові слова
KEYWORDS = [
    "lord of the rings", "the lord of the rings", "lotr", "rings", "ring",
    "hobbit", "the hobbit", "middle-earth", "middle earth", "tolkien",
    "gandalf", "frodo", "sam", "samwise", "merry", "pippin", "aragorn",
    "legolas", "gimli", "boromir", "elrond", "galadriel", "arwen", "saruman",
    "sauron", "gollum", "orc", "uruk hai", "balrog", "mordor", "shire",
    "rohan", "gondor", "rivendell", "mirkwood", "erebor", "smaug",
    "thorin", "bard", "beorn", "nazgul", "witch-king", "fellowship",
    "isengard", "minas tirith", "helm’s deep", "orthanc", "mount doom",

    "володар перснів", "перснів", "персня", "персні", "гобіт", "гобіти",
    "середзем’я", "гандальф", "фродо", "сем", "мирі", "піпін", "арагорн",
    "леголас", "ґімлі", "боромир", "ельронд", "галадріель", "арвен",
    "саруман", "саурон", "голлум", "орк", "орки", "урук-хай", "балрог",
    "мордор", "шір", "рохан", "гондор", "рівендел", "мирквуд", "еребор",
    "смауг", "торін", "бард", "беорн", "назгул", "король-чаклун", "братство",
    "ізенгард", "мінус тіріт", "гельмів яр", "ортанк", "гора приречення",

    "властелин колец", "кольца", "властелин", "хоббит", "средиземье",
    "гэндальф", "фродо", "сам", "мэрри", "пиппин", "арагорн", "леголас",
    "гимли", "боромир", "эльронд", "галадриэль", "арвен", "саруман",
    "саурон", "голлум", "орки", "урук", "балрог", "мордор", "шир",
    "рохан", "гондор", "ривенделл", "мглистые горы", "эребор", "смауг",
    "торин", "бард", "беорн", "назу́л", "чёрный всадник", "братство кольца",
    "изенгард", "минас тирит", "хельмова падь", "ортанк", "гора судьбы"
]

MIN_PRICE = None
MAX_PRICE = None
CHECK_INTERVAL = 60  # кожну хвилину
STATE_FILE = "seen.json"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

# ---------- Вспомогательные функции ----------
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

# ---------- Telegram-команды ----------
def check_status(update=None, context=None):
    send_telegram("🤖 Бот активний та працює стабільно!")

def start(update, context):
    update.message.reply_text("👋 Привіт! Бот запущений і моніторить оголошення на OLX.")

# ---------- Парсер ----------
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

# ---------- Основні процеси ----------
def run_bot():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("status", check_status))
    updater.start_polling()
    updater.idle()

def run_monitor():
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
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    run_monitor()
