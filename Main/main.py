import re
import os
import time
import html
import shutil
import sqlite3
import random
import asyncio
import warnings
import threading
import requests
from glob import glob
from io import BytesIO
from fpdf import FPDF
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
from pymongo import MongoClient
from pymongo.server_api import ServerApi
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



#connecting to MongoDB database
try:
    
    mongo_pass = os.getenv("MDB_pass_shadow")
    url = f"mongodb+srv://shadow_mist0:{mongo_pass}@cluster0.zozzwwv.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
    client = MongoClient(url, server_api=ServerApi("1"))
    db = client["phantom_bot"]
except Exception as e:
    print(f"Error Connecting to MongoDB.\n\nError Code - {e}")


#all globals variable

channel_id = -1002575042671

#loading the bot api
def get_token():
    try:
        TOKENs = db["API"].find()[0]["bot_api"]
        return TOKENs
    except Exception as e:
        print(f"Error Code -{e}")
TOKEN = get_token()[0]


#all registered user
def load_all_user():
    try:
        users = tuple(int(user) for user in db.list_collection_names() if user.isdigit())
        all_users = tuple(db["all_user"].find_one({"type":"all_user"})["users"])
        for user in users:
            if user not in all_users:
                db["all_user"].update_one(
                    {"type" : "all_user"},
                    {"$push" : {"users" : user}}
                )
        return users
    except Exception as e:
        print(f"Error in load_all_user fnction.\n\n Error code -{e}")
all_users = load_all_user()


#function to load all admin
def load_admin():
    try:
        admins = tuple(int(admin) for admin in db["admin"].find()[0]["admin"])
        return admins
    except Exception as e:
        print(f"Error in load_admin function.\n\nError Code - {e}")
all_admins = load_admin()

#function to load all gemini model
def load_gemini_model():
    try:
        models = tuple(db["ai_model"].find()[0]["model_name"])
        return models
    except Exception as e:
        print(f"Error Loading Gemini Model.\n\nError Code -{e}")
        return None

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


