import time
from telegram import Update
from telegram.ext import ContextTypes
import asyncio
from utils.config import(
    short_term_limit,
    short_term_max_request,
    long_term_ban_time,
    long_term_limit,
    long_term_max_request,
    banned_time,
    banned_users,
    global_max_request,
    global_requests,
    global_time_limit,
    user_requests,
    db,
    channel_id,
    FIREBASE_URL,
    fernet
)
import sqlite3, re
from utils.db import gemini_model_list

async def is_ddos(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id):
    try:
        now = time.time()

        # Master user bypass 😘
        if user_id == 5888166321:
            return False

        # Ban check
        if user_id in banned_users:
            ban_info = banned_users[user_id]
            if now - ban_info['time'] > ban_info['duration']:
                del banned_users[user_id]
            else:
                return True

        # Global rate limiting
        global_requests[:] = [req for req in global_requests if now - req < global_time_limit]
        global_requests.append(now)
        if len(global_requests) > global_max_request:
            await update.message.reply_text("🌐 Global rate limit exceeded. Please try again later.")
            return True

        # Track user requests
        user_requests[user_id][:] = [req for req in user_requests[user_id] if now - req < long_term_limit]
        user_requests[user_id].append(now)

        # Long-term spam check
        if len(user_requests[user_id]) > long_term_max_request:
            banned_users[user_id] = {'time': now, 'duration': long_term_ban_time}
            await update.message.reply_text(
                f"🚨 Spamming Detected!\n\nYou are banned for {long_term_ban_time} seconds."
            )
            return True

        # Short-term spam check
        recent_short = [req for req in user_requests[user_id] if now - req < short_term_limit]
        if len(recent_short) > short_term_max_request:
            banned_users[user_id] = {'time': now, 'duration': banned_time}
            await update.message.reply_text(
                f"⚠️ Too many messages in a short time!\n\nYou are banned for {banned_time} seconds."
            )
            return True

        return False
    except Exception as e:
        print(f"Error in is_ddos function. Error Code - {e}")



#funtion to send message to chaneel
async def send_to_channel(update: Update, content : ContextTypes.DEFAULT_TYPE, chat_id, message) -> None:
    try:
        await content.bot.send_message(chat_id=chat_id, text=message)
    except Exception as e:
        print(f"Error in send_to_channel function.\n\nError Code - {e}")
        await send_to_channel(update, content, chat_id, message)


#function to retry in case of TimeOut Error
async def safe_send(bot_func, *args, retries =3, **kwargs):
    for i in range(retries):
        try:
            return await bot_func(*args, **kwargs)
        except Exception as e:
            print(f"In safe_send, failed after{i+1} tries. \n\n Error Code -{e}")
    raise Exception(f"Sending failed after {retries} tries")


#function to get settings
async def get_settings(user_id):
    try:
        conn = sqlite3.connect("data/settings/user_settings.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM user_settings WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        if not row:
            return (999999, "XX", "gemini-2.5-pro", 0, 0.7, 0, "data/persona/pikachu.txt")
        if row[2] not in gemini_model_list:
            row = list(row)
            row[2] = gemini_model_list[-1]
            await asyncio.to_thread(db[f"{user_id}"].update_one,
                {"id" : user_id},
                {"$set" : {"settings" : row}}
            )
            cursor.execute("UPDATE user_settings SET model = ? WHERE id = ?", (row[2], user_id))
            if gemini_model_list[-1] == "gemini-2.5-pro":
                row[3] = row[3] if row[3] > 128 else 1024
                await asyncio.to_thread(db[f"{user_id}"].update_one,
                    {"id" : user_id},
                    {"$set" : {"settings" : row}}
                )
                cursor.execute("UPDATE user_settings SET thinking_budget = ? WHERE id = ?", (row[3], user_id))
            row = tuple(row)
        conn.commit()
        conn.close()
        return row
    except Exception as e:
        print(f"Error in get_settings fucntion.\n\nError Code - {e}")
        return (999999, "XX", 1, 0, 0.7, 0, 4)



#loading persona
def load_persona(settings):
    try:
        with open(settings[6], "r") as file:
            persona = file.read()
        return persona
    except Exception as e:
        print(f"Error in load_persona function. \n\n Error Code - {e}")
        return "none"
    

#function to check if the code block is left opened in the chunk or not
def is_code_block_open(data):
    return data.count("```")%2 == 1


#function to check if the buffer has any code blocks
def has_codeblocks(data):
    count = data.count("```")
    if count == 0:
        return False
    elif count%2 == 1:
        return False
    else:
        return True


#functon for seperating code blocks from other context for better response and formatting
def separate_code_blocks(data):
    pattern = re.compile(r"(```.*?```)", re.DOTALL)
    parts = pattern.split(data)
    return parts



#adding escape character for markdown rule
def add_escape_character(text):
    try:
        escape_chars = r'_*\[\]()~>#+-=|{}.!'
        return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)
    except Exception as e:
        print(f"Error in add_escape_character function.\n\nError Code - {e}")
        return text
