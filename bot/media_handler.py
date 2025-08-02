import os
import json
import random
import sqlite3
import asyncio
from telegram import Update
from telegram.ext import ContextTypes
from utils.utils import is_ddos, get_settings, send_to_channel, load_persona
from telegram.constants import ChatAction
from PIL import Image
from google import genai
from google.genai import types
from utils.config import channel_id, media_count_limit, media_size_limit, premium_media_count_limit, premium_media_size_limit
from ext.user_content_tools import create_prompt
from utils.db import gemini_api_keys, gemini_model_list, premium_users
from collections import defaultdict, deque
import time
from utils.func_description import media_description_generator_function, search_online_function
from ai.gemini_schema import search_online
from utils.utils import(
    is_ddos,
    send_to_channel,
    safe_send,
    get_settings,
    add_escape_character,
    has_codeblocks,
    is_code_block_open
)
from ext.user_content_tools import save_conversation, save_group_conversation







tools = []



#a function to save media conversation history with media description
async def save_media_conversation(update:Update, content:ContextTypes.DEFAULT_TYPE, prompt, response, user_id, path, file_id, file_type):
    try:
        description = await media_description_generator(update,content, path, file_id)
        if description:
            await asyncio.to_thread(save_conversation, f"<{file_type}>Type: {description[1]}, Description: {description[2]}, Path: {description[3]}, Size: {description[4]} MB</{file_type}>\n" + prompt + "\n", response.text, user_id)
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
        if(settings[5]):
            message_object  = await message.reply_text("Typing...")
            buffer = ""
            sent_message = ""
            chunks = ''
            for chunk in response:
                if not chunk.text:
                    continue
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
                        message_object = await safe_send(message.reply_text,buffer)
                    else:
                        buffer = chunk.text
                        sent_message += chunk.text
                        message_object = await safe_send(message.reply_text, buffer)
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
        #if streaming is off
        else:
            sent_message = response.text
            if len(sent_message) > 4080:
                messages = [sent_message[i:i+4080] for i in range(0, len(sent_message), 4080)]
                for i,msg in enumerate(messages):
                    if is_code_block_open(msg):
                        messages[i] += "```"
                        messages[i+1] = "```\n" + messages[i+1]
                    if not (has_codeblocks(msg)):
                        try:
                            await safe_send(message.reply_text, messages[i], parse_mode="Markdown")
                        except:
                            try:
                                await message.reply_text(add_escape_character(messages[i]), parse_mode="MarkdownV2")
                            except:
                                await message.reply_text(messages[i])
                    else:
                        try:
                            await message.reply_text(messages[i], parse_mode="Markdown")
                        except:
                            try:
                                await message.reply_text(add_escape_character(messages[i]), parse_mode="MarkdownV2")
                            except:
                                await message.reply_text(messages[i])
            else:
                if not(has_codeblocks(sent_message)):
                    try:
                        await message.reply_text(sent_message, parse_mode ="Markdown")
                    except:
                        try:
                            await message.reply_text(add_escape_character(sent_message), parse_mode="MarkdownV2")
                        except:
                            await message.reply_text(sent_message)
                else:
                    try:
                        await safe_send(message.reply_text, sent_message, parse_mode ="Markdown")
                    except:
                        try:
                            await message.reply_text(add_escape_character(sent_message), parse_mode="MarkdownV2")
                        except:
                            await message.reply_text(sent_message)
    except Exception as e:
        print(f"Error in send_message function Error Code - {e}")
        await send_to_channel(update, content, channel_id, f"Error in send_message function \n\nError Code -{e}")