#function to create settings file MongoDB to offline for optimization
def create_settings_file():
    try:
        shutil.rmtree("settings", ignore_errors=True)
        os.makedirs("settings", exist_ok=True)
        conn = sqlite3.connect("settings/user_settings.db")
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_settings(
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                model INTEGER,
                thinking_budget INTEGER,
                temperature REAL,
                streaming INTEGER,
                persona INTEGER
            )
        """)
        for user in all_users:
            settings = tuple(db[f"{user}"].find()[0]["settings"])
            cursor.execute("""
                INSERT OR IGNORE INTO user_settings 
                (id, name, model, thinking_budget, temperature, streaming, persona)
                VALUES (?,?,?,?,?,?,?)
        """, settings
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error in create_settings_file function. \n\nError Code -{e}")



#function to create offline file for conversation history
def create_conversation_file():
    try:
        shutil.rmtree("Conversation", ignore_errors=True)
        os.makedirs("Conversation", exist_ok=True)
        for user in all_users:
            conv_data = db[f"{user}"].find()[0]["conversation"]
            with open(f"Conversation/conversation-{user}.txt", "w") as file:
                if conv_data:
                    file.write(conv_data)
                else:
                    pass
        try:
            conv_data = db["group"].find()[0]["conversation"]
            with open(f"Conversation/conversation-group.txt", "w") as file:
                file.write(conv_data)
        except:
            print("Group conversation doesn't exist")
            with open(f"Conversation/conversation-group.txt", "w") as file:
                pass
    except Exception as e:
        print(f"Error in create_conversation_file function. \n\n Error Code  {e}")


#function to create offline file for memory
def create_memory_file():
    try:
        shutil.rmtree("memory", ignore_errors=True)
        os.makedirs("memory", exist_ok=True)
        for user in all_users:
            mem_data = db[f"{user}"].find()[0]["memory"]
            with open(f"memory/memory-{user}.txt", "w") as file:
                if mem_data:
                    file.write(mem_data)
                else:
                    pass
        try:
            mem_data = db["group"].find()[0]["memory"]
            with open(f"memory/memory-group.txt", "w") as file:
                file.write(mem_data)
        except:
            print("Group memory doesn't exist")
            with open(f"memory/memory-group.txt", "w") as file:
                pass
    except Exception as e:
        print(f"Error in create_memory_file function. \n\n Error Code  {e}")


#function to create offline file for memory
def create_persona_file():
    try:
        shutil.rmtree("persona", ignore_errors=True)
        os.makedirs("persona", exist_ok=True)
        personas = [persona for persona in db["persona"].find({"type":"persona"})]
        for persona in personas:
            with open(f"persona/{persona["name"]}.txt", "w") as f:
                f.write(persona["persona"])
    except Exception as e:
        print(f"Error in create_persona_file function. \n\n Error Code  {e}")

    
#function to create user_data file MongoDB to offline for optimization
def create_user_data_file():
    try:
        if os.path.exists("info/user_data.db"):
            os.remove("info/user_data.db")
        os.makedirs("info", exist_ok=True)
        conn = sqlite3.connect("info/user_data.db")
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users(
                user_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                gender TEXT,
                roll INTEGER,
                password TEXT,
                api TEXT
            )
        """)
        for user in all_users:
            user_data = tuple(data for data in db[f"{user}"].find_one({"id":user})["user_data"])
            cursor.execute("""
                INSERT OR IGNORE INTO users 
                (user_id, name, gender, roll, password, api)
                VALUES (?,?,?,?,?,?)
        """, user_data
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error in create_user_data_file function.\n\nError Code - {e}")


#function to create a password file for admin
def create_admin_pass_file():
    try:
        shutil.rmtree("admin", ignore_errors=True)
        os.makedirs("admin", exist_ok=True)
        content = db["admin"].find_one({"type" : "admin"})["admin_password"]
        content = fernet.encrypt(content.encode())
        with open("admin/admin_password.shadow", "wb") as f:
            f.write(content)
    except Exception as e:
        print(f"Error in create_admin_pass_file function.\n\nError Code - {e}")


#function to create routine folder offline
def create_routine_file():
    try:
        shutil.rmtree("routine", ignore_errors=True)
        os.makedirs("routine", exist_ok=True)
        with open("routine/lab_routine.txt", "w") as f:
            data = db["routine"].find_one({"type" : "routine"})["lab_routine"]
            f.write(data)
        with open("routine/rt1.png", "wb") as f:
            data = db["routine"].find_one({"type" : "routine"})["rt1"]
            f.write(data)
        with open("routine/rt2.png", "wb") as f:
            data = db["routine"].find_one({"type" : "routine"})["rt2"]
            f.write(data)
    except Exception as e:
        print(f"Error in create_routine_file function. Error Code - {e}")


#function to create info file locally from MongoDB
def create_info_file():
    os.makedirs("info",exist_ok=True)
    colllection = db["info"]
    for file in colllection.find({"type" : "info"}):
        file_name = file["name"]
        path = f"info/{file_name}.txt" if file_name == "group_training_data" else f"info/{file_name}.shadow"
        if file_name == "group_training_data":
            with open(path, "w") as f:
                f.write(file["data"])
        else:
            with open(path, "wb") as f:
                f.write(fernet.encrypt(file["data"].encode()))


#calling all those function to create offline file from MongoDB
create_info_file()
create_memory_file()
create_persona_file()
create_routine_file()
create_settings_file()
create_user_data_file()
create_admin_pass_file()
create_conversation_file()




        

#all function description and function for gemini to use
#NOT RECOMMENDED TO TOUCH



# Define the function declaration for the model
create_image_function = {
    "name" : "create_image",
    "description" :"Generates a highly detailed and visually appealing image based on the user's prompt — designed to go beyond plain representations and create beautiful, vivid, and stylized visuals that capture the essence of the subject.",
    "parameters" : {
        "type" : "object",
        "properties" : {
            "prompt" : {
                "type" : "string",
                "description" : "A rich, descriptive prompt that guides the image generation — include details like subject, environment, lighting, emotion, style, and mood to get the most beautiful and expressive result.",
            },
        },
        "required" : ["prompt"],
    },
}


search_online_function = {
    "name": "search_online",
    "description": (
        "Performs a real-time online search to retrieve accurate and current information. "
        "Can search the web based on a query or extract context from a specific URL if provided."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search term or question to look up online. Or A specific URL to fetch and extract information from with a perfect command for what to do."
            },
        },
        "required" : ["query"],
    },
}


