import re
import os
import time
import html
import sqlite3
import asyncio
import warnings
import threading
import requests
from glob import glob
from io import BytesIO
from flask import Flask, request
from cryptography.fernet import Fernet
from datetime import datetime, timedelta
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import(
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
    ConversationHandler,
    CallbackQueryHandler,
)
from telegram.constants import ChatAction
from telegram.error import RetryAfter, TimedOut
from telegram._utils.warnings import PTBUserWarning
from telegram.request import HTTPXRequest
from google import genai
from google.genai import types
from PIL import Image




key = os.getenv("decryption_key")
fernet = Fernet(key)


#code to ignore warnig about per_message in conv handler and increase poll size
warnings.filterwarnings("ignore",category=PTBUserWarning)
request = HTTPXRequest(connection_pool_size=50, pool_timeout=30)



#a flask to ignore web pulling condition

app = Flask(__name__)
@app.route('/')
def home():
    return "Bot is runnig", 200
def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
threading.Thread(target=run_web).start()





#all globals variable

channel_id = -1002575042671

#loading the bot api
try:
    conn = sqlite3.connect("API/bot_api.db")
    cursor = conn.cursor()
    cursor.execute("SELECT api from bot_api")
    rows = cursor.fetchall()
    tokens = tuple(row[0] for row in rows)
    TOKEN = tokens[1]
except Exception as e:
    print(f"Error Code -{e}")


#all registered user
def load_all_user():
    try:
        conn = sqlite3.connect("info/user_data.db")
        cursor = conn.cursor()
        cursor.execute("SELECT user_id from users")
        rows = cursor.fetchall()
        users = tuple(row[0] for row in rows)
        conn.close()
        return users
    except Exception as e:
        print(f"Error in load_all_user fnction.\n\n Error code -{e}")
all_users = load_all_user()


#function to load all admin
def load_admin():
    try:
        conn = sqlite3.connect("admin/admin.db")
        cursor = conn.cursor()
        cursor.execute("SELECT user_id from admin")
        rows = cursor.fetchall()
        admins = tuple(row[0] for row in rows)
        conn.close()
        return admins
    except Exception as e:
        print(f"Error in load_admin function.\n\nError Code - {e}")
all_admins = load_admin()

#function to load all gemini model
def load_gemini_model():
    try:
        conn = sqlite3.connect("info/gemini_model.db")
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM model")
        rows = cursor.fetchall()
        gemini_model_list = tuple(row[0] for row in rows)
        return gemini_model_list
    except Exception as e:
        print(f"Error Loading Gemini Model.\n\nError Code -{e}")

gemini_model_list = load_gemini_model()

#ct routine url for cse sec c
FIREBASE_URL = 'https://last-197cd-default-rtdb.firebaseio.com/routines.json'



# #function for webhook
# Application = None
# @app.route(f"/webhook/{TOKEN}", methods=["POST"])
# def webhook():
#     if Application is not None:
#         return Application.update_webhook(request)
#     return "Bot is not ready", 503





#All the global function 

#loading persona
def load_persona(settings):
    try:
        files = sorted(glob("persona/*shadow"))
        with open(files[settings[6]], "rb") as file:
            persona = fernet.decrypt(file.read()).decode("utf-8")
        return persona
    except Exception as e:
        print(f"Error in load_persona function. \n\n Error Code - {e}")
        return "none"
    

#Loading api key
def load_gemini_api():
    try:
        conn = sqlite3.connect("API/gemini_api.db")
        cursor = conn.cursor()
        cursor.execute("SELECT api from gemini_api")
        rows = cursor.fetchall()
        api_list = tuple(row[0] for row in rows)
        return api_list
    except Exception as e:
        print(f"Error lading gemini API. \n\nError Code -{e}")


#adding escape character for markdown rule
def add_escape_character(text):
    escape_chars = r'_*\[\]()~>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)


#function to get settings
def get_settings(user_id):
    conn = sqlite3.connect("settings/user_settings.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM user_settings WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    if row[2] > len(gemini_model_list)-1:
        row = list(row)
        row[2] = len(gemini_model_list)-1
        cursor.execute("UPDATE user_settings SET model = ? WHERE id = ?", (row[2], user_id))
        if gemini_model_list[-1] == "gemini-2.5-pro":
            row[3] = row[3] if row[3] > 128 else 1024
            cursor.execute("UPDATE user_settings SET thinking_budget = ? WHERE id = ?", (row[3], user_id))
        row = tuple(row)
    conn.commit()
    conn.close()

    if row:
        return row
    else:
        return None


#gemini response for stream on
def gemini_stream(user_message, api, settings):
    try:
        if gemini_model_list[settings[2]] == "gemini-2.5-pro" or gemini_model_list[settings[2]] == "gemini-2.5-flash":
            config = types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_budget=settings[3]),
                temperature = settings[4],
                system_instruction=load_persona(settings)
            )
        else:
            config = types.GenerateContentConfig(
                temperature = settings[4],
                system_instruction=load_persona(settings)
            )
        client = genai.Client(api_key=api)
        response = client.models.generate_content_stream(
            model = gemini_model_list[settings[2]],
            contents = [user_message],
            config = config,
        )
        return response
    except Exception as e:
        print(f"Error getting gemini response.\n\n Error Code - {e}")


#gemini response for stream off
def gemini_non_stream(user_message, api, settings):
    try:
        if gemini_model_list[settings[2]] == "gemini-2.5-pro" or gemini_model_list[settings[2]] == "gemini-2.5-flash":
            config = types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_budget=settings[3]),
                temperature = settings[4],
                system_instruction=load_persona(settings)
            )
        else:
            config = types.GenerateContentConfig(
                temperature = settings[4],
                system_instruction=load_persona(settings)
            )
        client = genai.Client(api_key=api)
        response = client.models.generate_content(
            model = gemini_model_list[settings[2]],
            contents = [user_message],
            config = config,
        )
        return response
    except Exception as e:
        print(f"Error getting gemini response.\n\n Error Code - {e}")
        


#A function to delete n times convo from conversation history
def delete_n_convo(user_id, n):
    try:
        if user_id < 0:
            group_id = user_id
            with open(f"Conversation/conversation-group-{group_id}.txt", "r+", encoding="utf-8") as f:
                data = f.read()
                data = data.split("You: ")
                if len(data) >= n+1:
                    data = data[n:]
                    f.seek(0)
                    f.truncate(0)
                    f.write("You: ".join(data))
            return
        with open(f"Conversation/conversation-{user_id}.txt", "r+", encoding="utf-8") as f:
            data = f.read()
            data = data.split("You: ")
            if len(data) >= n+1:
                data = data[n:]
                f.seek(0)
                f.truncate(0)
                f.write("You: ".join(data))
    except Exception as e:
        print(f"Failed to delete conversation history \n Error Code - {e}")



#creating memory, SPECIAL_NOTE: THIS FUNCTION ALWAYS REWRITE THE WHOLE MEMORY, SO THE MEMORY SIZE IS LIMITED TO THE RESPONSE SIZE OF GEMINI, IT IS DONE THIS WAY BECAUSE OTHERWISE THERE WILL BE DUPLICATE DATA 
async def create_memory(api, user_id):
    try:
        if user_id > 0:
            with open("persona/memory_persona.shadow", "rb") as f:
                instruction = fernet.decrypt(f.read()).decode("utf-8")
            with open(f"memory/memory-{user_id}.txt", "a+", encoding = "utf-8") as f:
                f.seek(0)
                data = "***PREVIOUS MEMORY***\n\n"
                data += f.read()
                data += "\n\n***END OF MEMORY***\n\n"
            with open(f"Conversation/conversation-{user_id}.txt", "a+", encoding = "utf-8") as f:
                f.seek(0)
                data += "\n\n***CONVERSATION HISTORY***"
                data += f.read()
                data += "\n\n***END OF CONVERSATION***\n\n"
        elif user_id < 0:
            group_id = user_id
            with open("persona/memory_persona.shadow", "rb") as f:
                instruction = fernet.decrypt(f.read()).decode("utf-8")
            with open(f"memory/memory-group-{group_id}.txt", "a+", encoding = "utf-8") as f:
                f.seek(0)
                data = "***PREVIOUS MEMORY***\n\n"
                data += f.read()
                data += "\n\n***END OF MEMORY***\n\n"
            with open(f"Conversation/conversation-group-{group_id}.txt", "a+", encoding = "utf-8") as f:
                f.seek(0)
                data += "\n\n***CONVERSATION HISTORY***"
                data += f.read()
                data += "\n\n***END OF CONVERSATION***\n\n"
        client = genai.Client(api_key=api)
        response = client.models.generate_content(
            model = "gemini-2.5-flash",
            contents = data,
            config = types.GenerateContentConfig(
                thinking_config = types.ThinkingConfig(thinking_budget=1024),
                temperature = 0.7,
                system_instruction =  instruction,
            ),
        )
        if user_id > 0:
            with open(f"memory/memory-{user_id}.txt", "a+", encoding="utf-8") as f:
                f.write(response.text)
            delete_n_convo(user_id, 10)
        elif user_id < 0:
            group_id = user_id
            with open(f"memory/memory-group-{group_id}.txt", "a+", encoding="utf-8") as f:
                f.write(response.text)
            delete_n_convo(group_id,100)
    except Exception as e:
        print(f"Failed to create memory\n Error code-{e}")



