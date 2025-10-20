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

if not BOT_TOKEN or not SPREADSHEET_ID:
    raise ValueError("BOT_TOKEN or SPREADSHEET_ID not set in environment variables")

CSV_URL = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid=0"
PAGE_SIZE = 5  # Har sahifada 5 ta modda tugmasi

constitution_cache = None

def load_constitution():
    global constitution_cache
    if constitution_cache is None:
        response = requests.get(CSV_URL, timeout=10)
        response.raise_for_status()
        f = StringIO(response.text)
        reader = csv.DictReader(f)
        if "Modda" not in reader.fieldnames or "Matn" not in reader.fieldnames:
            raise ValueError("CSV file missing required columns: 'Modda' or 'Matn'")
        data = {}
        for row in reader:
            modda = row.get("Modda")
            matn = row.get("Matn")
            if modda and matn:
                data[modda.strip()] = matn.strip()
        if len(data) != 16:
            raise ValueError(f"Expected 16 articles, but found {len(data)}")
        constitution_cache = data
    return constitution_cache

def build_keyboard_page(items, page, page_size=PAGE_SIZE):
    start = page * page_size
    end = start + page_size
    sorted_items = sorted(items, key=lambda x: int(x))  # Sort numerically
    page_items = sorted_items[start:end]
    keyboard = [[KeyboardButton(str(modda))] for modda in page_items]
    nav_buttons = []
    if page > 0:
        nav_buttons.append(KeyboardButton("⬅️ Oldingi"))
    if end < len(items):
        nav_buttons.append(KeyboardButton("Keyingi ➡️"))
    if nav_buttons:
        keyboard.append(nav_buttons)
    return keyboard

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data['constitution'] = load_constitution()
    except Exception as e:
        await update.message.reply_text(f"Ma'lumotlarni yuklashda xatolik: {e}")
        return

    context.user_data['current_page'] = 0
    keys = sorted(context.user_data['constitution'].keys(), key=lambda x: int(x))
    keyboard = build_keyboard_page(keys, page=0)

    await update.message.reply_text(
        "Konstitutsiya moddalari bo‘yicha ma'lumot olish uchun modda raqamini tanlang:",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    )

async def refresh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global constitution_cache
    constitution_cache = None
    try:
        context.user_data['constitution'] = load_constitution()
        context.user_data['current_page'] = 0
        keys = sorted(context.user_data['constitution'].keys(), key=lambda x: int(x))
        keyboard = build_keyboard_page(keys, page=0)
        await update.message.reply_text(
            "Ma'lumotlar yangilandi. Modda raqamini tanlang:",
            reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
    except Exception as e:
        await update.message.reply_text(f"Ma'lumotlarni yangilashda xatolik: {e}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if 'constitution' not in context.user_data:
        context.user_data['constitution'] = load_constitution()
    if 'current_page' not in context.user_data:
        context.user_data['current_page'] = 0

    keys = sorted(context.user_data['constitution'].keys(), key=lambda x: int(x))
    page = context.user_data['current_page']

    if text == "Keyingi ➡️":
        if (page + 1) * PAGE_SIZE < len(keys):
            context.user_data['current_page'] = page + 1
        page = context.user_data['current_page']
        keyboard = build_keyboard_page(keys, page)
        await update.message.reply_text(
            f"Moddalar, sahifa {page + 1}:",
            reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
    elif text == "⬅️ Oldingi":
        if page > 0:
            context.user_data['current_page'] = page - 1
        page = context.user_data['current_page']
        keyboard = build_keyboard_page(keys, page)
        await update.message.reply_text(
            f"Moddalar, sahifa {page + 1}:",
            reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
    elif text in context.user_data['constitution']:
        await update.message.reply_text(context.user_data['constitution'][text])
    else:
        keyboard = build_keyboard_page(keys, page)
        await update.message.reply_text(
            "Kechirasiz, bunday modda topilmadi yoki noto'g'ri tugma bosildi.\nIltimos, klaviaturadan modda raqamini tanlang:",
            reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        )

if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("refresh", refresh))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot ishga tushdi...")
    app.run_polling()
