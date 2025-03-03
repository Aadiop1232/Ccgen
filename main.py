import threading
import time
import requests
import telebot
from telebot import types
import random
import re
from datetime import datetime
from gatet import Tele


TOKEN = "7973439072:AAFhqqrP9-JMCyCW6ljpmLacvQwxTmFE_oc" 
OWNER_ID = 7218606355          

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")


APPROVED_USERS_FILE = "approved_users.txt"
BANNED_USERS_FILE   = "banned_users.txt"

approved_users = set()
banned_users = set()
processing = {}           # For mass check file processing per user
stop_processing = {}      # To signal stop of mass check per user
expecting_mass_file = {}  # Tracks if user has initiated /mchk
mass_results = {}         # Store results for mass checking per user

def load_users(file_path):
    try:
        with open(file_path, "r") as f:
            return set(line.strip() for line in f.readlines())
    except FileNotFoundError:
        return set()

approved_users = load_users(APPROVED_USERS_FILE)
banned_users = load_users(BANNED_USERS_FILE)

def save_user(file_path, user_id):
    with open(file_path, "a") as f:
        f.write(f"{user_id}\n")

# -------------------- CARD GENERATION FUNCTIONS --------------------
def random_int(min_val, max_val):
    return random.randint(min_val, max_val)

def luhn_algorithm(card_number):
    digits = [int(d) for d in card_number]
    for i in range(len(digits) - 1, -1, -2):
        digits[i] *= 2
        if digits[i] > 9:
            digits[i] -= 9
    total_sum = sum(digits)
    check_digit = (total_sum * 9) % 10
    return str(check_digit)

def generate_card(bin_pattern):
    card_number = re.sub(r'x', lambda _: str(random_int(0, 9)), bin_pattern)
    while len(card_number) < 15:
        card_number += str(random_int(0, 9))
    return card_number + luhn_algorithm(card_number)

def generate_cvv():
    return str(random_int(100, 999))

def generate_month():
    return f"{random_int(1, 12):02d}"

def generate_year():
    return f"{(datetime.now().year + random_int(1, 5)) % 100:02d}"

def generate_cards(bin_input, fixed_month=None, fixed_year=None, fixed_cvv=None, amount=10):
    cards = []
    for _ in range(amount):
        card_number = generate_card(bin_input)
        month = fixed_month if fixed_month else generate_month()
        year  = fixed_year if fixed_year else generate_year()
        cvv   = fixed_cvv if fixed_cvv else generate_cvv()
        cards.append(f"{card_number}|{month}|{year}|{cvv}")
    return cards

# -------------------- MESSAGE TEMPLATES --------------------
def generate_approved_message(cc, response, bin_info, time_taken, requester):
    return (
        "𝘼𝙥𝙥𝙧𝙤𝙫𝙚𝙙 ✅\n"
        f"• 𝘾𝙖𝙧𝙙 ➻ <code>{cc}</code>\n"
        f"• 𝙍𝙚𝙨𝙥𝙤𝙣𝙨𝙚 ➻ {response}\n"
        f"• 𝘽𝙞𝙣 𝙄𝙣𝙛𝙤 ➻ {bin_info.get('type', 'Unknown')} ➻ {bin_info.get('brand', 'Unknown')} ➻ {bin_info.get('level', 'Unknown')}\n"
        f"• 𝙄𝙨𝙨𝙪𝙚𝙧 ➻ {bin_info.get('bank', 'Unknown')}\n"
        f"• 𝘽𝙞𝙣 ➻ <code>{cc[:6]}</code>\n"
        f"• 𝙏𝙞𝙢𝙚 𝙏𝙖𝙠𝙚𝙣 ➻ {time_taken}\n"
        f"• 𝙍𝙚𝙦𝙪𝙚𝙨𝙩𝙚𝙙 𝘽𝙮 ➻ {requester}"
        f"• 𝘽𝙤𝙩 𝘽𝙮 ➻ @MrLazyOp"
    )

