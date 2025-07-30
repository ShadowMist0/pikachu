from utils.config import db, fernet, channel_id
from utils.db import gemini_api_keys
from telegram import Update
from telegram.ext import ContextTypes
from google import genai
import asyncio
from utils.message_utils import send_to_channel
import pytz
from google.genai import types
import os
import sqlite3
from datetime import datetime
from utils.utils import get_settings, load_persona
import html




#A function to delete n times convo from conversation history
def delete_n_convo(user_id, n):
    try:
        if user_id < 0:
            with open(f"ext/Conversation/conversation-group.txt", "r+", encoding="utf-8") as f:
                data = f.read()
                data = data.split("You: ")
                if len(data) >= n+1:
                    data = data[n:]
                    f.seek(0)
                    f.truncate(0)
                    data =  "You: ".join(data)
                    f.write(data)
                    db[f"group"].update_one(
                        {"id" : "group"},
                        {"$set" : {"conversation" : data}}
                    )
                elif len(data)-n > n:
                    data = data[-n:]
                    f.seek(0)
                    f.truncate(0)
                    data = "You: ".join(data)
                    f.write(data)
                    db[f"group"].update_one(
                        {"id" : "group"},
                        {"$set" : {"conversation" : data}}
                    )
            return
        with open(f"ext/Conversation/conversation-{user_id}.txt", "r+", encoding="utf-8") as f:
            data = f.read()
            data = data.split("You: ")
            if len(data) >= n+1 and len(data)-n < n:
                data = data[n:]
                f.seek(0)
                f.truncate(0)
                data =  "You: ".join(data)
                f.write(data)
                db[f"{user_id}"].update_one(
                    {"id" : user_id},
                    {"$set" : {"conversation" : data}}
                )
            elif len(data)-n > n:
                data = data[-n:]
                f.seek(0)
                f.truncate(0)
                data = "You: ".join(data)
                f.write(data)
                db[f"{user_id}"].update_one(
                    {"id" : user_id},
                    {"$set" : {"conversation" : data}}
                )
    except Exception as e:
        print(f"Failed to delete conversation history \n Error Code - {e}")


#creating memory, SPECIAL_NOTE: THIS FUNCTION ALWAYS REWRITE THE WHOLE MEMORY, SO THE MEMORY SIZE IS LIMITED TO THE RESPONSE SIZE OF GEMINI, IT IS DONE THIS WAY BECAUSE OTHERWISE THERE WILL BE DUPLICATE DATA 
async def create_memory(update:Update, content:ContextTypes.DEFAULT_TYPE, api, user_id):
    try:
        settings = await get_settings(update.effective_user.id)
        if user_id > 0:
            with open("ext/persona/memory_persona.txt", "r", encoding="utf-8") as f:
                instruction = load_persona(settings) + f.read()
            with open(f"ext/memory/memory-{user_id}.txt", "a+", encoding = "utf-8") as f:
                f.seek(0)
                data = "***PREVIOUS MEMORY***\n\n"
                data += f.read()
                data += "\n\n***END OF MEMORY***\n\n"
            with open(f"ext/Conversation/conversation-{user_id}.txt", "a+", encoding = "utf-8") as f:
                f.seek(0)
                data += "\n\n***CONVERSATION HISTORY***"
                data += f.read()
                data += "\n\n***END OF CONVERSATION***\n\n"
        elif user_id < 0:
            group_id = user_id
            with open("ext/persona/memory_persona.txt", "r") as f:
                instruction = f.read()
            with open(f"ext/memory/memory-group.txt", "a+", encoding = "utf-8") as f:
                f.seek(0)
                data = "***PREVIOUS MEMORY***\n\n"
                data += f.read()
                data += "\n\n***END OF MEMORY***\n\n"
            with open(f"ext/Conversation/conversation-group.txt", "a+", encoding = "utf-8") as f:
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
        if response.prompt_feedback and response.prompt_feedback.block_reason:
            await update.message.reply_text(f"Your response is blocked by gemini because of {response.prompt_feedback.block_reason} Conversation history is erased.")
            if os.path.exists(f"ext/Conversation/conversation-{user_id}.txt"):
                with open(f"ext/Conversation/conversation-{user_id}.txt", "w") as f:
                    pass
                await asyncio.to_thread(db[f"{user_id}"].update_one,
                    {"id" : user_id},
                    {"$set" : {"conversation" : None}}
                )
            return True
        if response.text is not None:
            if user_id > 0:
                with open(f"ext/memory/memory-{user_id}.txt", "a+", encoding="utf-8") as f:
                    f.write(response.text)
                    f.seek(0)
                    memory = f.read()
                await asyncio.to_thread(db[f"{user_id}"].update_one,
                    {"id" : user_id},
                    {"$set" : {"memory" : memory}}
                )
                await asyncio.to_thread(delete_n_convo, user_id, 10)
            elif user_id < 0:
                group_id = user_id
                with open(f"ext/memory/memory-group.txt", "a+", encoding="utf-8") as f:
                    f.write(response.text)
                    f.seek(0)
                    memory = f.read()
                await asyncio.to_thread(db[f"group"].update_one,
                    {"id" : "group"},
                    {"$set" : {"memory" : memory}}
                )
                await asyncio.to_thread(delete_n_convo, group_id,100)
            return True
        else:
            if (gemini_api_keys.index(api) > len(gemini_api_keys)-3):
                if os.path.exists(f"ext/Conversation/conversation-{user_id}.txt"):
                    with open(f"ext/Conversation/conversation-{user_id}.txt", "w") as f:
                        pass
                    await asyncio.to_thread(db[f"{user_id}"].update_one,
                        {"id" : user_id},
                        {"$set" : {"conversation" : None}}
                    )
                    return True
            else:
                return False
    except Exception as e:
        print(f"Failed to create memory\n Error code-{e}")



