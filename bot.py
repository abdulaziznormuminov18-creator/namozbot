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
SPREADSHEET_ID = "1nLeSnPXHA5vJvd5oEsZlZ45mSrPg6UMzuO0CyZpzW3k"
GROUP_ID = -1002761583094
TIMEZONE = "Asia/Tashkent"
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))  # Sizning Telegram ID ingiz

bot = telebot.TeleBot(BOT_TOKEN)
user_states = {}
registered_today = set()

# ─── YORDAMCHI FUNKSIYALAR ────────────────────────────────────

def is_bomdod_time():
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)
    minutes = now.hour * 60 + now.minute
    return 180 <= minutes <= 335  # 03:00 dan 05:35 gacha

def get_today():
    return datetime.now(pytz.timezone(TIMEZONE)).strftime("%Y-%m-%d")

def get_zikr_sheet():
    logging.info(f"SPREADSHEET_ID={SPREADSHEET_ID}")

    creds_json = os.environ.get("GOOGLE_CREDENTIALS", "{}")
    creds_dict = json.loads(creds_json)
    scopes = ["https://www.googleapis.com/auth/spreadsheets",
              "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SPREADSHEET_ID)

    try:
        ws = sheet.worksheet("Zikr")
    except:
        ws = sheet.add_worksheet("Zikr", 2000, 10)
        ws.append_row(["UserID", "Ism", "Username", "Sana", "Zikr", "Son", "Vaqt"])

    return ws

def get_zikr_sheet():
    creds_json = os.environ.get("GOOGLE_CREDENTIALS", "{}")
    creds_dict = json.loads(creds_json)
    scopes = ["https://www.googleapis.com/auth/spreadsheets",
              "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SPREADSHEET_ID)
    try:
        ws = sheet.worksheet("Zikr")
    except:
        ws = sheet.add_worksheet("Zikr", 2000, 10)
        ws.append_row(["UserID", "Ism", "Username", "Sana", "Zikr", "Son", "Vaqt"])
    return ws

# ─── ZIKR: Google Sheets bilan ishlash ───────────────────────

def zikr_get_today_entries(uid):
    """Bugungi foydalanuvchi zikrlarini qaytaradi: {zikr_nomi: {son, row_index}}"""
    today = get_today()
    try:
        ws = get_zikr_sheet()
        all_rows = ws.get_all_values()
        result = {}
        for i, row in enumerate(all_rows[1:], start=2):  # 1-qator sarlavha
            if len(row) >= 6 and str(row[0]) == str(uid) and row[3] == today:
                result[row[4]] = {"son": int(row[5]), "row": i}
        return result
    except Exception as e:
        logging.error(f"zikr_get_today_entries: {e}")
        return {}

def zikr_save(uid, name, username, zikr_nomi, son, mode="add"):
    """Zikrni saqlash yoki yangilash"""
    today = get_today()
    now = datetime.now(pytz.timezone(TIMEZONE))
    try:
        ws = get_zikr_sheet()
        entries = zikr_get_today_entries(uid)
        if zikr_nomi in entries:
            row_idx = entries[zikr_nomi]["row"]
            old_son = entries[zikr_nomi]["son"]
            new_son = son if mode == "replace" else old_son + son
            ws.update_cell(row_idx, 6, new_son)
            ws.update_cell(row_idx, 7, now.strftime("%H:%M"))
            return new_son
        else:
            ws.append_row([str(uid), name, f"@{username}", today, zikr_nomi, son, now.strftime("%H:%M")])
            return son
    except Exception as e:
        logging.error(f"zikr_save: {e}")
        return None

def zikr_get_all_today():
    """Admin uchun: bugungi barcha zikrlar"""
    today = get_today()
    try:
        ws = get_zikr_sheet()
        all_rows = ws.get_all_values()
        result = {}
        for row in all_rows[1:]:
            if len(row) >= 6 and row[3] == today:
                name = row[1]
                son = int(row[5])
                if name not in result:
                    result[name] = 0
                result[name] += son
        return result
    except Exception as e:
        logging.error(f"zikr_get_all_today: {e}")
        return {}

# ─── ASOSIY MENYU ─────────────────────────────────────────────

def main_menu(uid):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🕌 Bomdod yo'qlama", "📿 Zikr bo'limi")
    markup.row("📊 Mening statistikam")
    if uid == ADMIN_ID:
        markup.row("👑 Admin panel")
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    if message.chat.type != "private":
        return
    uid = message.from_user.id
    bot.send_message(uid,
        "Assalomu alaykum! 🌙\n\nQuyidagilardan birini tanlang:",
        reply_markup=main_menu(uid)
    )

# ─── BOMDOD YO'QLAMA ──────────────────────────────────────────

@bot.message_handler(func=lambda m: m.text == "🕌 Bomdod yo'qlama" and m.chat.type == "private")
def bomdod_start(message):
    uid = message.from_user.id
    today = get_today()

    if not is_bomdod_time():
        now = datetime.now(pytz.timezone(TIMEZONE))
        bot.send_message(uid,
            f"Assalomu alaykum! 🌙\n"
            f"Hozir soat {now.strftime('%H:%M')}.\n"
            f"Yo'qlama vaqti: 03:00 — 05:35\n"
            f"O'sha vaqtda keling! ✅"
        )
        return

    if f"{uid}_{today}" in registered_today:
        bot.send_message(uid, "Bugun qatnashgansiz! ✅ JazakAllahu khayran! 🤲")
        return

    user_states[uid] = "bomdod_waiting_name"
    bot.send_message(uid,
        "Bomdod yo'qlamasiga xush kelibsiz! 🌅\n\n"
        "To'liq Ism Familiyangizni yozing:"
    )

# ─── ZIKR BO'LIMI ─────────────────────────────────────────────

@bot.message_handler(func=lambda m: m.text == "📿 Zikr bo'limi" and m.chat.type == "private")
def zikr_bolim(message):
    uid = message.from_user.id
    user_states[uid] = "zikr_waiting_name"
    bot.send_message(uid,
        "📿 *Zikr bo'limi*\n\n"
        "Ismingizni yozing:",
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda m: m.chat.type == "private" and user_states.get(m.from_user.id) == "zikr_waiting_name")
def zikr_get_name(message):
    uid = message.from_user.id
    name = message.text.strip()
    if len(name) < 2:
        bot.send_message(uid, "Iltimos, to'liq ism yozing.")
        return
    user_states[uid] = f"zikr_name_{name}"
    bot.send_message(uid,
        "Bugun qaysi zikrni aytdingiz? ✍️\n\n"
        "Masalan: Astag'firulloh, Subhanalloh, Alhamdulilloh, Allahu akbar, Salovat...\n\n"
        "Yoki quyidagilardan birini tanlang:",
        reply_markup=zikr_type_markup()
    )

def zikr_type_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("سُبْحَانَ اللَّهِ SubhanAlloh", "الْحَمْدُ لِلَّهِ Alhamdulilloh")
    markup.row("اللَّهُ أَكْبَرُ Allahu akbar", "أَسْتَغْفِرُ اللَّهَ Astag'firulloh")
    markup.row("لَا إِلَهَ إِلَّا اللَّهُ La ilaha illalloh", "Salovat")
    markup.row("🔙 Orqaga")
    return markup

@bot.message_handler(func=lambda m: m.chat.type == "private" and str(user_states.get(m.from_user.id, "")).startswith("zikr_name_"))
def zikr_get_type(message):
    uid = message.from_user.id
    if message.text == "🔙 Orqaga":
        user_states.pop(uid, None)
        bot.send_message(uid, "Asosiy menyu:", reply_markup=main_menu(uid))
        return

    state = user_states[uid]
    name = state.replace("zikr_name_", "", 1)
    zikr_nomi = message.text.strip()

    user_states[uid] = f"zikr_count_{name}|{zikr_nomi}"

    # Bugun bu zikrni kiritganmi?
    entries = zikr_get_today_entries(uid)
    if zikr_nomi in entries:
        old_son = entries[zikr_nomi]["son"]
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row("➕ Qo'shish", "✏️ Almashtirish")
        markup.row("🔙 Orqaga")
        bot.send_message(uid,
            f"📿 {zikr_nomi}\n"
            f"🔢 Bugun: *{old_son} ta*\n\n"
            f"Nechta qo'shamiz yoki almashtiramiz?",
            parse_mode="Markdown",
            reply_markup=markup
        )
        user_states[uid] = f"zikr_edit_{name}|{zikr_nomi}|{old_son}"
    else:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row("🔙 Orqaga")
        bot.send_message(uid,
            f"📿 *{zikr_nomi}*\n\nNecha marta aytdingiz? 🔢",
            parse_mode="Markdown",
            reply_markup=markup
        )

@bot.message_handler(func=lambda m: m.chat.type == "private" and str(user_states.get(m.from_user.id, "")).startswith("zikr_edit_"))
def zikr_edit_choice(message):
    uid = message.from_user.id
    if message.text == "🔙 Orqaga":
        user_states.pop(uid, None)
        bot.send_message(uid, "Asosiy menyu:", reply_markup=main_menu(uid))
        return

    state = user_states[uid]
    parts = state.replace("zikr_edit_", "", 1).split("|")
    name, zikr_nomi, old_son = parts[0], parts[1], int(parts[2])

    if message.text == "➕ Qo'shish":
        user_states[uid] = f"zikr_count_{name}|{zikr_nomi}|add"
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row("🔙 Orqaga")
        bot.send_message(uid, f"Qancha qo'shamiz? (Hozir: {old_son} ta)", reply_markup=markup)
    elif message.text == "✏️ Almashtirish":
        user_states[uid] = f"zikr_count_{name}|{zikr_nomi}|replace"
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row("🔙 Orqaga")
        bot.send_message(uid, "Yangi son necha? 🔢", reply_markup=markup)

@bot.message_handler(func=lambda m: m.chat.type == "private" and str(user_states.get(m.from_user.id, "")).startswith("zikr_count_"))
def zikr_save_count(message):
    uid = message.from_user.id
    if message.text == "🔙 Orqaga":
        user_states.pop(uid, None)
        bot.send_message(uid, "Asosiy menyu:", reply_markup=main_menu(uid))
        return

    try:
        son = int(message.text.strip())
        if son < 1:
            raise ValueError
    except:
        bot.send_message(uid, "Iltimos, to'g'ri son kiriting. Masalan: 100")
        return

    state = user_states[uid]
    parts = state.replace("zikr_count_", "", 1).split("|")
    name = parts[0]
    zikr_nomi = parts[1]
    mode = parts[2] if len(parts) > 2 else "add"
    username = message.from_user.username or "yoq"

    new_son = zikr_save(uid, name, username, zikr_nomi, son, mode)
    user_states.pop(uid, None)

    if new_son is not None:
        markup = types.InlineKeyboardMarkup()
        markup.row(
            types.InlineKeyboardButton("➕ Yana qo'shish", callback_data=f"zikr_more|{name}|{zikr_nomi}"),
            types.InlineKeyboardButton("📊 Statistika", callback_data="zikr_stats")
        )
        bot.send_message(uid,
            f"✅ *Saqlandi!*\n\n"
            f"📿 {zikr_nomi}\n"
            f"🔢 {new_son} ta",
            parse_mode="Markdown",
            reply_markup=markup
        )
        bot.send_message(uid, "Asosiy menyu:", reply_markup=main_menu(uid))
    else:
        bot.send_message(uid, "❌ Xato yuz berdi. Qayta urinib ko'ring.", reply_markup=main_menu(uid))

# ─── STATISTIKA ───────────────────────────────────────────────

@bot.message_handler(func=lambda m: m.text == "📊 Mening statistikam" and m.chat.type == "private")
def my_stats(message):
    uid = message.from_user.id
    entries = zikr_get_today_entries(uid)

    if not entries:
        bot.send_message(uid,
            "📊 *Mening statistikam*\n\n"
            "📅 Bugun hali zikr kiritilmagan.\n\n"
            "📿 Zikr bo'limi ga boring!",
            parse_mode="Markdown"
        )
        return

    text = "📊 *Mening statistikam*\n\n📅 Bugun:\n"
    jami = 0
    for zikr, data in entries.items():
        text += f"📿 {zikr} — *{data['son']}*\n"
        jami += data['son']
    text += f"\n🌟 Jami: *{jami} ta*"

    bot.send_message(uid, text, parse_mode="Markdown")

# ─── ADMIN PANEL ──────────────────────────────────────────────

@bot.message_handler(func=lambda m: m.text == "👑 Admin panel" and m.chat.type == "private")
def admin_panel(message):
    uid = message.from_user.id
    if uid != ADMIN_ID:
        bot.send_message(uid, "Ruxsat yo'q! ❌")
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("📊 Bugungi faollar", "📋 Bugungi yo'qlama")
    markup.row("🔙 Orqaga")
    bot.send_message(uid, "👑 *Admin panel*", parse_mode="Markdown", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "📊 Bugungi faollar" and m.chat.type == "private")
def admin_zikr_stats(message):
    uid = message.from_user.id
    if uid != ADMIN_ID:
        return

    data = zikr_get_all_today()
    if not data:
        bot.send_message(uid, "📊 Bugun hali zikr kiritilmagan.")
        return

    sorted_data = sorted(data.items(), key=lambda x: x[1], reverse=True)
    medals = ["🥇", "🥈", "🥉"]
    text = f"📊 *Bugungi faollar* ({get_today()})\n\n"
    for i, (name, son) in enumerate(sorted_data):
        medal = medals[i] if i < 3 else f"{i+1}."
        text += f"{medal} {name} — *{son}* ta\n"

    total = sum(data.values())
    text += f"\n🌟 Jami: *{total}* ta zikr\n👥 {len(data)} kishi"

    bot.send_message(uid, text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "📋 Bugungi yo'qlama" and m.chat.type == "private")
def admin_bomdod_stats(message):
    uid = message.from_user.id
    if uid != ADMIN_ID:
        return
    today = get_today()
    count = sum(1 for k in registered_today if k.endswith(f"_{today}"))
    bot.send_message(uid, f"📋 Bugungi bomdod yo'qlama:\n✅ {count} kishi qatnashdi")

@bot.message_handler(func=lambda m: m.text == "🔙 Orqaga" and m.chat.type == "private")
def back_to_main(message):
    uid = message.from_user.id
    user_states.pop(uid, None)
    bot.send_message(uid, "Asosiy menyu:", reply_markup=main_menu(uid))

# ─── CALLBACK HANDLER ─────────────────────────────────────────

@bot.callback_query_handler(func=lambda call: call.data.startswith("zikr_"))
def zikr_callback(call):
    uid = call.from_user.id

    if call.data == "zikr_stats":
        bot.answer_callback_query(call.id)
        entries = zikr_get_today_entries(uid)
        if not entries:
            bot.send_message(uid, "Hali zikr kiritilmagan.")
            return
        text = "📊 *Bugungi zikrlaringiz:*\n\n"
        jami = 0
        for zikr, data in entries.items():
            text += f"📿 {zikr} — *{data['son']}*\n"
            jami += data['son']
        text += f"\n🌟 Jami: *{jami} ta*"
        bot.send_message(uid, text, parse_mode="Markdown")

    elif call.data.startswith("zikr_more|"):
        bot.answer_callback_query(call.id)
        parts = call.data.split("|")
        name, zikr_nomi = parts[1], parts[2]
        user_states[uid] = f"zikr_count_{name}|{zikr_nomi}|add"
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row("🔙 Orqaga")
        bot.send_message(uid, f"📿 {zikr_nomi}\n\nQancha qo'shamiz?", reply_markup=markup)

# ─── BOMDOD: ism kutish ───────────────────────────────────────

@bot.message_handler(func=lambda m: m.chat.type == "private" and user_states.get(m.from_user.id) == "bomdod_waiting_name")
def bomdod_get_name(message):
    uid = message.from_user.id
    today = get_today()

    if not is_bomdod_time():
        user_states.pop(uid, None)
        bot.send_message(uid, "Vaqt o'tdi. Ertaga 03:00 da keling! 🌙", reply_markup=main_menu(uid))
        return

    if f"{uid}_{today}" in registered_today:
        user_states.pop(uid, None)
        bot.send_message(uid, "Bugun qatnashgansiz! ✅", reply_markup=main_menu(uid))
        return

    name = message.text.strip()
    if len(name) < 3:
        bot.send_message(uid, "To'liq ism familiya yozing. 📝")
        return

    user_states[uid] = f"confirm_{name}"
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ Bomdod namozini o'qidim", callback_data="bomdod_yes"),
        types.InlineKeyboardButton("❌ Bekor", callback_data="bomdod_no")
    )
    bot.send_message(uid, f"Ism: {name}\n\nTasdiqlaysizmi?", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data in ["bomdod_yes", "bomdod_no"])
def bomdod_callback(call):
    uid = call.from_user.id
    today = get_today()

    if call.data == "bomdod_no":
        user_states.pop(uid, None)
        bot.edit_message_text("Bekor qilindi. 🌙", uid, call.message.message_id)
        bot.send_message(uid, "Asosiy menyu:", reply_markup=main_menu(uid))
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
        bot.send_message(uid, "Asosiy menyu:", reply_markup=main_menu(uid))
    except Exception as e:
        logging.error(e)
        bot.edit_message_text("Xato! Qayta urinib ko'ring. 🔄", uid, call.message.message_id)

    bot.answer_callback_query(call.id)

logging.info("Bot ishlamoqda!")
bot.infinity_polling()