# -------------------- USER REGISTRATION, HELP & ADMIN NOTIFICATION --------------------
@bot.message_handler(commands=["start", "help"])
def send_welcome(message):
    user_id = str(message.from_user.id)
    if user_id in banned_users:
        bot.reply_to(message, "🚫 You are banned from using this bot.")
        return
    if user_id not in approved_users:
        welcome_text = (
            "👋 𝚆𝚎𝚕𝚌𝚘𝚖𝚎 𝚝𝚘 𝚃𝚑𝚎 𝙲𝙲 𝙲𝚑𝚎𝚌𝚔𝚎𝚛 & 𝙶𝚎𝚗𝚎𝚛𝚊𝚝𝚘𝚛 𝙱𝚘𝚝!\n\n"
            "Please tap 𝚁𝚎𝚐𝚒𝚜𝚝𝚎𝚛 ➻ to start using all features, or tap 𝙷𝚎𝚕𝚙 ➻ to view commands."
        )
        markup = types.InlineKeyboardMarkup()
        btn_reg = types.InlineKeyboardButton("𝚁𝚎𝚐𝚒𝚜𝚝𝚎𝚛 ➻", callback_data="register")
        btn_help = types.InlineKeyboardButton("𝙷𝚎𝚕𝚙 ➻", callback_data="help")
        markup.add(btn_reg, btn_help)
        bot.send_message(message.chat.id, welcome_text, reply_markup=markup)
    else:
        bot.reply_to(message, "✅ 𝙱𝚘𝚝 𝚜𝚝𝚊𝚛𝚝𝚎𝚍 𝚜𝚞𝚌𝚌𝚎𝚜𝚜𝚏𝚞𝚕𝚕𝚢! You can now use all commands.")

@bot.callback_query_handler(func=lambda call: call.data == "register")
def handle_registration(call):
    user_id = str(call.from_user.id)
    if user_id in banned_users:
        bot.answer_callback_query(call.id, "🚫 You are banned and cannot register.")
        return
    if user_id in approved_users:
        bot.answer_callback_query(call.id, "ℹ️ You are already registered.")
        return
    save_user(APPROVED_USERS_FILE, user_id)
    approved_users.add(user_id)
    bot.answer_callback_query(call.id, "✅ Registration successful!")
    bot.send_message(call.message.chat.id, "✅ 𝚁𝚎𝚐𝚒𝚜𝚝𝚛𝚊𝚝𝚒𝚘𝚗 𝚜𝚞𝚌𝚌𝚎𝚜𝚜𝚏𝚞𝚕. You can now use all commands.")

@bot.callback_query_handler(func=lambda call: call.data == "help")
def handle_help(call):
    help_text = (
        "𝙰𝚟𝚊𝚒𝚕𝚊𝚋𝚕𝚎 𝙲𝚘𝚖𝚖𝚊𝚗𝚍𝚜 ➻\n\n"
        "• 𝚂𝚝𝚊𝚛𝚝 – Start the bot and view the welcome message with registration/help buttons.\n"
        "• 𝙼𝚌𝚑𝚔 – Initiate mass CC checking. Then upload a TXT file (max 1000 cards, one per line, format: number|MM|YY|CVV).\n"
        "• 𝙲𝚑𝚔 <cc> – Check a single credit card. (Format: number|MM|YY|CVV)\n"
        "• 𝙶𝚎𝚗 <BIN> [quantity] [CVV|MM|YY] – Generate CCs. (Example: /gen 440066 20 or /gen 440066 15|387)\n"
        "• 𝚂𝚎𝚗𝚍 <message> – (Admin only) Broadcast a message to all approved users.\n"
        "\nFor mass checking, after processing, you'll receive a summary with buttons:\n"
        "   • 𝙰𝚙𝚙𝚛𝚘𝚟𝚎𝚍 CC's\n"
        "   • 𝙳𝚎𝚊𝚍 CC's\n"
        "   • 𝚄𝚗𝚔𝚗𝚘𝚠𝚗 CC's\n"
        "\nTap a button to receive a TXT file of that category. If no CC's exist, you'll be notified."
    )
    bot.answer_callback_query(call.id, "Help info sent!")
    bot.send_message(call.message.chat.id, help_text)

