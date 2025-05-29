import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
import requests
import tempfile
import os
from PIL import Image
import imagehash

TELEGRAM_TOKEN = "7911469039:AAFbpPSKTvgGT9cdzyB-wkwNsmFToxT5-Lw"  # Ваш токен тут
CHAT_ID = "1075736931"  # Ваш Chat ID тут

bot = telebot.TeleBot(TELEGRAM_TOKEN)

stats_fetcher = None
_increment_stat_func = None

# --- URL-адреси для еталонних зображень ---
# ЗАМІНІТЬ ЦІ URL-АДРЕСИ НА РЕАЛЬНІ ПОСИЛАННЯ НА ВАШІ ЕТАЛОННІ ЗОБРАЖЕННЯ (3 ШТ.)
# Переконайтесь, що посилання прямі та доступні для завантаження ботом.
TEMPLATE_IMAGE_URLS_WITH_NAMES = {
    "Map": "https://gachi.gay/StZqB",
    "Road": "https://gachi.gay/4kO7c",
}

PREDEFINED_IMAGE_HASHES = {}  # Сюди будуть завантажені хеші з URL
HASH_THRESHOLD = 3  # Поріг схожості, можна налаштувати


def get_image_hash(image_path):
    """Обчислює pHash для зображення за заданим шляхом."""
    try:
        with Image.open(image_path) as img:
            return imagehash.phash(img)
    except FileNotFoundError:
        print(f"Помилка: Файл не знайдено для хешування - {image_path}")
        return None
    except Exception as e:
        print(f"Помилка при обчисленні хеша для {image_path}: {e}")
        return None


def _initialize_template_hashes():
    """Завантажує еталонні зображення за URL, обчислює їх хеші та зберігає."""
    print("⏳ Початок ініціалізації еталонних хешів...")
    for name, url in TEMPLATE_IMAGE_URLS_WITH_NAMES.items():
        temp_file_path = None
        try:
            print(f"  Завантаження еталону '{name}' з {url}...")
            response = requests.get(url, stream=True, timeout=20)  # Збільшено таймаут
            response.raise_for_status()  # Перевірка на HTTP помилки (4xx, 5xx)

            content_type = response.headers.get('Content-Type', '').lower()
            if 'png' in content_type:
                suffix = '.png'
            elif 'jpeg' in content_type or 'jpg' in content_type:
                suffix = '.jpg'
            elif 'gif' in content_type:
                suffix = '.gif'
            elif 'webp' in content_type:
                suffix = '.webp'
            else:
                print(
                    f"  Увага: Не вдалося визначити тип файлу для '{name}' з Content-Type: {content_type}. Використовується .tmp")
                suffix = '.tmp'

            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
                for chunk in response.iter_content(chunk_size=8192):
                    temp_file.write(chunk)
                temp_file_path = temp_file.name

            print(f"  Обчислення хеша для еталону '{name}' (файл: {temp_file_path})...")
            img_hash = get_image_hash(temp_file_path)

            if img_hash:
                PREDEFINED_IMAGE_HASHES[name] = img_hash
                print(f"  ✅ Еталон '{name}' успішно завантажено та хешовано: {img_hash}")
            else:
                print(
                    f"  ⚠️ Не вдалося обчислити хеш для еталону '{name}' з {url}. Можливо, файл не є зображенням або пошкоджений.")

        except requests.exceptions.Timeout:
            print(f"  ❌ Таймаут при завантаженні еталону '{name}' з {url}.")
        except requests.exceptions.RequestException as e:
            print(f"  ❌ Помилка завантаження еталону '{name}' з {url}: {e}")
        except Exception as e:  # Інші можливі помилки (наприклад, з Pillow)
            print(f"  ❌ Загальна помилка обробки еталону '{name}' ({url}): {e}")
        finally:
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                    print(f"  🗑️ Тимчасовий файл {temp_file_path} для '{name}' видалено.")
                except Exception as e:
                    print(f"  Помилка видалення тимчасового файлу {temp_file_path}: {e}")

    # Підсумкове повідомлення після ініціалізації
    if not PREDEFINED_IMAGE_HASHES:
        print(
            "‼️ ПОПЕРЕДЖЕННЯ: Не вдалося завантажити ЖОДНОГО еталонного хеша. Перевірка схожості з еталонами не працюватиме.")
    elif len(PREDEFINED_IMAGE_HASHES) < len(TEMPLATE_IMAGE_URLS_WITH_NAMES):
        print(
            f"⚠️ УВАГА: Завантажено лише {len(PREDEFINED_IMAGE_HASHES)} з {len(TEMPLATE_IMAGE_URLS_WITH_NAMES)} очікуваних еталонних хешів. Перевірка на схожість буде обмеженою.")
    else:
        print(f"✅ Успішно завантажено та хешовано {len(PREDEFINED_IMAGE_HASHES)} еталонних зображень.")
    print("🏁 Ініціалізація еталонних хешів завершена.")


