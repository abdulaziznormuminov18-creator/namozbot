import logging
import asyncio
from datetime import datetime, time
import pytz
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import gspread
from google.oauth2.service_account import Credentials
import json
import os

# === SOZLAMALAR ===
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN")
SPREADSHEET_ID = "1zEIXv-r467FzdEetmR6qhEQSoUstNhlK"
GROUP_ID = -1002761583094
TIMEZONE = "Asia/Tashkent"
BOMDOD_START = time(3, 0)   # 03:00 - bot xabar yuboradi
BOMDOD_END = time(5, 35)    # 05:35 - yopiladi

# === GOOGLE SHEETS ULANISH ===
def get_sheet():
    creds_json = os.environ.get("GOOGLE_CREDENTIALS")
    creds_dict = json.loads(creds_json)
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SPREADSHEET_ID)
    try:
        worksheet = sheet.worksheet("Bomdod")
    except:
        worksheet = sheet.add_worksheet(title="Bomdod", rows=1000, cols=10)
        worksheet.append_row(["Ism Familiya", "Telegram Username", "Sana", "Vaqt"])
    return worksheet

# === FOYDALANUVCHI HOLATI ===
user_states = {}
registered_today = set()

def is_bomdod_time():
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz).time()
    return BOMDOD_START <= now <= BOMDOD_END

def get_today():
    tz = pytz.timezone(TIMEZONE)
    return datetime.now(tz).strftime("%Y-%m-%d")

# === START KOMANDASI ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    today = get_today()

    if not is_bomdod_time():
        tz = pytz.timezone(TIMEZONE)
        now = datetime.now(tz)
        await update.message.reply_text(
            f"Assalomu alaykum! 🌙\n\n"
            f"Hozir soat {now.strftime('%H:%M')}.\n"
            f"Bomdod yo'qlama vaqti: 03:00 — 05:35 oralig'ida.\n\n"
            f"O'sha vaqtda keling! ✅"
        )
        return

    if f"{user_id}_{today}" in registered_today:
        await update.message.reply_text(
            "Siz bugun allaqachon qatnashgansiz! ✅\n"
            "JazakAllahu khayran! 🤲"
        )
        return

    user_states[user_id] = "waiting_name"
    await update.message.reply_text(
        "Assalomu alaykum! 🌅\n\n"
        "Bomdod namozi yo'qlamasiga xush kelibsiz!\n\n"
        "Iltimos, to'liq *Ism Familiyangizni* yozing:",
        parse_mode="Markdown"
    )

# === ISM FAMILIYA QABUL QILISH ===
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    today = get_today()

    if user_states.get(user_id) != "waiting_name":
        await update.message.reply_text("Yo'qlama uchun /start bosing. 👋")
        return

    if not is_bomdod_time():
        await update.message.reply_text("Vaqt o'tib ketdi. Ertaga 03:00 da keling! 🌙")
        user_states.pop(user_id, None)
        return

    if f"{user_id}_{today}" in registered_today:
        await update.message.reply_text("Siz bugun allaqachon qatnashgansiz! ✅")
        user_states.pop(user_id, None)
        return

    name = update.message.text.strip()
    if len(name) < 3:
        await update.message.reply_text("Iltimos, to'liq ism familiyangizni yozing. 📝")
        return

    context.user_data["name"] = name
    keyboard = [
        [InlineKeyboardButton("✅ Bomdod namozini o'qidim", callback_data="confirmed")],
        [InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"Ism: *{name}*\n\n"
        f"Bomdod namozini o'qiganingizni tasdiqlaysizmi?",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

# === TUGMA BOSILGANDA ===
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    today = get_today()

    if query.data == "cancel":
        user_states.pop(user_id, None)
        await query.edit_message_text("Bekor qilindi. Qaytib kelishingiz mumkin! 🌙")
        return

    if query.data == "confirmed":
        if f"{user_id}_{today}" in registered_today:
            await query.edit_message_text("Siz bugun allaqachon qatnashgansiz! ✅")
            return
        if not is_bomdod_time():
            await query.edit_message_text("Vaqt o'tib ketdi. Ertaga keling! 🌙")
            return

        name = context.user_data.get("name", "Noma'lum")
        username = query.from_user.username or "username yoq"
        tz = pytz.timezone(TIMEZONE)
        now = datetime.now(tz)
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M")

        try:
            sheet = get_sheet()
            sheet.append_row([name, f"@{username}", date_str, time_str])
            registered_today.add(f"{user_id}_{today}")
            user_states.pop(user_id, None)
            await query.edit_message_text(
                f"✅ *Qayd etildi!*\n\n"
                f"👤 Ism: {name}\n"
                f"📅 Sana: {date_str}\n"
                f"⏰ Vaqt: {time_str}\n\n"
                f"JazakAllahu khayran! 🤲\n"
                f"Bomdod namozi qabul bo'lsin! 🌅",
                parse_mode="Markdown"
            )
        except Exception as e:
            logging.error(f"Sheets xato: {e}")
            await query.edit_message_text("Xato yuz berdi. Iltimos qayta urinib ko'ring. 🔄")

# === STATISTIKA ===
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    today = get_today()
    count = sum(1 for key in registered_today if key.endswith(f"_{today}"))
    await update.message.reply_text(
        f"📊 *Bugungi statistika*\n\n"
        f"📅 Sana: {today}\n"
        f"✅ Qatnashganlar: {count} kishi",
        parse_mode="Markdown"
    )

# === GURUHGA AVTOMATIK XABAR ===
async def send_bomdod_reminder(context: ContextTypes.DEFAULT_TYPE):
    bot_username = (await context.bot.get_me()).username
    await context.bot.send_message(
        chat_id=GROUP_ID,
        text=(
            "🌅 *Bomdod namozi vaqti!*\n\n"
            "Assalomu alaykum, aziz singillar! 🤲\n\n"
            "Bomdod namozini o'qib, botga kiring va belgilang:\n"
            f"👉 @{bot_username}\n\n"
            "⏰ Qabul vaqti: 03:00 — 05:35\n"
            "Alloh qabul qilsin! 🌙"
        ),
        parse_mode="Markdown"
    )

# === ASOSIY FUNKSIYA ===
def main():
    logging.basicConfig(level=logging.INFO)
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Har kuni 03:00 da guruhga xabar yuborish
    tz = pytz.timezone(TIMEZONE)
    app.job_queue.run_daily(
        send_bomdod_reminder,
        time=time(3, 0),
        tzinfo=tz
    )

    print("Bot ishlamoqda... 🚀")
    app.run_polling()

if __name__ == "__main__":
    main()