@bot.message_handler(commands=["send"])
def admin_send(message):
    user_id = str(message.from_user.id)
    if user_id != str(OWNER_ID):
        bot.reply_to(message, "🚫 You are not authorized to use this command.")
        return
    parts = message.text.split(" ", 1)
    if len(parts) < 2:
        bot.reply_to(message, "Usage: /send <message>")
        return
    broadcast_msg = parts[1]
    # Broadcast to every approved user
    for uid in approved_users:
        try:
            bot.send_message(uid, f"📢 **Broadcast Message:**\n{broadcast_msg}")
        except Exception as e:
            print(f"Failed to send to {uid}: {e}")
    bot.reply_to(message, "✅ Message sent to all users.")

# -------------------- SINGLE CC CHECKING --------------------
@bot.message_handler(commands=["chk"])
def chk_cc_command(message):
    user_id = str(message.from_user.id)
    if user_id in banned_users or user_id not in approved_users:
        bot.reply_to(message, "❌ You must be registered to use this command.")
        return
    parts = message.text.split(" ", 1)
    if len(parts) < 2 or not parts[1].strip():
        bot.reply_to(message, "❌ Provide a card to check. Example: /chk 4111111111111111|12|25|123")
        return
    cc = parts[1].strip()
    requester = message.from_user.username or message.from_user.first_name or str(message.from_user.id)
    start_time = time.time()
    bin_info = {}
    try:
        bin_data_url = f"https://bins.antipublic.cc/bins/{cc[:6]}"
        bin_info = requests.get(bin_data_url).json()
    except Exception as e:
        print(f"BIN Lookup Error: {e}")
    try:
        result = Tele(cc)
    except Exception as e:
        print(f"Error in Tele: {e}")
        result = {"error": {"message": "Card check failed."}}
    elapsed = f"{time.time() - start_time:.2f}s"
    if "succeeded" in str(result).lower():
        msg = generate_approved_message(cc, "Approved", bin_info, elapsed, requester)
    else:
        reason = "Declined"
        if isinstance(result, dict) and "error" in result:
            reason = result["error"].get("message", "Declined")
        msg = (
            "𝘿𝙚𝙘𝙡𝙞𝙣𝙚𝙙 ❌ ➻\n"
            f"• 𝘾𝙖𝙧𝙙 ➻ <code>{cc}</code>\n"
            f"• 𝘽𝙞𝙣 𝙄𝙣𝙛𝙤 ➻ {bin_info.get('type', 'Unknown')} ➻ {bin_info.get('brand', 'Unknown')} ➻ {bin_info.get('level', 'Unknown')}\n"
            f"• 𝙄𝙨𝙨𝙪𝙚𝙧 ➻ {bin_info.get('bank', 'Unknown')}\n"
            f"• 𝙍𝙚𝙦𝙪𝙚𝙨𝙩𝙚𝙙 𝘽𝙮 ➻ {requester}\n"
            f"• 𝙍𝙚𝙨𝙥𝙤𝙣𝙨𝙚 ➻ {reason}\n"
            f"• 𝙏𝙞𝙢𝙚 𝙏𝙖𝙠𝙚𝙣 ➻ {elapsed}"
        )
    bot.send_message(message.chat.id, msg)

# -------------------- CC GENERATION --------------------
@bot.message_handler(commands=["gen"])
def gen_cc_command(message):
    user_id = str(message.from_user.id)
    if user_id in banned_users or user_id not in approved_users:
        bot.reply_to(message, "❌ You must be registered to use this command.")
        return
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "❌ Please provide a BIN number. Example: /gen 440066 20")
        return
    bin_input = parts[1].strip()
    try:
        quantity = int(parts[2]) if len(parts) >= 3 else 10
    except ValueError:
        quantity = 10
    if quantity > 100:
        quantity = 100  # limit generation quantity
    fixed_month = fixed_year = fixed_cvv = None
    # If additional fixed parameters are provided with pipe separators in bin_input, handle them
    if "|" in bin_input:
        subparts = bin_input.split("|")
        bin_input = subparts[0].strip()
        if len(subparts) >= 2 and re.fullmatch(r"\d{1,2}", subparts[1].strip()):
            fixed_month = subparts[1].strip().zfill(2)
        if len(subparts) >= 3 and re.fullmatch(r"\d{2}", subparts[2].strip()):
            fixed_year = subparts[2].strip()
        if len(subparts) >= 4 and re.fullmatch(r"\d{3,4}", subparts[3].strip()):
            fixed_cvv = subparts[3].strip()
    bin_info = {}
    try:
        bin_data_url = f"https://bins.antipublic.cc/bins/{bin_input[:6]}"
        bin_info = requests.get(bin_data_url).json()
    except Exception as e:
        print(f"BIN Lookup Error: {e}")
    cards = generate_cards(bin_input, fixed_month, fixed_year, fixed_cvv, amount=quantity)
    card_lines = [f"<code>{card}</code>" for card in cards]
    response_text = (
        f"𝘽𝙞𝙣 ➻ <code>{bin_input}</code>\n"
        f"𝙂𝙚𝙣𝙚𝙧𝙖𝙩𝙚𝙙 ➻ ({quantity}) Cards:\n" + "\n".join(card_lines) +
        f"\nType ➻ {bin_info.get('type', 'Unknown').title()}\n"
        f"𝘽𝙧𝙖𝙣𝙙 ➻ {bin_info.get('brand', 'Unknown').title()}\n"
        f"𝙄𝙨𝙨𝙪𝙚𝙧 ➻ {bin_info.get('bank', 'Unknown')}\n"
        f"𝘾𝙤𝙪𝙣𝙩𝙧𝙮 ➻ {bin_info.get('country_name', 'Unknown')} {bin_info.get('country_flag', '')}\n"
    )
    bot.send_message(message.chat.id, response_text)

