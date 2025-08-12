from fileinput import filename
from urllib import response
from google import genai
from google.genai import types
from pkg_resources import run_main
from utils.db import gemini_model_list
from utils.utils import load_persona
from telegram import Update
from telegram.ext import ContextTypes
import asyncio
from PIL import Image
from io import BytesIO
import os, time
import sqlite3
from fpdf import FPDF
import random
from bot.info_handler import get_ct_data, routine_handler, information_handler
from utils.func_description import(
    func_list
)
import json
from ext.user_content_tools import save_conversation, save_group_conversation
from utils.utils import is_ddos, send_to_channel, safe_send, is_code_block_open
from utils.config import channel_id, db
from utils.db import gemini_api_keys







#a function to convert hex to rgb
def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) for i in (0,2,4))



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
            await safe_send(update,content, message_to_send)
        if message.chat.type == "private":
            await asyncio.to_thread(save_conversation, user_message, message_to_send, update.effective_user.id)
        elif message.chat.type != "private":
            await asyncio.to_thread(save_group_conversation, update, user_message, message_to_send)
    except Exception as e:
        print(f"Error in send_message function Error Code - {e}")
        await send_to_channel(update, content, channel_id, f"Error in send_message function \n\nError Code -{e}")





def search_online(user_message, api, settings):
    try:
        tools=[]
        tools.append(types.Tool(google_search=types.GoogleSearch))
        tools.append(types.Tool(url_context=types.UrlContext))
        
        if settings[2] == "gemini-2.5-pro" or settings[2] == "gemini-2.5-flash":
            config = types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_budget=settings[3]),
                temperature = settings[4],
                system_instruction=load_persona(settings),
                tools = tools,
                response_modalities=["TEXT"],
            )
        else:
            config = types.GenerateContentConfig(
                temperature = settings[4],
                system_instruction=load_persona(settings),
                tools = tools,
                response_modalities=["TEXT"]
            )
        
        client = genai.Client(api_key=api)
        response = client.models.generate_content(
            model = settings[2],
            contents = [user_message],
            config = config,
        )
        return response
    except Exception as e:
        print(f"Error getting gemini response in search_online function.\n\n Error Code - {e}")
        return None


async def create_pdf(update: Update, content: ContextTypes.DEFAULT_TYPE, argument: dict, usr_msg, pre_msg):
    try:
        msg = await update.message.reply_text("Creating PDF...\n\nThis may take some time.")
        now = int(time.time())
        user_id = update.effective_user.id
        os.makedirs("data/media", exist_ok=True)
        pdf_filename = f"data/media/{user_id}-{now}.pdf"
        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_font('DejaVu', '', 'font/DejaVu.ttf', uni=True)
        pdf.add_font('DejaVu', 'B', 'font/DejaVuB.ttf', uni=True)
        pdf.add_font('DejaVu', 'I', 'font/DejaVuI.ttf', uni=True)
        pdf.add_font('DejaVu', 'BI', 'font/DejaVuBI.ttf', uni=True)
        texts = argument.get("text", [])
        font_sizes = argument.get("font_size", [])
        font_colors_hex = argument.get("font_color", [])
        font_styles = argument.get("font_style", [])
        alignments = argument.get("text_alignment", [])

        # Set default values
        default_font_size = 12
        default_font_color = "#000000"
        default_font_style = ''
        default_alignment = 'L'

        # Pad lists to match texts length
        def pad_list(lst, default):
            return lst + [default] * (len(texts) - len(lst))

        font_sizes = pad_list(font_sizes, default_font_size)
        font_colors_hex = pad_list(font_colors_hex, default_font_color)
        font_styles = pad_list(font_styles, default_font_style)
        alignments = pad_list(alignments, default_alignment)
        font_colors_rgb = [hex_to_rgb(color) for color in font_colors_hex]

        for i in range(len(texts)):
            current_text = texts[i].replace("💋", "[kiss]")
            pdf.set_font("DejaVu", style=font_styles[i], size=font_sizes[i])
            r, g, b = font_colors_rgb[i]
            pdf.set_text_color(r, g, b)
            pdf.multi_cell(w=0, txt=current_text, border=0, align=alignments[i], ln=1)
            pdf.ln(5)
            texts[i] = f"[color:{font_colors_rgb[i]}, size:{font_sizes[i]}, align:{alignments[i]}, font_style:{font_styles[i]}] {current_text}"
        pdf.output(pdf_filename)
        try:
            with open(pdf_filename, "rb") as file:
                await content.bot.send_document(
                    chat_id=user_id, 
                    document=file, 
                    caption="Here is your PDF, created by AI."
                )
            await content.bot.delete_message(chat_id=user_id, message_id=msg.message_id)
        except Exception as e:
            print(f"Error sending PDF: {e}")
        response = "\n".join(texts)
        await asyncio.to_thread(save_conversation, usr_msg, pre_msg + "\n<PDF CONTENT>\n" + response + "\n</PDF CONTENT>", user_id)
        return pdf_filename
    except Exception as e:
        print(f"Error in create_pdf function.\n\nError Code -{e}")
        await msg.edit_text(f"Internal Error, Contact admin ot try again later.\n\nError Code - {e}")


