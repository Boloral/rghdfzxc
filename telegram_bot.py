import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
import requests
import tempfile
import os
from PIL import Image
import imagehash
from collections import defaultdict

TELEGRAM_TOKEN = "7911469039:AAFbpPSKTvgGT9cdzyB-wkwNsmFToxT5-Lw"
CHAT_ID = "1075736931"

bot = telebot.TeleBot(TELEGRAM_TOKEN)

stats_fetcher = None

image_hashes = defaultdict(lambda: None)
HASH_THRESHOLD = 3

def get_image_hash(image_path):
    try:
        with Image.open(image_path) as img:
            return imagehash.phash(img)
    except Exception as e:
        print(f"Помилка при обчисленні хеша: {e}")
        return None

def is_similar_to_sent_images(new_hash):
    if new_hash is None:
        return False
        
    for sent_hash in image_hashes.values():
        if sent_hash is not None and (new_hash - sent_hash) < HASH_THRESHOLD:
            return True
    return False

def send_telegram_preview(url, content_type):
    try:
        response = requests.get(url, stream=True, timeout=10)
        if response.status_code != 200:
            raise Exception("Не вдалося завантажити файл")

        # Визначаємо розширення файлу з Content-Type або URL
        file_extension = None
        if content_type.startswith("image/"):
            file_extension = ".png" if "png" in content_type.lower() else ".jpg"
        elif content_type.startswith("video/"):
            file_extension = ".mp4"

        # Створюємо тимчасовий файл з правильним розширенням
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
            for chunk in response.iter_content(chunk_size=1024):
                temp_file.write(chunk)
            temp_file_path = temp_file.name

        should_send = True
        
        if content_type.startswith("image/"):
            current_hash = get_image_hash(temp_file_path)
            if current_hash is not None and is_similar_to_sent_images(current_hash):
                print(f"⏩ Пропускаємо схоже зображення: {url}")
                should_send = False
            else:
                image_hashes[url] = current_hash

            with Image.open(temp_file_path) as img:
                max_size = 1280
                if img.width > max_size or img.height > max_size:
                    scale = max_size / max(img.width, img.height)
                    new_size = (int(img.width * scale), int(img.height * scale))
                    img = img.resize(new_size, Image.Resampling.LANCZOS)
                    
                    # Визначаємо формат для збереження
                    save_format = "PNG" if img.mode == 'RGBA' else "JPEG"
                    img.save(temp_file_path, format=save_format)

        if should_send:
            if content_type.startswith("image/"):
                with open(temp_file_path, 'rb') as photo:
                    # Відправляємо як фото (Telegram сам оптимізує)
                    bot.send_photo(CHAT_ID, photo, caption=f"📸 Знайдено зображення:\n{url}")
            elif content_type.startswith("video/"):
                with open(temp_file_path, 'rb') as video:
                    bot.send_video(CHAT_ID, video, caption=f"🎥 Знайдено відео:\n{url}")
            else:
                bot.send_message(CHAT_ID, f"Знайдено медіа:\n{url}")

        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

    except Exception as e:
        print(f"❌ Помилка: {e}")
        bot.send_message(CHAT_ID, f"❌ Помилка при обробці {url}: {str(e)}")

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
    stats = stats_fetcher() if stats_fetcher else {"found_new": 0, "found_repeat": 0}
    response = (
        "📈 *Статистика пошуку:*\n"
        f"🔹 Унікальних знайдено: *{stats.get('found_new', 0)}*\n"
        f"🔁 Повторів: *{stats.get('found_repeat', 0)}*"
    )
    bot.send_message(message.chat.id, response, parse_mode="Markdown")

def run_bot(fetch_stats_func):
    global stats_fetcher
    stats_fetcher = fetch_stats_func
    print("✅ Telegram бот запущено.")
    bot.infinity_polling()
