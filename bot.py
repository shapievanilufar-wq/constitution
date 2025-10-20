import os
import csv
import re
import requests
from io import StringIO
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

# .env fayldan sozlamalarni yuklash
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")

if not BOT_TOKEN or not SPREADSHEET_ID:
    raise ValueError("BOT_TOKEN yoki SPREADSHEET_ID muhiti o'zgaruvchilari o'rnatilmagan")

CSV_URL = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid=0"
PAGE_SIZE = 5  # Har sahifada 5 ta modda tugmasi

constitution_cache = None

# Matnni tozalash va imlo xatolarini minimallashtirish funksiyasi
def clean_text(text):
    """Matnni tozalash: ortiqcha bo'shliqlar, noto'g'ri belgilarni olib tashlash"""
    # Ortiqcha bo'shliqlarni olib tashlash
    text = re.sub(r'\s+', ' ', text.strip())
    # Noto'g'ri apostroflarni tuzatish (masalan, '’' ni '‘' ga)
    text = text.replace("’", "‘").replace("'", "‘")
    # O'zbek tilidagi umumiy imlo xatolarini tuzatish (masalan, "uz" ni "o‘z" ga)
    text = re.sub(r'\buz\b', "o‘z", text, flags=re.IGNORECASE)
    text = re.sub(r'\bg\'', "g‘", text)
    text = re.sub(r'\bo\'', "o‘", text)
    return text

def load_constitution():
    """Google Sheets'dan konstitutsiya ma'lumotlarini yuklash"""
    global constitution_cache
    if constitution_cache is None:
        try:
            response = requests.get(CSV_URL, timeout=10)
            response.raise_for_status()
            response.encoding = 'utf-8'  # UTF-8 kodlashni ta'minlash
            f = StringIO(response.text)
            reader = csv.DictReader(f)
            if "Modda" not in reader.fieldnames or "Matn" not in reader.fieldnames:
                raise ValueError("CSV faylda 'Modda' yoki 'Matn' ustunlari yo'q")
            data = {}
            for row in reader:
                modda = row.get("Modda")
                matn = row.get("Matn")
                if modda and matn:
                    # Matnni tozalash
                    cleaned_matn = clean_text(matn)
                    data[modda.strip()] = cleaned_matn
            if not data:
                raise ValueError("CSV faylda ma'lumotlar topilmadi")
            constitution_cache = data
        except Exception as e:
            raise ValueError(f"Ma'lumotlarni yuklashda xatolik: {str(e)}")
    return constitution_cache

def build_keyboard_page(items, page, page_size=PAGE_SIZE):
    """Sahifali klaviatura yaratish"""
    start = page * page_size
    end = start + page_size
    sorted_items = sorted(items, key=lambda x: int(x))  # Raqamlar bo'yicha tartiblash
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
    """Botni ishga tushirish"""
    try:
        context.user_data['constitution'] = load_constitution()
    except Exception as e:
        await update.message.reply_text(f"Ma'lumotlarni yuklashda xatolik: {str(e)}")
        return

    context.user_data['current_page'] = 0
    keys = sorted(context.user_data['constitution'].keys(), key=lambda x: int(x))
    keyboard = build_keyboard_page(keys, page=0)

    await update.message.reply_text(
        "O‘zbekiston Respublikasi Konstitutsiyasi moddalarini ko‘rish uchun modda raqamini tanlang:",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True),
        parse_mode="Markdown"
    )

async def refresh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ma'lumotlarni yangilash"""
    global constitution_cache
    constitution_cache = None
    try:
        context.user_data['constitution'] = load_constitution()
        context.user_data['current_page'] = 0
        keys = sorted(context.user_data['constitution'].keys(), key=lambda x: int(x))
        keyboard = build_keyboard_page(keys, page=0)
        await update.message.reply_text(
            "Ma'lumotlar yangilandi. Modda raqamini tanlang:",
            reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True),
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(f"Ma'lumotlarni yangilashda xatolik: {str(e)}")

async def send_long_text(update, text, max_length=4096):
    """Uzun matnlarni qismlarga bo'lib yuborish"""
    if len(text) <= max_length:
        await update.message.reply_text(text, parse_mode="Markdown")
    else:
        parts = [text[i:i+max_length] for i in range(0, len(text), max_length)]
        for part in parts:
            await update.message.reply_text(part, parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Foydalanuvchi xabarlarini qayta ishlash"""
    text = update.message.text.strip()

    if 'constitution' not in context.user_data:
        try:
            context.user_data['constitution'] = load_constitution()
        except Exception as e:
            await update.message.reply_text(f"Ma'lumotlarni yuklashda xatolik: {str(e)}")
            return
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
            reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True),
            parse_mode="Markdown"
        )
    elif text == "⬅️ Oldingi":
        if page > 0:
            context.user_data['current_page'] = page - 1
        page = context.user_data['current_page']
        keyboard = build_keyboard_page(keys, page)
        await update.message.reply_text(
            f"Moddalar, sahifa {page + 1}:",
            reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True),
            parse_mode="Markdown"
        )
    elif text in context.user_data['constitution']:
        # Matnni Markdown formatida ko'rsatish
        formatted_text = f"**Modda {text}**\n{context.user_data['constitution'][text]}"
        await send_long_text(update, formatted_text)
    else:
        keyboard = build_keyboard_page(keys, page)
        await update.message.reply_text(
            "Kechirasiz, bunday modda topilmadi. Iltimos, quyidagi moddalardan birini tanlang:",
            reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True),
            parse_mode="Markdown"
        )

if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("refresh", refresh))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot ishga tushdi...")
    app.run_polling()