#function to get response using group data
async def get_group_data(update:Update, content:ContextTypes.DEFAULT_TYPE, user_message, settings, api, func_name):
    try:
        tools=[]
        tools.append(types.Tool(google_search=types.GoogleSearch))
        tools.append(types.Tool(url_context=types.UrlContext))
        if func_name == "get_group_data":
            data = "****TRAINING DATA****\n\n"
            with open("data/info/group_training_data.txt") as f:
                data += f.read()
            data += "\n\n****END OF TRAINIG DATA****\n\n"
            data += user_message
        elif func_name == "get_ct_data":
            data = "***ALL CT DATA***\n\n"
            data += str(get_ct_data())
            data += "***END OF CT DATA***\n\n"
            data += """Use this format to represent CT data
            📚 Upcoming CTs

            ⏰ NEXT: <Subject>
            🗓️ <date>
            👨‍🏫 <teacher name>
            📖 <topic1>
            →<topic2>
            →<topic3>
            """
            data += "Rules: Recheck the time and date"
            data += "\n\n" + user_message
        if settings[2] == "gemini-2.5-pro" or settings[2] == "gemini-2.5-flash":
            config = types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_budget=settings[3]),
                temperature = settings[4],
                system_instruction=load_persona(settings),
                tools = tools,
                response_modalities=["TEXT"],
            )
        else:
            config = types.GenerateContentConfig(
                temperature = settings[4],
                system_instruction=load_persona(settings),
                tools = tools,
                response_modalities=["TEXT"],
            )
        
        client = genai.Client(api_key=api)
        response = client.models.generate_content(
            model = settings[2],
            contents = [data],
            config = config,
        )
        return response
    except Exception as e:
        print(f"Error in get_group_data function.\n\nError Code - {e}")
        return None


#function to create image based on user request
async def create_image(update:Update, content:ContextTypes.DEFAULT_TYPE, api, prompt):
    try:
        message = update.message or update.edited_message
        user_id = update.effective_user.id
        msg = await message.reply_text("Image creation is in process, This may take a while please wait patiently.")
        def sync_block(prompt,api):
            temp_api = gemini_api_keys
            for _ in range(len(gemini_api_keys)):
                try:
                    api_key = random.choice(temp_api)
                    client = genai.Client(api_key=api)
                    response = client.models.generate_content(
                        model = "gemini-2.0-flash-preview-image-generation",
                        contents = prompt,
                        config = types.GenerateContentConfig(
                            response_modalities=["TEXT", "IMAGE"],
                        )
                    )
                    if response:
                        return response
                    else:
                        raise Exception
                except:
                    temp_api.remove(api_key)
        response = await asyncio.to_thread(sync_block, prompt, api)
        await content.bot.delete_message(chat_id=user_id, message_id=msg.message_id)
        for part in response.candidates[0].content.parts:
            if hasattr(part, "text") and part.text is not None:
                await update.message.reply_text(part.text)
                await asyncio.to_thread(save_conversation, None, part.text, update.effective_user.id)
            elif hasattr(part, "inline_data") and part.inline_data is not None:
                image = Image.open(BytesIO(part.inline_data.data))
                bio = BytesIO()
                image.save(bio, "PNG")
                bio.seek(0)
                await content.bot.send_photo(chat_id=user_id, photo=bio, caption="Generated By AI")
    except Exception as e:
        print(f"Error in create_image function.\n\nError Code - {e}")