get_group_data_function ={
    "name" : "get_group_data",
    "description" : (
        "Fetch data that holds all the message and description about our class and all the user and give response from it"
        "This are the class member:\n"
        """1. Umme Kulsum
            2. Urboshi Mahmud
            3. Shahriar Joy
            4. Tasnimul Hassan Tanim
            5. Mahdi Haque
            6. Suprio Roy Chowdhury
            7. Tahmim Ullah
            8. Shafayet Hossain Shuvo
            9. Athai Dey
            10. Abdullah Sifat
            11. Tanvir Chowdhury
            12. Esika Tanzum
            13. Saroar Jahan Tius
            14. Tafsirul Ahmed Azan
            15. Muhammad Khushbo Nahid
            16. Reyano Kabir
            17. MD Tasdid Hossain
            18. Fazle Rabbi
            19. Fahad Kabir
            20. Md Shibli Sadik Sihab
            21. Tasaouf Ahnaf
            22. Shariqul Islam
            23. Shohanur Rahman Shadhin
            24. Rabib Rehman
            25. Sumon Majumder
            26. Shadman Ahmed
            27. Bitto Saha
            28. Nazmus Saquib Sinan
            29. Fajle Hasan Rabbi
            30. Nilay Paul
            31. Afra Tahsin Anika
            32. MD Shoykot Molla
            33. Arefin Noused Ratul
            34. Avijet Chakraborty
            35. A Bid
            36. Aftab Uddin Antu
            37. Prantik Paul
            38. Eram Ohid
            39. Sazedul Islam
            40. Mirajul Islam
            41. Sayem Bin Salim
            42. Fardin Numan
            43. Anjum Shahitya
            44. Tanvir Ahmed
            45. Sujoy Rabidas
            46. Samiul Islam Wrivu
            47. Md. Sami Sadik
            48. Aminul Islam Sifat
            49. Salman Ahmed Sabbir
            50. Aqm Mahdi Haque
            51. Mehedi Hasan
            52. Shahriar Joy
            53. Mawa Tanha
            54. Sara Arpa
            55. Md Tausif Al Sahad
            56. Mubin R.
            57. Abdul Mukit
            58. Arnob Benedict Tudu
            59. Sajid Ahmed
            60. Yasir Arafat
            61. Morchhalin Alam Amio"""
        "Get info about CR, teacher etc"
    ),
    "parameters" : {
        "type" : "object",
        "properties" : {
            
        }
    }
}


get_ct_data_function = {
    "name" : "get_ct_data",
    "description" : "Fetch data of upcoming class test or CT",
    "parameters" : {
        "type" :"object",
        "properties" : {

        }
    }
}


def search_online(user_message, api):
    try:
        print("searching...")
        tools=[]
        tools.append(types.Tool(google_search=types.GoogleSearch))
        tools.append(types.Tool(url_context=types.UrlContext))
        
        config = types.GenerateContentConfig(
            temperature = 0.7,
            tools = tools,
            system_instruction=open("persona/Pikachu.txt").read(),
            response_modalities=["TEXT"],
        )
        client = genai.Client(api_key=api)
        response = client.models.generate_content(
            model = "gemini-2.5-flash",
            contents = [user_message],
            config = config,
        )
        return response
    except Exception as e:
        print(f"Error getting gemini response.\n\n Error Code - {e}")





#funtion to send message to chaneel
async def send_to_channel(update: Update, content : ContextTypes.DEFAULT_TYPE, chat_id, message) -> None:
    try:
        await content.bot.send_message(chat_id=chat_id, text=message)
    except Exception as e:
        print(f"Error in send_to_channel function.\n\nError Code - {e}")
        await send_to_channel(update, content, chat_id, message)





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
        api_list = tuple(db["API"].find()[0]["gemini_api"])
        return api_list
    except Exception as e:
        print(f"Error lading gemini API. \n\nError Code -{e}")
gemini_api_keys = load_gemini_api()


#adding escape character for markdown rule
def add_escape_character(text):
    escape_chars = r'_*\[\]()~>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)


