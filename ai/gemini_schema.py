from google import genai
from google.genai import types
from utils.db import gemini_model_list
from utils.utils import load_persona
from telegram import Update
from telegram.ext import ContextTypes
import asyncio
from PIL import Image
from io import BytesIO
import os
from bot.info_handler import get_ct_data, routine_handler, information_handler
from utils.func_description import func_list
import json
from ext.user_content_tools import save_conversation, save_group_conversation
from utils.utils import is_ddos, send_to_channel, safe_send, add_escape_character, has_codeblocks, is_code_block_open
from utils.config import channel_id








#function for editing and sending message
async def send_message(update : Update, content : ContextTypes.DEFAULT_TYPE, response, user_message, settings) -> None:
    try:
        if not response:
            await update.message.reply_text("Failed to precess your request. Try again later.")
            return
        if await is_ddos(update, content, update.effective_user.id):
            return
        if(settings[5]):
            message_object  = await update.message.reply_text("Typing...")
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
                await asyncio.to_thread(save_conversation, user_message, sent_message , update.effective_user.id)
            elif update.message.chat.type != "private":
                await asyncio.to_thread(save_group_conversation, update, user_message, sent_message)
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
                await asyncio.to_thread(save_conversation, user_message, sent_message, update.effective_user.id)
            elif update.message.chat.type != "private":
                await asyncio.to_thread(save_group_conversation, update, user_message, sent_message)
    except Exception as e:
        print(f"Error in send_message function Error Code - {e}")
        await send_to_channel(update, content, channel_id, f"Error in send_message function \n\nError Code -{e}")





def search_online(user_message, api, settings):
    try:
        tools=[]
        tools.append(types.Tool(google_search=types.GoogleSearch))
        tools.append(types.Tool(url_context=types.UrlContext))
        
        if gemini_model_list[settings[2]] == "gemini-2.5-pro" or gemini_model_list[settings[2]] == "gemini-2.5-flash":
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
            model = gemini_model_list[settings[2]],
            contents = [user_message],
            config = config,
        )
        return response
    except Exception as e:
        print(f"Error getting gemini response in search_online function.\n\n Error Code - {e}")
        return None


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
        if gemini_model_list[settings[2]] == "gemini-2.5-pro" or gemini_model_list[settings[2]] == "gemini-2.5-flash":
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
            model = gemini_model_list[settings[2]],
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
            client = genai.Client(api_key=api)
            response = client.models.generate_content(
                model = "gemini-2.0-flash-preview-image-generation",
                contents = prompt,
                config = types.GenerateContentConfig(
                    response_modalities=["TEXT", "IMAGE"],
                )
            )
            return response
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
        print(f"Error in create_image function.\n\nError Code - {e}")






#All the global function 







#gemini response for stream on
async def gemini_stream(update, content, user_message, api, settings):
    try:
        tools=[]
        # tools.append(types.Tool(google_search=types.GoogleSearch))
        # tools.append(types.Tool(url_context=types.UrlContext))
        tools.append(types.Tool(function_declarations=func_list))

        if gemini_model_list[settings[2]] == "gemini-2.5-pro" or gemini_model_list[settings[2]] == "gemini-2.5-flash":
            config = types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_budget=settings[3]),
                temperature = settings[4],
                system_instruction=load_persona(settings),
                tools = tools,
                response_modalities=["TEXT"]
            )
        else:
            config = types.GenerateContentConfig(
                temperature = settings[4],
                system_instruction=load_persona(settings),
                tools = tools,
                response_modalities=["TEXT"],
            )
        def sync_block(api):
            client = genai.Client(api_key=api)
            response = client.models.generate_content_stream(
                model = gemini_model_list[settings[2]],
                contents = [user_message],
                config = config,
            )
            return response
        response = await asyncio.to_thread(sync_block, api)
        if response.candidates[0].content.parts[0].function_call:
            function_call = response.candidates[0].content.parts[0].function_call
            if function_call.name == "search_online":
                response = search_online(user_message, api, settings)
        return response
    except Exception as e:
        print(f"Error getting gemini response.\n\n Error Code - {e}")


#gemini response for stream off
async def gemini_non_stream(update:Update, content:ContextTypes.DEFAULT_TYPE, user_message, api, settings):
    try:
        user_id = update.effective_user.id
        tools=[]
        # tools.append(types.Tool(google_search=types.GoogleSearch))
        # tools.append(types.Tool(url_context=types.UrlContext))
        tools.append(types.Tool(function_declarations=func_list))
        if gemini_model_list[settings[2]] == "gemini-2.5-pro" or gemini_model_list[settings[2]] == "gemini-2.5-flash":
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
                model = gemini_model_list[settings[2]],
                contents = [user_message],
                config = config,
            )
            with open("Main/response.txt", "w") as file:
                json.dump(response.to_json_dict(), file, indent=2, ensure_ascii=False)
            return response
        response = await asyncio.to_thread(sync_block, api)
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
                            await send_message(update, content, response, user_message, settings)
                        await content.bot.delete_message(chat_id = update.effective_user.id, message_id=msg.message_id)
            elif function_call.name == "get_group_data":
                response = await get_group_data(update, content, user_message, settings, api, function_call.name)
                return response
            elif function_call.name == "get_ct_data":
                response = await get_group_data(update, content, user_message, settings, api, function_call.name)
                return response
            elif function_call.name == "create_image":
                image_text = ""
                for part in response.candidates[0].content.parts:
                    if hasattr(part, "text") and part.text is not None:
                        await update.message.reply_text(part.text)
                prompt = function_call.args["prompt"]
                await create_image(update,content, api, prompt)
            elif function_call.name == "get_routine":
                for part in response.candidates[0].content.parts:
                    if hasattr(part, "text") and part.text is not None:
                        await update.message.reply_text(part.text)
                        await asyncio.to_thread(save_conversation,user_message, part.text, user_id)
                await routine_handler(update, content)
            elif function_call.name == "add_memory_content":
                data = function_call.args["memory_content"]
                for part in response.candidates[0].content.parts:
                    if hasattr(part, "text") and part.text is not None:
                        await update.message.reply_text(part.text)
                        await asyncio.to_thread(save_conversation,user_message, part.text, user_id)
                await add_memory_content(update, content, data)
                return False
            elif function_call.name == "information_handler":
                markup = await information_handler(update, content, function_call.args["info_name"])
                for part in response.candidates[0].content.parts:
                    if hasattr(part, "text") and part.text is not None:
                        if type(markup) == str or markup is None:
                            await update.message.reply_text(part.text)
                            await asyncio.to_thread(save_conversation, user_message, part.text, user_id)
                        else:
                            text = part.text
                            await update.message.reply_text(text, reply_markup=markup)
                            await asyncio.to_thread(save_conversation, user_message, text, user_id)
                            return False
                if type(markup) == str:
                    await update.message.reply_text(markup, parse_mode="Markdown")
                    await asyncio.to_thread(save_conversation, user_message, markup, user_id)
                    return False
                else:
                    await update.message.reply_text("Click the button to see your requested data", reply_markup=markup)
                    await asyncio.to_thread(save_conversation, user_message, "Click the button to see your requested data", user_id)
                    return False
            if not response:
                return response
            return False
        return response
    except Exception as e:
        print(f"Error getting gemini response.\n\n Error Code - {e}")
        