#function to add a piece of information to memory
async def add_memory_content(update:Update, content:ContextTypes.DEFAULT_TYPE, data):
    try:
        await update.message.reply_text("📝🧠 Memory Updated")
        user_id = update.effective_user.id
        if os.path.exists(f"data/memory/memory-{user_id}.txt"):
            with open(f"data/memory/memory-{user_id}.txt", "a+") as file:
                file.write("\n" + data + "\n")
    except Exception as e:
        print(f"Error in add_memory_content function.\n\nError Code - {e}")





#All the global function 
async def analyze_media(update: Update, content: ContextTypes.DEFAULT_TYPE, media_list, prompt, settings, usr_msg):
    try:
        user_id = update.effective_user.id
        message = await update.message.reply_text("Analyzing all available file and media, please wait...")
        if not media_list:
            await content.bot.delete_message(chat_id=user_id, message_id=message.message_id)
            await update.message.reply_text("No media found to analyze.")
            return None
        temp_api = list(gemini_api_keys)
        def sync_block(media_list):
            for _ in range(len(gemini_api_keys)):
                try:
                    api = random.choice(temp_api)
                    client = genai.Client(api_key=api)
                    contents = []
                    for media in media_list:
                        if os.path.exists(media):
                            contents.append(client.files.upload(file=media))
                        else:
                            print(f"File {media} does not exist.")
                            return None
                    contents.append(prompt)
                    response = client.models.generate_content(
                        model = settings[2],
                        contents = contents,
                        config = types.GenerateContentConfig(
                            thinking_config=types.ThinkingConfig(thinking_budget=settings[3]),
                            temperature=settings[4],
                            system_instruction=load_persona(settings),
                            response_modalities=["TEXT"],
                        )
                    )
                    response.text
                    return response
                except Exception as e:
                    temp_api.remove(api)
                    if not temp_api:
                        return None
                    print(f"Error in analyzing media with API key {gemini_api_keys.index(api)}. Retrying with next key.\n\nError Code - {e}")

        response = await asyncio.to_thread(sync_block, media_list)
        await content.bot.delete_message(chat_id=user_id, message_id=message.message_id)
        if response:
            await send_message(update, content, response, usr_msg, settings)
        else:
            await update.message.reply_text("Failed to analyze the media")
    except Exception as e:
        print(f"Error in analyze_media function. \n\nError Code - {e}")
        return None 