#create the conversation history as prompt
async def create_prompt(update:Update, content:ContextTypes.DEFAULT_TYPE, user_message, user_id):
    try:
        if update.message.chat.type == "private":
            data = "***RULES***\n"
            with open("info/rules.shadow", "rb" ) as f:
                data += fernet.decrypt(f.read()).decode("utf-8")
                data += "\n***END OF RULES***\n\n\n"
                data += "***MEMORY***\n"
            with open(f"memory/memory-{user_id}.txt", "a+", encoding="utf-8") as f:
                f.seek(0)
                data += f.read()
                data += "\n***END OF MEMORY***\n\n\n"
            with open(f"Conversation/conversation-{user_id}.txt", "a+", encoding="utf-8") as f:
                f.seek(0)
                data += "***CONVERSATION HISTORY***\n\n"
                data += f.read()
                data += "\nUser: " + user_message
                f.seek(0)
                if(f.read().count("You: ")>20):
                    asyncio.create_task(background_memory_creation(update, content, user_id))
            return data
        if update.message.chat.type != "private":
            group_id = update.effective_chat.id
            data = "***RULES***\n"
            with open("info/group_rules.shadow", "rb") as f:
                data += fernet.decrypt(f.read()).decode("utf-8")
                data += "\n***END OF RULES***\n\n\n"
            data += "******TRAINING DATA******\n\n"
            with open("info/group_training_data.shadow", "rb") as f:
                data += fernet.decrypt(f.read()).decode("utf-8")
                data += "******END OF TRAINING DATA******\n\n"
            data += "***MEMORY***\n"
            with open(f"memory/memory-group-{group_id}.txt", "a+", encoding="utf-8") as f:
                f.seek(0)
                data += f.read()
                data += "\n***END OF MEMORY***\n\n\n"
            with open(f"Conversation/conversation-group-{group_id}.txt", "a+", encoding="utf-8") as f:
                f.seek(0)
                data += "***CONVERSATION HISTORY***\n\n"
                data += f.read()
                data += "\nUser: " + user_message
                f.seek(0)
                if(f.read().count("You: ")>200):
                    asyncio.create_task(background_memory_creation(update, content, user_id))
            return data
    except Exception as e:
        print(f"Error in create_promot function. \n\n Error Code - {e}")
        await send_to_channel(update, content, channel_id, f"Error in create_prompt function. \n\n Error Code - {e}")


#function to save conversation
def save_conversation(user_message : str , gemini_response:str , user_id:int) -> None:
    try:
        with open(f"Conversation/conversation-{user_id}.txt", "a+", encoding="utf-8") as f:
            f.write(f"\nUser: {user_message}\nYou: {gemini_response}\n")
    except Exception as e:
        print(f"Error in saving conversation. \n\n Error Code - {e}")


#function to save group conversation
def save_group_conversation(update : Update,user_message, gemini_response):
    try:
        group_id = update.effective_chat.id
        name = update.effective_user.first_name or "X" +" "+ update.effective_user.last_name or "X"
        with open(f"Conversation/conversation-group-{group_id}.txt", "a+", encoding="utf-8") as f:
            f.write(f"\n{name}: {user_message}\nYou: {gemini_response}\n")
    except Exception as e:
        print(f"Error in saving conversation. \n\n Error Code - {e}")



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


#function to identify it is lab for 1st 30 or 2nd 30
def lab_participant():
    with open("routine/lab_routine.txt", "r", encoding="utf-8") as f:
        data = f.read()
    lab = [0, '0']
    start_date = datetime.strptime("3-7-2025", "%d-%m-%Y")
    today = datetime.now()
    if (today.weekday()) in [3,4]:
        days = (5-today.weekday())%7
        saturday = today + timedelta(days)
        lab[1] = saturday.strftime("%d-%m-%Y")
    else:
        days = (today.weekday() - 5)%7
        saturday = today - timedelta(days)
        lab[1] = saturday.strftime("%d-%m-%Y")
    if int((today-start_date).days / 7) % 2 == 0:
        lab[0] = 1 if data == "first" else 0
    else:
        lab[0] = 0 if data == "first" else 1
    return lab






#all function for cse sec c


async def routine_handler(update : Update, content : ContextTypes.DEFAULT_TYPE) -> None:
    try:
        lab = lab_participant()
        if lab[0]:
            rt = "routine/rt1.png"
        else:
            rt = "routine/rt2.png"
        keyboard = [
            [InlineKeyboardButton("Live Routine", url="https://routine-c.vercel.app")]
        ]
        routine_markup = InlineKeyboardMarkup(keyboard)
        with open(rt, "rb") as photo:
            await content.bot.send_photo(update.effective_chat.id, photo, caption = f"This routine is applicable from {lab[1]}.", reply_markup=routine_markup)
    except Exception as e:
        print(f"Error in routine_handler function.\n\n Error Code -{e}")
        await send_to_channel(update, content, channel_id, f"Error in routine_handler function.\n\n Error Code -{e}")

    
#function to fetch ct data from firebase url
def get_ct_data():
    try:
        response = requests.get(FIREBASE_URL)
        response.raise_for_status()
        return response.json() or {}
    except Exception as e:
        print(f"Error in get_ct_data functio. \n\n Error Code -{e}")
        return None



#function to handle ct command
async def handle_ct(update:Update, content:ContextTypes.DEFAULT_TYPE) -> None:
    ct_data = get_ct_data()
    if ct_data == None:
        await update.message.reply_text("Couldn't Connect to FIREBASE URL. Try again later.")
        return
    elif not ct_data:
        await update.message.reply_text("📭 No CTs scheduled yet.")
        return
    else:
        now = datetime.now()
        upcoming = []

        for ct_id, ct in ct_data.items():
            try:
                ct_date = datetime.strptime(ct['date'], "%Y-%m-%d")
                if ct_date >= now:
                    days_left = (ct_date - now).days
                    upcoming.append({
                        'subject': ct.get('subject', 'No Subject'),
                        'date': ct_date,
                        'days_left': days_left,
                        'teacher': ct.get('teacher', 'Not specified'),
                        'syllabus': ct.get('syllabus', 'No syllabus')
                    })
            except (KeyError, ValueError) as e:
                print(f"Skipping malformed CT {ct_id}: {e}")

        if not upcoming:
            await update.message.reply_text("🎉 No upcoming CTs! You're all caught up!")
            return

        # Sort by nearest date
        upcoming.sort(key=lambda x: x['date'])

        # Format message
        message = ["📚 <b>Upcoming CTs</b>"]
        for i, ct in enumerate(upcoming):
            days_text = f"{ct['days_left']+1} days"
            date_str = ct['date'].strftime("%a, %d %b")

            if i == 0:
                message.append(f"\n⏰ <b>NEXT:</b> {ct['subject']}")
            else:
                message.append(f"\n📅 {ct['subject']}")

            message.append(
                f"🗓️ {date_str} ({days_text})\n"
                f"👨‍🏫 {ct['teacher']}\n"
                f"📖 {ct['syllabus']}"
            )

        await update.message.reply_text("\n".join(message), parse_mode='HTML')


#function to inform all the student 
async def inform_all(update:Update, content:ContextTypes.DEFAULT_TYPE) -> None:
    ct_data = get_ct_data()
    if ct_data is None or not ct_data:
        await update.message.reply_text("⚠️ Couldn't connect to database or no CT data available.")
        return
    now = datetime.now()
    tomorrow = now.date() + timedelta(days=1)
    tomorrow_cts = []
    for ct_id, ct in ct_data.items():
        try:
            ct_date = datetime.strptime(ct['date'], "%Y-%m-%d").date()
            if ct_date == tomorrow:
                tomorrow_cts.append({
                    'subject': ct.get('subject', 'No Subject'),
                    'teacher': ct.get('teacher', 'Not specified'),
                    'syllabus': ct.get('syllabus', 'No syllabus')
                })
        except (KeyError, ValueError) as e:
            print(f"Skipping malformed CT {ct_id}: {e}")
    if not tomorrow_cts:
        await update.message.reply_text("ℹ️ No CTs scheduled for tomorrow.")
        return

    # Format the reminder message
    message = ["🔔 <b>CT Reminder: Tomorrow's Tests</b>"]
    for ct in tomorrow_cts:
        message.append(
            f"\n📚 <b>{ct['subject']}</b>\n"
            f"👨‍🏫 {ct['teacher']}\n"
            f"📖 {ct['syllabus']}\n"
        )
    full_message = "\n".join(message)
    try:
        sent = 0
        failed = 0
        failed_list = "Failed to send message to those user:\n"
        for user in all_users:
            try:
                await content.bot.send_message(chat_id=user, text=full_message, parse_mode="HTML")
                sent += 1
            except:
                failed += 1
                failed_list += str(user) + "\n"
        report = (
                f"📊 Notification sent to {sent} users\n"
                f"⚠️ Failed to send to {failed} users\n"
            )
        await update.message.reply_text(report)
        if failed != 0:
            await update.message.reply_text(failed_list, parse_mode="Markdown")
    except Exception as e:
        print(f"Error in inform_all function.\n\n Error Code - {e}")
        await send_to_channel(update, content, channel_id, f"Error in inform_all function.\n\n Error Code - {e}")


#fuction to circulate message
async def circulate_message(update : Update, content : ContextTypes.DEFAULT_TYPE):
    try:
        message = update.message.text.strip()
        await update.message.reply_text("Please wait while bot is circulating the message.")
        sent = 0
        failed = 0
        failed_list = "Failed to send message to those user:\n"
        for user in all_users:
            try:
                await content.bot.send_message(
                    chat_id=user,
                    text="*** IMPORTANT NOTICE ***\n\n" + message,
                    parse_mode="Markdown"
                )
                sent += 1
            except:
                failed += 1
                failed_list += str(user) + "\n"
        report = (
                f"📊 Notification sent to {sent} users\n"
                f"⚠️ Failed to send to {failed} users\n"
            )
        await update.message.reply_text(report)
        if failed != 0:
            await update.message.reply_text(failed_list, parse_mode="Markdown")
    except Exception as e:
        print(f"Error in circulate_message function.\n\n Error Code - {e}")


#function to circulate routine among all users
async def circulate_routine(update:Update, content:ContextTypes.DEFAULT_TYPE) -> None:
    try:
        lab = lab_participant()
        if lab[0]:
            rt = "routine/rt1.png"
        else:
            rt = "routine/rt2.png"
        sent = 0
        failed = 0
        failed_list = "Failed to send routine to those user:\n"
        for user in all_users:
            try:
                with open(rt,"rb") as photo:
                    await content.bot.send_photo(chat_id=user, photo=photo, caption="Renewed Routine")
                sent += 1
            except Exception as e:
                print(e)
                failed += 1
                failed_list += str(user) + "\n"
        report = (
                f"📊 Notification sent to {sent} users\n"
                f"⚠️ Failed to send to {failed} users\n"
            )
        await update.message.reply_text(report, parse_mode="HTML")
        if failed != 0:
            await update.message.reply_text(failed_list, parse_mode="Markdown")
    except Exception as e:
        print(f"Error in circulate message function.\n\nError Code - {e}")





#All the python telegram bot function

