import os
import json
import random
import sqlite3
import asyncio
from telegram import Update
from telegram.ext import ContextTypes
from utils.utils import is_ddos, get_settings, send_to_channel, load_persona
from telegram.constants import ChatAction
from google import genai
from google.genai import types
from utils.config import channel_id, media_count_limit, media_size_limit, premium_media_count_limit, premium_media_size_limit
from ext.user_content_tools import create_prompt
from utils.db import gemini_api_keys, premium_users
import time
from utils.utils import(
    is_ddos,
    send_to_channel,
    safe_send,
    get_settings,
    is_code_block_open
)
from ext.user_content_tools import save_conversation





valid_ext = [
    ".pdf", ".json", ".txt", ".docx", ".py", ".c", ".cpp",
    ".cxx", ".html", ".htm", ".js" , ".java", ".css", ".xml",
    ".php", ".json", ".doc", ".ppt", ".pptx", ".xls", "xlsx",
    ".csv", ".md", ".log", ".yaml", ".png", ".jpg", ".jpeg",
    ".gif", ".webp", ".mp4", ".avi", ".mkv", ".webm", ".mp3",
    ".ogg", ".wav", ".m4a"
]




#a function to save media conversation history with media description
async def save_media_conversation(update:Update, content:ContextTypes.DEFAULT_TYPE, prompt, response, user_id, path, file_id, file_type):
    try:
        description = await media_description_generator(update,content, path, file_id)
        if description:
            await asyncio.to_thread(save_conversation, f"<{file_type}>Type: {description[1]}, Path: {description[2]}, Size: {description[3]} MB</{file_type}>\n" + prompt + "\n", response.text, user_id)
        else:
            await asyncio.to_thread(save_conversation, f"<{file_type}>"+prompt, response.text, user_id)
    except Exception as e:
        print(f"Error in save_media_conversation function.\n\nError Code -{e}")


#function for editing and sending message
async def send_message(update : Update, content : ContextTypes.DEFAULT_TYPE, response, user_message, settings) -> None:
    try:
        message = update.message or update.edited_message
        if not response:
            await message.reply_text("Failed to precess your request. Try again later.")
            return
        if await is_ddos(update, content, update.effective_user.id):
            return
        message_to_send = response.text if hasattr(response, "text") else str(response)
        if len(message_to_send) > 4080:
            message_chunks = [message_to_send[i:i+4080] for i in range(0, len(message_to_send), 4080)]
            for i,msg in enumerate(message_chunks):
                if is_code_block_open(msg):
                    message_chunks[i] += "```"
                    message_chunks[i+1] = "```\n" + message_chunks[i+1]
                await safe_send(update, content, message_chunks[i])
        else:
            await safe_send(update, content, message_to_send)
    except Exception as e:
        print(f"Error in send_message function Error Code - {e}")
        await send_to_channel(update, content, channel_id, f"Error in send_message function \n\nError Code -{e}")






async def media_description_generator(update:Update, content:ContextTypes.DEFAULT_TYPE, path, file_id):
    try:
        await media_manager(update, content, path, os.path.getsize(path)/(1024*1024))
        def get_description():
            temp_api = list(gemini_api_keys)
            for _ in range(len(gemini_api_keys)):
                api_key = random.choice(temp_api)
                if not api_key:
                    return "Failed to process your request. Please try again later."
                try:
                    client = genai.Client(api_key=api_key)
                    file = client.files.upload(file=path)
                    response = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=[file, "Generate up to 10 tags about and one line explaining its content. Keep it short but precise so that it can easily be found."],
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            response_schema={
                                "type" : "object",
                                "properties" : {
                                    "media_type" : {
                                        "type" : "string",
                                        "description" : "The type of media e.g. image, screenshot, video, python code etc."
                                    }
                                }
                            },
                        )
                    )
                    if response.prompt_feedback and response.prompt_feedback.block_reason:
                        print(f"Your response is blocked by gemini because of {response.prompt_feedback.block_reason}.")
                    return response
                except Exception as e:
                    print(f"Error generating description: {e}")
                    temp_api.remove(api_key)
        response = await asyncio.to_thread(get_description)
        response = json.loads(response.text)
        media_type = response.get("media_type", "unknown")
        if not response:
            return
        return [file_id, media_type, path, os.path.getsize(path)/(1024*1024)]
    except Exception as e:
        print(f"Error getting user id in media_description_generator function.\n\nError Code - {e}")



