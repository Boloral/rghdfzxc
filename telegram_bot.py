import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
import tempfile
import os

TELEGRAM_TOKEN = "7911469039:AAFbpPSKTvgGT9cdzyB-wkwNsmFToxT5-Lw"
CHAT_ID = "1075736931"

bot = telebot.TeleBot(TELEGRAM_TOKEN)

stats_fetcher = None

def send_telegram_preview(url, content_type):
    try:
        response = requests.get(url, stream=True, timeout=10)
        if response.status_code != 200:
            raise Exception("Не вдалося завантажити файл")

        suffix = ".jpg" if content_type.startswith("image/") else ".mp4"

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            for chunk in response.iter_content(chunk_size=1024):
                temp_file.write(chunk)
            temp_file_path = temp_file.name

        if content_type.startswith("image/"):
            with open(temp_file_path, 'rb') as photo:
                bot.send_photo(CHAT_ID, photo, caption=f"📸 Знайдено зображення:\n{url}")
        elif content_type.startswith("video/"):
            with open(temp_file_path, 'rb') as video:
                bot.send_video(CHAT_ID, video, caption=f"🎥 Знайдено відео:\n{url}")
        else:
            bot.send_message(CHAT_ID, f"Знайдено медіа:\n{url}")

    except Exception as e:
        print(f"Помилка надсилання прев’ю: {e}")
    finally:
        # Безпечно видаляємо тимчасовий файл, якщо був створений
        if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
            os.remove(temp_file_path)

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
