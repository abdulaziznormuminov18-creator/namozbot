import logging
import json
import os
from datetime import datetime
import pytz
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)
import gspread
from google.oauth2.service_account import Credentials

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
SPREADSHEET_ID = "1zEIXv-r467FzdEetmR6qhEQSoUstNhlK"
GROUP_ID = -1002761583094
TIMEZONE = "Asia/Tashkent"

user_states = {}
registered_today = set()

def is_bomdod_time():
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)
    h, m = now.hour, now.minute
    start = h * 60 + m >= 3 * 60
    end = h * 60 + m <= 5 * 60 + 35
    return start and end

def get_today():
    return datetime.now(pytz.timezone(TIMEZONE)).strftime("%Y-%m-%d")

def get_sheet():
    creds_json = os.environ.get("GOOGLE_CREDENTIALS", "{}")
    creds_dict = json.loads(creds_json)
    scopes = ["https://www.googleapis.com/auth/spreadsheets",
              "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SPREADSHEET_ID)
    try:
        ws = sheet.worksheet("Bomdod")
    except:
        ws = sheet.add_worksheet("Bomdod", 1000, 10)
        ws.append_row(["Ism Familiya", "Username", "Sana", "Vaqt"])
    return ws

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    today = get_today()
    if not is_bomdod_time():
        now = datetime.now(pytz.timezone(TIMEZONE))
        await update.message.reply_text(
            f"Assalomu alaykum! 🌙\nHozir soat {now.strftime('%H:%M')}.\n"
            f"Yo'qlama vaqti: 03:00—05:35\nO'sha vaqtda keling! ✅"
        )
        return
    if f"{uid}_{today}" in registered_today:
        await update.message.reply_text("Bugun qatnashgansiz! ✅ JazakAllahu khayran!")
        return
    user_states[uid] = "waiting_name"
    await update.message.reply_text(
        "Assalomu alaykum! 🌅\nBomdod yo'qlamasiga xush kelibsiz!\n\n"
        "To'liq *Ism Familiyangizni* yozing:",
        parse_mode="Markdown"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    today = get_today()
    if user_states.get(uid) != "waiting_name":
        await update.message.reply_text("Yo'qlama uchun /start bosing.")
        return
    if not is_bomdod_time():
        user_states.pop(uid, None)
        await update.message.reply_text("Vaqt o'tdi. Ertaga 03:00 da keling! 🌙")
        return
    if f"{uid}_{today}" in registered_today:
        user_states.pop(uid, None)
        await update.message.reply_text("Bugun qatnashgansiz! ✅")
        return
    name = update.message.text.strip()
    if len(name) < 3:
        await update.message.reply_text("To'liq ism familiya yozing. 📝")
        return
    context.user_data["name"] = name
    kb = [[InlineKeyboardButton("✅ Bomdod namozini o'qidim", callback_data="yes")],
          [InlineKeyboardButton("❌ Bekor", callback_data="no")]]
    await update.message.reply_text(
        f"*{name}*\n\nTasdiqlaysizmi?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb)
    )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    today = get_today()
    if q.data == "no":
        user_states.pop(uid, None)
        await q.edit_message_text("Bekor qilindi. 🌙")
        return
    if f"{uid}_{today}" in registered_today:
        await q.edit_message_text("Bugun qatnashgansiz! ✅")
        return
    if not is_bomdod_time():
        await q.edit_message_text("Vaqt o'tdi! 🌙")
        return
    name = context.user_data.get("name", "Noma'lum")
    uname = q.from_user.username or "yoq"
    now = datetime.now(pytz.timezone(TIMEZONE))
    try:
        ws = get_sheet()
        ws.append_row([name, f"@{uname}", now.strftime("%Y-%m-%d"), now.strftime("%H:%M")])
        registered_today.add(f"{uid}_{today}")
        user_states.pop(uid, None)
        await q.edit_message_text(
            f"✅ *Qayd etildi!*\n\n👤 {name}\n📅 {now.strftime('%Y-%m-%d')}\n"
            f"⏰ {now.strftime('%H:%M')}\n\nJazakAllahu khayran! 🤲",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(e)
        await q.edit_message_text("Xato! Qayta urinib ko'ring. 🔄")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    today = get_today()
    count = sum(1 for k in registered_today if k.endswith(f"_{today}"))
    await update.message.reply_text(f"📊 Bugun: {count} kishi ✅")

async def reminder(context: ContextTypes.DEFAULT_TYPE):
    try:
        me = await context.bot.get_me()
        await context.bot.send_message(
            chat_id=GROUP_ID,
            text=f"🌅 *Bomdod vaqti!*\n\nBotga kiring: @{me.username}\n⏰ 03:00—05:35",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(e)

def main():
    from telegram.ext import Application
    import asyncio
    
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    tz = pytz.timezone(TIMEZONE)
    from datetime import time as dtime
    app.job_queue.run_daily(reminder, time=dtime(3, 0, tzinfo=tz))
    
    logger.info("Bot ishlamoqda!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
