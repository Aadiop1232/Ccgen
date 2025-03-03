#Dev = @im_satyam_chauhan
#Channel = @MrLazyOp
# Combined Bot: CC Checking, Generation, & Broadcast with Multi-Gateway Support

import threading
import time
import requests
import telebot
from telebot import types
import random
import re
from datetime import datetime
from gatet import Tele_gateway, generate_cards

# -------------------- CONFIGURATION --------------------
TOKEN = "7973439072:AAFhqqrP9-JMCyCW6ljpmLacvQwxTmFE_oc"  # Replace with your bot token
OWNER_ID = 7218606355          # Replace with your Telegram numeric user ID

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# -------------------- GLOBAL STATE & FILE PATHS --------------------
APPROVED_USERS_FILE = "approved_users.txt"
BANNED_USERS_FILE = "banned_users.txt"

approved_users = set()
banned_users = set()
processing = {}            # For mass checking file processing per user
stop_processing = {}       # To signal stopping mass checking per user
expecting_mass_file = {}   # Tracks gateway for mass check: "stripe", "braintree", "paypal"
mass_results = {}          # Store mass check results for each user

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

def generate_cards_custom(bin_input, fixed_month=None, fixed_year=None, fixed_cvv=None, amount=10):
    return generate_cards(bin_input, fixed_month, fixed_year, fixed_cvv, amount)

# -------------------- MESSAGE TEMPLATES --------------------
def format_approved(cc, bin_info, elapsed, requester, gateway_command):
    return (
        f"{gateway_command} 🔥\n"
        "--------------------------------------------------\n"
        f"[ϟ] 𝐂𝐚𝐫𝐝 ➻ {cc}\n"
        f"[ϟ] 𝐒𝐭𝐚𝐭𝐮𝐬 ➻ Approved\n"
        f"[ϟ] 𝐑𝐞𝐬𝐩𝐨𝐧𝐬𝐞 ➻ Approved\n"
        "--------------------------------------------------\n"
        f"[ϟ] 𝐈𝐧𝐟𝐨 ➻ {bin_info.get('type', 'Unknown')} ➻ {bin_info.get('brand', 'Unknown')} ➻ {bin_info.get('level', 'Unknown')}\n"
        f"[ϟ] 𝐁𝐚𝐧𝐤 ➻ {bin_info.get('bank', 'Unknown')}\n"
        f"[ϟ] 𝐂𝐨𝐮𝐧𝐭𝐫𝐲 ➻ {bin_info.get('country_name', 'Unknown')} {bin_info.get('country_flag', '')}\n"
        "--------------------------------------------------\n"
        f"[⌥] 𝐓𝐢𝐦𝐞 ➻ {elapsed} Sec.\n"
        f"[⎇] 𝐑𝐞𝐪 𝐁𝐲 ➻ {requester}\n"
        "--------------------------------------------------\n"
        f"𝐃𝐞𝐯 𝐛𝐲 ➻ @MrLazyOp"
    )

def format_declined(cc, bin_info, elapsed, requester, gateway_command, reason):
    return (
        f"{gateway_command} 🔥\n"
        "--------------------------------------------------\n"
        f"[ϟ] 𝐂𝐚𝐫𝐝 ➻ {cc}\n"
        f"[ϟ] 𝐒𝐭𝐚𝐭𝐮𝐬 ➻ Declined\n"
        f"[ϟ] 𝐑𝐞𝐬𝐩𝐨𝐧𝐬𝐞 ➻ {reason}\n"
        "--------------------------------------------------\n"
        f"[ϟ] 𝐈𝐧𝐟𝐨 ➻ {bin_info.get('type', 'Unknown')} ➻ {bin_info.get('brand', 'Unknown')} ➻ {bin_info.get('level', 'Unknown')}\n"
        f"[ϟ] 𝐁𝐚𝐧𝐤 ➻ {bin_info.get('bank', 'Unknown')}\n"
        f"[ϟ] 𝐂𝐨𝐮𝐧𝐭𝐫𝐲 ➻ {bin_info.get('country_name', 'Unknown')} {bin_info.get('country_flag', '')}\n"
        "--------------------------------------------------\n"
        f"[⌥] 𝐓𝐢𝐦𝐞 ➻ {elapsed} Sec.\n"
        f"[⎇] 𝐑𝐞𝐪 𝐁𝐲 ➻ {requester}\n"
        "--------------------------------------------------\n"
        f"𝐃𝐞𝐯 𝐛𝐲 ➻ @MrLazyOp"
    )