#function to get settings
async def get_settings(user_id):
    conn = sqlite3.connect("settings/user_settings.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM user_settings WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    if not row:
        return (999999, "XX", 1, 0, 0.7, 0, 4)
    if row[2] > len(gemini_model_list)-1:
        row = list(row)
        row[2] = len(gemini_model_list)-1
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


#A function to delete n times convo from conversation history
def delete_n_convo(user_id, n):
    try:
        if user_id < 0:
            with open(f"Conversation/conversation-group.txt", "r+", encoding="utf-8") as f:
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
        with open(f"Conversation/conversation-{user_id}.txt", "r+", encoding="utf-8") as f:
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


#create the conversation history as prompt
async def create_prompt(update:Update, content:ContextTypes.DEFAULT_TYPE, user_message, user_id, media):
    try:
        settings = await get_settings(user_id)
        if update.message.chat.type == "private":
            data = "***RULES***\n"
            with open("info/rules.shadow", "rb" ) as f:
                data += fernet.decrypt(f.read()).decode("utf-8")
                data += "\n***END OF RULES***\n\n\n"
            data += "****TRAINING DATA****"
            if (settings[6] == 4 or settings[6] == 0) and media == 0:
                with open("info/group_training_data.txt", "r") as file:
                    data += file.read()
            data += "****END OF TRAINIG DATA****"
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
            if data:
                return data
            else:
                return "Hi"
        if update.message.chat.type != "private":
            data = "***RULES***\n"
            with open("info/group_rules.shadow", "rb") as f:
                data += fernet.decrypt(f.read()).decode("utf-8")
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
            if data:
                return data
            else:
                return "Hi"
    except Exception as e:
        print(f"Error in create_promot function. \n\n Error Code - {e}")
        await send_to_channel(update, content, channel_id, f"Error in create_prompt function. \n\n Error Code - {e}")



#creating memory, SPECIAL_NOTE: THIS FUNCTION ALWAYS REWRITE THE WHOLE MEMORY, SO THE MEMORY SIZE IS LIMITED TO THE RESPONSE SIZE OF GEMINI, IT IS DONE THIS WAY BECAUSE OTHERWISE THERE WILL BE DUPLICATE DATA 
async def create_memory(api, user_id):
    try:
        if user_id > 0:
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
        elif user_id < 0:
            group_id = user_id
            with open("persona/memory_persona.txt", "r") as f:
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
            model = "gemini-2.5-pro",
            contents = data,
            config = types.GenerateContentConfig(
                thinking_config = types.ThinkingConfig(thinking_budget=1024),
                temperature = 0.7,
                system_instruction =  instruction,
            ),
        )
        if user_id > 0:
            with open(f"memory/memory-{user_id}.txt", "w", encoding="utf-8") as f:
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
            with open(f"memory/memory-group.txt", "w", encoding="utf-8") as f:
                f.write(response.text)
                f.seek(0)
                memory = f.read()
            await asyncio.to_thread(db[f"group"].update_one,
                {"id" : "group"},
                {"$set" : {"memory" : memory}}
            )
            await asyncio.to_thread(delete_n_convo, group_id,100)
    except Exception as e:
        print(f"Failed to create memory\n Error code-{e}")





#function to create memory in background
async def background_memory_creation(update: Update,content,user_id):
    try:
        if update.message.chat.type == "private":
            await asyncio.create_task(create_memory(gemini_api_keys[-1], user_id))
            await send_to_channel(update, content, channel_id, f"Created memory for User - {user_id}")
            with open(f"memory/memory-{user_id}.txt", "rb") as file:
                await content.bot.send_document(chat_id=channel_id, document = file, caption = "Heres the memory file.")
        elif update.message.chat.type != "private":
            group_id = update.effective_chat.id
            await asyncio.create_task(create_memory(gemini_api_keys[-1], group_id))
            await send_to_channel(update, content, channel_id, "Created memory for group")
            with open(f"memory/memory-group.txt", "r", encoding="utf-8") as f:
                await content.bot.send_document(chat_id=channel_id, document=file, caption="Memory for the group.")
    except Exception as e:
        print(f"Error in background_memory_creation function.\n\n Error Code -{e}")
        await send_to_channel(update, content, channel_id, f"Error in background_memory_creation function.\n\n Error Code -{e}")































#a function to restart renew all the bot info
async def restart(update:Update, content:ContextTypes.DEFAULT_TYPE) -> None:
    try:
        await update.message.reply_text("Restarting please wait....")
        create_info_file()
        create_memory_file()
        create_persona_file()
        create_routine_file()
        create_settings_file()
        create_user_data_file()
        create_admin_pass_file()
        create_conversation_file()
        await update.message.reply_text("Restart Successful.")
    except Exception as e:
        print(f"Error in restart function.\n\nError Code - {e}")







temp_api = list(gemini_api_keys)
for i in range(len(gemini_api_keys)):
    api = random.choice(temp_api)
    print(gemini_api_keys.index(api))
    temp_api.remove(api)
    client = genai.Client(api_key=api)
    config = types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_budget=0),
        temperature = 0.7,
        system_instruction=open("persona/Pikachu.txt").read(),
    )
    response =  client.models.generate_content(
        model = "gemini-2.5-flash",
        contents= ["hi there write a 10000 word paragraph explaining how AI works"],
        config=config,
    )
    print(response.text)