import telebot
from telebot import types
import gspread
from google.oauth2.service_account import Credentials
import json
import os
from datetime import datetime
import pytz
import logging

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
SPREADSHEET_ID = "1zEIXv-r467FzdEetmR6qhEQSoUstNhlK"
GROUP_ID = -1002761583094
TIMEZONE = "Asia/Tashkent"

bot = telebot.TeleBot(BOT_TOKEN)
user_states = {}
registered_today = set()

def is_bomdod_time():
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)
    minutes = now.hour * 60 + now.minute
    return 180 <= minutes <= 335  # 03:00 dan 05:35 gacha

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

@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    today = get_today()
    
    if not is_bomdod_time():
        now = datetime.now(pytz.timezone(TIMEZONE))
        bot.reply_to(message,
            f"Assalomu alaykum! 🌙\n"
            f"Hozir soat {now.strftime('%H:%M')}.\n"
            f"Yo'qlama vaqti: 03:00 — 05:35\n"
            f"O'sha vaqtda keling! ✅"
        )
        return
    
    if f"{uid}_{today}" in registered_today:
        bot.reply_to(message, "Bugun qatnashgansiz! ✅ JazakAllahu khayran! 🤲")
        return
    
    user_states[uid] = "waiting_name"
    bot.reply_to(message,
        "Assalomu alaykum! 🌅\n\n"
        "Bomdod yo'qlamasiga xush kelibsiz!\n\n"
        "To'liq Ism Familiyangizni yozing:"
    )

@bot.message_handler(commands=['stats'])
def stats(message):
    today = get_today()
    count = sum(1 for k in registered_today if k.endswith(f"_{today}"))
    bot.reply_to(message, f"📊 Bugun: {count} kishi ✅")

@bot.message_handler(func=lambda m: True)
def handle_message(message):
    uid = message.from_user.id
    today = get_today()
    
    if user_states.get(uid) != "waiting_name":
        bot.reply_to(message, "Yo'qlama uchun /start bosing. 👋")
        return
    
    if not is_bomdod_time():
        user_states.pop(uid, None)
        bot.reply_to(message, "Vaqt o'tdi. Ertaga 03:00 da keling! 🌙")
        return
    
    if f"{uid}_{today}" in registered_today:
        user_states.pop(uid, None)
        bot.reply_to(message, "Bugun qatnashgansiz! ✅")
        return
    
    name = message.text.strip()
    if len(name) < 3:
        bot.reply_to(message, "To'liq ism familiya yozing. 📝")
        return
    
    user_states[uid] = f"confirm_{name}"
    
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ Bomdod namozini o'qidim", callback_data="yes"),
        types.InlineKeyboardButton("❌ Bekor", callback_data="no")
    )
    bot.send_message(uid,
        f"Ism: {name}\n\nTasdiqlaysizmi?",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    uid = call.from_user.id
    today = get_today()
    
    if call.data == "no":
        user_states.pop(uid, None)
        bot.edit_message_text("Bekor qilindi. 🌙", uid, call.message.message_id)
        return
    
    state = user_states.get(uid, "")
    if not state.startswith("confirm_"):
        bot.answer_callback_query(call.id)
        return
    
    name = state.replace("confirm_", "", 1)
    
    if f"{uid}_{today}" in registered_today:
        bot.edit_message_text("Bugun qatnashgansiz! ✅", uid, call.message.message_id)
        return
    
    if not is_bomdod_time():
        bot.edit_message_text("Vaqt o'tdi! 🌙", uid, call.message.message_id)
        return
    
    uname = call.from_user.username or "yoq"
    now = datetime.now(pytz.timezone(TIMEZONE))
    
    try:
        ws = get_sheet()
        ws.append_row([name, f"@{uname}", now.strftime("%Y-%m-%d"), now.strftime("%H:%M")])
        registered_today.add(f"{uid}_{today}")
        user_states.pop(uid, None)
        bot.edit_message_text(
            f"✅ Qayd etildi!\n\n"
            f"👤 {name}\n"
            f"📅 {now.strftime('%Y-%m-%d')}\n"
            f"⏰ {now.strftime('%H:%M')}\n\n"
            f"JazakAllahu khayran! 🤲",
            uid, call.message.message_id
        )
    except Exception as e:
        logging.error(e)
        bot.edit_message_text("Xato! Qayta urinib ko'ring. 🔄", uid, call.message.message_id)
    
    bot.answer_callback_query(call.id)

logging.info("Bot ishlamoqda!")
bot.infinity_polling()