#function for editing and sending message
async def send_message(update : Update, content : ContextTypes.DEFAULT_TYPE, response, user_message, settings) -> None:
    try:
        if(settings[5]):
            message_object  = await update.message.reply_text("Typing...")
            buffer = ""
            sent_message = ""
            chunks = ''
            for chunk in response:
                chunks += chunk.text
                if chunk.text is not None and chunk.text.strip() and len(buffer+chunk.text)<4080:
                    buffer += chunk.text if chunk.text else "."
                    sent_message += chunk.text if chunk.text else "."
                    if len(chunks) > 500:
                        for i in range(0,5):
                            try:
                                await message_object.edit_text(buffer)
                                chunks = ""
                                break
                            except TimeoutError as e:
                                print(f"Error in editing message for {i+1} times. \n\n Error Code - {e}")
                                await send_to_channel(update,content,channel_id, f"Error in editing message for {i+1} times. \n\n Error Code - {e}")

                else:
                    if is_code_block_open(buffer):
                        buffer += "\n```"
                        try:
                            await message_object.edit_text(buffer, parse_mode="Markdown")
                        except:
                            try:
                                await message_object.edit_text(add_escape_character(buffer), parse_mode="MarkdownV2")
                            except:
                                await message_object.edit_text(buffer)
                        buffer = "```\n" + chunk.text
                        message_object = await safe_send(update.message.reply_text,buffer)
                    else:
                        buffer = chunk.text
                        sent_message += chunk.text
                        message_object = await safe_send(update.message.reply_text, buffer)
            if not(has_codeblocks(buffer)):
                try:
                    await message_object.edit_text(buffer+"\n.", parse_mode="Markdown")
                except:
                    try:
                        await message_object.edit_text(add_escape_character(buffer+"\n."), parse_mode="MarkdownV2")
                    except:
                        await message_object.edit_text(buffer+"\n.")
            else:
                try:
                    await message_object.edit_text(buffer+"\n.", parse_mode="Markdown")
                except:
                    try:
                        await message_object.edit_text(add_escape_character(buffer+"\n."), parse_mode="MarkdownV2")
                    except:
                        await message_object.edit_text(buffer+"\n")
            if update.message.chat.type == "private":
                save_conversation(user_message, sent_message , update.effective_user.id)
            elif update.message.chat.type != "private":
                save_group_conversation(update, user_message, sent_message)
        #if streaming is off
        else:
            sent_message = response.text
            if len(sent_message) > 4080:
                messages = [sent_message[i:i+4080] for i in range(0, len(sent_message), 4080)]
                for i,message in enumerate(messages):
                    if is_code_block_open(message):
                        messages[i] += "```"
                        messages[i+1] = "```\n" + messages[i+1]
                    if not (has_codeblocks(message)):
                        try:
                            await safe_send(update.message.reply_text, messages[i], parse_mode="Markdown")
                        except:
                            try:
                                await update.message.reply_text(add_escape_character(messages[i]), parse_mode="MarkdownV2")
                            except:
                                await update.message.reply_text(messages[i])
                    else:
                        try:
                            await update.message.reply_text(messages[i], parse_mode="Markdown")
                        except:
                            try:
                                await update.message.reply_text(add_escape_character(messages[i]), parse_mode="MarkdownV2")
                            except:
                                await update.message.reply_text(messages[i])
            else:
                if not(has_codeblocks(sent_message)):
                    try:
                        await update.message.reply_text(sent_message, parse_mode ="Markdown")
                    except:
                        try:
                            await update.message.reply_text(add_escape_character(sent_message), parse_mode="MarkdownV2")
                        except:
                            await update.message.reply_text(sent_message)
                else:
                    try:
                        await safe_send(update.message.reply_text, sent_message, parse_mode ="Markdown")
                    except:
                        try:
                            await update.message.reply_text(add_escape_character(sent_message), parse_mode="MarkdownV2")
                        except:
                            await update.message.reply_text(sent_message)
            if update.message.chat.type == "private":
                save_conversation(user_message, sent_message, update.effective_user.id)
            elif update.message.chat.type != "private":
                save_group_conversation(update, user_message, sent_message)
    except Exception as e:
        print(f"Error in send_message function Error Code - {e}")
        await send_to_channel(update, content, channel_id, f"Error in send_message function \n\nError Code -{e}")

    