async def media_description_generator(update:Update, content:ContextTypes.DEFAULT_TYPE, path, file_id):
    try:
        await media_manager(update, content, path, os.path.getsize(path)/(1024*1024))
        user_id = update.effective_user.id
        settings = await get_settings(user_id)
        conn = sqlite3.connect('user_media/user_media.db')
        c = conn.cursor()
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
                                    },
                                    "description" : {
                                        "type" : "string",
                                        "description" : "A short summarized yet precise description in one sentence"
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
        media_description = response.get("description", "")
        print(media_type)
        print(media_description)
        if not response:
            return
        return [file_id, media_type, media_description, path, os.path.getsize(path)/(1024*1024)]
    except Exception as e:
        print(f"Error getting user id in media_description_generator function.\n\nError Code - {e}")



async def media_manager(update: Update, content: ContextTypes.DEFAULT_TYPE, path, size):
    try:
        user_id = update.effective_user.id
        timestamp = int(time.time())
        conn = sqlite3.connect('user_media/user_media.db')
        c = conn.cursor()

        # Delete ALL media older than 1 hour (Global cleanup)
        c.execute('''SELECT media_path FROM user_media WHERE timestamp < ?''', (timestamp - 60*60,))
        old_media = c.fetchall()
        for media in old_media:
            media_path = media[0]
            if os.path.exists(media_path):
                os.remove(media_path)
        c.execute('''DELETE FROM user_media WHERE timestamp < ?''', (timestamp - 60*60,))
        conn.commit()

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





#function to handle image
async def handle_image(update : Update, content : ContextTypes.DEFAULT_TYPE) -> None:
    #try:
    chat_id = update.effective_chat.id
    tools = [
        types.Tool(google_search=types.GoogleSearch),
        types.Tool(url_context=types.UrlContext)
    ]
    global gemini_api_keys
    if await is_ddos(update, content, chat_id):
        return
    message = update.message or update.edited_message
    try:
        if message.chat.type != "private":
            await message.reply_text("This function is only available in private chat.")
            return
        if not update.edited_message:
            await message.chat.send_action(action=ChatAction.TYPING)
    except:
        pass
    os.makedirs("data/media",exist_ok=True)
    settings = await get_settings(update.effective_user.id)
    if message and message.photo:
        msg = await message.reply_text("Downloading Image...")
        caption = message.caption if message.caption else "Describe this imgae, if this image have question answer this."
        photo_file = await message.photo[-1].get_file()
        file_size = photo_file.file_size/(1024*1024)
        if file_size > 20:
            await message.reply_text("Failed to process your request. Telegram bot only  supports file up to 20 MB.")
            return
        ext = os.path.splitext(os.path.basename(photo_file.file_path))[1]
        if not ext:
            ext = ".jpg"
        if ext not in [".jpg", ".jpeg", ".png", ".webp", ".gif"]:
            await msg.edit_text("Invalid file format. Only jpg, jpeg, png, webp and gif are supported.")
            return
        file_id = photo_file.file_unique_id
        path = f"data/media/{file_id}{ext}"
        await photo_file.download_to_drive(path)
        try:
            photo = Image.open(path)
        except:
            await message.reply_text("Failed to process. Try again later.")
        prompt = await create_prompt(update, content, caption, chat_id, 1)

        if not os.path.exists(path):
            await message.reply_text("Invalid file.")
            return
        await msg.edit_text("🤖 Analyzing Image...\nThis may take a while ⏳")
        def gemini_photo_worker(image, prompt):
            if os.path.getsize(path)/(1024*1024) > 8:
                return "File size is too long for free tier. Contact admin to activate premium subscription."
            model = "gemini-2.5-pro" if gemini_model_list[settings[2]] == "gemini-2.5-pro" else "gemini-2.5-flash"
            temp_api = list(gemini_api_keys)
            for _ in range(len(gemini_api_keys)):
                api_key = random.choice(temp_api)
                if not api_key:
                    return "Failed to process your request. Please try again later."
                try:
                    client = genai.Client(api_key=api_key)
                    response = client.models.generate_content(
                        model = model,
                        contents = [image, prompt],
                        config = types.GenerateContentConfig(
                            thinking_config=types.ThinkingConfig(thinking_budget=settings[3]),
                            temperature = settings[4],
                            system_instruction = load_persona(settings),
                            tools = tools,
                        )
                    )
                    if response.prompt_feedback and response.prompt_feedback.block_reason:
                        return f"Your response is blocked by gemini because of {response.prompt_feedback.block_reason}."
                    if response:
                        return response
                except Exception as e:
                    print(f"Error getting response for API-{gemini_api_keys.index(api_key)}\n\nError Code - {e}")
                    temp_api.remove(api_key)
                    if not temp_api:
                        return "Failed to process your request. Please try again later."
            return None
        
        response = await asyncio.to_thread(gemini_photo_worker, photo, prompt)
        if type(response) == str:
            await message.reply_text(response)
            await content.bot.delete_message(chat_id=chat_id, message_id=msg.message_id)
            return
        if response:
            await send_message(update, content, response, caption, settings)
            await content.bot.delete_message(chat_id=chat_id, message_id=msg.message_id)
            asyncio.create_task(save_media_conversation(update,content, caption, response, chat_id, path, file_id, "Image"))
            return
    # except Exception as e:
    #     print(f"Error in handle_image function.\n\nError Code - {e}")
    #     await send_to_channel(update, content, channel_id, f"Error in handle_image function \n\nError Code -{e}")


#function to handle video
async def handle_video(update : Update, content : ContextTypes.DEFAULT_TYPE) -> None:
    try:
        global gemini_api_keys
        chat_id = update.effective_chat.id
        if await is_ddos(update, content, chat_id):
            return
        message = update.message or update.edited_message
        if message.chat.type != "private":
            await message.reply_text("This function is only available in private chat.")
            return
        os.makedirs("data/media",exist_ok=True)
        if not update.edited_message:
            await message.chat.send_action(action=ChatAction.TYPING)
        if message and message.video:
            file_size = message.video.file_size/(1024*1024)
            if file_size > 20:
                await message.reply_text("Failed to process your request. Telegram bot only  supports file up to 20 MB.")
                return
            video_file = await message.video.get_file()
            file_id = message.video.file_unique_id
            settings = await get_settings(update.effective_user.id)
            caption = message.caption if message.caption else "Descrive this video."
            chat_type = message.chat.type
            prompt = await create_prompt(update, content, caption, chat_id, 1)
            msg = await message.reply_text("Downloading video...")
            file_name = message.video.file_name
            ext = os.path.splitext(os.path.basename(file_name))[1] or ".mp4"
            valid_ext = [".mp4", ".mov", ".avi", ".mkv", ".webm"]
            if ext not in valid_ext:
                await msg.edit_text("Invalid file format. Only mp4, mov, avi, mkv and webm are supported.")
                return
            path = f"data/media/{file_id}{ext}"
            await video_file.download_to_drive(path)
            await msg.edit_text("🤖 Analyzing video...\nThis may take a while ⏳")

            def gemini_analysis_worker(prompt, path, video_file):
                if os.path.getsize(path)/(1024*1024) > 30:
                    return "File size is too long for free tier. Contact admin to activate premium subscription."
                temp_api = list(gemini_api_keys)
                model = "gemini-2.5-pro" if gemini_model_list[settings[2]] == "gemini-2.5-pro" else "gemini-2.5-flash"
                for _ in range(len(gemini_api_keys)):
                    api_key = random.choice(temp_api)
                    if not api_key:
                        return "Failed to process your request. Please try again later."
                    try:
                        if os.path.getsize(path)/(1024*1024) > 20:
                            client = genai.Client(api_key=api_key)
                            try:
                                up_video = client.files.upload(file=path)
                            except:
                                return "Failed to process.Try again later"
                            response = client.models.generate_content(
                                model = model,
                                contents = [up_video, prompt],
                                config = types.GenerateContentConfig(
                                    media_resolution=types.MediaResolution.MEDIA_RESOLUTION_LOW,
                                    system_instruction=load_persona(settings),
                                    tools = tools,
                                    thinking_config=types.ThinkingConfig(thinking_budget=settings[3]),
                                    temperature = settings[4]
                                )
                            )
                        else:
                            video = open(path, "rb").read()
                            client = genai.Client(api_key=api_key)
                            response = client.models.generate_content(
                                model = "models/gemini-2.5-flash",
                                contents = types.Content(
                                    parts = [
                                        types.Part(
                                        inline_data=types.Blob(data=video, mime_type=message.video.mime_type)
                                    ),
                                    types.Part(text=prompt)
                                    ]
                                ),
                                config = types.GenerateContentConfig(
                                    system_instruction=load_persona(settings),
                                    tools = tools,
                                    thinking_config=types.ThinkingConfig(thinking_budget=settings[3]),
                                    temperature = settings[4]
                                )
                            )
                        if response.prompt_feedback and response.prompt_feedback.block_reason:
                            return f"Your response is blocked by gemini because of {response.prompt_feedback.block_reason}."
                        try:
                            response.text
                            return response
                        except:
                            pass
                    except Exception as e:
                        print(f"Error getting response for api-{gemini_api_keys.index(api_key)}.\n\nError Code - {e}")
                        temp_api.remove(api_key)
                    if not temp_api:
                        return "Failed to process your request."
            response = await asyncio.to_thread(gemini_analysis_worker, prompt, path, video_file)
            print(response)
            if type(response) == str:
                await message.reply_text(response)
                await content.bot.delete_message(chat_id=chat_id, message_id=msg.message_id)
                return
            if response:
                await send_message(update, content, response, caption, settings)
                await content.bot.delete_message(chat_id=chat_id, message_id=msg.message_id)
                asyncio.create_task(save_media_conversation(update,content, caption, response, chat_id, path, file_id, "Video"))
                return
        else:
            await message.reply_text("Operation Failed")
    except Exception as e:
        print(f"Error in handle_video function.\n\n Error Code - {e}")
        await send_to_channel(update, content, channel_id, f"Error in handle_video function \n\nError Code -{e}")


#fuction to handle audio
async def handle_audio(update : Update, content : ContextTypes.DEFAULT_TYPE) -> None:
    try:
        global gemini_api_keys
        chat_id = update.effective_chat.id
        if await is_ddos(update, content, chat_id):
            return
        message = update.message or update.edited_message
        if message.chat.type != "private":
            await message.reply_text("This function is only available in private chat.")
            return
        os.makedirs("data/media",exist_ok=True)
        await message.chat.send_action(action=ChatAction.TYPING)
        if message and message.audio:
            file_size = message.audio.file_size/(1024*1024)
            if file_size > 20:
                await message.reply_text("Failed to process your request. Telegram bot only  supports file up to 20 MB.")
                return
            msg = await message.reply_text("Downloading audio....")
            audio_file = await message.audio.get_file()
            f_name = message.audio.file_name
            ext = os.path.splitext(os.path.basename(f_name))[1] or "mp3"
            file_id = message.audio.file_unique_id
            path =  f"data/media/{file_id}{ext}"
            valid_ext = [".mp3", ".ogg", ".wav", ".m4a"]
            if ext not in valid_ext:
                await msg.edit_text("Invalid file format. Only mp3, ogg, wav and m4a are supported.")
                return
            await audio_file.download_to_drive(path)
            settings = await get_settings(chat_id)
            chat_type = message.chat.type
            caption = message.caption if message.caption else "Descrive the audio."
            prompt = await create_prompt(update, content, caption, chat_id, 1)

            if not os.path.exists(path):
                await message.reply_text("Invalid file.")
                return
            await msg.edit_text("🤖 Analyzing audio...\nThis may take a while ⏳")

            def gemini_audio_worker(prompt, path):
                if os.path.getsize(path)/(1024*1024) > 15:
                    return "File size is too long for free tier. Contact admin to activate premium subscription."
                temp_api = list(gemini_api_keys)
                model = "gemini-2.5-pro" if gemini_model_list[settings[2]] == "gemini-2.5-pro" else "gemini-2.5-flash"
                for _ in range(len(gemini_api_keys)):
                    api_key = random.choice(temp_api)
                    if not api_key:
                        return "Failed to process your request. Please try again later."
                    try:
                        client = genai.Client(api_key=api_key)
                        try:
                            file = client.files.upload(file=path)
                        except:
                            return "Failed to process. Try again later."
                        response = client.models.generate_content(
                            model = model,
                            contents = [prompt, file],
                            config=types.GenerateContentConfig(
                                system_instruction=load_persona(settings),
                                tools = tools,
                                thinking_config=types.ThinkingConfig(thinking_budget=settings[3]),
                                temperature = settings[4]
                            )
                        )
                        if response.prompt_feedback and response.prompt_feedback.block_reason:
                            return f"Your response is blocked by gemini because of {response.prompt_feedback.block_reason}."
                        try:
                            response.text
                            return response
                        except:
                            pass
                    except Exception as e:
                        temp_api.remove(api_key)
                        print(f"Error getting response for api-{gemini_api_keys.index(api_key)}.\n\nError Code - {e}")
                if not temp_api:
                    return "Failed to process your request. Please try again later."
                return None

            
            response = await asyncio.to_thread(gemini_audio_worker, prompt, path)
            print(response)
            if type(response) == str:
                await message.reply_text(response)
                await content.bot.delete_message(chat_id=chat_id, message_id=msg.message_id)
                return
            if response:
                await send_message(update, content, response, caption, settings)
                await content.bot.delete_message(chat_id=chat_id, message_id=msg.message_id)
                asyncio.create_task(save_media_conversation(update,content, caption, response, chat_id, path, file_id, "Audio"))
                return
        else:
            await message.reply_text("This doesn't seems like a audio at all")
    except Exception as e:
        print(f"Error in handle_audio function.\n\n Error Code - {e}")
        await send_to_channel(update, content, channel_id, f"Error in handle_audio function \n\nError Code -{e}")



#function to handle voice
async def handle_voice(update : Update, content : ContextTypes.DEFAULT_TYPE) -> None:
    try:
        global gemini_api_keys
        chat_id = update.effective_chat.id
        if await is_ddos(update, content, chat_id):
            return
        message = update.message or update.edited_message
        if message.chat.type != "private":
            await message.reply_text("This function is only available in private chat.")
            return
        if update.message and message.voice:
            if message.voice.duration > 60:
                await message.reply_text("Failed to process your request. Telegram bot only supports voice up to 60 seconds.")
                return
        os.makedirs("data/media",exist_ok=True)
        await message.chat.send_action(action=ChatAction.TYPING)
        if message and message.voice:
            file_size = message.voice.file_size/(1024*1024)
            if file_size > 20:
                await message.reply_text("Failed to process your request. Telegram bot only  supports file up to 20 MB.")
                return
            settings = await get_settings(update.effective_user.id)
            caption = ""
            chat_type = message.chat.type
            msg = await message.reply_text("Downloading voice...")
            voice_file = await message.voice.get_file()
            file_id = message.voice.file_unique_id
            path = f"data/media/voice-{file_id}.ogg"
            await voice_file.download_to_drive(path)
            if not os.path.exists(path):
                await message.reply_text("Invalid file.")
                return

            await msg.edit_text("🤖 Analyzing voice...\nThis may take a while ⏳")
            def gemini_voice_worker(caption, file_id):
                if os.path.getsize(path)/(1024*1024) > 15:
                    return "File size is too long for free tier. Contact admin to activate premium subscription."
                temp_api = list(gemini_api_keys)
                model = "gemini-2.5-pro" if gemini_model_list[settings[2]] == "gemini-2.5-pro" else "gemini-2.5-flash"
                for _ in range(len(gemini_api_keys)):
                    api_key = random.choice(temp_api)
                    if not api_key:
                        return "Failed to process your request. Please try again later."
                    try:
                        client = genai.Client(api_key=api_key)
                        try:
                            file = client.files.upload(file=path)
                        except:
                            return "Failed to process. Try again later."
                        response = client.models.generate_content(
                            model = model,
                            contents = [caption, file],
                            config=types.GenerateContentConfig(
                                system_instruction=load_persona(settings),
                                tools = tools,
                                thinking_config=types.ThinkingConfig(thinking_budget=settings[3]),
                                temperature = settings[4]
                            )
                        )
                        if response.prompt_feedback and response.prompt_feedback.block_reason:
                            return f"Your response is blocked by gemini because of {response.prompt_feedback.block_reason}."
                        try:
                            response.text
                            return response
                        except:
                            pass
                    except Exception as e:
                        temp_api.remove(api_key)
                        print(f"Error getting response for api-{gemini_api_keys.index(api_key)}.\n\nError Code - {e}")
                if not temp_api:
                    return "Failed to process your request. Please try again later."
                return None

            response = await asyncio.to_thread(gemini_voice_worker, caption, file_id)
            print(response)
            if type(response) == str:
                await message.reply_text(response)
                await content.bot.delete_message(chat_id=chat_id, message_id=msg.message_id)
                return
            if response:
                await send_message(update, content, response, caption, settings)
                await content.bot.delete_message(chat_id=chat_id, message_id=msg.message_id)
                asyncio.create_task(save_media_conversation(update,content, caption, response, chat_id, path, file_id, "Voice"))
                return
        else:
            await message.reply_text("This doesn't seems like a voice at all")
    except Exception as e:
        print(f"Error in handle_voice function.\n\n Error Code - {e}")
        await send_to_channel(update, content, channel_id, f"Error in handle_voice function \n\nError Code -{e}")


from collections import defaultdict, deque

# Store media context for each chat (max 10 items)
media_context_store = defaultdict(lambda: deque(maxlen=10))

#function to handle sticker
async def handle_sticker(update : Update, content : ContextTypes.DEFAULT_TYPE) -> None:
    try:
        global gemini_api_keys
        chat_id = update.effective_chat.id
        if await is_ddos(update, content, chat_id):
            return
        message = update.message or update.edited_message
        if message.chat.type != "private":
            await message.reply_text("This function is only available in private chat.")
            return
        msg = await message.reply_text("Downloading Sticker...")
        await msg.edit_text("🤖 Analyzing Sticker...\nThis may take a while ⏳")
        settings = await get_settings(chat_id)
        if message and message.sticker:
            file_size = message.sticker.file_size/(1024*1024)
            if file_size > 20:
                await message.reply_text("Failed to process your request. Telegram bot only  supports file up to 20 MB.")
                return
            sticker = message.sticker
            file_id = sticker.file_unique_id
            caption = ""
            if sticker.is_animated:
                await message.reply_text("I recieved your sticker but i can't do anything with it.")
                return
            elif sticker.is_video:
                ext = "webm"
                mime = "video/webm"
            else:
                ext = "webp"
                mime = "image/webp"
            path = f"data/media/{file_id}.{ext}"
            file = await sticker.get_file()
            os.makedirs("data/media", exist_ok=True)
            await file.download_to_drive(path)
            if not os.path.exists(path):
                await message.reply_text("Invalid file.")
                return

            # Store media context for next 10 messages
            chat_media_queue = media_context_store[chat_id]
            chat_media_queue.append({
                "type": "sticker",
                "path": path,
                "mime": mime,
                "caption": caption,
                "file_id": file_id
            })

            def gemini_sticker_worker(path, chat_id):
                if os.path.getsize(path)/(1024*1024) > 7:
                    return "File size is too long for free tier. Contact admin to activate premium subscription."
                temp_api = list(gemini_api_keys)
                # Gather last 10 media contexts for this chat
                media_contexts = list(media_context_store[chat_id])
                for _ in range(len(gemini_api_keys)):
                    api_key = random.choice(temp_api)
                    if not api_key:
                        return "Failed to process your request. Please try again later."
                    try:
                        sticker = open(path, "rb").read()
                        client = genai.Client(api_key=api_key)
                        # Build context parts from stored media
                        context_parts = []
                        for media in media_contexts:
                            if os.path.exists(media["path"]):
                                context_parts.append(
                                    types.Part(
                                        inline_data=types.Blob(data=open(media["path"], "rb").read(), mime_type=media["mime"])
                                    )
                                )
                                if media["caption"]:
                                    context_parts.append(types.Part(text=media["caption"]))
                        # Add current sticker
                        context_parts.append(types.Part(inline_data=types.Blob(data=sticker, mime_type=mime)))
                        if caption:
                            context_parts.append(types.Part(text=caption))
                        response = client.models.generate_content(
                            model = "models/gemini-2.5-flash",
                            contents = types.Content(parts=context_parts),
                            config = types.GenerateContentConfig(
                                system_instruction=load_persona(settings),
                                tools = tools,
                                thinking_config=types.ThinkingConfig(thinking_budget=settings[3]),
                                temperature = settings[4]
                            )
                        )
                        if response.prompt_feedback and response.prompt_feedback.block_reason:
                            return f"Your response is blocked by gemini because of {response.prompt_feedback.block_reason}."
                        try:
                            response.text
                            return response
                        except:
                            pass
                    except Exception as e:
                        temp_api.remove(api_key)
                        if not temp_api:
                            return "Failed to process your request. Please try again later."
                return None

            response = await asyncio.to_thread(gemini_sticker_worker, path, chat_id)
            if type(response) == str:
                await message.reply_text(response)
                await content.bot.delete_message(chat_id=chat_id, message_id=msg.message_id)
                return
            if response:
                await send_message(update, content, response, caption, settings)
                await content.bot.delete_message(chat_id=chat_id, message_id=msg.message_id)
                asyncio.create_task(save_media_conversation(update,content, caption, response, chat_id, path, file_id, "Sticker"))
                return
        else:
            await message.reply_text("Operation Failed")
    except Exception as e:
        print(f"Error on handle_sticker function. \n\n Error Code -{e}")
        await send_to_channel(update, content, channel_id, f"Error in handle_sticker function \n\nError Code -{e}")


#function to handle document
async def handle_document(update:Update, content:ContextTypes.DEFAULT_TYPE) -> None:
    try:
        global gemini_api_keys
        chat_id = update.effective_chat.id
        if await is_ddos(update, content, chat_id):
            return
        message = update.message or update.edited_message
        if message.chat.type != "private":
            await message.reply_text("This function is only available in private chat.")
            return
        await message.chat.send_action(action=ChatAction.TYPING)
        os.makedirs("data/media", exist_ok=True)
        chat_type = message.chat.type
        settings = await get_settings(chat_id)
        if message and message.document:
            file_size = message.document.file_size/(1024*1024)
            if file_size > 20:
                await message.reply_text("Failed to process your request. Telegram bot only  supports file up to 20 MB.")
                return
            if not message.document.file_name:
                await message.reply_text("This document doesn't have a file name. Please send a document with a file name.")
                return
            if not message.document.mime_type:
                await message.reply_text("This document doesn't have a mime type. Please send a document with a mime type.")
                return
            if not message.document.mime_type.startswith("application/") and not message.document.mime_type.startswith("text/"):
                await message.reply_text("This document doesn't have a valid mime type. Please send a document with a valid mime type.")
                return
            msg = await message.reply_text("Downloading Document...")
            caption = message.caption or "Describe this and if this have any question then answer this. If this is code solve the error and suggest improvement."
            prompt = await create_prompt(update, content, caption, chat_id, 1)
            file_name = message.document.file_name
            valid_ext = [
                ".pdf",
                ".json",
                ".txt",
                ".docx",
                ".py",
                ".c",
                ".cpp",
                ".cxx",
                ".html",
                ".htm",
                ".js" ,
                ".java",
                ".css",
                ".xml",
                ".php",
                ".json",
                ".doc",
                ".ppt",
                ".pptx",
                ".xls",
                ".xlsx",
                ".csv",
                ".md",
                ".log",
                ".yaml",
                ".yml",
                ".png",
                ".jpg",
                ".jpeg",
                ".gif",
                ".webp",
                ".mp4",
                ".avi",
                ".mkv",
                ".webm",
                ".mp3",
                ".ogg",
                ".wav",
                ".m4a",
            ]
            ext = os.path.splitext(os.path.basename(file_name))[1]
            if ext not in valid_ext:
                await msg.edit_text("Unsupported Format...")
                return
            file_id = message.document.file_unique_id
            path = f"data/media/{file_id}{ext}"
            doc_file = await message.document.get_file()
            try:
                await doc_file.download_to_drive(path)
                if not os.path.exists(path):
                    await message.reply_text("Invalid file.")
                    return
            except:
                await message.reply_text("Invalid File.")
                return

            await msg.edit_text("🤖 Analyzing document...\nThis may take a while ⏳")
            def gemini_doc_worker(caption, path):
                if os.path.getsize(path)/(1024*1024) > 15:
                    return "File size is too long for free tier. Contact admin to activate premium subscription."
                temp_api = list(gemini_api_keys)
                model = "gemini-2.5-pro" if gemini_model_list[settings[2]] == "gemini-2.5-pro" else "gemini-2.5-flash"
                for _ in range(len(gemini_api_keys)):
                    api_key = random.choice(temp_api)
                    if not api_key:
                        return "Failed to process your request. Please try again later."
                    try:
                        client = genai.Client(api_key=api_key)
                        try:
                            u_doc = client.files.upload(file=path)
                        except:
                            return "Failed to process. Try agian later."
                        response = client.models.generate_content(
                            model=model,
                            contents = [u_doc, caption],
                            config=types.GenerateContentConfig(
                                system_instruction=load_persona(settings),
                                tools = tools,
                                thinking_config=types.ThinkingConfig(thinking_budget=settings[3]),
                                temperature = settings[4]
                            )
                        )
                        if response.prompt_feedback and response.prompt_feedback.block_reason:
                            return f"Your response is blocked by gemini because of {response.prompt_feedback.block_reason}"
                        try:
                            response.text
                            return response
                        except:
                            pass
                    except Exception as e:
                        temp_api.remove(api_key)
                        if not temp_api:
                            return "Failed to process your request. Please try again later."
                        print(f"Error getting response for API{gemini_api_keys.index(api_key)}.\n\nError Code - {e}")
                return None
            
            response = await asyncio.to_thread(gemini_doc_worker, prompt, path)
            print(response)
            if type(response) == str:
                await message.reply_text(response)
                await content.bot.delete_message(chat_id=chat_id, message_id=msg.message_id)
                return
            if response:
                await send_message(update, content, response, caption, settings)
                await content.bot.delete_message(chat_id=chat_id, message_id=msg.message_id)
                asyncio.create_task(save_media_conversation(update,content, caption, response, chat_id, path, file_id, "Document"))
                return
        else:
            await message.reply_text("This doensn't seems like a document at all")
    except Exception as e:
        print(f"Error in handle_document function.\n\n Error Code - {e}")
        await send_to_channel(update, content, channel_id, f"Error in handle_document function \n\nError Code -{e}")
        



#function to handle location
async def handle_location(update:Update, content:ContextTypes.DEFAULT_TYPE):
    try:
        if update.message.location:
            location = update.message.location
            location = (location.latitude, location.longitude)
            await update.message.reply_text(f"Your latitude is {location[0]} and longitude is {location[1]}")
    except Exception as e:
        print(f"Error in handle_location function. \n\nError code - {e}")
