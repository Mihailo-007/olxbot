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

# 🔹 Імітація веб-сервера, щоб Render дозволив безкоштовний режим
def keep_alive():
    PORT = 8080
    Handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        httpd.serve_forever()

threading.Thread(target=keep_alive, daemon=True).start()

# 🔹 НАЛАШТУВАННЯ
BOT_TOKEN = "8574839052:AAF-DXQhtnXeY3r2Oc8oiz1WiDA1Hru7EPI"
CHAT_ID = "1400522756"

# 🔹 Посилання для моніторингу
RSS_OR_SEARCH_URLS = [
    "https://www.olx.ua/uk/detskiy-mir/igrushki/konstruktory/q-lego-%D0%BC%D0%B8%D0%BD%D0%B8%D1%84%D0%B8%D0%B3%D1%83%D1%80%D0%BA%D0%B8/",
    "https://www.olx.ua/uk/list/q-lego%20lord%20of%20rings/?min_id=905594298&reason=observed_search&search%5Border%5D=created_at%3Adesc",
    "https://www.olx.ua/uk/list/q-lego%20%D0%B2%D0%BB%D0%B0%D1%81%D1%82%D0%B5%D0%BB%D0%B8%D0%BD%20%D0%BA%D0%BE%D0%BB%D0%B5%D1%86/?min_id=905107950&reason=observed_search&search%5Border%5D=relevance%3Adesc",
    "https://www.olx.ua/uk/list/q-lego%20hobbit/?min_id=905454579&reason=observed_search&search%5Border%5D=relevance%3Adesc",
    "https://www.olx.ua/uk/list/q-lego%20%D1%85%D0%BE%D0%B1%D0%B1%D0%B8%D1%82/?min_id=905454579&reason=observed_search&search%5Border%5D=relevance%3Adesc",
    "https://www.olx.ua/uk/detskiy-mir/igrushki/konstruktory/q-%D0%BB%D0%B5%D0%B3%D0%BE%20%D1%87%D0%B5%D0%BB%D0%BE%D0%B2%D0%B5%D1%87%D0%BA%D0%B8/?min_id=905640198&reason=observed_search&currency=UAH&search%5Border%5D=relevance%3Adesc",
]

# 🔹 Ключові слова
KEYWORDS = [
    "lego", "legolas", "lord", "rings", "lord of the rings", "hobbit", "the hobbit",
    "властелин колец", "хоббит", "гоблин", "варг", "тролль", "торин", "гандальф", "гольдум",
    "гном", "эльф", "средиземье", "бильбо", "фродо", "саурон", "орки",
    "79010", "79011", "79012"
]

MIN_PRICE = None
MAX_PRICE = None
CHECK_INTERVAL = 60 * 5  # перевірка кожні 5 хвилин
STATE_FILE = "seen.json"

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


# 🔹 Завантаження і збереження побачених оголошень
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

# 🔹 Надсилання повідомлень у Telegram
def send_telegram(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "disable_web_page_preview": False}
    try:
        r = requests.post(url, data=payload, timeout=10)
        return r.ok
    except Exception as e:
        print("Telegram send error:", e)
        return False

# 🔹 Фільтрація оголошень
def entry_passes_filters(title, price):
    s = title.lower()
    if MIN_PRICE is not None and price is not None and price < MIN_PRICE:
        return False
    if MAX_PRICE is not None and price is not None and price > MAX_PRICE:
        return False
    if KEYWORDS:
        return any(k.lower() in s for k in KEYWORDS)
    return True

# 🔹 Парсинг RSS
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

# 🔹 Парсинг HTML
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
        print("HTML parse error:", e)
        return []

# 🔹 Форматування повідомлення
def format_message(item):
    t = item.get("title") or "Без назви"
    p = item.get("price")
    pr = f"{p} грн" if p else "Ціна не вказана"
    l = item.get("link")
    pub = datetime.now().strftime("%Y-%m-%d %H:%M")
    return f"{t}\n{pr}\n{l}\n{pub}"

# 🔹 Надсилання повідомлення раз на годину
def send_status_message():
    send_telegram("🤖 Бот активний, працює стабільно.")
    threading.Timer(3600, send_status_message).start()

# 🔹 Основна логіка
def main():
    send_status_message()  # запускаємо перевірку активності
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
                            print("✅ Відправлено:", it.get("title"))
                            seen.add(uid)
                        else:
                            print("❌ Помилка відправки:", it.get("title"))
                save_seen(seen)
        except Exception as e:
            print("Main loop error:", e)
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
