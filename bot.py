import os
import csv
import requests
from io import StringIO
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")

CSV_URL = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid=0"

# Moddalarni yuklash funksiyasi
def load_constitution():
    response = requests.get(CSV_URL)
    response.raise_for_status()
    f = StringIO(response.text)
    reader = csv.DictReader(f)
    data = {}
    for row in reader:
        modda = row.get("Modda")
        matn = row.get("Matn")
        if modda and matn:
            data[modda.strip()] = matn.strip()
    return data

keyboard = []
constitution = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global constitution, keyboard
    try:
        constitution = load_constitution()
        keyboard = [list(constitution.keys())]
    except Exception as e:
        await update.message.reply_text(f"Ma'lumotlarni yuklashda xatolik: {e}")
        return

    await update.message.reply_text(
        "Konstitutsiya moddalari bo‘yicha ma'lumot olish uchun modda raqamini tanlang:",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text in constitution:
        await update.message.reply_text(constitution[text])
    else:
        await update.message.reply_text("Kechirasiz, bunday modda topilmadi. Iltimos, klaviaturadan modda raqamini tanlang.")

if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot ishga tushdi...")
    app.run_polling()