async def media_manager(update: Update, content: ContextTypes.DEFAULT_TYPE, path, size):
    try:
        user_id = update.effective_user.id
        timestamp = int(time.time())
        conn = sqlite3.connect('user_media/user_media.db')
        c = conn.cursor()

        # Limits based on user type
        size_limit = media_size_limit if str(user_id) not in premium_users else premium_media_size_limit
        count_limit = media_count_limit if str(user_id) not in premium_users else premium_media_count_limit

        # Fetch user’s current media
        c.execute('''SELECT * FROM user_media WHERE user_id=? ORDER BY timestamp ASC''', (user_id,))
        existing_media = c.fetchall()

        # Enforce media count limit
        while len(existing_media) >= count_limit:
            oldest_media = existing_media[0]
            oldest_path = oldest_media[2]
            if os.path.exists(oldest_path):
                os.remove(oldest_path)
            c.execute('''DELETE FROM user_media WHERE media_path=?''', (oldest_media[2],))
            conn.commit()
            # Refresh list after deletion
            c.execute('''SELECT * FROM user_media WHERE user_id=? ORDER BY timestamp ASC''', (user_id,))
            existing_media = c.fetchall()

        # Enforce size limit
        while sum(media[3] for media in existing_media) + size > size_limit:
            if not existing_media:
                break  # Safety check
            oldest_media = existing_media[0]
            oldest_path = oldest_media[2]
            if os.path.exists(oldest_path):
                os.remove(oldest_path)
            c.execute('''DELETE FROM user_media WHERE media_path=?''', (oldest_media[2],))
            conn.commit()
            # Refresh list after deletion
            c.execute('''SELECT * FROM user_media WHERE user_id=? ORDER BY timestamp ASC''', (user_id,))
            existing_media = c.fetchall()

        # Insert new media
        c.execute('''
            INSERT INTO user_media (user_id, timestamp, media_path, media_size)
            VALUES (?, ?, ?, ?)
        ''', (user_id, timestamp, path, size))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error in media_manager function: {e}")




#function to handle location
async def handle_location(update:Update, content:ContextTypes.DEFAULT_TYPE):
    try:
        if update.message.location:
            location = update.message.location
            location = (location.latitude, location.longitude)
            await update.message.reply_text(f"Your latitude is {location[0]} and longitude is {location[1]}")
    except Exception as e:
        print(f"Error in handle_location function. \n\nError code - {e}")



async def handle_media(update:Update, content:ContextTypes.DEFAULT_TYPE) -> None:
    try:
        global gemini_api_keys, valid_ext
        tools = [
            types.Tool(google_search=types.GoogleSearch),
            types.Tool(url_context=types.UrlContext)
        ]
        message = update.message or update.edited_message
        os.makedirs("data/media", exist_ok=True)
        chat_id = update.effective_chat.id
        settings = await get_settings(chat_id)
        await message.chat.send_action(action=ChatAction.TYPING)
        if(
            not message and not message.photo and not message.video
            and not message.audio and not message.voice 
            and not message.sticker and not message.document
            and message.chat.type != "private"
        ):
            return
        if await is_ddos(update, content, chat_id):
            return
        msg = await update.message.reply_text("Downloading...")
        if message.photo:
            file = message.photo[-1]
            photo = await message.photo[-1].get_file()
            ext = os.path.splitext(os.path.basename(photo.file_path))[1]
        elif message.voice:
            file = message.voice
            ext = ".ogg"
        else:
            file = message.video or message.audio or message.sticker or message.document
            file_obj = await file.get_file()
            ext = os.path.splitext(os.path.basename(file_obj.file_path))[1]
        file_size = file.file_size/(1024*1024)
        if file_size > 20:
            await message.reply_text("Failed to process your request. Telegram bot only  supports file up to 20 MB.")
            return
        if ext not in valid_ext:
            await update.message.reply_text("Unsupported Format...")
            return
        caption = message.caption or "If there is any question answer them if there is code find error and suggest improvement if there is no question and code then describe the content."
        file_id = file.file_unique_id
        path = f"data/media/{file_id}{ext}"
        prompt = await create_prompt(update, content, caption, chat_id, 1)
        media_file = await file.get_file()
        await media_file.download_to_drive(path)
        if not os.path.exists(path):
            await msg.edit_text("Download failed.. Try again later.")
            return
        await msg.edit_text("🤖 Analyzing content...\nThis may take a while ⏳")

        def gemini_analysis_worker():
                temp_api = list(gemini_api_keys)
                model = "gemini-2.5-pro" if settings[2] == "gemini-2.5-pro" else "gemini-2.5-flash"
                for _ in range(len(gemini_api_keys)):
                    api_key = random.choice(temp_api)
                    try:
                        client = genai.Client(api_key=api_key)
                        media = client.files.upload(file=path)
                        response = client.models.generate_content(
                            model=model,
                            contents = [media, prompt],
                            config=types.GenerateContentConfig(
                                system_instruction=load_persona(settings),
                                tools = tools,
                                thinking_config=types.ThinkingConfig(thinking_budget=settings[3]),
                                temperature = settings[4]
                            )
                        )
                        if response.prompt_feedback and response.prompt_feedback.block_reason:
                            return f"Your response is blocked by gemini because of {response.prompt_feedback.block_reason}"
                        response.text
                        return response
                    except Exception as e:
                        temp_api.remove(api_key)
                        if not temp_api:
                            return "Failed to process your request. Please try again later."
                        print(f"Error getting response for API{gemini_api_keys.index(api_key)}.\n\nError Code - {e}")
                return None
        
        response = await asyncio.to_thread(gemini_analysis_worker)
        if type(response) == str:
            await message.reply_text(response)
            await content.bot.delete_message(chat_id=chat_id, message_id=msg.message_id)
            return
        if response:
            await send_message(update, content, response, caption, settings)
            await content.bot.delete_message(chat_id=chat_id, message_id=msg.message_id)
            asyncio.create_task(save_media_conversation(update,content, caption, response, chat_id, path, file_id, "Media"))
            return
    except Exception as e:
        print(f"Error in handle_media function.\n\n Error Code - {e}")
        await send_to_channel(update, content, channel_id, f"Error in handle_media function \n\nError Code -{e}")
        
        