# Викликаємо функцію ініціалізації один раз при завантаженні модуля (тобто при старті бота)
_initialize_template_hashes()


def send_telegram_preview(url, content_type):
    global _increment_stat_func
    try:
        response = requests.get(url, stream=True, timeout=10)
        if response.status_code != 200:
            raise Exception("Не вдалося завантажити файл")

        file_extension = ".png" if "png" in content_type.lower() else ".jpg" if content_type.startswith(
            "image/") else ".mp4"

        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
            for chunk in response.iter_content(chunk_size=1024):
                temp_file.write(chunk)
            temp_file_path = temp_file.name

        should_send = True

        if content_type.startswith("image/"):
            current_hash = get_image_hash(temp_file_path)

            if current_hash is not None and PREDEFINED_IMAGE_HASHES:  # Перевіряємо, чи є еталонні хеші
                closest_diff = float('inf')
                closest_template_name = None

                for template_name, predefined_hash in PREDEFINED_IMAGE_HASHES.items():
                    diff = current_hash - predefined_hash
                    if diff < closest_diff:
                        closest_diff = diff
                        closest_template_name = template_name

                if closest_diff < HASH_THRESHOLD:
                    print(
                        f"⏩ Пропускаємо зображення '{url}', схоже на еталон '{closest_template_name}' (різниця: {closest_diff})")
                    bot.send_message(
                        CHAT_ID,
                        f"🚫 Пропущено зображення, схоже на еталон '{closest_template_name}':\n"
                        f"Нове: {url}\n"
                        f"Рівень схожості: {closest_diff}/{HASH_THRESHOLD}",
                        disable_web_page_preview=True
                    )
                    should_send = False
                    if _increment_stat_func:
                        _increment_stat_func("found_similar")
            elif current_hash is not None and not PREDEFINED_IMAGE_HASHES:
                print(
                    "Увага: Попередньо визначені еталонні хеші не завантажені. Перевірка на схожість з еталонами неможлива.")

            # Обробка зображення (ресайз + конвертація)
            with Image.open(temp_file_path) as img:
                max_size = 1280
                if img.width > max_size or img.height > max_size:
                    scale = max_size / max(img.width, img.height)
                    new_size = (int(img.width * scale), int(img.height * scale))
                    img = img.resize(new_size, Image.Resampling.LANCZOS)

                    save_format = "PNG" if img.mode == 'RGBA' else "JPEG"
                    img.save(temp_file_path, format=save_format)

        if should_send:
            if content_type.startswith("image/"):
                with open(temp_file_path, 'rb') as photo:
                    bot.send_photo(CHAT_ID, photo, caption=f"📸 Знайдено зображення:\n{url}")
            elif content_type.startswith("video/"):
                with open(temp_file_path, 'rb') as video:
                    bot.send_video(CHAT_ID, video, caption=f"🎥 Знайдено відео:\n{url}")

        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

    except Exception as e:
        print(f"❌ Помилка в send_telegram_preview для {url}: {e}")
        # Надсилати повідомлення про помилку в чат тут може бути надто часто, якщо URL часто недоступні
        # bot.send_message(CHAT_ID, f"❌ Помилка при обробці {url}: {str(e)}")


@bot.message_handler(commands=['start'])
def handle_start(message):
    if str(message.chat.id) != CHAT_ID:
        return
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("📊 Показати статистику"))
    bot.send_message(message.chat.id, "Привіт! Натисни кнопку, щоб побачити статистику:", reply_markup=keyboard)


@bot.message_handler(func=lambda msg: msg.text == "📊 Показати статистику")
def handle_stats(message):
    if str(message.chat.id) != CHAT_ID:
        return
    stats = stats_fetcher() if stats_fetcher else {"found_new": 0, "found_repeat": 0, "found_similar": 0}
    response = (
        "📈 *Статистика пошуку:*\n"
        f"🔹 Унікальних знайдено: *{stats.get('found_new', 0)}*\n"
        f"🔁 Повторів: *{stats.get('found_repeat', 0)}*\n"
        f"👯 Схожих (на еталони) пропущено: *{stats.get('found_similar', 0)}*"
    )
    bot.send_message(message.chat.id, response, parse_mode="Markdown")


def run_bot(fetch_stats_func, increment_stat_func):
    global stats_fetcher, _increment_stat_func
    stats_fetcher = fetch_stats_func
    _increment_stat_func = increment_stat_func
    # Повідомлення про статус завантаження хешів тепер друкуються в _initialize_template_hashes()
    print("✅ Telegram бот запущено (після ініціалізації еталонів).")
    bot.infinity_polling()