#fuction for start command
async def start(update : Update, content : ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        ["ROUTINE", "CT"],
        ["SETTINGS ", "RESOURCES"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False, selective=False, is_persistent=True)
    try:
        user_id = update.effective_user.id
        paths = [
            f"Conversation/conversation-{user_id}.txt",
            f"memory/memory-{user_id}.txt",
        ]

        for path in paths:
            if not os.path.exists(path):
                with open(path, "w", encoding = "utf-8") as f:
                    pass
        users = load_all_user()
        if user_id in users:
            await update.message.reply_text("Hi there, I am your personal assistant. If you need any help feel free to ask me.", reply_markup=reply_markup)
            return
        if user_id not in users:
            keyboard = [
                [InlineKeyboardButton("Register", callback_data="c_register"), InlineKeyboardButton("Cancel", callback_data="cancel")]
            ]
            markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("You are not registerd yet.", reply_markup=markup)
    except Exception as e:
        print(f"Error in start function. \n Error Code - {e}")
        await send_to_channel(update, content, channel_id, f"Error in start function \n\nError Code -{e}")


#a code to handle multiple user at the same time
queue = asyncio.Queue()
async def handle_all_messages():
    while True:
        update, content, bot_name = await queue.get()
        try:
            await user_message_handler(update, content, bot_name)
        finally:
            queue.task_done()


#a function to add multiple workers to handle response
async def run_workers(n):
    for _ in range(4):
        asyncio.create_task(handle_all_messages())


#function to get response from gemini
async def user_message_handler(update:Update, content:ContextTypes.DEFAULT_TYPE, bot_name) -> None:
    try:
        user_message = update.message.text.strip()
        user_id = update.effective_user.id
        gemini_api_keys = load_gemini_api()
        if update.message.chat.type != "private" and (f"@{bot_name}" not in user_message.lower() or f"{bot_name}" not in user_message.lower()):
            return
        else:
            settings = get_settings(user_id)
            if not settings:
                update.message.reply_text("You are not registered.")
                return
            if update.message.chat.type != "private":
                group_id = update.effective_chat.id
                settings = (group_id,"group",1,0,0.7,0,4, None)
            prompt = await create_prompt(update, content, user_message, user_id)
            for i in range(len(gemini_api_keys)):
                try:
                    if(settings[5]):
                        response = await asyncio.to_thread(gemini_stream, prompt, gemini_api_keys[i],settings)
                        next(response).text
                        break
                    else:
                        response = await asyncio.to_thread(gemini_non_stream, prompt, gemini_api_keys[i],settings)
                        response.text
                        break
                except Exception as e:
                    print(f"Error getting gemini response for API-{i}. \n Error Code -{e}")
                    continue
            if response is not None:
                await send_message(update, content, response, user_message, settings)
            else:
                print("Failed to get a response from gemini.")
    except RetryAfter as e:
        await update.message.reply_text(f"Telegram Limit hit, need to wait {e.retry_after} seconds.")
        await send_to_channel(update, content, channel_id, f"Telegram Limit hit for user {user_id}, He need to wait {e.retry_after} seconds.")


#function for all other messager that are directly send to bot without any command
async def echo(update : Update, content : ContextTypes.DEFAULT_TYPE) -> None:
    try:
        bot_name_obj = await content.bot.get_my_name()
        bot_name = bot_name_obj.name.lower()
        user_id = update.effective_chat.id
        if user_id not in all_users:
            keyboard = [
                [InlineKeyboardButton("Register", callback_data="c_register"), InlineKeyboardButton("Cancel", callback_data="cancel")]
            ]
            markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("You are not registered.", reply_markup=markup)
            return
        user_name = f"{update.effective_user.first_name or update.effective_user.last_name or "Unknown"}".strip()
        user_message = (update.message.text or "...").strip()
        if (update.message and update.message.chat.type == "private") or (update.message.chat.type != "private" and (f"@{bot_name}" in user_message.lower() or f"{bot_name}" in user_message.lower())):
            await update.message.chat.send_action(action = ChatAction.TYPING)
        gemini_api_keys = load_gemini_api()
        if user_message == "ROUTINE":
            await routine_handler(update, content)
            return
        elif user_message == "SETTINGS":
            await handle_settings(update, content)
            await update.message.delete()
            return
        elif user_message == "CT":
            await handle_ct(update, content)
            return
        elif user_message == "RESOURCES":
            keyboard = [
                [InlineKeyboardButton("Drive", url="https://drive.google.com/drive/folders/1xbyCdj3XQ9AsCCF8ImI13HCo25JEhgUJ"), InlineKeyboardButton("Syllabus", url="https://drive.google.com/file/d/1pVF40-E0Oe8QI-EZp9S7udjnc0_Kquav/view?usp=drive_link")],
                [InlineKeyboardButton("Orientation Files", url = "https://drive.google.com/drive/folders/10_-xTV-FsXnndtDiw_StqH2Zy9tQcWq0"), InlineKeyboardButton("All Websites", callback_data="c_all_websites")],
                [InlineKeyboardButton("G. Classroom Code", callback_data="g_classroom"), InlineKeyboardButton("Cancel", callback_data="cancel")]
            ]
            resource_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("All the resources available for CSE SECTION C", reply_markup=resource_markup, parse_mode="Markdown")
            await update.message.delete()
            return
        else:
            #await user_message_handler(update, content, bot_name)
            await queue.put((update, content, bot_name))
    except Exception as e:
        print(f"Error in echo function.\n\n Error Code - {e}")
        await send_to_channel(update, content, channel_id, f"Error in echo function \n\nError Code -{e}")


#function for the resetting the conversation history
async def reset(update : Update, content : ContextTypes.DEFAULT_TYPE, query) -> None:
    try:
        user_id = update.callback_query.from_user.id
        try:
            if update.message.chat.type != "private":
                await update.message.reply_text("This function is not available in group. I don't save conversation of group.")
                return
        except:
            pass
        if os.path.exists(f"Conversation/conversation-{user_id}.txt"):
            with open(f"Conversation/conversation-{user_id}.txt", "w") as f:
                pass
            await query.edit_message_text("All clear, Now we are starting fresh.")
        else:
            await query.edit_message_text("It seems you don't have a conversation at all.")
    except Exception as e:
        await update.callback_query.message.reply_text(f"Sorry, The operation failed. Here's the error message:\n<pre>{html.escape(str(e))}</pre>", parse_mode="HTML")
        await send_to_channel(update, content, channel_id, f"Error in reset function \n\nError Code -{e}")


#function for the command api
async def api(update : Update, content : ContextTypes.DEFAULT_TYPE) -> None:
    try:
        if update.message.chat.type != "private":
            await update.message.reply_text("This function is only available in private chat.")
            return
        keyboard = [[InlineKeyboardButton("cancel", callback_data="cancel_conv")]]
        markup = InlineKeyboardMarkup(keyboard)
        with open("info/getting_api.shadow", "rb") as f:
            data = fernet.decrypt(f.read()).decode("utf-8")
            await update.message.reply_text(data, reply_markup=markup)
        return 1
    except Exception as e:
        print(f"Error in api function.\nError Code - {e}")
        await send_to_channel(update, content, channel_id, f"Error in api function \n\nError Code -{e}")


#function to handle api
async def handle_api(update : Update, content : ContextTypes.DEFAULT_TYPE) -> None:
    try:
        existing_apis = load_gemini_api()
        user_api = update.message.text.strip()
        await update.message.chat.send_action(action = ChatAction.TYPING)
        try:
            settings = get_settings(update.effective_user.id)
            response = gemini_stream("Checking if the gemini api is working or not", user_api, settings)
            chunk = next(response)
            if(
                user_api.startswith("AIza")
                and user_api not in existing_apis
                and " " not in user_api
                and len(user_api) >= 39
                and chunk.text
            ):
                conn = sqlite3.connect("API/gemini_api.db")
                cursor = conn.cursor()
                cursor.execute("INSERT OR IGNORE INTO gemini_api(api) VALUES(?)", (user_api,))
                conn.commit()
                conn.close()
                await update.message.reply_text("The API is saved successfully.")
                return ConversationHandler.END
            else:
                await update.message.reply_text("Sorry, This is an invalid or Duplicate API, try again with a valid API.")
                return ConversationHandler.END
        except Exception as e:
            await update.message.reply_text(f"Sorry, The API didn't work properly.\n Error Code - {e}")
            return ConversationHandler.END
    except Exception as e:
        print(f"Error in handling api. \n Error Code - {e}")
        await send_to_channel(update, content, channel_id, f"Error in handle_api function \n\nError Code -{e}")


#function to handle image
async def handle_image(update : Update, content : ContextTypes.DEFAULT_TYPE) -> None:
    try:
        await update.message.chat.send_action(action=ChatAction.TYPING)
        if update.message and update.message.photo:
            await update.message.reply_text("You have sent a Image")
            photo_file = await update.message.photo[-1].get_file()
            photo = await photo_file.download_as_bytearray()
            photo = BytesIO(photo)
            await update.message.reply_text("I have recieved your Image")
            await content.bot.send_photo(chat_id=channel_id, photo = photo, caption="Sent from handle_image function of Phantom bot")
            await update.message.reply_text("I downloaded your Image. But this function is under development, Try again later")
        else:
            await update.message.reply_text("That doesn't seems like an Image at all")
    except Exception as e:
        print(f"Error in handle_image function.\n\nError Code - {e}")
        await send_to_channel(update, content, channel_id, f"Error in handle_image function \n\nError Code -{e}")


#function to handle video
async def handle_video(update : Update, content : ContextTypes.DEFAULT_TYPE) -> None:
    try:
        await update.message.chat.send_action(action=ChatAction.TYPING)
        if update.message and update.message.video:
            await update.message.reply_text("You sent a video.")
            video_file = await update.message.video.get_file()
            video = await video_file.download_as_bytearray()
            video = BytesIO(video)
            await update.message.reply_text("I got your video")
            await content.bot.send_video(chat_id=channel_id, video=video, caption="Video sent from handle_video function of Phantom Bot")
            await update.message.reply_text("I downloaded your video. But this function is under developement please try again later.")
        else:
            await update.message.reply_text("This doesn't seems like a Video at all")
    except Exception as e:
        print(f"Error in handle_video function.\n\n Error Code - {e}")
        await send_to_channel(update, content, channel_id, f"Error in handle_video function \n\nError Code -{e}")


#fuction to handle audio
async def handle_audio(update : Update, content : ContextTypes.DEFAULT_TYPE) -> None:
    try:
        await update.message.chat.send_action(action=ChatAction.TYPING)
        if update.message and update.message.audio:
            await update.message.reply_text("You sent a audio.")
            audio_file = await update.message.audio.get_file()
            audio = await audio_file.download_as_bytearray()
            audio = BytesIO(audio)
            await update.message.reply_text("I got your audio")
            await content.bot.send_audio(chat_id=channel_id, audio=audio, caption="Audio sent from handle_audio function of Phantom Bot")
            await update.message.reply_text("I downloaded your audio. But this function is under developement please try again later.")
        else:
            await update.message.reply_text("This doesn't seems like a audio at all")
    except Exception as e:
        print(f"Error in handle_audio function.\n\n Error Code - {e}")
        await send_to_channel(update, content, channel_id, f"Error in handle_audio function \n\nError Code -{e}")



#function to handle voice
async def handle_voice(update : Update, content : ContextTypes.DEFAULT_TYPE) -> None:
    try:
        await update.message.chat.send_action(action=ChatAction.TYPING)
        if update.message and update.message.voice:
            await update.message.reply_text("You sent a voice.")
            voice_file = await update.message.voice.get_file()
            voice_data = await voice_file.download_as_bytearray()
            voice_data = BytesIO(voice_data) 
            await update.message.reply_text("I got your voice")
            await content.bot.send_voice(chat_id=channel_id, voice=voice_data, caption="Voice sent from handle_voice function of Phantom Bot")
            await update.message.reply_text("I downloaded your voice. But this function is under developement please try again later.")
        else:
            await update.message.reply_text("This doesn't seems like a voice at all")
    except Exception as e:
        print(f"Error in handle_voice function.\n\n Error Code - {e}")
        await send_to_channel(update, content, channel_id, f"Error in handle_voice function \n\nError Code -{e}")


#function to handle sticker
async def handle_sticker(update : Update, content : ContextTypes.DEFAULT_TYPE) -> None:
    try:
        if update.message and update.message.sticker:
            sticker = update.message.sticker
            await update.message.reply_text("I recieved your sticker, but this function is under developement. Please try again Later.")
            await content.bot.send_sticker(chat_id=channel_id, sticker=sticker.file_id, emoji=sticker.emoji or "X")
            await update.message.reply_text("I downloaded your sticker")
        else:
            await update.message.reply_text("This doesn't seems like a sticker")
    except Exception as e:
        print(f"Error on handle_sticker function. \n\n Error Code -{e}")
        await send_to_channel(update, content, channel_id, f"Error in handle_sticker function \n\nError Code -{e}")


#A function to return memory for user convention
async def see_memory(update : Update, content : ContextTypes.DEFAULT_TYPE, query) -> None:
    try:
        try:
            if update.message.chat.type != "private":
                await update.message.reply_text("Memory is not visible from group. Privacy concern idiot.")
                return
        except:
            pass
        with open(f"memory/memory-{update.callback_query.from_user.id}.txt", "a+") as f:
            f.seek(0)
            data = f.read()
            await query.edit_message_text("Here is my Diary about you:")
            if data.strip() == "":
                await update.callback_query.message.reply_text("I haven't written anything about you. You expected something huh\nLOL")
            else:
                await update.callback_query.message.reply_text(data)
    except Exception as e:
        print(f"Error in see_memory function.\n\nError Code - {e}")
        await send_to_channel(update.callback_query, content, channel_id, f"Error in see_memory function \n\nError Code -{e}")


#function for deleting memory
async def delete_memory(update : Update, content : ContextTypes.DEFAULT_TYPE, query) -> None:
    try:
        with open(f"memory/memory-{update.callback_query.from_user.id}.txt", "w") as f:
            pass
        await query.edit_message_text("You cleared my memory about you, It really makes me sad.")
    except Exception as e:
        print(f"Error in delete_memory function.\n\nError Code - {e}")
        await send_to_channel(update, content, channel_id, f"Error in delete_memory function \n\nError Code -{e}")


#a function to handle settings
async def handle_settings(update : Update, content : ContextTypes.DEFAULT_TYPE) -> None:
    try:
        await update.message.chat.send_action(action=ChatAction.TYPING)
        keyboard= [
            [InlineKeyboardButton("AI Engine", callback_data = "c_model"),InlineKeyboardButton("Temperature", callback_data="c_temperature")],
            [InlineKeyboardButton("Thinking", callback_data = "c_thinking"), InlineKeyboardButton("Persona", callback_data="c_persona")],
            [InlineKeyboardButton("Streaming Response", callback_data="c_streaming"), InlineKeyboardButton("Conversation History", callback_data="c_conv_history")],
            [InlineKeyboardButton("Memory", callback_data="c_memory"), InlineKeyboardButton("cancel", callback_data="cancel")]
        ]
        settings_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("You change the bot configuration from here.\nBot Configuration Menu:", reply_markup=settings_markup)
    except Exception as e:
        await send_to_channel(update, content, channel_id, f"Error in handle_settings function \n\nError Code -{e}")
        print(f"Error in handle_settings function. \n\n Error Code -{e}")


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


#function to create memory in background
async def background_memory_creation(update: Update,content,user_id):
    try:
        if update.message.chat.type == "private":
            await create_memory(load_gemini_api()[-1], user_id)
            await send_to_channel(update, content, channel_id, f"Created memory for User - {user_id}")
            with open(f"memory/memory-{user_id}.txt", "rb") as file:
                await content.bot.send_document(chat_id=channel_id, document = file, caption = "Heres the memory file.")
        elif update.message.chat.type != "private":
            group_id = update.effective_chat.id
            await create_memory(load_gemini_api()[-1], group_id)
            await send_to_channel(update, content, channel_id, "Created memory for group")
            with open(f"memory/memory-group-{group_id}.txt", "r", encoding="utf-8") as f:
                await content.bot.send_document(chat_id=channel_id, document=file, caption="Memory for the group.")
    except Exception as e:
        print(f"Error in background_memory_creation function.\n\n Error Code -{e}")
        await send_to_channel(update, content, channel_id, f"Error in background_memory_creation function.\n\n Error Code -{e}")






#a function for admin call
async def admin_handler(update : Update, content : ContextTypes.DEFAULT_TYPE) -> None:
    try:
        user_id = update.effective_user.id
        if user_id in all_admins:
            keyboard = [
                [InlineKeyboardButton("Circulate Message", callback_data="c_circulate_message"), InlineKeyboardButton("Show All User", callback_data="c_show_all_user")],
                [InlineKeyboardButton("Circulate Routine", callback_data="c_circulate_routine"), InlineKeyboardButton("Toggle Routine", callback_data="c_toggle_routine")],
                [InlineKeyboardButton("Manage Admin", callback_data="c_manage_admin"), InlineKeyboardButton("Manage AI Model", callback_data="c_manage_ai_model")],
                [InlineKeyboardButton("cancel", callback_data="cancel")]
            ]
            admin_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("Given operation will circulate among all registered user.", parse_mode="Markdown", reply_markup=admin_markup)
            await update.message.delete()
        else:
            await update.message.reply_text("Sorry you are not an Admin.")
    except Exception as e:
        print(f"Error in admin_handler function.\n\n Error Code - {e}")
        await send_to_channel(update, content, channel_id, f"Error in admin_handler function.\n\n Error Code - {e}")



#function to handle help command
async def help(update: Update, content : ContextTypes.DEFAULT_TYPE) -> None:
    try:
        keyboard = [
            [InlineKeyboardButton("Admin Help", callback_data="c_admin_help"), InlineKeyboardButton("Cancel", callback_data="cancel")],
            [InlineKeyboardButton("Read Documentation", url = "https://github.com/sifat1996120/Phantom_bot")]
        ]
        help_markup = InlineKeyboardMarkup(keyboard)
        with open("info/help.shadow", "rb") as file:
            await update.message.reply_text(fernet.decrypt(file.read()).decode("utf-8"), reply_markup=help_markup)
    except Exception as e:
        print(f"Error in help function. \n\n Error Code - {e}")
        await send_to_channel(update, content, channel_id, f"Error in help function. \n\n Error Code - {e}")


#function to take message for circulate message
async def message_taker(update:Update, content:ContextTypes.DEFAULT_TYPE) -> None:
    try:
        keyboard = [[InlineKeyboardButton("Cancel", callback_data="cancel_conv")]]
        mt_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text("Enter the message here:", reply_markup=mt_markup)
        return "CM"
    except Exception as e:
        print(f"Error in message_taker function.\n\nError Code -{e}")
        await update.message.reply_text("Internal Error. Please try again later or contact admin.")
        return ConversationHandler.END


#function to take password for admin function
async def admin_password_taker(update: Update, content:ContextTypes.DEFAULT_TYPE) -> None:
    try:
        Keyboard = [[InlineKeyboardButton("Cancel", callback_data="cancel_conv")]]
        pt_markup = InlineKeyboardMarkup(Keyboard)
        msg = await update.callback_query.edit_message_text("Password for Admin:", reply_markup=pt_markup)
        content.user_data["pt_message_id"] = msg.message_id
        return "MA"
    except Exception as e:
        print(f"Error in admin_password_taker function.\n\nError Code -{e}")
        await update.message.reply_text("Internal Error. Please try again later or contact admin.")
        return ConversationHandler.END


#function to create background task for circulate message
async def handle_circulate_message(update:Update, content:ContextTypes.DEFAULT_TYPE) -> None:
    try:
        asyncio.create_task(circulate_message(update, content))
        return ConversationHandler.END
    except Exception as e:
        print(f"Error in handle_circulate_message function.\n\nError Code -{e}")
        await update.message.reply_text("Internal Error. Please try again later or contact admin.")
        return ConversationHandler.END


#function to manage admin
async def manage_admin(update:Update, content:ContextTypes.DEFAULT_TYPE) -> None:
    try:
        msg_id = content.user_data.get("pt_message_id")
        try:
            await content.bot.delete_message(chat_id=update.effective_chat.id, message_id=msg_id)
        except:
            pass
        given_password = update.message.text.strip()
        with open("admin/admin_password.shadow", "rb") as file:
            password = fernet.decrypt(file.read().strip()).decode("utf-8")
        if password != given_password:
            await update.message.reply_text("Wrong Password.")
            return ConversationHandler.END
        else:
            keyboard = [
                [InlineKeyboardButton("See All Admin", callback_data="see_all_admin")],
                [InlineKeyboardButton("Add Admin", callback_data="add_admin"), InlineKeyboardButton("Delete Admin", callback_data="delete_admin")],
                [InlineKeyboardButton("Cancel", callback_data="cancel_conv")]
            ]
            ma_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("Please chose an option:", reply_markup=ma_markup)
            await update.message.delete()
            return "ADMIN_ACTION"
    except Exception as e:
        print(f"Error in manage_admin function.\n\nError Code -{e}")
        await update.message.reply_text("Internal Error. Please try again later or contact admin.")
        return ConversationHandler.END


#function to manage admin action
async def admin_action(update:Update, content:ContextTypes.DEFAULT_TYPE) -> None:
    try:
        query = update.callback_query
        await query.answer()
        keyboard = [[InlineKeyboardButton("cancel", callback_data="cancel_conv")]]
        markup = InlineKeyboardMarkup(keyboard)
        if query.data == "add_admin":
            msg = await query.edit_message_text("Enter the user_id to add as admin:", reply_markup=markup)
            content.user_data["admin_action"] = "add_admin"
            content.user_data["aa_message_id"] = msg.message_id
        elif query.data == "delete_admin":
            msg = await query.edit_message_text("Enter the user_id to delete an admin:", reply_markup=markup)
            content.user_data["admin_action"] = "delete_admin"
            content.user_data["aa_message_id"] = msg.message_id
        elif query.data == "see_all_admin":
            if all_admins:
                admin_data = "All Active Admin:\n"
                for i,admin in enumerate(all_admins):
                    admin_data += f"{i+1}. {admin}\n"
                await query.edit_message_text(admin_data)
                return ConversationHandler.END
            else:
                await query.edit_message_text("There is currently no active admin.")
        return "ENTER_USER_ID"
    except Exception as e:
        print(f"Error in manage_admin function.\n\nError Code -{e}")
        await update.message.reply_text("Internal Error. Please try again later or contact admin.")
        return ConversationHandler.END


#function to add or delete admin
async def add_or_delete_admin(update:Update, content:ContextTypes.DEFAULT_TYPE) -> None:
    try:
        user_id = update.message.text.strip()
        action = content.user_data.get("admin_action")
        msg_id = content.user_data.get("aa_message_id")
        await content.bot.delete_message(chat_id=update.effective_chat.id, message_id=msg_id)
        conn = sqlite3.connect("admin/admin.db")
        cursor = conn.cursor()
        global all_admins
        if action == "add_admin":
            if user_id not in all_admins:
                cursor.execute("INSERT OR IGNORE INTO admin(user_id) VALUES(?)", (user_id,))
                conn.commit()
                conn.close()
                await update.message.reply_text(f"Successfully added {user_id} user_id as Admin.")
                all_admins = load_admin()
            else:
                await update.message.reply_text(f"{user_id} is already an Admin.")
                conn.close()
            return ConversationHandler.END
        elif action == "delete_admin":
            if user_id in all_admins:
                cursor.execute("DELETE FROM admin WHERE user_id=?", (user_id,))
                await update.message.reply_text(f"Successfully deleted {user_id} from admin.")
                all_admins = load_admin()
                conn.commit()
                conn.close()
            else:
                await update.message.reply_text(f"{user_id} is not an Admin.")
                conn.close()
            return ConversationHandler.END
    except Exception as e:
        print(f"Error in add_or_delete_admin function.\n\nError Code -{e}")
        await update.message.reply_text("Internal Error. Please try again later or contact admin.")
        return ConversationHandler.END


#function to register a new user
async def take_name(update:Update, content:ContextTypes.DEFAULT_TYPE):
    try:
        keyboard = [[InlineKeyboardButton("Cancel", callback_data="cancel_conv")]]
        markup = InlineKeyboardMarkup(keyboard)
        if update.callback_query:
            msg = await update.callback_query.edit_message_text("Enter Your Name: ", reply_markup=markup)
            content.user_data["tn_message_id"] = msg.message_id
            return "TG"
        else:
            msg = await update.message.reply_text("Enter Your Name: ", reply_markup=markup)
            content.user_data["tn_message_id"] = msg.message_id
            return "TG"
    except Exception as e:
        print(f"Error in take_name function.\n\nError Code -{e}")
        await update.message.reply_text("Internal Error. Please try again later or contact admin.")
        return ConversationHandler.END


#fuction to take gender from user
async def take_gender(update:Update, content: ContextTypes.DEFAULT_TYPE):
    try:
        name = update.message.text.strip()
        content.user_data["user_name"] = name
        keyboard = [
            [InlineKeyboardButton("Male", callback_data="c_male"), InlineKeyboardButton("Female", callback_data="c_female")],
            [InlineKeyboardButton("Cancel", callback_data="cancel_conv")]
        ]
        markup = InlineKeyboardMarkup(keyboard)
        msg = await update.message.reply_text("Select Your Gender: ", reply_markup=markup)
        await content.bot.delete_message(chat_id=update.effective_user.id, message_id=content.user_data.get("tn_message_id"))
        await update.message.delete()
        content.user_data["tg_message_id"] = msg.message_id
        return "TR"
    except Exception as e:
        print(f"Error in take_gender function.\n\nError Code -{e}")
        await update.message.reply_text("Internal Error. Please try again later or contact admin.")
        return ConversationHandler.END


#function to handle gender action
async def take_roll(update: Update, content:ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        if query.data == "c_male":
            content.user_data["gender"] = "male"
        elif query.data == "c_female":
            content.user_data["gender"] = "female"
        keyboard = [[InlineKeyboardButton("Cancel", callback_data="cancel_conv")]]
        markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Please Enter Your Roll number:", reply_markup=markup)
        return "RA"
    except Exception as e:
        print(f"Error in take_roll function.\n\nError Code -{e}")
        await update.message.reply_text("Internal Error. Please try again later or contact admin.")
        return ConversationHandler.END


#function to check if the provided roll is valid
async def roll_action(update:Update, content:ContextTypes.DEFAULT_TYPE):
    try:
        roll = update.message.text.strip()
        if len(roll) != 7:
            msg = await update.message.reply_text("Invalid format. Try again with your full roll number.")
            content.user_data["tr_message_id"] = msg.message_id
            await content.bot.delete_message(chat_id=update.effective_user.id, message_id=content.user_data.get("tg_message_id"))
            await update.message.delete()
            return ConversationHandler.END
        if not roll.startswith("2403"):
            msg = await update.message.reply_text("This bot is only available for CSE Section C of 24 series.")
            content.user_data["tr_message_id"] = msg.message_id
            await content.bot.delete_message(chat_id=update.effective_user.id, message_id=content.user_data.get("tg_message_id"))
            await update.message.delete()
            return ConversationHandler.END
        else:
            try:
                roll = int(roll)
            except:
                msg = await update.message.reply_text("Invalid Roll Number.")
                content.user_data["tr_message_id"] = msg.message_id
                await content.bot.delete_message(chat_id=update.effective_user.id, message_id=content.user_data.get("tg_message_id"))
                await update.message.delete()
                return ConversationHandler.END
            if roll<2403120 or roll>2403180:
                msg = await update.message.reply_text("Sorry you are not allowed to use this bot")
                content.user_data["tr_message_id"] = msg.message_id
                await content.bot.delete_message(chat_id=update.effective_user.id, message_id=content.user_data.get("tg_message_id"))
                await update.message.delete()
                return ConversationHandler.END
            else:
                content.user_data["roll"] = roll
                keyboard = [[InlineKeyboardButton("Skip", callback_data="c_skip"),InlineKeyboardButton("Cancel",callback_data="cancel_conv")]]
                markup = InlineKeyboardMarkup(keyboard)
                with open("info/getting_api.shadow", "rb") as file:
                    help_data = add_escape_character(fernet.decrypt(file.read()).decode("utf-8"))
                msg = await update.message.reply_text(help_data, reply_markup=markup, parse_mode="MarkdownV2")
                content.user_data["ra_message_id"] = msg.message_id
                await content.bot.delete_message(chat_id=update.effective_user.id, message_id=content.user_data.get("tg_message_id"))
                await update.message.delete()
                return "AH"
    except Exception as e:
        print(f"Error in roll_action function.\n\nError Code -{e}")
        await update.message.reply_text("Internal Error. Please try again later or contact admin.")
        return ConversationHandler.END


#function to handler skip
async def handle_skip(update:Update, content:ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        keyboard = [[InlineKeyboardButton("Cancel", callback_data="cancel_conv")]]
        markup = InlineKeyboardMarkup(keyboard)
        if query.data == "c_skip":
            msg = await query.edit_message_text("You might sometime face problem getting answer. You can always register your api by /api command.\n\nSet Your Password:", reply_markup=markup, parse_mode="Markdown")
            content.user_data["hac_message_id"] = msg.message_id
            content.user_data["user_api"] = None
            return "TP"
    except Exception as e:
        print(f"Error in handle_skip function.\n\nError Code -{e}")
        await query.edit_message_text("Internal Error. Please try again later or contact admin.")
        return ConversationHandler.END


#function to take api
async def handle_api_conv(update : Update, content : ContextTypes.DEFAULT_TYPE) -> None:
    try:
        existing_apis = load_gemini_api()
        user_api = update.message.text.strip()
        await update.message.chat.send_action(action = ChatAction.TYPING)
        keyboard = [[InlineKeyboardButton("Cancel", callback_data="cancel_conv")]]
        markup = InlineKeyboardMarkup(keyboard)
        try:
            client = genai.Client(api_key=user_api)
            response = client.models.generate_content(
                model = gemini_model_list[1],
                contents = "hi, respond in one word.",
            )
            if(
                user_api.startswith("AIza")
                and user_api not in existing_apis
                and " " not in user_api
                and len(user_api) >= 39
                and response.text
            ):
                conn = sqlite3.connect("API/gemini_api.db")
                cursor = conn.cursor()
                cursor.execute("INSERT OR IGNORE INTO gemini_api(api) VALUES(?)", (user_api,))
                conn.commit()
                conn.close()
                msg = await update.message.reply_text("The API is saved successfully.\nSet you password:", reply_markup=markup)
                content.user_data["user_api"] = user_api
                await content.bot.delete_message(chat_id=update.effective_user.id, message_id=content.user_data.get("ra_message_id"))
                await update.message.delete()
                content.user_data["hac_message_id"] = msg.message_id
                return "TP"
            elif user_api in existing_apis:
                msg = await update.message.reply_text("The API already exists, you are excused.\n Set your password:", reply_markup=markup)
                content.user_data["user_api"] = None
                await content.bot.delete_message(chat_id=update.effective_user.id, message_id=content.user_data.get("ra_message_id"))
                await update.message.delete()
                content.user_data["hac_message_id"] = msg.message_id
                return "TP"
            else:
                await update.message.reply_text("Sorry, This is an invalid or Duplicate API, try again with a valid API.")
                await content.bot.delete_message(chat_id=update.effective_user.id, message_id=content.user_data.get("ra_message_id"))
                await update.message.delete()
                return ConversationHandler.END
        except Exception as e:
            await update.message.reply_text(f"Sorry, The API didn't work properly.\n Error Code - {e}")
            await content.bot.delete_message(chat_id=update.effective_user.id, message_id=content.user_data.get("ra_message_id"))
            await update.message.delete()
            return ConversationHandler.END
    except Exception as e:
        print(f"Error in handling api. \n Error Code - {e}")
        await send_to_channel(update, content, channel_id, f"Error in handle_api function \n\nError Code -{e}")



#function to take password from user
async def take_password(update:Update, content:ContextTypes.DEFAULT_TYPE):
    try:
        password = update.message.text.strip()
        keyboard = [[InlineKeyboardButton("Cancel",callback_data="cancel_conv")]]
        markup = InlineKeyboardMarkup(keyboard)
        msg = await update.message.reply_text("Confirm Your password:", reply_markup=markup)
        content.user_data["password"] = password
        content.user_data["tp_message_id"] = msg.message_id
        await content.bot.delete_message(chat_id = update.effective_user.id, message_id=content.user_data.get("hac_message_id"))
        await update.message.delete()
        return "CP"
    except Exception as e:
        print(f"Error in take_password function.\n\nError Code -{e}")
        await update.message.reply_text("Internal Error. Please try again later or contact admin.")
        return ConversationHandler.END


#function to confirm user password
async def confirm_password(update:Update, content:ContextTypes.DEFAULT_TYPE):
    try:
        c_password = update.message.text.strip()
        password = content.user_data.get("password")
        if password == c_password:
            keyboard = [
                ["ROUTINE", "CT"],
                ["SETTINGS ", "RESOURCES"]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False, selective=False, is_persistent=True)
            try:
                conn = sqlite3.connect("info/user_data.db")
                cursor = conn.cursor()
                user_info = [
                    update.effective_user.id,
                    content.user_data.get("user_name"),
                    content.user_data.get("gender"),
                    content.user_data.get("roll"),
                    content.user_data.get("password"),
                    content.user_data.get("user_api")
                ]
                cursor.execute("""
                    INSERT OR IGNORE INTO users(user_id, name, gender, roll, password, api)
                    VALUES(?,?,?,?,?,?)
                """,
                tuple(info for info in user_info)
                )
                conn.commit()
                conn.close()
                conn = sqlite3.connect("settings/user_settings.db")
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR IGNORE INTO user_settings
                        (id, name, model, thinking_budget, temperature, streaming, persona)
                        VALUES(?,?,?,?,?,?,?)
                """,
                (user_info[0], user_info[1], 1, 0, 0.7, 0, 0)
                )
                conn.commit()
                conn.close()
                global all_users
                all_users = load_all_user()
                await update.message.reply_text("Registration Seccessful.", reply_markup=reply_markup)
                await content.bot.delete_message(chat_id = update.effective_user.id, message_id=content.user_data.get("tp_message_id"))
                await update.message.delete()
            except Exception as e:
                print(f"Error adding user.\n\nError code - {e}")
            return ConversationHandler.END
        else:
            await update.message.reply_text("Passwords are not identical. Try again later.")
            await content.bot.delete_message(chat_id = update.effective_user.id, message_id=content.user_data.get("tp_message_id"))
            await update.message.delete()
            return ConversationHandler.END
    except Exception as e:
        print(f"Error in confirm_password function.\n\nError Code -{e}")
        await update.message.reply_text("Internal Error. Please try again later or contact admin.")
        return ConversationHandler.END
    

#function to enter temperature conversation
async def temperature(update:Update, content:ContextTypes.DEFAULT_TYPE):
    try:
        settings = get_settings(update.effective_user.id)
        keyboard = [
            [InlineKeyboardButton("Cancel", callback_data="cancel_conv")]
        ]
        markup = InlineKeyboardMarkup(keyboard)
        query = update.callback_query
        msg = await query.edit_message_text(f"Temperature represents the creativity of the bots response.\nCurrent Temperature is {settings[4]}\n\nEnter a value between 0.0 to 1.0:", reply_markup=markup)
        content.user_data["t_message_id"] = msg.message_id
        return "TT"
    except Exception as e:
        print(f"Error in temperatre function.\n\nError Code -{e}")
        await query.edit_message_text("Internal Error. Please try again later or contact admin.")
        return ConversationHandler.END


#function to take temperature
async def take_temperature(update:Update, content:ContextTypes.DEFAULT_TYPE):
    try:
        data = update.message.text.strip()
        user_id = update.effective_user.id
        try:
            data = round(float(data),1)
        except:
            await update.message.reply_text("Invalid Input. Try Again Later.")
            await content.bot.delete_message(chat_id=user_id, message_id=content.user_data.get("t_message_id"))
            await update.message.delete()
            return ConversationHandler.END
        if data > 1.0 or data < 0.0:
            await update.message.reply_text("Invalid Input. Temperature should be between 0.0 to 1.0")
            await content.bot.delete_message(chat_id=user_id, message_id=content.user_data.get("t_message_id"))
            await update.message.delete()
            return ConversationHandler.END
        else:
            conn = sqlite3.connect("settings/user_settings.db")
            cursor = conn.cursor()
            cursor.execute("UPDATE user_settings SET temperature = ? WHERE id = ?", (data, user_id))
            conn.commit()
            conn.close()
            await update.message.reply_text(f"Temperature is successfully set to {data}.")
            await content.bot.delete_message(chat_id=user_id, message_id=content.user_data.get("t_message_id"))
            await update.message.delete()
            return ConversationHandler.END
    except Exception as e:
        print(f"Error in take_temperature function.\n\nError Code -{e}")
        await update.message.reply_text("Internal Error. Please try again later or contact admin.")
        return ConversationHandler.END
        

#function to enter thinking conversation
async def thinking(update:Update, content:ContextTypes.DEFAULT_TYPE):
    try:
        settings = get_settings(update.effective_user.id)
        keyboard = [
            [InlineKeyboardButton("Cancel", callback_data="cancel_conv")]
        ]
        markup = InlineKeyboardMarkup(keyboard)
        query = update.callback_query
        msg = await query.edit_message_text(f"Thinking represents the thinking budget of the bot measured in token.\nCurrent Thinking budger is {settings[3]}\nAllowed Range - (0 to 24576)\nRecommended Range - (0 to 5000)\n\nEnter a value:", reply_markup=markup)
        content.user_data["t_message_id"] = msg.message_id
        return "TT"
    except Exception as e:
        print(f"Error in thinking function.\n\nError Code -{e}")
        await query.edit_message_text("Internal Error. Please try again later or contact admin.")
        return ConversationHandler.END


#function to take temperature
async def take_thinking(update:Update, content:ContextTypes.DEFAULT_TYPE):
    try:
        data = update.message.text.strip()
        user_id = update.effective_user.id
        try:
            data = int(data)
        except:
            await update.message.reply_text("Invalid Input. Try Again Later.")
            await content.bot.delete_message(chat_id=user_id, message_id=content.user_data.get("t_message_id"))
            await update.message.delete()
            return ConversationHandler.END
        if data > 24576 or data < 0:
            await update.message.reply_text("Invalid Input. Temperature should be between 0 to 24576")
            await content.bot.delete_message(chat_id=user_id, message_id=content.user_data.get("t_message_id"))
            await update.message.delete()
            return ConversationHandler.END
        else:
            settings = get_settings(update.effective_user.id)
            conn = sqlite3.connect("settings/user_settings.db")
            cursor = conn.cursor()
            if gemini_model_list[settings[2]] != "gemini-2.5-pro":
                cursor.execute("UPDATE user_settings SET thinking_budget = ? WHERE id = ?", (data, user_id))
                conn.commit()
                conn.close()
                await update.message.reply_text(f"Thinking Budget is successfully set to {data}.")
                await content.bot.delete_message(chat_id=user_id, message_id=content.user_data.get("t_message_id"))
                await update.message.delete()
                return ConversationHandler.END
            else:
                data = data if data>=128 else 1024
                cursor.execute("UPDATE user_settings SET thinking_budget = ? WHERE id = ?", (data, user_id))
                conn.commit()
                conn.close()
                await update.message.reply_text(f"Thinking Budget is successfully set to {data}. Gemini 2.5 pro only works with thinking budget greater than 128.")
                await content.bot.delete_message(chat_id=user_id, message_id=content.user_data.get("t_message_id"))
                await update.message.delete()
                return ConversationHandler.END
    except Exception as e:
        print(f"Error in take_thinking function.\n\nError Code -{e}")
        await update.message.reply_text("Internal Error. Please try again later or contact admin.")
        return ConversationHandler.END
    

#funtion to enter manage model conversation
async def manage_model(update:Update, content:ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        keyboard = [[InlineKeyboardButton("Cancel", callback_data="cancel_conv")]]
        markup = InlineKeyboardMarkup(keyboard)
        if query.data == "c_add_model":
            msg = await query.edit_message_text("Enter the model name:", reply_markup=markup)
            content.user_data["action"] = "c_add_model"
        elif query.data == "c_delete_model":
            msg = await query.edit_message_text("Enter the model name to delete:", reply_markup=markup)
            content.user_data["action"] = "c_delete_model"
        content.user_data["mm_message_id"] = msg.message_id
        return "TMN"
    except Exception as e:
        print(f"Error in manage_model function.\n\nError Code -{e}")
        await update.message.reply_text("Internal Error. Please try again later or contact admin.")
        return ConversationHandler.END


#function to take model_name
async def take_model_name(update:Update, content:ContextTypes.DEFAULT_TYPE):
    try:
        data = update.message.text.strip()
        action = content.user_data.get("action")
        global gemini_model_list
        if action == "c_add_model":
            if data not in gemini_model_list:
                try:
                    client = genai.Client(api_key=load_gemini_api()[-1])
                    response = client.models.generate_content(
                    model = data,
                    contents = "hi, respond in one word.",
                    )
                    response.text
                    conn = sqlite3.connect("info/gemini_model.db")
                    cursor = conn.cursor()
                    cursor.execute("INSERT OR IGNORE INTO model (name) VALUES(?)", (data,))
                    conn.commit()
                    conn.close()
                    await update.message.reply_text(f"{data} added successfully as a model.")
                except Exception as e:
                    await update.message.reply_text(f"Invalid Model Name.\n\nError Code - {e}")
                gemini_model_list = load_gemini_model()
            elif data in gemini_model_list:
                await update.message.reply_text("The model name is already registered.")
            else:
                await update.message.reply_text("The model name is invalid.")
        elif action == "c_delete_model":
            if data not in gemini_model_list:
                await update.message.reply_text(f"Sorry there is no model named {data}")
            else:
                conn = sqlite3.connect("info/gemini_model.db")
                cursor = conn.cursor()
                cursor.execute("DELETE FROM model WHERE name = ?", (data,))
                conn.commit()
                conn.close()
                gemini_model_list = load_gemini_model()
                await update.message.reply_text(f"The model named {data} is deleted successfully")
        await content.bot.delete_message(chat_id=update.effective_user.id, message_id=content.user_data.get("mm_message_id"))
        await update.message.delete()
        return ConversationHandler.END
    except Exception as e:
        print(f"Error in take_model_name function.\n\nError Code -{e}")
        await update.message.reply_text("Internal Error. Please try again later or contact admin.")
        return ConversationHandler.END

        

#function to cancel conversation by cancel button
async def cancel_conversation(update: Update, content: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        await update.callback_query.delete_message()
        return ConversationHandler.END
    except Exception as e:
        print(f"Error in cancel_conversation function.\n\nError Code -{e}")
        await update.message.reply_text("Internal Error. Please try again later or contact admin.")
        return ConversationHandler.END


#A function to handle button response
async def button_handler(update:Update, content:ContextTypes.DEFAULT_TYPE) -> None:
    try:
        query = update.callback_query
        await query.answer()
        try:
            user_id = update.effective_user.id
        except:
            user_id = query.from_user.id
        settings = get_settings(user_id)
        c_model = tuple(f"model{i}" for i in range(len(gemini_model_list)))
        personas = glob("persona/*shadow")
        c_persona = tuple(f"persona{i}" for i in range(len(personas)))

        if query.data == "c_model":
            keyboard = []
            for i in range(0, len(gemini_model_list), 2):
                row =[]
                row.append(InlineKeyboardButton(text=gemini_model_list[i], callback_data=f"model{i}"))
                if i+1 < len(gemini_model_list):
                    row.append(InlineKeyboardButton(text=gemini_model_list[i+1], callback_data=f"model{i+1}"))
                keyboard.append(row)
            keyboard.append([InlineKeyboardButton("Cancel", callback_data="cancel")])
            model_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(f"Current Model: {gemini_model_list[settings[2]]}\nChoose a model:", reply_markup=model_markup, parse_mode="Markdown")

        elif query.data == "c_streaming":
            keyboard = [
                [InlineKeyboardButton("ON", callback_data="c_streaming_on"), InlineKeyboardButton("OFF", callback_data="c_streaming_off")]    
            ]
            markup = InlineKeyboardMarkup(keyboard)
            settings = get_settings(user_id)
            c_s = "ON" if settings[5] == 1 else "OFF"
            await query.edit_message_text(f"Streaming let you stream the bot response in real time.\nCurrent setting : {c_s}", reply_markup=markup)

        elif query.data == "c_streaming_on":
            conn = sqlite3.connect("settings/user_settings.db")
            cursor = conn.cursor()
            cursor.execute("UPDATE user_settings SET streaming = ? WHERE id = ?", (1, user_id))
            conn.commit()
            conn.close()
            await query.edit_message_text("Streaming has turned on.")

        elif query.data == "c_streaming_off":
            conn = sqlite3.connect("settings/user_settings.db")
            cursor = conn.cursor()
            cursor.execute("UPDATE user_settings SET streaming = ? WHERE id = ?", (0, user_id))
            conn.commit()
            conn.close()
            await query.edit_message_text("Streaming has turned off.")

        elif query.data == "c_persona":
            personas = sorted(glob("persona/*shadow"))
            settings = get_settings(user_id)
            keyboard = []
            for i in range(0, len(personas), 2):
                row = []
                name = os.path.splitext(os.path.basename(personas[i]))[0]
                if name != "memory_persona":
                    row.append(InlineKeyboardButton(text=name, callback_data="persona"+str(i)))
                if i+1 < len(personas):
                    name = os.path.splitext(os.path.basename(personas[i+1]))[0]
                    if name != "memory_persona":
                        row.append(InlineKeyboardButton(text = name, callback_data="persona"+str(i+1)))
                keyboard.append(row)
            keyboard.append([InlineKeyboardButton("Cancel", callback_data="cancel")])
            markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("Select a persona:", reply_markup=markup, parse_mode="Markdown")

        elif query.data == "c_memory":
            keyboard = [
                [InlineKeyboardButton("Show Memory", callback_data="c_show_memory"), InlineKeyboardButton("Delete Memory", callback_data="c_delete_memory")],
                [InlineKeyboardButton("Cancel", callback_data="cancel")]
            ]
            memory_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("Memory is created based on you conversation history to provide more personalized response.", reply_markup=memory_markup, parse_mode="Markdown")

        elif query.data == "c_conv_history":
            keyboard = [
                [InlineKeyboardButton("Show", callback_data="c_ch_show"), InlineKeyboardButton("Reset", callback_data="c_ch_reset")],
                [InlineKeyboardButton("Cancel", callback_data="cancel")]
            ]
            ch_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("Conversation history holds your conversation with the bot.", reply_markup=ch_markup, parse_mode="Markdown")

        elif query.data in c_model :
            conn = sqlite3.connect("settings/user_settings.db")
            cursor = conn.cursor()
            model_num = int(query.data[5:])
            if gemini_model_list[model_num] != "gemini-2.5-pro":
                cursor.execute("UPDATE user_settings SET model = ? WHERE id = ?", (model_num, user_id))
                conn.commit()
                conn.close()
                await query.edit_message_text(f"AI model is successfully changed to {gemini_model_list[model_num]}.")
            elif gemini_model_list[model_num] == "gemini-2.5-pro":
                cursor.execute("UPDATE user_settings SET model = ?, thinking_budget = ? WHERE id = ? AND thinking_budget = 0", (model_num, 1024, user_id))
                conn.commit()
                conn.close()
                await query.edit_message_text(f"AI model is successfully changed to {gemini_model_list[model_num]}.")

        elif query.data in c_persona:
            conn = sqlite3.connect("settings/user_settings.db")
            cursor = conn.cursor()
            persona_num = int(query.data[7:])
            cursor.execute("UPDATE user_settings SET persona = ? WHERE id = ?", (persona_num, user_id))
            conn.commit()
            conn.close()
            personas = sorted(glob("persona/*shadow"))
            await query.edit_message_text(f"Persona is successfully changed to {os.path.splitext(os.path.basename(personas[persona_num]))[0]}.")

        elif query.data == "g_classroom":
            await query.edit_message_text("CSE Google classroom code: ```2o2ea2k3```\n\nMath G. Classroom code: ```aq4vazqi```\n\nChemistry G. Classroom code: ```wnlwjtbg```", parse_mode="Markdown")

        elif query.data == "c_all_websites":
            keyboard = [
                [InlineKeyboardButton("CSE 24 Website", url="https://ruetcse24.vercel.app/")],
                [InlineKeyboardButton("Facebook", url="https://www.facebook.com/profile.php?id=61574730479807"), InlineKeyboardButton("Profiles", url="https://ruetcse24.vercel.app/profiles")],
                [InlineKeyboardButton("Cancel", callback_data="cancel")]
            ]
            aw_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("CSE 24 RELATED ALL WEBSITES:", reply_markup=aw_markup)

        elif query.data == "c_circulate_routine":
            await query.edit_message_text("Please wait while bot is circulating the routine.")
            asyncio.create_task(circulate_routine(update.callback_query, content))

        elif query.data == "c_toggle_routine":
            keyboard = [
                [InlineKeyboardButton("Sure", callback_data="c_tr_sure"), InlineKeyboardButton("Cancel", callback_data="c_tr_cancel")]
            ]
            tr_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("Are you sure you want to toggle the routine?", reply_markup=tr_markup)

        elif query.data == "c_tr_sure":
            with open("routine/lab_routine.txt", "r+", encoding="utf-8") as f:
                active = f.read()
                f.seek(0)
                f.truncate(0)
                if active == "first":
                    f.write("second")
                elif active=="second":
                    f.write("first")
                await query.edit_message_text("Routine Succesfully Toggled.")

        elif query.data == "c_tr_cancel":
            await query.edit_message_text("Thanks.")

        elif query.data == "cancel":
            await query.delete_message()

        elif query.data == "c_show_memory":
            await see_memory(update, content, query)

        elif query.data == "c_delete_memory":
            await delete_memory(update, content, query)

        elif query.data == "c_ch_show":
            await query.edit_message_text("Your conversation history:")
            with open(f"Conversation/conversation-{user_id}.txt", "rb") as file:
                if os.path.getsize(f"Conversation/conversation-{user_id}.txt") == 0:
                    await query.message.reply_text("You don't have any conversation history.")
                else:
                    await content.bot.send_document(chat_id=user_id, document=file)

        elif query.data == "c_ch_reset":
            await reset(update, content, query)

        elif query.data == "c_admin_help":
            if user_id in all_admins:
                keyboard = [
                    [InlineKeyboardButton("Read Documentation", url = "https://github.com/sifat1996120/Phantom_bot")],
                     [InlineKeyboardButton("Cancel", callback_data="cancel")]
                ]
                markup = InlineKeyboardMarkup(keyboard)
                with open("admin/admin_help.shadow", "rb") as file:
                    help_data = fernet.decrypt(file.read()).decode("utf-8")
                    help_data = help_data if help_data else "Sorry no document. Try again later."
                await query.edit_message_text(help_data, reply_markup=markup)
            else:
                await query.edit_message_text("Sorry you are not a Admin.")
        
        elif query.data == "c_manage_ai_model":
            keyboard = [
                [InlineKeyboardButton("Add Model", callback_data="c_add_model"), InlineKeyboardButton("Delete Model", callback_data="c_delete_model")],
                [InlineKeyboardButton("Cancel", callback_data="cancel")]
            ]
            markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("From here you can manage the AI model this bot use to provide response.\n\nChoose an option:", reply_markup=markup, parse_mode="Markdown")

        elif query.data == "c_show_all_user":
            conn = sqlite3.connect("info/user_data.db")
            cursor = conn.cursor()
            cursor.execute("SELECT user_id from users")
            rows = cursor.fetchall()
            users = tuple(row[0] for row in rows)
            user_data = "All registered users are listed below:\n"
            for i, user in enumerate(users):
                user_data += f"{i+1}. {user}\n"
            await query.edit_message_text(user_data)


    except Exception as e:
        print(f"Error in button_handler function.\n\nError Code -{e}")
        await query.edit_message_text("Internal Error. Please try again later or contact admin.")
        return ConversationHandler.END











#main function

async def main():
    try:
        app = ApplicationBuilder().token(TOKEN).request(request).concurrent_updates(True).build()

        #conversation handler for managing model
        manage_ai_model_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(manage_model, pattern="^(c_add_model|c_delete_model)$")],
            states = {
                "TMN" : [MessageHandler(filters.TEXT & ~filters.COMMAND, take_model_name)]
            },
            fallbacks=[CallbackQueryHandler(cancel_conversation, pattern="^cancel_conv$")]
        )

        #conversation handler for taking thinking token
        thinking_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(thinking, pattern="^c_thinking$")],
            states={
                "TT" : [MessageHandler(filters.TEXT & ~filters.COMMAND, take_thinking)]
            },
            fallbacks=[CallbackQueryHandler(cancel_conversation, pattern="^cancel_conv$")]
        )

        #conversation handler for taking temperature
        temperature_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(temperature, pattern="^c_temperature$")],
            states={
                "TT" : [MessageHandler(filters.TEXT & ~filters.COMMAND, take_temperature)]
            },
            fallbacks=[CallbackQueryHandler(cancel_conversation, pattern="^cancel_conv$")]
        )

        #conversation handler for registering new user
        register_conv = ConversationHandler(
            entry_points=[
                CallbackQueryHandler(take_name, pattern="c_register")
            ],
            states = {
                "TG" : [MessageHandler(filters.TEXT & ~filters.COMMAND, take_gender)],
                "TR" : [CallbackQueryHandler(take_roll, pattern="^(c_male|c_female)$")],
                "RA" : [MessageHandler(filters.TEXT & ~filters.COMMAND, roll_action)],
                "AH" : [
                        CallbackQueryHandler(handle_skip, pattern="^c_skip$"),
                        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_api_conv)
                ],
                "TP" : [MessageHandler(filters.TEXT & ~filters.COMMAND, take_password)],
                "CP" : [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_password)],
                
            },
            fallbacks=[CallbackQueryHandler(cancel_conversation, pattern="^cancel_conv$")],
            per_message=False,
        )

        #conversation handler for managing admin commad
        manage_admin_conv = ConversationHandler(
            entry_points = [CallbackQueryHandler(admin_password_taker, pattern="^c_manage_admin$")],
            states = {
                "MA" : [MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    manage_admin,
                )],
                "ADMIN_ACTION" : [CallbackQueryHandler(admin_action, pattern="^(add_admin|delete_admin|see_all_admin)$")],
                "ENTER_USER_ID" : [MessageHandler(filters.TEXT & ~filters.COMMAND, add_or_delete_admin)]
            },
            fallbacks=[CallbackQueryHandler(cancel_conversation, pattern="^cancel_conv$")],
            per_message=False
        )

        #conversation handler for circulate message
        circulate_message_conv = ConversationHandler(
            entry_points = [CallbackQueryHandler(message_taker, pattern="^c_circulate_message$")],
            states = {
                "CM" : [MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    handle_circulate_message,
                )],
            },
            fallbacks=[CallbackQueryHandler(cancel_conversation, pattern="^cancel_conv")],
            per_message=False
        )

        #conversation handler for adding a new api
        api_conv_handler = ConversationHandler(
            entry_points = [CommandHandler("api", api)],
            states = {
                1 : [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_api)]
            },
            fallbacks = [CallbackQueryHandler(cancel_conversation, pattern="^cancel_conv$")],
        )
        app.add_handler(register_conv)
        app.add_handler(api_conv_handler)
        app.add_handler(thinking_conv)
        app.add_handler(temperature_conv)
        app.add_handler(manage_admin_conv)
        app.add_handler(manage_ai_model_conv)
        app.add_handler(circulate_message_conv)
        app.add_handler(CommandHandler("help", help))
        app.add_handler(CommandHandler("start",start))
        app.add_handler(CallbackQueryHandler(button_handler))
        app.add_handler(CommandHandler("admin", admin_handler))
        app.add_handler(MessageHandler(filters.Sticker.ALL, handle_sticker))
        app.add_handler(MessageHandler(filters.PHOTO & ~filters.ChatType.CHANNEL, handle_image))
        app.add_handler(MessageHandler(filters.AUDIO & ~filters.ChatType.CHANNEL, handle_audio))
        app.add_handler(MessageHandler(filters.VOICE & ~filters.ChatType.CHANNEL, handle_voice))
        app.add_handler(MessageHandler(filters.VIDEO & ~filters.ChatType.CHANNEL, handle_video))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.ChatType.CHANNEL, echo))
        # with open("info/webhook_url.shadow", "rb") as file:
        #     url = fernet.decrypt(file.read().strip()).decode("utf-8")
        # app.run_webhook(
        #     listen = "0.0.0.0",
        #     port = int(os.environ.get("PORT", 10000)),
        #     webhook_url = url
        #)
        await run_workers(8)
        await app.initialize()
        await app.start()
        await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        await asyncio.Event().wait()
        #app.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        print(f"Error in main function. Error Code - {e}")


if __name__=="__main__":
    asyncio.run(main())