# -------------------- MASS CC CHECKING --------------------
@bot.message_handler(commands=["mchk"])
def mchk_command(message):
    user_id = str(message.from_user.id)
    if user_id in banned_users or user_id not in approved_users:
        bot.reply_to(message, "❌ You must be registered to use this command.")
        return
    expecting_mass_file[user_id] = True
    bot.reply_to(message, "📄 Please upload your TXT file for mass checking.\nFormat: number|MM|YY|CVV (max 1000 cards).")

@bot.message_handler(content_types=["document"])
def handle_document(message):
    user_id = str(message.from_user.id)
    if user_id in banned_users or user_id not in approved_users:
        bot.reply_to(message, "❌ You must be registered to use this command.")
        return
    if not expecting_mass_file.get(user_id, False):
        bot.reply_to(message, "❌ Please use the /mchk command first to initiate mass checking.")
        return
    expecting_mass_file[user_id] = False
    if processing.get(user_id, False):
        bot.reply_to(message, "⌛ Please wait! Your previous file is still being processed.")
        return
    processing[user_id] = True
    stop_processing[user_id] = False
    file_info = bot.get_file(message.document.file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    file_path = f"combo_{user_id}.txt"
    with open(file_path, "wb") as f:
        f.write(downloaded_file)
    # Limit file to 1000 lines
    with open(file_path, "r") as f:
        lines = f.readlines()
    if len(lines) > 1000:
        lines = lines[:1000]
        with open(file_path, "w") as f:
            f.writelines(lines)
    mass_results[user_id] = {"total": len(lines), "approved": [], "dead": [], "unknown": []}
    status_msg_id = bot.reply_to(message, "🔄 CC checking in progress...\nPress [ STOP 🛑 ] to cancel.").message_id
    threading.Thread(target=process_cards, args=(message, file_path, user_id, status_msg_id)).start()

def process_cards(message, file_path, user_id, status_msg_id):
    try:
        with open(file_path, "r") as f:
            lines = f.readlines()
        total = len(lines)
        for cc in lines:
            if stop_processing.get(user_id, False):
                bot.send_message(message.chat.id, "🛑 Processing stopped by the user.")
                break
            cc = cc.strip()
            # Check basic format (must have 3 pipes)
            if cc.count("|") != 3:
                mass_results[user_id]["unknown"].append(cc)
                continue
            bin_info = {}
            try:
                bin_data_url = f"https://bins.antipublic.cc/bins/{cc[:6]}"
                bin_info = requests.get(bin_data_url).json()
            except Exception as e:
                print(f"BIN Lookup Error: {e}")
            # Update inline status message
            processed = len(mass_results[user_id]["approved"]) + len(mass_results[user_id]["dead"]) + len(mass_results[user_id]["unknown"])
            markup = types.InlineKeyboardMarkup(row_width=1)
            markup.add(
                types.InlineKeyboardButton(f"Processed ➻ {processed}/{total}", callback_data="status"),
                types.InlineKeyboardButton("[ STOP 🛑 ]", callback_data="stop_process")
            )
            try:
                bot.edit_message_text("🔎 CC checking in progress...", chat_id=message.chat.id, message_id=status_msg_id, reply_markup=markup)
            except Exception as e:
                print(f"Edit message error: {e}")
            start_card = time.time()
            try:
                result = Tele(cc)
            except Exception as e:
                print(f"Tele error: {e}")
                result = {"error": {"message": "Request failed."}}
            elapsed = f"{time.time() - start_card:.2f}s"
            if "succeeded" in str(result).lower():
                mass_results[user_id]["approved"].append(cc)
                approved_msg = generate_approved_message(cc, "Approved", bin_info, elapsed, message.from_user.username or message.from_user.first_name)
                bot.send_message(message.chat.id, approved_msg)
            else:
                mass_results[user_id]["dead"].append(cc)
        # After processing, send a summary with buttons (without Total)
        summary_text = (
            "👋 Hey there! I have checked all your CC's and got these results:\n\n"
            f"Approved CC's ➻ {len(mass_results[user_id]['approved'])}\n"
            f"Dead CC's ➻ {len(mass_results[user_id]['dead'])}\n"
            f"Unknown CC's ➻ {len(mass_results[user_id]['unknown'])}\n"
        )
        summary_markup = types.InlineKeyboardMarkup(row_width=2)
        summary_markup.add(
            types.InlineKeyboardButton(f"Approved ➻ {len(mass_results[user_id]['approved'])}", callback_data=f"show_approved_{user_id}"),
            types.InlineKeyboardButton(f"Dead ➻ {len(mass_results[user_id]['dead'])}", callback_data=f"show_dead_{user_id}"),
            types.InlineKeyboardButton(f"Unknown ➻ {len(mass_results[user_id]['unknown'])}", callback_data=f"show_unknown_{user_id}")
        )
        bot.send_message(message.chat.id, summary_text, reply_markup=summary_markup)
    except Exception as e:
        print(f"Error processing cards: {e}")
    finally:
        processing[user_id] = False
        stop_processing[user_id] = False

@bot.callback_query_handler(func=lambda call: call.data.startswith("show_"))
def show_results_callback(call):
    # Format: show_<category>_<user_id>
    parts = call.data.split("_")
    if len(parts) < 3:
        return
    category = parts[1]  # approved, dead, unknown
    user_id = parts[2]
    results = mass_results.get(user_id, {}).get(category, [])
    if not results:
        bot.answer_callback_query(call.id, "😞 Sad, I didn't get any CC's for this category.")
        return
    file_content = "\n".join(results)
    filename = f"{category}_ccs_{user_id}.txt"
    with open(filename, "w") as f:
        f.write(file_content)
    with open(filename, "rb") as f:
        bot.send_document(call.message.chat.id, f, caption=f"📄 {category.capitalize()} CC's")
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "stop_process")
def stop_process_callback(call):
    user_id = str(call.from_user.id)
    if processing.get(user_id, False):
        stop_processing[user_id] = True
        bot.answer_callback_query(call.id, "🛑 Processing has been stopped.")
    else:
        bot.answer_callback_query(call.id, "ℹ️ No ongoing processing to stop.")

@bot.message_handler(commands=["status"])
def status_command(message):
    user_id = str(message.from_user.id)
    if processing.get(user_id, False):
        bot.reply_to(message, "⌛ Your file is still being processed. Please wait.")
    else:
        bot.reply_to(message, "ℹ️ No file is currently being processed.")

@bot.message_handler(commands=["send"])
def admin_send(message):
    # Only owner can use /send
    if str(message.from_user.id) != str(OWNER_ID):
        bot.reply_to(message, "🚫 You are not authorized to use this command.")
        return
    parts = message.text.split(" ", 1)
    if len(parts) < 2:
        bot.reply_to(message, "Usage: /send <message>")
        return
    broadcast_msg = parts[1]
    for uid in approved_users:
        try:
            bot.send_message(uid, f"📢 Broadcast Message ➻\n{broadcast_msg}")
        except Exception as e:
            print(f"Failed to send to {uid}: {e}")
    bot.reply_to(message, "✅ Message sent to all approved users.")

# -------------------- START THE BOT --------------------
bot.polling(none_stop=True)
        
