import os
import asyncio
from telegram import Update
from telegram.ext import ContextTypes
from utils.utils import is_ddos, get_settings, send_to_channel, load_persona
from telegram.constants import ChatAction
from PIL import Image
from google import genai
from google.genai import types
from utils.config import channel_id
from data.user_content_tools import create_prompt
from utils.message_utils import send_message
from utils.db import gemini_api_keys






#function to handle image
async def handle_image(update : Update, content : ContextTypes.DEFAULT_TYPE) -> None:
    try:
        global gemini_api_keys
        chat_id = update.effective_chat.id
        if await is_ddos(update, content, chat_id):
            return
        if update.message.chat.type != "private":
            await update.message.reply_text("This function is only available in private chat.")
            return
        os.makedirs("ext/media",exist_ok=True)
        await update.message.chat.send_action(action=ChatAction.TYPING)
        settings = await get_settings(update.effective_user.id)
        if update.message and update.message.photo:
            message = await update.message.reply_text("Downloading Image...")
            caption = update.message.caption if update.message.caption else "Describe this imgae, if this image have question answer this."
            photo_file = await update.message.photo[-1].get_file()
            file_size = photo_file.file_size/(1024*1024)
            if file_size > 20:
                await update.message.reply_text("Failed to process your request. Telegram bot only  supports file up to 20 MB.")
                return
            ext = os.path.splitext(os.path.basename(photo_file.file_path))[1]
            if not ext:
                ext = ".jpg"
            if ext not in [".jpg", ".jpeg", ".png", ".webp", ".gif"]:
                await message.edit_text("Invalid file format. Only jpg, jpeg, png, webp and gif are supported.")
                return
            file_id = photo_file.file_unique_id
            path = f"ext/media/{file_id}.{ext}"
            await photo_file.download_to_drive(path)
            try:
                photo = Image.open(path)
            except:
                await update.message.reply_text("Failed to process. Try again later.")
            prompt = await create_prompt(update, content, caption, chat_id, 1)

            if not os.path.exists(path):
                await update.message.reply_text("Invalid file.")
                return
            await message.edit_text("🤖 Analyzing Image...\nThis may take a while ⏳")
            def gemini_photo_worker(image, caption):
                if os.path.getsize(path)/(1024*1024) > 8:
                    return "File size is too long for free tier. Contact admin to activate premium subscription."
                temp_api = list(gemini_api_keys)
                for api_key in temp_api:
                    try:
                        client = genai.Client(api_key=api_key)
                        response = client.models.generate_content(
                            model = "gemini-2.5-flash",
                            contents = [image, caption],
                            config = types.GenerateContentConfig(
                                thinking_config=types.ThinkingConfig(thinking_budget=1024),
                                temperature = 0.7,
                                system_instruction = load_persona(settings)
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
                        print(f"Error getting response for API-{gemini_api_keys.index(api_key)}\n\nError Code - {e}")
                        temp_api.remove(api_key)
                        if not temp_api:
                            return "Failed to process your request. Please try again later."
                return None
            
            response = await asyncio.to_thread(gemini_photo_worker, photo, prompt)
            if os.path.exists(path):
                os.remove(path)
            if type(response) == str:
                await update.message.reply_text(response)
                await content.bot.delete_message(chat_id=chat_id, message_id=message.message_id)
                return
            await send_message(update, content, response, "<Image>" + caption, settings)
            await content.bot.delete_message(chat_id=chat_id, message_id=message.message_id)
    except Exception as e:
        print(f"Error in handle_image function.\n\nError Code - {e}")
        await send_to_channel(update, content, channel_id, f"Error in handle_image function \n\nError Code -{e}")


#function to handle video
async def handle_video(update : Update, content : ContextTypes.DEFAULT_TYPE) -> None:
    try:
        global gemini_api_keys
        chat_id = update.effective_chat.id
        if await is_ddos(update, content, chat_id):
            return
        if update.message.chat.type != "private":
            await update.message.reply_text("This function is only available in private chat.")
            return
        os.makedirs("ext/media",exist_ok=True)
        await update.message.chat.send_action(action=ChatAction.TYPING)
        if update.message and update.message.video:
            file_size = update.message.video.file_size/(1024*1024)
            if file_size > 20:
                await update.message.reply_text("Failed to process your request. Telegram bot only  supports file up to 20 MB.")
                return
            video_file = await update.message.video.get_file()
            settings = await get_settings(update.effective_user.id)
            caption = update.message.caption if update.message.caption else "Descrive this video."
            chat_type = update.message.chat.type
            prompt = await create_prompt(update, content, caption, chat_id, 1)
            message = await update.message.reply_text("Downloading video...")
            file_name = update.message.video.file_name or f"video-{update.message.video.file_unique_id}.mp4"
            if not file_name.endswith((".mp4", ".mkv", ".avi", ".mov", ".webm")):
                await message.edit_text("Invalid file format. Only mp4, mkv, avi, mov and webm are supported.")
                return
            if len(file_name) > 100:
                file_name = file_name[:100]
            file_name = file_name.replace(" ", "_").replace("/", "_").replace("\\", "_").replace(":", "_").replace("*", "_").replace("?", "_").replace('"', "_").replace("<", "_").replace(">", "_").replace("|", "_")
            path = f"ext/media/{file_name}"
            await video_file.download_to_drive(path)
            await message.edit_text("🤖 Analyzing video...\nThis may take a while ⏳")

            def gemini_analysis_worker(caption, path, video_file):
                if os.path.getsize(path)/(1024*1024) > 30:
                    return "File size is too long for free tier. Contact admin to activate premium subscription."
                temp_api = list(gemini_api_keys)
                for api_key in temp_api:
                    try:
                        if os.path.getsize(path)/(1024*1024) > 20:
                            client = genai.Client(api_key=api_key)
                            try:
                                up_video = client.files.upload(file=path)
                            except:
                                return "Failed to process.Try again later"
                            response = client.models.generate_content(
                                model = "gemini-2.5-flash",
                                contents = [up_video, caption],
                                config = types.GenerateContentConfig(
                                    media_resolution=types.MediaResolution.MEDIA_RESOLUTION_LOW,
                                    system_instruction=load_persona(settings)
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
                                        inline_data=types.Blob(data=video, mime_type=update.message.video.mime_type)
                                    ),
                                    types.Part(text=caption)
                                    ]
                                ),
                                config = types.GenerateContentConfig(
                                    system_instruction=load_persona(settings)
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
            if os.path.exists(path):
                os.remove(path)
            if type(response) == str:
                await update.message.reply_text(response)
                await content.bot.delete_message(chat_id=chat_id, message_id=message.message_id)
                return
            await send_message(update, content, response, "<video>" + caption, settings)
            await content.bot.delete_message(chat_id=chat_id, message_id=message.message_id)
        else:
            await update.message.reply_text("Operation Failed")
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
        if update.message.chat.type != "private":
            await update.message.reply_text("This function is only available in private chat.")
            return
        os.makedirs("ext/media",exist_ok=True)
        await update.message.chat.send_action(action=ChatAction.TYPING)
        if update.message and update.message.audio:
            file_size = update.message.audio.file_size/(1024*1024)
            if file_size > 20:
                await update.message.reply_text("Failed to process your request. Telegram bot only  supports file up to 20 MB.")
                return
            message = await update.message.reply_text("Downloading audio....")
            audio_file = await update.message.audio.get_file()
            f_name = update.message.audio.file_name
            ext = os.path.splitext(os.path.basename(f_name))[1] or "mp3"
            file_id = update.message.audio.file_unique_id
            path =  f"ext/media/{file_id}{ext}"
            valid_ext = [".mp3", ".ogg", ".wav", ".m4a"]
            if ext not in valid_ext:
                await message.edit_text("Invalid file format. Only mp3, ogg, wav and m4a are supported.")
                return
            await audio_file.download_to_drive(path)
            settings = await get_settings(chat_id)
            chat_type = update.message.chat.type
            caption = update.message.caption if update.message.caption else "Descrive the audio."
            prompt = await create_prompt(update, content, caption, chat_id, 1)

            if not os.path.exists(path):
                await update.message.reply_text("Invalid file.")
                return
            await message.edit_text("🤖 Analyzing audio...\nThis may take a while ⏳")

            def gemini_audio_worker(caption, path):
                if os.path.getsize(path)/(1024*1024) > 15:
                    return "File size is too long for free tier. Contact admin to activate premium subscription."
                temp_api = list(gemini_api_keys)
                for api_key in temp_api:
                    try:
                        client = genai.Client(api_key=api_key)
                        try:
                            file = client.files.upload(file=path)
                        except:
                            return "Failed to process. Try again later."
                        response = client.models.generate_content(
                            model = "gemini-2.5-flash",
                            contents = [caption, file],
                            config=types.GenerateContentConfig(
                                system_instruction=load_persona(settings)
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
            if os.path.exists(path):
                os.remove(path)
            if type(response) == str:
                await update.message.reply_text(response)
                await content.bot.delete_message(chat_id=chat_id, message_id=message.message_id)
                return
            await send_message(update, content, response, "<audio>" + caption, settings)
            await content.bot.delete_message(chat_id=chat_id, message_id=message.message_id)
        else:
            await update.message.reply_text("This doesn't seems like a audio at all")
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
        if update.message.chat.type != "private":
            await update.message.reply_text("This function is only available in private chat.")
            return
        if update.message and update.message.voice:
            if update.message.voice.duration > 60:
                await update.message.reply_text("Failed to process your request. Telegram bot only supports voice up to 60 seconds.")
                return
        os.makedirs("ext/media",exist_ok=True)
        await update.message.chat.send_action(action=ChatAction.TYPING)
        if update.message and update.message.voice:
            file_size = update.message.voice.file_size/(1024*1024)
            if file_size > 20:
                await update.message.reply_text("Failed to process your request. Telegram bot only  supports file up to 20 MB.")
                return
            settings = await get_settings(update.effective_user.id)
            caption = ""
            chat_type = update.message.chat.type
            message = await update.message.reply_text("Downloading voice...")
            voice_file = await update.message.voice.get_file()
            file_id = update.message.voice.file_unique_id
            path = f"ext/media/voice-{file_id}.ogg"
            await voice_file.download_to_drive(path)
            if not os.path.exists(path):
                await update.message.reply_text("Invalid file.")
                return

            await message.edit_text("🤖 Analyzing voice...\nThis may take a while ⏳")
            def gemini_voice_worker(caption, file_id):
                if os.path.getsize(path)/(1024*1024) > 15:
                    return "File size is too long for free tier. Contact admin to activate premium subscription."
                temp_api = list(gemini_api_keys)
                for api_key in temp_api:
                    try:
                        client = genai.Client(api_key=api_key)
                        try:
                            file = client.files.upload(file=path)
                        except:
                            return "Failed to process. Try again later."
                        response = client.models.generate_content(
                            model = "gemini-2.5-flash",
                            contents = [caption, file],
                            config=types.GenerateContentConfig(
                                system_instruction=load_persona(settings)
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
            if os.path.exists(f"ext/media/voice-{file_id}.ogg"):
                os.remove(f"ext/media/voice-{file_id}.ogg")
            if type(response) == str:
                await update.message.reply_text(response)
                await content.bot.delete_message(chat_id=chat_id, message_id=message.message_id)
                return
            await send_message(update, content, response, "<voice>" + caption, settings)
            await content.bot.delete_message(chat_id=chat_id, message_id=message.message_id)
            return
        else:
            await update.message.reply_text("This doesn't seems like a voice at all")
    except Exception as e:
        print(f"Error in handle_voice function.\n\n Error Code - {e}")
        await send_to_channel(update, content, channel_id, f"Error in handle_voice function \n\nError Code -{e}")


#function to handle sticker
async def handle_sticker(update : Update, content : ContextTypes.DEFAULT_TYPE) -> None:
    try:
        global gemini_api_keys
        chat_id = update.effective_chat.id
        if await is_ddos(update, content, chat_id):
            return
        if update.message.chat.type != "private":
            await update.message.reply_text("This function is only available in private chat.")
            return
        message = await update.message.reply_text("Downloading Sticker...")
        await message.edit_text("🤖 Analyzing Sticker...\nThis may take a while ⏳")
        settings = await get_settings(chat_id)
        if update.message and update.message.sticker:
            file_size = update.message.sticker.file_size/(1024*1024)
            if file_size > 20:
                await update.message.reply_text("Failed to process your request. Telegram bot only  supports file up to 20 MB.")
                return
            sticker = update.message.sticker
            file_id = sticker.file_unique_id
            caption = ""
            if sticker.is_animated:
                await update.message.reply_text("I recieved your sticker but i can't do anything with it.")
                return
            elif sticker.is_video:
                ext = "webm"
                mime = "video/webm"
            else:
                ext = "webp"
                mime = "image/webp"
            path = f"ext/media/{file_id}.{ext}"
            file = await sticker.get_file()
            os.makedirs("ext/media", exist_ok=True)
            await file.download_to_drive(path)
            if not os.path.exists(path):
                await update.message.reply_text("Invalid file.")
                return

            def gemini_sticker_worker(path):
                if os.path.getsize(path)/(1024*1024) > 7:
                    return "File size is too long for free tier. Contact admin to activate premium subscription."
                temp_api = list(gemini_api_keys)
                for api_key in temp_api:
                    try:
                        sticker = open(path, "rb").read()
                        client = genai.Client(api_key=api_key)
                        response = client.models.generate_content(
                            model = "models/gemini-2.5-flash",
                            contents = types.Content(
                                parts = [
                                    types.Part(
                                    inline_data=types.Blob(data=sticker, mime_type=mime)
                                ),
                                types.Part(text=caption)
                                ]
                            ),
                            config = types.GenerateContentConfig(
                                system_instruction=load_persona(settings)
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
                        print(f"Error getting response for api-{gemini_api_keys.index(api_key)}.\n\nError Code - {e}")
                if not response:
                    return None
   
            response = await asyncio.to_thread(gemini_sticker_worker, path)
            if os.path.exists(path):
                os.remove(path)
            if type(response) == str:
                await update.message.reply_text(response)
                await content.bot.delete_message(chat_id=chat_id, message_id=message.message_id)
                return
            await send_message(update, content, response, "<video>" + caption, settings)
            await content.bot.delete_message(chat_id=chat_id, message_id=message.message_id)
        else:
            await update.message.reply_text("Operation Failed")
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
        if update.message.chat.type != "private":
            await update.message.reply_text("This function is only available in private chat.")
            return
        await update.message.chat.send_action(action=ChatAction.TYPING)
        os.makedirs("ext/media", exist_ok=True)
        chat_type = update.message.chat.type
        settings = await get_settings(chat_id)
        if update.message and update.message.document:
            file_size = update.message.document.file_size/(1024*1024)
            if file_size > 20:
                await update.message.reply_text("Failed to process your request. Telegram bot only  supports file up to 20 MB.")
                return
            if not update.message.document.file_name:
                await update.message.reply_text("This document doesn't have a file name. Please send a document with a file name.")
                return
            if not update.message.document.mime_type:
                await update.message.reply_text("This document doesn't have a mime type. Please send a document with a mime type.")
                return
            if not update.message.document.mime_type.startswith("application/") and not update.message.document.mime_type.startswith("text/"):
                await update.message.reply_text("This document doesn't have a valid mime type. Please send a document with a valid mime type.")
                return
            message = await update.message.reply_text("Downloading Document...")
            caption = update.message.caption or "Describe this document."
            prompt = await create_prompt(update, content, caption, chat_id, 1)
            file_name = update.message.document.file_name
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
            print(ext)
            if ext not in valid_ext:
                await message.edit_text("Unsupported Format...")
                return
            file_id = update.message.document.file_unique_id
            path = f"ext/media/{file_id}{ext}"
            doc_file = await update.message.document.get_file()
            try:
                await doc_file.download_to_drive(path)
                if not os.path.exists(path):
                    await update.message.reply_text("Invalid file.")
                    return
            except:
                await update.message.reply_text("Invalid File.")
                return

            await message.edit_text("🤖 Analyzing document...\nThis may take a while ⏳")
            def gemini_doc_worker(caption, path):
                if os.path.getsize(path)/(1024*1024) > 15:
                    return "File size is too long for free tier. Contact admin to activate premium subscription."
                temp_api = list(gemini_api_keys)
                for api_key in temp_api:
                    try:
                        client = genai.Client(api_key=api_key)
                        try:
                            u_doc = client.files.upload(file=path)
                        except:
                            return "Failed to process. Try agian later."
                        response = client.models.generate_content(
                            model="gemini-2.5-flash",
                            contents = [u_doc, caption],
                            config=types.GenerateContentConfig(
                                system_instruction=load_persona(settings)
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
            if os.path.exists(path):
                os.remove(path)
            if type(response) == str:
                await update.message.reply_text(response)
                await content.bot.delete_message(chat_id=chat_id, message_id=message.message_id)
                return
            await send_message(update, content, response,"<document>" + caption, settings)
            await content.bot.delete_message(chat_id=chat_id, message_id=message.message_id)
            return
        else:
            await update.message.reply_text("This doensn't seems like a document at all")
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