#create the conversation history as prompt
async def create_prompt(update:Update, content:ContextTypes.DEFAULT_TYPE, user_message, user_id, media):
    try:
        settings = await get_settings(user_id)
        if update.message.chat.type == "private":
            data = "***RULES***\n"
            data += (
                "Never ever user any timestamp in your response."
                "Timestamp is only for you to understand the user better and provide more realistic response"
                "So, You must not use timestamp in your response."
            )
            with open("ext/info/rules.shadow", "rb" ) as f:
                data += fernet.decrypt(f.read()).decode("utf-8")
                data += "\n***END OF RULES***\n\n\n"
            # if (settings[6] == 4 or settings[6] == 0) and media == 0:
            #     data += "****TRAINING DATA****"
            #     with open("ext/info/group_training_data.txt", "r") as file:
            #         data += file.read()
            #     data += "****END OF TRAINIG DATA****"
            data += "***MEMORY***\n"
            with open(f"ext/memory/memory-{user_id}.txt", "a+", encoding="utf-8") as f:
                f.seek(0)
                data += f.read()
                data += "\n***END OF MEMORY***\n\n\n"
            with open(f"ext/Conversation/conversation-{user_id}.txt", "a+", encoding="utf-8") as f:
                f.seek(0)
                data += "***CONVERSATION HISTORY***\n\n"
                data += f.read()
                data += "\nUser: " + user_message
                f.seek(0)
                if(f.read().count("You: ")>20):
                    asyncio.create_task(background_memory_creation(update, content, user_id))
            if data:
                return data
            else:
                return "Hi"
        if update.message.chat.type != "private":
            data = "***RULES***\n"
            with open("ext/info/group_rules.shadow", "rb") as f:
                data += fernet.decrypt(f.read()).decode("utf-8")
                data += "\n***END OF RULES***\n\n\n"
            data += "******TRAINING DATA******\n\n"
            with open("ext/info/group_training_data.txt", "r") as f:
                data += f.read()
                data += "******END OF TRAINING DATA******\n\n"
            data += "***MEMORY***\n"
            with open(f"ext/memory/memory-group.txt", "a+", encoding="utf-8") as f:
                f.seek(0)
                data += f.read()
                data += "\n***END OF MEMORY***\n\n\n"
            with open(f"ext/Conversation/conversation-group.txt", "a+", encoding="utf-8") as f:
                f.seek(0)
                data += "***CONVERSATION HISTORY***\n\n"
                data += f.read()
                data += "\nUser: " + user_message
                f.seek(0)
                if(f.read().count("You: ")>200):
                    asyncio.create_task(background_memory_creation(update, content, user_id))
            if data:
                return data
            else:
                return "Hi"
    except Exception as e:
        print(f"Error in create_promot function. \n\n Error Code - {e}")
        await send_to_channel(update, content, channel_id, f"Error in create_prompt function. \n\n Error Code - {e}")


