import csv
import os
import requests
from io import StringIO
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# === .env faylni yuklaymiz ===
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv"

# Google Sheets'dan ma'lumotni CSV ko‘rinishda olish
def get_constitution_data():
    try:
        response = requests.get(CSV_URL)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print("Xatolik:", e)
        return {}

    data = {}
    csv_data = response.content.decode('utf-8')
    reader = csv.reader(StringIO(csv_data))

    for row in reader:
        if len(row) >= 2:
            raqam = row[0].strip()
            matn = row[1].strip()
            data[raqam] = matn

    return data

def start(update: Update, context: CallbackContext):
    data = get_constitution_data()
    if not data:
        update.message.reply_text("Ma'lumotlarni yuklashda xatolik yuz berdi.")
        return

    keyboard = [[k] for k in data.keys()]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    update.message.reply_text("Qaysi moddani ko‘rmoqchisiz?", reply_markup=reply_markup)

def handle_message(update: Update, context: CallbackContext):
    raqam = update.message.text.strip()
    data = get_constitution_data()

    if raqam in data:
        update.message.reply_text(data[raqam])
    else:
        update.message.reply_text("Bunday modda topilmadi. Iltimos, /start buyrug'ini qayta yuboring.")

def main():
    if not BOT_TOKEN or not SPREADSHEET_ID:
        print("❌ BOT_TOKEN yoki SPREADSHEET_ID .env faylda topilmadi!")
        return

    updater = Updater(BOT_TOKEN)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
