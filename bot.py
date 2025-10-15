import os
import logging
import gspread
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# Logger
logging.basicConfig(level=logging.INFO)

# Google Sheets ulanish
gc = gspread.service_account(filename="credentials.json")
spreadsheet_id = os.getenv("SPREADSHEET_ID")
sheet = gc.open_by_key(spreadsheet_id).sheet1  # 1-sheet

# Bot token
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Klaviatura tugmalari (1–10 misol tariqasida, kerak bo‘lsa kengaytiring)
keyboard = [[str(i)] for i in range(1, 11)]  # 1 dan 10 gacha tugmalar

markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Assalomu alaykum! Raqamni kiriting (masalan, 1) — shunda o‘sha modda chiqariladi.", reply_markup=markup)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if text.isdigit():
        modda_raqami = int(text)
        try:
            # Sheetda: A ustun = raqam, B ustun = modda matni deb faraz qilamiz
            rows = sheet.get_all_records()
            modda = next((row for row in rows if int(row['modda']) == modda_raqami), None)

            if modda:
                await update.message.reply_text(f"🧾 {modda_raqami}-modda:\n\n{modda['matn']}")
            else:
                await update.message.reply_text("❌ Bunday modda topilmadi.")
        except Exception as e:
            logging.error(f"Xato: {e}")
            await update.message.reply_text("❌ Xatolik yuz berdi. Keyinroq urinib ko‘ring.")
    else:
        await update.message.reply_text("❗ Iltimos, faqat modda raqamini kiriting.")


if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.add_handler(MessageHandler(filters.COMMAND, start))
    app.run_polling()