#function to save conversation
def save_conversation(user_message : str , gemini_response:str , user_id:int) -> None:
    try:
        bd_tz = pytz.timezone("Asia/Dhaka")
        now = datetime.now(bd_tz).strftime("%d-%m-%Y, %H:%M:%S")
        conn = sqlite3.connect("ext/info/user_data.db")
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM users WHERE user_id = ?", (user_id,))
        name = cursor.fetchone()[0]
        with open(f"ext/Conversation/conversation-{user_id}.txt", "a+", encoding="utf-8") as f:
            if user_message == None:
                f.write(f"{gemini_response}\n")
            else:
                f.write(f"\n[{now}] {name}: {user_message}\nYou: {gemini_response}\n")
            f.seek(0)
            data = f.read()
        db[f"{user_id}"].update_one(
            {"id" : user_id},
            {"$set" : {"conversation" : data}}
        )
    except Exception as e:
        print(f"Error in saving conversation. \n\n Error Code - {e}")


#function to save group conversation
def save_group_conversation(update : Update,user_message, gemini_response):
    try:
        name = update.effective_user.first_name or "X" +" "+ update.effective_user.last_name or "X"
        with open(f"ext/Conversation/conversation-group.txt", "a+", encoding="utf-8") as f:
            f.write(f"\n{name}: {user_message}\nYou: {gemini_response}\n")
            f.seek(0)
            data = f.read()
        db["group"].update_one(
            {"id" : "group"},
            {"$set" : {"conversation" : data}}
        )
    except Exception as e:
        print(f"Error in saving conversation. \n\n Error Code - {e}")


#function to create memory in background
async def background_memory_creation(update: Update,content,user_id):
    try:
        if update.message.chat.type == "private":
            for api in gemini_api_keys:
                result = await asyncio.create_task(create_memory(update, content, api, user_id))
                if result:
                    break
        elif update.message.chat.type != "private":
            group_id = update.effective_chat.id
            for api in gemini_api_keys:
                result = await asyncio.create_task(create_memory(update, content, api, group_id))
                if result:
                    break
    except Exception as e:
        print(f"Error in background_memory_creation function.\n\n Error Code -{e}")
        await send_to_channel(update, content, channel_id, f"Error in background_memory_creation function.\n\n Error Code -{e}")



#function for deleting memory
async def delete_memory(update : Update, content : ContextTypes.DEFAULT_TYPE, query) -> None:
    try:
        user_id = update.effective_chat.id
        with open(f"ext/memory/memory-{update.callback_query.from_user.id}.txt", "w") as f:
            pass
        await asyncio.to_thread(db[f"{user_id}"].update_one,
            {"id" : user_id},
            {"$set" : {"memory" : None}}
        )
        await query.edit_message_text("You cleared my memory about you, It really makes me sad.")
    except Exception as e:
        print(f"Error in delete_memory function.\n\nError Code - {e}")
        await send_to_channel(update, content, channel_id, f"Error in delete_memory function \n\nError Code -{e}")



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
        if os.path.exists(f"ext/Conversation/conversation-{user_id}.txt"):
            with open(f"ext/Conversation/conversation-{user_id}.txt", "w") as f:
                pass
            await asyncio.to_thread(db[f"{user_id}"].update_one,
                {"id" : user_id},
                {"$set" : {"conversation" : None}}
            )
            await query.edit_message_text("All clear, Now we are starting fresh.")
        else:
            await query.edit_message_text("It seems you don't have a conversation at all.")
    except Exception as e:
        await update.callback_query.message.reply_text(f"Sorry, The operation failed. Here's the error message:\n<pre>{html.escape(str(e))}</pre>", parse_mode="HTML")
        await send_to_channel(update, content, channel_id, f"Error in reset function \n\nError Code -{e}")


   #A function to return memory for user convention
async def see_memory(update : Update, content : ContextTypes.DEFAULT_TYPE, query) -> None:
    try:
        try:
            if update.message.chat.type != "private":
                await update.message.reply_text("Memory is not visible from group. Privacy concern idiot.")
                return
        except:
            pass
        with open(f"ext/memory/memory-{update.callback_query.from_user.id}.txt", "a+") as f:
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
