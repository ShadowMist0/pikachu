import re
import os
import time
import html
import sqlite3
import asyncio
import threading
import requests
from glob import glob
from io import BytesIO
from flask import Flask, request
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
    CallbackQueryHandler
)
from telegram.constants import ChatAction
from telegram.error import RetryAfter, TimedOut
from google import genai
from google.genai import types




#a flask to ignore web pulling condition

app = Flask(__name__)
@app.route('/')
def home():
    return "Bot is runnig", 200





#all globals variable

channel_id = -1002575042671
#Loading all gemini model and selecting a model
try:
    with open("info/gemini_model.txt" , "r") as f:
        gemini_model_list = [line.strip() for line in f.readlines() if line.strip()]
except Exception as e:
    print(f"Error Code -{e}")

#loading the bot api
try:
    with open("API/bot_api.txt", "r") as f:
        TOKEN = f.read()
except Exception as e:
    print(f"Error Code -{e}")

if TOKEN:
    try:
        Application = ApplicationBuilder().token(TOKEN).build()
    except Exception as e:
        print(f"Error building telegram application.\n\nError Code-{e}")
        Application = None
else:
    Application = None

#all registered user
def load_all_user():
    try:
        conn = sqlite3.connect("info/user_data.db")
        cursor = conn.cursor()
        cursor.execute("SELECT user_id from users")
        rows = cursor.fetchall()
        users = {row[0] for row in rows}
        conn.close()
        return users
    except Exception as e:
        print(f"Error in load_all_user fnction.\n\n Error code -{e}")
all_users = load_all_user()

#ct routine url for cse sec c
FIREBASE_URL = 'https://last-197cd-default-rtdb.firebaseio.com/routines.json'



#function for webhook
@app.route(f"/webhook/{TOKEN}", methods=["POST"])
def webhook():
    if Application is not None:
        return Application.update_webhook(request)
    return "Bot is not ready", 503


def run_web():
    port = int(os.environ.get("PORT", 5000))  # Render sets $PORT automatically
    app.run(host='0.0.0.0', port=port)

threading.Thread(target=run_web).start()




#All the global function 

#loading persona
def load_persona(settings):
    try:
        files = sorted(glob("persona/*txt"))
        with open(files[settings[6]], "r") as file:
            persona = file.read()
        return persona
    except Exception as e:
        print(f"Error in load_persona function. \n\n Error Code - {e}")
        return "none"
    

#Loading api key
def load_gemini_api():
    try:
        with open("API/gemini_api.txt", "r") as f:
            return [line.strip() for line in f.readlines() if line.strip()]
    except Exception as e:
        print(f"Error lading gemini API. \n\nError Code -{e}")


#adding escape character for markdown rule
def add_escape_character(text):
    escape_chars = r'_*\[\]()~>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)