#gemini response for stream off
async def gemini_non_stream(update:Update, content:ContextTypes.DEFAULT_TYPE, user_message, api, settings, usr_msg):
    try:
        tmsg = False
        user_id = update.effective_user.id
        tools=[]
        tools.append(types.Tool(function_declarations=func_list))
        if settings[2] == "gemini-2.5-pro" or settings[2] == "gemini-2.5-flash":
            if settings[3] != 0:
                tmsg = await update.message.reply_text("Thinking...")
            config = types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_budget=settings[3]),
                temperature = settings[4],
                system_instruction=load_persona(settings),
                tools = tools,
                response_modalities=["TEXT"],
            )
        else:
            config = types.GenerateContentConfig(
                temperature = settings[4],
                system_instruction=load_persona(settings),
                tools = tools,
                response_modalities=["TEXT"]
            )
        def sync_block(api):
            client = genai.Client(api_key=api)
            response = client.models.generate_content(
                model = settings[2],
                contents = [user_message],
                config = config,
            )
            with open("Main/response.txt", "w") as file:
                json.dump(response.to_json_dict(), file, indent=2, ensure_ascii=False)
            return response
        response = await asyncio.to_thread(sync_block, api)
        if tmsg:
            await content.bot.delete_message(chat_id=user_id, message_id=tmsg.message_id)
        if response.prompt_feedback and response.prompt_feedback.block_reason:
            await update.message.reply_text("Prohibited content detected. Conversation history will be deleted.")
            if os.path.exists(f"data/Conversation/conversation-{user_id}.txt"):
                with open(f"data/Conversation/conversation-{user_id}.txt", "w") as f:
                    pass
                await asyncio.to_thread(db[f"{user_id}"].update_one,
                    {"id" : user_id},
                    {"$set" : {"conversation" : None}}
                )
            return "false"
        has_function = False
        for part in response.candidates[0].content.parts:
            if hasattr(part, "function_call") and part.function_call is not None:
                has_function = True
                function_call = part.function_call
        if has_function:
            if function_call.name == "search_online":
                for part in response.candidates[0].content.parts:
                    if hasattr(part, "text") and part.text is not None:
                        await update.message.reply_text(part.text)
                    if hasattr(part, "function_call") and part.function_call is not None:
                        msg = await update.message.reply_text("Searching...")
                        response = await asyncio.to_thread(search_online,function_call.args["query"], api, settings)
                        if response.text is not None:
                            await send_message(update, content, response, usr_msg, settings)
                        await content.bot.delete_message(chat_id = update.effective_user.id, message_id=msg.message_id)
            elif function_call.name == "get_group_data":
                response = await get_group_data(update, content, user_message, settings, api, function_call.name)
                return response
            elif function_call.name == "get_ct_data":
                response = await get_group_data(update, content, user_message, settings, api, function_call.name)
                return response
            elif function_call.name == "create_image":
                for part in response.candidates[0].content.parts:
                    if hasattr(part, "text") and part.text is not None:
                        await update.message.reply_text(part.text)
                await asyncio.to_thread(save_conversation,usr_msg, response.text, user_id)
                prompt = function_call.args["prompt"]
                await create_image(update,content, api, prompt)
            elif function_call.name == "get_routine":
                for part in response.candidates[0].content.parts:
                    if hasattr(part, "text") and part.text is not None:
                        await update.message.reply_text(part.text)
                        await asyncio.to_thread(save_conversation,usr_msg, part.text, user_id)
                await routine_handler(update, content)
            elif function_call.name == "add_memory_content":
                data = function_call.args["memory_content"]
                for part in response.candidates[0].content.parts:
                    if hasattr(part, "text") and part.text is not None:
                        await update.message.reply_text(part.text)
                        await asyncio.to_thread(save_conversation,usr_msg, part.text, user_id)
                await add_memory_content(update, content, data)
                return "false"
            elif function_call.name == "information_handler":
                markup = await information_handler(update, content, function_call.args["info_name"])
                for part in response.candidates[0].content.parts:
                    if hasattr(part, "text") and part.text is not None:
                        if type(markup) == str and markup:
                            text = response.text + markup
                            await update.message.reply_text(text, parse_mode="Markdown")
                            await asyncio.to_thread(save_conversation, usr_msg, text, user_id)
                        else:
                            text = part.text
                            await update.message.reply_text(text, reply_markup=markup, parse_mode="Markdown")
                            await asyncio.to_thread(save_conversation, usr_msg, text, user_id)
                            return "false"
                    else:
                        if type(markup) == str and markup:
                            text = markup
                            await asyncio.to_thread(save_conversation, usr_msg,text, user_id)
                            await update.message.reply_text(text, parse_mode="Markdown")
                            return "false"
                        else:
                            await update.message.reply_text("Click the button to see your requested data", reply_markup=markup)
                            await asyncio.to_thread(save_conversation, usr_msg, "Click the button to see your requested data", user_id)
                            return 'false'
            elif function_call.name == "fetch_media_content":
                media_paths = function_call.args["media_paths"]
                print(f"Media Paths: {media_paths}")
                await analyze_media(update, content, media_paths, user_message, settings, usr_msg)
                return 'false'
            elif function_call.name == "run_code":
                data = ""
                for part in response.candidates[0].content.parts:
                    if hasattr(part, "text") and part.text is not None:
                        data += part.text
                    if hasattr(part, "function_call") and part.function_call is not None:
                        code = part.function_call.args["code"]
                        if code:
                            data += "\n" + code
                if data:
                    await send_message(update, content, data, user_message, settings)
                    return 'false'
            elif function_call.name == "create_pdf":
                if hasattr(response, "text"):
                    if response.text:
                        await update.message.reply_text(response.text)
                pre_msg = response.text or "Here is your requested pdf:"
                path = await create_pdf(update, content, function_call.args, usr_msg, pre_msg)
                if os.path.exists(path):
                    os.remove(path)
            return 'false'
        if not response:
            if tmsg:
                await content.bot.delete_message(chat_id=user_id, message_id=tmsg.message_id)
        return response
    except Exception as e:
        if tmsg:
            await content.bot.delete_message(chat_id=user_id, message_id=tmsg.message_id)
        print(f"Error getting gemini response.\n\n Error Code - {e}")
        

