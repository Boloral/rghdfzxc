import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

TELEGRAM_TOKEN = "7911469039:AAFbpPSKTvgGT9cdzyB-wkwNsmFToxT5-Lw"
CHAT_ID = "1075736931"

bot = telebot.TeleBot(TELEGRAM_TOKEN)

stats_fetcher = None

def send_telegram_preview(url, content_type):
    try:
        if content_type.startswith("image/"):
            bot.send_photo(CHAT_ID, url, caption=f"📸 Знайдено зображення:\n{url}")
        elif content_type.startswith("video/"):
            bot.send_video(CHAT_ID, url, caption=f"🎥 Знайдено відео:\n{url}")
        else:
            bot.send_message(CHAT_ID, f"Знайдено медіа:\n{url}")
    except Exception as e:
        print(f"Помилка надсилання прев’ю: {e}")

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