def format_generation(bin_input, quantity, cards, bin_info, elapsed):
    card_lines = "\n".join([f"{card}" for card in cards])
    return (
        "✅ 𝐂𝐂 𝐆𝐞𝐧𝐞𝐫𝐚𝐭𝐢𝐨𝐧 𝐂𝐨𝐦𝐩𝐥𝐞𝐭𝐞 🔥\n"
        "--------------------------------------------------\n"
        f"𝐁𝐢𝐧 ➻ {bin_input}\n"
        f"𝐀𝐦𝐨𝐮𝐧𝐭 ➻ {quantity}\n"
        f"Generated Cards:\n{card_lines}\n"
        "--------------------------------------------------\n"
        f"𝐈𝐧𝐟𝐨 ➻ {bin_info.get('type', 'Unknown').title()}\n"
        f"   ▷ 𝐁𝐀𝐍𝐊 ➻ {bin_info.get('bank', 'Unknown')}\n"
        f"   ▷ 𝐂𝐎𝐔𝐍𝐓𝐑𝐘 ➻ {bin_info.get('country_name', 'Unknown')} {bin_info.get('country_flag', '')}\n"
        "--------------------------------------------------\n"
        f"⏳ 𝐓𝐢𝐦𝐞 𝐓𝐚𝐤𝐞𝐧 ➻ {elapsed} Sec.\n"
        f"- 𝐂𝐡𝐞𝐜𝐤𝐞𝐝 ➻ {bin_info.get('requester', 'Unknown')}\n"
        f"[⌤] 𝐃𝐞𝐯 𝐛𝐲 ➻ @MrLazyOp"
    )

# -------------------- SINGLE CC CHECKING COMMANDS --------------------
def process_single_cc(message, gateway, command_label):
    user_id = str(message.from_user.id)
    if user_id in banned_users or user_id not in approved_users:
        bot.reply_to(message, "❌ You must be registered to use this command.")
        return
    parts = message.text.split(" ", 2)
    if len(parts) < 2 or not parts[1].strip():
        bot.reply_to(message, f"❌ Provide a card to check. Example: {command_label} 4111111111111111|12|25|123")
        return
    # If a gateway is provided in the command, use it; else default to the command's gateway
    if len(parts) == 2:
        cc = parts[1].strip()
    else:
        cc = parts[2].strip()
    requester = message.from_user.username or message.from_user.first_name or str(message.from_user.id)
    start_time = time.time()
    bin_info = {}
    try:
        bin_data_url = f"https://bins.antipublic.cc/bins/{cc[:6]}"
        bin_info = requests.get(bin_data_url).json()
    except Exception as e:
        print(f"BIN Lookup Error: {e}")
    try:
        result = Tele_gateway(gateway, cc)
    except Exception as e:
        print(f"Error in Tele: {e}")
        result = {"error": {"message": "Card check failed."}}
    elapsed = f"{time.time() - start_time:.2f}"
    if "succeeded" in str(result).lower():
        msg = format_approved(cc, bin_info, elapsed, requester, command_label)
    else:
        reason = "Declined"
        if isinstance(result, dict) and "error" in result:
            reason = result["error"].get("message", "Declined")
        msg = format_declined(cc, bin_info, elapsed, requester, command_label, reason)
    bot.send_message(message.chat.id, msg)

@bot.message_handler(commands=["str"])
def chk_stripe(message):
    process_single_cc(message, "stripe", "/str")

@bot.message_handler(commands=["b3"])
def chk_braintree(message):
    process_single_cc(message, "braintree", "/b3")

@bot.message_handler(commands=["pp"])
def chk_paypal(message):
    process_single_cc(message, "paypal", "/pp")

# -------------------- MASS CC CHECKING COMMANDS --------------------
def initiate_mass_check(message, gateway, command_label):
    user_id = str(message.from_user.id)
    if user_id in banned_users or user_id not in approved_users:
        bot.reply_to(message, "❌ You must be registered to use this command.")
        return
    expecting_mass_file[user_id] = gateway  # store which gateway to use
    bot.reply_to(message, f"📄 Please upload your TXT file for mass checking using {command_label}.\nFormat: number|MM|YY|CVV (max 1000 cards).")