#function to get settings
def get_settings(user_id,user_name):
    conn = sqlite3.connect("settings/user_settings.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO user_settings (
            id,
            name,
            model,
            thinking_budget,
            temperature,
            streaming,
            persona
        )
        VALUES(?,?,?,?,?,?,?)
        """,
        (user_id,user_name,1,0,0.7,0,0)
    )
    conn.commit()
    cursor.execute("SELECT * FROM user_settings WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        return list(row)
    else:
        return [user_id, user_name, 1, 0, 0.7, 0, 0]


#gemini response for stream on
def gemini_stream(user_message, api, settings):
    try:
        client = genai.Client(api_key=api)
        response = client.models.generate_content_stream(
            model = gemini_model_list[settings[2]],
            contents = [user_message],
            config = types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_budget=settings[3]),
                temperature = settings[4],
                system_instruction = load_persona(settings),
            ),
        )
        return response
    except Exception as e:
        print(f"Error getting gemini response.\n\n Error Code - {e}")


#gemini response for stream off
def gemini_non_stream(user_message, api, settings):
    try:
        client = genai.Client(api_key=api)
        response = client.models.generate_content(
            model = gemini_model_list[settings[2]],
            contents = [user_message],
            config = types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_budget=settings[3]),
                temperature = settings[4],
                system_instruction = load_persona(settings),
            ),
        )
        return response
    except Exception as e:
        print(f"Error getting gemini response.\n\n Error Code - {e}")
        


#A function to delete n times convo from conversation history
def delete_n_convo(user_id, n):
    try:
        if user_id == 100:
            with open(f"Conversation/conversation-group.txt", "r+", encoding="utf-8") as f:
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
        if user_id != 100:
            with open("persona/memory_persona.txt", "r", encoding="utf-8") as f:
                instruction = f.read()
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
        elif user_id == 100:
            with open("persona/memory_persona.txt", "r", encoding="utf-8") as f:
                instruction = f.read()
            with open(f"memory/memory-group.txt", "a+", encoding = "utf-8") as f:
                f.seek(0)
                data = "***PREVIOUS MEMORY***\n\n"
                data += f.read()
                data += "\n\n***END OF MEMORY***\n\n"
            with open(f"Conversation/conversation-group.txt", "a+", encoding = "utf-8") as f:
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
        if user_id != 100:
            with open(f"memory/memory-{user_id}.txt", "a+", encoding="utf-8") as f:
                f.write(response.text)
            delete_n_convo(user_id, 10)
        elif user_id == 100:
            with open(f"memory/memory-group.txt", "a+", encoding="utf-8") as f:
                f.write(response.text)
            delete_n_convo(100,100)
    except Exception as e:
        print(f"Failed to create memory\n Error code-{e}")



#create the conversation history as prompt
async def create_prompt(update:Update, content:ContextTypes.DEFAULT_TYPE, user_message, user_id):
    try:
        if update.message.chat.type == "private":
            data = "***RULES***\n"
            with open("info/rules.txt", "r" , encoding="utf-8") as f:
                data += f.read()
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
            data = "***RULES***\n"
            with open("info/group-rules.txt", "r" , encoding="utf-8") as f:
                data += f.read()
                data += "\n***END OF RULES***\n\n\n"
            data += "******TRAINING DATA******\n\n"
            with open("info/group_training_data.txt", "r") as f:
                data += f.read()
                data += "******END OF TRAINING DATA******\n\n"
            data += "***MEMORY***\n"
            with open(f"memory/memory-group.txt", "a+", encoding="utf-8") as f:
                f.seek(0)
                data += f.read()
                data += "\n***END OF MEMORY***\n\n\n"
            with open(f"Conversation/conversation-group.txt", "a+", encoding="utf-8") as f:
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
        name = update.effective_user.first_name or "X" +" "+ update.effective_user.last_name or "X"
        with open(f"Conversation/conversation-group.txt", "a+", encoding="utf-8") as f:
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
                    buffer += chunk.text
                    sent_message += chunk.text
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
            await update.message.reply_text("You are not registerd yet.", reply_markup=reply_markup)
            all_users = load_all_user()
    except Exception as e:
        print(f"Error in start function. \n Error Code - {e}")
        await send_to_channel(update, content, channel_id, f"Error in start function \n\nError Code -{e}")



#function for all other messager that are directly send to bot without any command
async def echo(update : Update, content : ContextTypes.DEFAULT_TYPE) -> None:
    try:
        if update.message:
            await update.message.chat.send_action(action = ChatAction.TYPING)
        gemini_api_keys = load_gemini_api()
        user_id = update.effective_user.id
        user_name = f"{update.effective_user.first_name or "X"} {update.effective_user.last_name or "X"}".strip()
        user_message = (update.message.text or "...").strip()
        if user_message == "ROUTINE":
            await routine_handler(update, content)
        elif user_message == "SETTINGS":
            await handle_settings(update, content)
            await update.message.delete()
        elif user_message == "CT":
            await handle_ct(update, content)
        elif user_message == "RESOURCES":
            keyboard = [
                [InlineKeyboardButton("Drive", url="https://drive.google.com/drive/folders/1xbyCdj3XQ9AsCCF8ImI13HCo25JEhgUJ"), InlineKeyboardButton("Syllabus", url="https://drive.google.com/file/d/1pVF40-E0Oe8QI-EZp9S7udjnc0_Kquav/view?usp=drive_link")],
                [InlineKeyboardButton("Orientation Files", url = "https://drive.google.com/drive/folders/10_-xTV-FsXnndtDiw_StqH2Zy9tQcWq0"), InlineKeyboardButton("All Websites", callback_data="c_all_websites")],
                [InlineKeyboardButton("G. Classroom Code", callback_data="g_classroom"), InlineKeyboardButton("Cancel", callback_data="cancel")]
            ]
            resource_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("All the resources available for CSE SECTION C", reply_markup=resource_markup, parse_mode="Markdown")
            await update.message.delete()
        else:
            settings = get_settings(user_id, user_name)
            if update.message.chat.type != "private":
                settings = [100,"group",1,0,0.7,0,4]
            prompt = await create_prompt(update, content, user_message, user_id)
            for i in range(len(gemini_api_keys)):
                try:
                    if(settings[5]):
                        response = gemini_stream(prompt, gemini_api_keys[i],settings)
                        next(response).text
                        break
                    else:
                        response = gemini_non_stream(prompt, gemini_api_keys[i],settings)
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
    except Exception as e:
        print(f"Error in echo function.\n\n Error Code - {e}")
        await send_to_channel(update, content, channel_id, f"Error in echo function \n\nError Code -{e}")


#function for the command reset
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
        with open("info/getting_api.txt") as f:
            for line in f.readlines():
                if line.strip():
                    await update.message.reply_text(line.strip())
        return 1
    except Exception as e:
        print(f"Error in api function.\nError Code - {e}")
        await send_to_channel(update, content, channel_id, f"Error in api function \n\nError Code -{e}")


#function to handle api
async def handle_api(update : Update, content : ContextTypes.DEFAULT_TYPE) -> None:
    try:
        with open("API/gemini_api.txt", "r", encoding="utf-8") as f:
            existing_apis = f.read()
        existing_apis = set(line.strip() for line in existing_apis.splitlines() if line.strip())
        user_api = update.message.text.strip()
        await update.message.chat.send_action(action = ChatAction.TYPING)
        user_name = f"{update.effective_user.first_name or "X"} {update.effective_user.last_name or "X"}".strip()
        try:
            settings = get_settings(update.effective_user.id, user_name)
            response = gemini_stream("Checking if the gemini api is working or not", user_api, settings)
            chunk = next(response)
            if(
                user_api.startswith("AIza")
                and user_api not in existing_apis
                and " " not in user_api
                and len(user_api) >= 39
                and chunk.text
            ):
                with open("API/gemini_api.txt", "a") as f:
                    f.write(f"\n{user_api}")
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


#function to handle persona
async def handle_persona(update : Update, content : ContextTypes.DEFAULT_TYPE) -> None:
    if update.message.chat.type != "private":
        await update.message.reply_text("This function is only available in private chat.")
        return
    await update.message.reply_text("The Persona function is under developement, Try again Later")


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


#function to add persona from user
async def add_persona(update : Update, content : ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("The add_persona function is under developement, Try again Later")


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
        await update.message.reply_text("Bot Configuration Menu:", reply_markup=settings_markup)
        user_name = f"{update.effective_user.first_name or "X"} {update.effective_user.last_name or "X"}".strip()
        settings = get_settings(update.effective_user.id, user_name)
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
            await create_memory(load_gemini_api()[-1], 100)
            await send_to_channel(update, content, channel_id, "Created memory for group")
            with open(f"memory/memory-group.txt", "r", encoding="utf-8") as f:
                await content.bot.send_document(chat_id=channel_id, document=file, caption="Memory for the group.")
    except Exception as e:
        print(f"Error in background_memory_creation function.\n\n Error Code -{e}")
        await send_to_channel(update, content, channel_id, f"Error in background_memory_creation function.\n\n Error Code -{e}")






#a function for admin call
async def admin_handler(update : Update, content : ContextTypes.DEFAULT_TYPE) -> None:
    try:
        if update.effective_user.id == 6226239719 :
            keyboard = [
                [InlineKeyboardButton("Circulate Routine", callback_data="c_circulate_routine")],
                [InlineKeyboardButton("Circulate Message", callback_data="c_circulate_message")],
                [InlineKeyboardButton("Toggle Routine", callback_data="c_toggle_routine")],
                [InlineKeyboardButton("Manage Admin", callback_data="c_manage_admin")],
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
            [InlineKeyboardButton("Read Documentation", url = "https://github.com/sifat1996120/Phantom_bot")]
        ]
        help_markup = InlineKeyboardMarkup(keyboard)
        with open("info/help.txt", "r", encoding="utf-8") as file:
            await update.message.reply_text(file.read(), reply_markup=help_markup)
    except Exception as e:
        print(f"Error in help function. \n\n Error Code - {e}")
        await send_to_channel(update, content, channel_id, f"Error in help function. \n\n Error Code - {e}")


#function to take message for circulate message
async def message_taker(update:Update, content:ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [[InlineKeyboardButton("Cancel", callback_data="cancel_conv")]]
    mt_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text("Enter the message here:", reply_markup=mt_markup)
    return "CM"


#function to take password for admin function
async def password_taker(update: Update, content:ContextTypes.DEFAULT_TYPE) -> None:
    Keyboard = [[InlineKeyboardButton("Cancel", callback_data="cancel_conv")]]
    pt_markup = InlineKeyboardMarkup(Keyboard)
    msg = await update.callback_query.edit_message_text("Password for Admin:", reply_markup=pt_markup)
    content.user_data["pt_message_id"] = msg.message_id
    return "MA"


#function to create background task for circulate message
async def handle_circulate_message(update:Update, content:ContextTypes.DEFAULT_TYPE) -> None:
    asyncio.create_task(circulate_message(update, content))
    return ConversationHandler.END


#function to manage admin
async def manage_admin(update:Update, content:ContextTypes.DEFAULT_TYPE) -> None:
    msg_id = content.user_data.get("pt_message_id")
    try:
        await content.bot.delete_message(chat_id=update.effective_chat.id, message_id=msg_id)
    except:
        pass
    given_password = update.message.text.strip()
    with open("admin/admin_password.txt", "r") as file:
        password = file.read().strip()
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


#function to manage admin action
async def admin_action(update:Update, content:ContextTypes.DEFAULT_TYPE) -> None:
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
        await query.edit_message_text("ALL ADMIN:")
        return ConversationHandler.END
    return "ENTER_USER_ID"


#function to add or delete admin
async def add_or_delete_admin(update:Update, content:ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.text.strip()
    action = content.user_data.get("admin_action")
    msg_id = content.user_data.get("aa_message_id")
    await content.bot.delete_message(chat_id=update.effective_chat.id, message_id=msg_id)
    if action == "add_admin":
        await update.message.reply_text("ADDED")
        return ConversationHandler.END
    elif action == "delete_admin":
        await update.message.reply_text("DELETED")
        return ConversationHandler.END


#function to cancel conversation by cancel button
async def cancel_conversation(update: Update, content: ContextTypes.DEFAULT_TYPE) -> None:
    await update.callback_query.delete_message()
    return ConversationHandler.END


#A function to handle button response
async def button_handler(update:Update, content:ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    conn = sqlite3.connect('settings/user_settings.db')
    user_id = update.effective_user.id
    settings = get_settings(user_id, update.effective_user.last_name)
    cursor = conn.cursor()
    if query.data == "c_model":
        keyboard = [[InlineKeyboardButton(text=model, callback_data=str(i))]
            for i, model in enumerate(gemini_model_list)
        ]
        keyboard.append([InlineKeyboardButton("Cancel", callback_data="cancel")])
        model_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(f"Current Model: {gemini_model_list[settings[2]]}", reply_markup=model_markup)
    elif query.data == "c_temperature":
        await query.edit_message_text("Temperature Clicked")
    elif query.data == "c_thinking":
        await query.edit_message_text("Thinking Clicked")
    elif query.data == "c_streaming":
        await query.edit_message_text("streaming Clicked")
    elif query.data == "c_persona":
        await query.edit_message_text("Persona Clicked")
    elif query.data == "c_memory":
        keyboard = [
            [InlineKeyboardButton("Show", callback_data="c_show_memory"), InlineKeyboardButton("Delete", callback_data="c_delete_memory")],
            [InlineKeyboardButton("Cancel", callback_data="cancel")]
        ]
        memory_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Chose an option:", reply_markup=memory_markup)
    elif query.data == "c_conv_history":
        keyboard = [
            [InlineKeyboardButton("Show", callback_data="c_ch_show"), InlineKeyboardButton("Reset", callback_data="c_ch_reset")],
            [InlineKeyboardButton("Cancel", callback_data="cancel")]
        ]
        ch_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Choose an option:", reply_markup=ch_markup)
    elif query.data == "1":
        await query.edit_message_text("1")
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
        with open("routine/lab_routine.txt", "w", encoding="utf-8") as f:
            f.write("second")
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
        user_id = update.callback_query.from_user.id
        with open(f"Conversation/conversation-{user_id}.txt", "rb") as file:
            content = file.read()
            if not content:
                await query.message.reply_text("You don't have any conversation history.")
            else:
                await content.bot.send_document(chat_id=user_id, document=file)
    elif query.data == "c_ch_reset":
        await reset(update, content, query)











#main function

def main():
    try:
        app = ApplicationBuilder().token(TOKEN).build()
        add_admin_conv = ConversationHandler(
            entry_points = [CallbackQueryHandler(password_taker, pattern="^c_manage_admin$")],
            states = {
                "MA" : [MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    manage_admin,
                )],
                "ADMIN_ACTION" : [CallbackQueryHandler(admin_action, pattern="^(add_admin|delete_admin|see_all_admin)$")],
                "ENTER_USER_ID" : [MessageHandler(filters.TEXT & ~filters.COMMAND, add_or_delete_admin)]
            },
            fallbacks=[CallbackQueryHandler(cancel_conversation, pattern="^cancel_conv$")]
        )
        circulate_message_conv = ConversationHandler(
            entry_points = [CallbackQueryHandler(message_taker, pattern="^c_circulate_message$")],
            states = {
                "CM" : [MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    handle_circulate_message,
                )],
            },
            fallbacks=[CallbackQueryHandler(cancel_conversation, pattern="^cancel_conv")],
            per_message=False,
        )
        api_conv_handler = ConversationHandler(
            entry_points = [CommandHandler("api", api)],
            states = {
                1 : [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_api)]
            },
            fallbacks = [CallbackQueryHandler(cancel_conversation, pattern="^cancel_conv$")],
        )
        app.add_handler(api_conv_handler)
        app.add_handler(add_admin_conv)
        app.add_handler(circulate_message_conv)
        app.add_handler(CommandHandler("start",start))
        app.add_handler(CommandHandler("help", help))
        app.add_handler(CommandHandler("admin", admin_handler))
        app.add_handler(MessageHandler(filters.Sticker.ALL, handle_sticker))
        app.add_handler(CallbackQueryHandler(button_handler))
        app.add_handler(MessageHandler(filters.PHOTO & ~filters.ChatType.CHANNEL, handle_image))
        app.add_handler(MessageHandler(filters.AUDIO & ~filters.ChatType.CHANNEL, handle_audio))
        app.add_handler(MessageHandler(filters.VOICE & ~filters.ChatType.CHANNEL, handle_voice))
        app.add_handler(MessageHandler(filters.VIDEO & ~filters.ChatType.CHANNEL, handle_video))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.ChatType.CHANNEL, echo))
        with open("info/webhook_url.txt", "r", encoding="utf-8") as file:
            url = file.read().strip()
        app.run_webhook(
            listen = "0.0.0.0",
            port = int(os.environ.get("PORT", 10000)),
            webhook_url = url
        )
    except Exception as e:
        print(f"Error in main function. Error Code - {e}")


if __name__=="__main__":
    main()