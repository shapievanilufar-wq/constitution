import os
import csv
import requests
from io import StringIO
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")

CSV_URL = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid=0"

PAGE_SIZE = 5  # Har sahifada 5 ta modda tugmasi

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

def build_keyboard_page(items, page, page_size=PAGE_SIZE):
    start = page * page_size
    end = start + page_size
    page_items = items[start:end]

    keyboard = [[KeyboardButton(str(modda))] for modda in page_items]

    nav_buttons = []
    if page > 0:
        nav_buttons.append(KeyboardButton("⬅️ Oldingi"))
    if end < len(items):
        nav_buttons.append(KeyboardButton("Keyingi ➡️"))
    if nav_buttons:
        keyboard.append(nav_buttons)

    return keyboard

constitution = {}
current_page = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global constitution, current_page

    try:
        constitution = load_constitution()
    except Exception as e:
        await update.message.reply_text(f"Ma'lumotlarni yuklashda xatolik: {e}")
        return

    user_id = update.effective_user.id
    current_page[user_id] = 0  # boshlang'ich sahifa 0

    keys = list(constitution.keys())
    keyboard = build_keyboard_page(keys, page=0)

    await update.message.reply_text(
        "Konstitutsiya moddalari bo‘yicha ma'lumot olish uchun modda raqamini tanlang:",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global current_page
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if user_id not in current_page:
        current_page[user_id] = 0

    keys = list(constitution.keys())
    page = current_page[user_id]

    if text == "Keyingi ➡️":
        if (page + 1) * PAGE_SIZE < len(keys):
            current_page[user_id] = page + 1
        page = current_page[user_id]
        keyboard = build_keyboard_page(keys, page)
        await update.message.reply_text(
            f"Moddalar, sahifa {page + 1}:",
            reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
    elif text == "⬅️ Oldingi":
        if page > 0:
            current_page[user_id] = page - 1
        page = current_page[user_id]
        keyboard = build_keyboard_page(keys, page)
        await update.message.reply_text(
            f"Moddalar, sahifa {page + 1}:",
            reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
    elif text in constitution:
        await update.message.reply_text(constitution[text])
    else:
        keyboard = build_keyboard_page(keys, page)
        await update.message.reply_text(
            "Kechirasiz, bunday modda topilmadi yoki noto'g'ri tugma bosildi.\nIltimos, klaviaturadan modda raqamini tanlang:",
            reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        )

if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot ishga tushdi...")
    app.run_polling()