@bot.message_handler(commands=["mstr"])
def mchk_stripe(message):
    initiate_mass_check(message, "stripe", "/mstr")

@bot.message_handler(commands=["mb3"])
def mchk_braintree(message):
    initiate_mass_check(message, "braintree", "/mb3")

@bot.message_handler(commands=["mpp"])
def mchk_paypal(message):
    initiate_mass_check(message, "paypal", "/mpp")

@bot.message_handler(content_types=["document"])
def handle_document(message):
    user_id = str(message.from_user.id)
    if user_id in banned_users or user_id not in approved_users:
        bot.reply_to(message, "❌ You must be registered to use this command.")
        return
    gateway = expecting_mass_file.get(user_id, None)
    if not gateway:
        bot.reply_to(message, "❌ Please use the /mchk command first to initiate mass checking with a specific gateway.")
        return
    expecting_mass_file[user_id] = None
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
    threading.Thread(target=process_mass_check, args=(message, file_path, user_id, status_msg_id, gateway)).start()

def process_mass_check(message, file_path, user_id, status_msg_id, gateway):
    try:
        with open(file_path, "r") as f:
            lines = f.readlines()
        total = len(lines)
        for cc in lines:
            if stop_processing.get(user_id, False):
                bot.send_message(message.chat.id, "🛑 Processing stopped by the user.")
                break
            cc = cc.strip()
            if cc.count("|") != 3:
                mass_results[user_id]["unknown"].append(cc)
                continue
            bin_info = {}
            try:
                bin_data_url = f"https://bins.antipublic.cc/bins/{cc[:6]}"
                bin_info = requests.get(bin_data_url).json()
            except Exception as e:
                print(f"BIN Lookup Error: {e}")
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
                result = Tele_gateway(gateway, cc)
            except Exception as e:
                print(f"Tele error: {e}")
                result = {"error": {"message": "Request failed."}}
            elapsed = f"{time.time() - start_card:.2f}"
            if "succeeded" in str(result).lower():
                mass_results[user_id]["approved"].append(cc)
                approved_msg = format_approved(cc, bin_info, elapsed, message.from_user.username or message.from_user.first_name, f"/{gateway[:4]}")
                bot.send_message(message.chat.id, approved_msg)
            else:
                mass_results[user_id]["dead"].append(cc)
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
        print(f"Error in mass processing: {e}")
    finally:
        processing[user_id] = False
        stop_processing[user_id] = False

@bot.callback_query_handler(func=lambda call: call.data.startswith("show_"))
def show_results_callback(call):
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

@bot.message_handler(commands=["ban"])
def ban_command(message):
    if str(message.from_user.id) != str(OWNER_ID):
        bot.reply_to(message, "🚫 You are not authorized to use this command.")
        return
    parts = message.text.split(" ", 1)
    if len(parts) < 2 or not parts[1].strip().isdigit():
        bot.reply_to(message, "Usage: /ban <user_id>")
        return
    target_id = parts[1].strip()
    banned_users.add(target_id)
    # Optionally, remove from approved_users:
    if target_id in approved_users:
        approved_users.remove(target_id)
    save_user(BANNED_USERS_FILE, target_id)
    bot.reply_to(message, f"✅ User {target_id} has been banned.")

@bot.message_handler(commands=["send"])
def admin_send(message):
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
            bot.send_message(uid, f"📢 Broadcast ➻\n{broadcast_msg}")
        except Exception as e:
            print(f"Failed to send to {uid}: {e}")
    bot.reply_to(message, "✅ Message sent to all approved users.")

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
        quantity = 100
    fixed_month = fixed_year = fixed_cvv = None
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
        f"Bin ➻ <code>{bin_input}</code>\n"
        f"Generated ➻ ({quantity}) Cards:\n" + "\n".join(card_lines) +
        f"\nType ➻ {bin_info.get('type', 'Unknown').title()}\n"
        f"Brand ➻ {bin_info.get('brand', 'Unknown').title()}\n"
        f"Issuer ➻ {bin_info.get('bank', 'Unknown')}\n"
        f"Country ➻ {bin_info.get('country_name', 'Unknown')} {bin_info.get('country_flag', '')}\n"
    )
    bot.send_message(message.chat.id, response_text)

# -------------------- START THE BOT --------------------
bot.polling(none_stop=True)
            
