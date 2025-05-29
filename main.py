import threading
import time
import requests
import random
import string
import psycopg2
import telegram_bot
from colorama import init, Fore

init(autoreset=True)

DB_URL = "postgresql://postgres:lXAsHodiOczWkRVNUrJCRVsyXHKnATgL@trolley.proxy.rlwy.net:14294/railway" # Ваша URL DB

conn = psycopg2.connect(DB_URL)
cursor = conn.cursor()

def init_db():
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS links (
            url TEXT PRIMARY KEY,
            found_at TIMESTAMP DEFAULT NOW()
        );
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stats (
            key TEXT PRIMARY KEY,
            value INTEGER NOT NULL
        );
    """)
    # Додано 'found_similar'
    for key in ["found_new", "found_repeat", "found_similar"]:
        cursor.execute("INSERT INTO stats (key, value) VALUES (%s, 0) ON CONFLICT (key) DO NOTHING;", (key,))
    conn.commit()

def generate_random_string(length=5):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def check_media_url(url):
    try:
        response = requests.head(url, allow_redirects=True, timeout=5)
        if response.status_code != 200:
            return False, None
        content_type = response.headers.get('Content-Type', '')
        if content_type.startswith('image/') or content_type.startswith('video/'):
            return True, content_type
        return False, None
    except Exception as e:
        print(f"Помилка перевірки URL: {e}")
        return False, None

def is_link_found(url):
    cursor.execute("SELECT 1 FROM links WHERE url = %s;", (url,))
    return cursor.fetchone() is not None

def save_link(url):
    cursor.execute("INSERT INTO links (url) VALUES (%s) ON CONFLICT DO NOTHING;", (url,))
    conn.commit()

def increment_stat(key):
    cursor.execute("UPDATE stats SET value = value + 1 WHERE key = %s;", (key,))
    conn.commit()

def get_stats():
    cursor.execute("SELECT key, value FROM stats;")
    rows = cursor.fetchall()
    return {row[0]: row[1] for row in rows}

def start_search():
    while True:
        rand = generate_random_string()
        url = f"https://gachi.gay/{rand}" # Обережно з використанням таких доменів
        found, content_type = check_media_url(url)
        if found:
            if is_link_found(url):
                print(Fore.YELLOW + f"Повторне посилання: {url}")
                increment_stat("found_repeat")
            else:
                print(Fore.GREEN + f"Знайдено. Посилання: {url}")
                save_link(url)
                increment_stat("found_new")
                # Функція send_telegram_preview тепер сама може інкрементувати 'found_similar'
                telegram_bot.send_telegram_preview(url, content_type)
        else:
            print(Fore.RED + f"Нічого не знайдено за {url}")
        time.sleep(1) # Можливо, варто збільшити для зменшення навантаження

def main():
    init_db()
    threading.Thread(target=start_search, daemon=True).start()
    # Передаємо get_stats та increment_stat до run_bot
    telegram_bot.run_bot(get_stats, increment_stat)

if __name__ == "__main__":
    main()
