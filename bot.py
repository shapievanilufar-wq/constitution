from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from google.oauth2 import service_account
from googleapiclient.discovery import build

# === Google Sheets sozlamalari ===
SERVICE_ACCOUNT_FILE = 'credentials.json'
SPREADSHEET_ID = 'SIZNING_SPREADSHEET_ID'  # <-- bu yerga Google Sheets faylingiz ID sini yozing
RANGE_NAME = 'A2:B'  # A ustun = raqami, B ustun = mazmuni (sarlavhasiz)

# Google Sheets API ulanish
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE,
    scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
)
sheets_service = build('sheets', 'v4', credentials=credentials)

# Google Sheetsdan ma'lumot o'qish
def get_constitution_data():
    sheet = sheets_service.spreadsheets()
    result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME).execute()
    values = result.get('values', [])
    data = {}
    for row in values:
        if len(row) >= 2:
            raqam = row[0].strip()
            matn = row[1].strip()
            data[raqam] = matn
    return data

# /start komandasi
def start(update: Update, context: CallbackContext):
    data = get_constitution_data()
    keyboard = [[k] for k in data.keys()]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    update.message.reply_text("Qaysi moddani ko‘rmoqchisiz?", reply_markup=reply_markup)

# Foydalanuvchi tugmani bosganda
def handle_message(update: Update, context: CallbackContext):
    raqam = update.message.text.strip()
    data = get_constitution_data()
    if raqam in data:
        update.message.reply_text(data[raqam])
    else:
        update.message.reply_text("Bunday modda topilmadi. Iltimos, /start ni qayta bosing.")

# Botni ishga tushurish
def main():
    TOKEN = 'SIZNING_BOT_TOKEN'  # <-- bu yerga @BotFather'dan olingan tokenni yozing
    updater = Updater(TOKEN)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
