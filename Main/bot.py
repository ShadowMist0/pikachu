import re
import os
import time
import html
import pytz
import json
import shutil
import random
import asyncio
import sqlite3
import requests
import warnings
import threading
from fpdf import FPDF
from PIL import Image
from glob import glob
from io import BytesIO
from google import genai
from google.genai import types
from pymongo import MongoClient
from flask_limiter import Limiter
from collections import defaultdict
from flask import render_template
from geopy.distance import geodesic
from cryptography.fernet import Fernet
from flask import Flask, request, abort
from pymongo.server_api import ServerApi
from telegram.constants import ChatAction
from telegram.request import HTTPXRequest
from telegram.error import RetryAfter, TimedOut
from flask_limiter.util import get_remote_address
from datetime import datetime, timedelta, timezone
from telegram._utils.warnings import PTBUserWarning
from google.genai.types import GenerateContentResponse
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton
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











key = os.getenv("decryption_key")
fernet = Fernet(key)


#code to ignore warnig about per_message in conv handler and increase poll size
warnings.filterwarnings("ignore",category=PTBUserWarning)
tg_request = HTTPXRequest(connection_pool_size=50, pool_timeout=30)



#a flask to ignore web pulling condition
app = Flask(__name__, template_folder="website")
limiter = Limiter(key_func=get_remote_address)
limiter.init_app(app)
@app.route('/')
@limiter.limit("20 per minute")
def home():
    return render_template("404.html"), 404

@app.route('/secret_admin_path', methods=['GET'])
def admin_route():
    key = request.args.get("key")
    if key != os.getenv("MDB_pass_shadow"):
        abort(403, description="You are not a admin")
    return "Bot is running"

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
TOKEN = get_token()[2]


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
        print("settings, ", end="")
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
        print(f"Error in create_settings_file funcion.\n\nError Code - {e}")


#function to create offline file for conversation history
def create_conversation_file():
    try:
        print("conversation file")
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
        print("memory, ", end="")
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
            with open(f"memory/memory-group.txt", "w") as file:
                pass
    except Exception as e:
        print(f"Error in create_memory_file function. \n\n Error Code  {e}")


#function to create offline file for memory
def create_persona_file():
    try:
        print("persona, ", end="")
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
        print("user_data, ", end="")
        if os.path.exists("info/user_data.db"):
            try:
                os.remove("info/user_data.db")
            except:
                pass
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
        print(f"Error in create_user_data_file function. \n\nError Code- {e}")


#function to create a password file for admin
def create_admin_pass_file():
    try:
        print("admin, ", end="")
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
        print("routine, ", end="")
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
    try:
        print("Creating info, ", end="")
        shutil.rmtree("info", ignore_errors=True)
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
    except Exception as e:
        print(f"Error in create_info_file function.\n\nError Code - {e}")


#calling all those function to create offline file from MongoDB
async def load_all_files():
    try:
        print("Loading all files and folder...")
        await asyncio.to_thread(create_info_file)
        await asyncio.to_thread(create_memory_file)
        await asyncio.to_thread(create_persona_file)
        await asyncio.to_thread(create_routine_file)
        await asyncio.to_thread(create_settings_file)
        await asyncio.to_thread(create_user_data_file)
        await asyncio.to_thread(create_admin_pass_file)
        await asyncio.to_thread(create_conversation_file)
        print("Successfully loaded all file and folder.")
    except Exception as e:
        print(f"Error in load_all_file function. \n\nError code - {e}")



#a function to restart renew all the bot info
async def restart(update:Update, content:ContextTypes.DEFAULT_TYPE) -> None:
    try:
        await update.message.reply_text("Restarting please wait....")
        await asyncio.to_thread(create_info_file)
        await asyncio.to_thread(create_memory_file)
        await asyncio.to_thread(create_persona_file)
        await asyncio.to_thread(create_routine_file)
        await asyncio.to_thread(create_settings_file)
        await asyncio.to_thread(create_user_data_file)
        await asyncio.to_thread(create_admin_pass_file)
        await asyncio.to_thread(create_conversation_file)
        await update.message.reply_text("Restart Successful.")
    except Exception as e:
        print(f"Error in restart function.\n\nError Code - {e}")
        
        
        
#all function description and function for gemini to use
#NOT RECOMMENDED TO TOUCH



# Define the function declaration for the model

#function to send the function action to the use
async def send_action(update:Update, content:ContextTypes.DEFAULT_TYPE, action):
    try:
        await update.message.reply_text(action)
    except Exception as e:
        print(f"Error in send_action function.\n\nError Code - {e}")

#all the function declaration goes here

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
        """ 1. Umme Kulsum
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
        """Retrieves and analyzes a comprehensive dataset for the 'CSE Section C' university student group (24 Series, RUET).
        This function is the primary source of information for any query related to the internal affairs, members, and culture of this specific group.
        The dataset contains a complete list of its 61 members, a detailed summary of important group dynamics, and an extensive log of their informal group chat messages.
        Use this function when asked about key individuals, teachers, inside jokes, or recurring topics of conversation within the group.
        Key individuals include: CRs Sumon Majumder (gaming enthusiast, 1st 30) and Fazle Rabbi (serious, 2nd 30);
        bot programmers Bitto Saha and Sifat (shadow_mist); all-rounder Mirajul Islam ('the Faculty');
        Competitive Programming expert Nilay Paul;
        and EEE expert Shadman Ahmed ('Dr. Snake').
        Key teachers frequently discussed are the very strict Helal Sir (Maths), and the highly-praised Mainul Sir (EEE) and Shahiduzzaman Sir (CSE).
        The data is rich with inside jokes like 'sikhan vai', 'kibabe sombob', 'dirim', 'dream vhai', 'sheet e to lekha nai', 'CG 4.69', and complaints about 'Helal sir er sheet'.
        The message logs cover topics such as academic planning (class routines, CTs, lab reports), social coordination (hangouts, football, CSE Night), technical projects (group website, Telegram bot), coding (CP, GitHub), and general student banter in a mix of Bengali and English ('Banglish')."""
    ),
    "parameters" : {
        "type" : "object",
        "properties" : {
            
        }
    }
}


get_ct_data_function = {
    "name" : "get_ct_data",
    "description" : """Fetch data of upcoming class test or CT use this format to represent""",
    "parameters" : {
        "type" :"object",
        "properties" : {

        }
    }
}

get_routine_function = {
    "name" : "get_routine",
    "description" : "Provide class routine",
    "parameters" : {
        "type" :"object",
        "properties" : {

        }
    }
}


create_memory_function = {
    "name" : "add_memory_content",
    "description" : (
        "Used to store user-specific memories or preferences when the user explicitly asks the assistant "
        "to remember something. This may include names, dates, preferences, personal facts, instructions, "
        "or frequently mentioned information. The assistant should extract the relevant part from the user's message "
        "and store it for future context-aware interactions."
        "like 'remember that...', 'don't forget...', or 'store this...'."
        "for future reference—such as preferences, important facts, habits, names, birthdays, or any "
        "custom instruction. The assistant should extract the relevant content from the user message "
        "and pass it as a structured parameter for long-term storage."
    ),
    "parameters" : {
        "type" : "object",
        "properties" : {
            "memory_content" : {
                "type" : "string",
                "description" : (
                    "The exact information or fact the user wants to store"
                    "It should be clear and useful for future context."
                )
            }
        },
        "required" : ["memory_content"]
    }
}




information_handler_function = {
    "name": "information_handler",
    "description": (
        "Handles all queries related to our class resources such as the Drive link, cover page generator, "
        "class website, Google Classroom code, and orientation materials. Responds with a helpful message and, "
        "if applicable with a clickable button (except for Google Classroom code)."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "info_name": {
                "type": "string",
                "description": (
                    "'drive' When the user asks for the class Drive (for notes, CTs, labs, etc).\n"
                    "'cover_page' When the user asks for a cover page generator for assignments or lab reports.\n"
                    "'website' When asked for the official class website.\n"
                    "'g_class_code' When the user asks for the Google Classroom code.\n"
                    "'orientation_file' When the user wants the file that includes student list, CSE '24 syllabus, and the prospectus."
                )
            }
        },
        "required": ["info_name"]
    }
}



async def information_handler(update:Update, content:ContextTypes.DEFAULT_TYPE, info_name):
    try:
        if info_name == "drive":
            keyboard = [[InlineKeyboardButton("Drive", url="https://drive.google.com/drive/folders/1xbyCdj3XQ9AsCCF8ImI13HCo25JEhgUJ")]]
            markup = InlineKeyboardMarkup(keyboard)
            return markup
        elif info_name == "cover_page":
            keyboard = [[InlineKeyboardButton("Lab Cover Page", url="https://ruet-cover-page.github.io/")]]
            markup = InlineKeyboardMarkup(keyboard)
            return markup
        elif info_name == "website":
            keyboard = [[InlineKeyboardButton("All Websites", callback_data="c_all_websites")]]
            markup = InlineKeyboardMarkup(keyboard)
            return markup
        elif info_name == "g_class_code":
            return "CSE Google classroom code: ```2o2ea2k3```\n\nMath G. Classroom code: ```aq4vazqi```\n\nChemistry G. Classroom code: ```wnlwjtbg```"
        elif info_name == "orientation_file":
            keyboard = [[InlineKeyboardButton("Orientation Files", url = "https://drive.google.com/drive/folders/10_-xTV-FsXnndtDiw_StqH2Zy9tQcWq0")]]
            markup = InlineKeyboardMarkup(keyboard)
            return markup
        else:
            return "Sorry i don't have your requested data."
    except Exception as e:
        print(f"Error in information_handler function.\n\nError Code - {e}")
        await update.message.reply_text("Internal Error. Contact admin or try again later.")


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
            with open("info/group_training_data.txt") as f:
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
        if os.path.exists(f"memory/memory-{user_id}.txt"):
            with open(f"memory/memory-{user_id}.txt", "a+") as file:
                file.write("\n" + data + "\n")
    except Exception as e:
        print(f"Error in create_image function.\n\nError Code - {e}")






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
    try:
        escape_chars = r'_*\[\]()~>#+-=|{}.!'
        return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)
    except Exception as e:
        print(f"Error in add_escape_character function.\n\nError Code - {e}")
        return text


#function to get settings
async def get_settings(user_id):
    try:
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
    except Exception as e:
        print(f"Error in get_settings fucntion.\n\nError Code - {e}")
        return (999999, "XX", 1, 0, 0.7, 0, 4)


#gemini response for stream on
async def gemini_stream(update, content, user_message, api, settings):
    try:
        tools=[]
        # tools.append(types.Tool(google_search=types.GoogleSearch))
        # tools.append(types.Tool(url_context=types.UrlContext))
        tools.append(types.Tool(function_declarations=[search_online_function]))

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
        tools.append(types.Tool(function_declarations=[search_online_function, get_ct_data_function, get_group_data_function, create_image_function, get_routine_function, create_memory_function, information_handler_function]))
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
            # with open("response.txt", "w") as file:
            #     json.dump(response.to_json_dict(), file, indent=2, ensure_ascii=False)
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


#creating memory, SPECIAL_NOTE: THIS FUNCTION ALWAYS REWRITE THE WHOLE MEMORY, SO THE MEMORY SIZE IS LIMITED TO THE RESPONSE SIZE OF GEMINI, IT IS DONE THIS WAY BECAUSE OTHERWISE THERE WILL BE DUPLICATE DATA 
async def create_memory(update:Update, content:ContextTypes.DEFAULT_TYPE, api, user_id):
    try:
        settings = await get_settings(update.effective_user.id)
        if user_id > 0:
            with open("persona/memory_persona.txt", "r", encoding="utf-8") as f:
                instruction = load_persona(settings) + f.read()
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
            if os.path.exists(f"Conversation/conversation-{user_id}.txt"):
                with open(f"Conversation/conversation-{user_id}.txt", "w") as f:
                    pass
                await asyncio.to_thread(db[f"{user_id}"].update_one,
                    {"id" : user_id},
                    {"$set" : {"conversation" : None}}
                )
            return True
        if response.text is not None:
            if user_id > 0:
                with open(f"memory/memory-{user_id}.txt", "a+", encoding="utf-8") as f:
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
                with open(f"memory/memory-group.txt", "a+", encoding="utf-8") as f:
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
                if os.path.exists(f"Conversation/conversation-{user_id}.txt"):
                    with open(f"Conversation/conversation-{user_id}.txt", "w") as f:
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
            with open("info/rules.shadow", "rb" ) as f:
                data += fernet.decrypt(f.read()).decode("utf-8")
                data += "\n***END OF RULES***\n\n\n"
            # if (settings[6] == 4 or settings[6] == 0) and media == 0:
            #     data += "****TRAINING DATA****"
            #     with open("info/group_training_data.txt", "r") as file:
            #         data += file.read()
            #     data += "****END OF TRAINIG DATA****"
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


#function to save conversation
def save_conversation(user_message : str , gemini_response:str , user_id:int) -> None:
    try:
        bd_tz = pytz.timezone("Asia/Dhaka")
        now = datetime.now(bd_tz).strftime("%d-%m-%Y, %H:%M:%S")
        conn = sqlite3.connect("info/user_data.db")
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM users WHERE user_id = ?", (user_id,))
        name = cursor.fetchone()[0]
        with open(f"Conversation/conversation-{user_id}.txt", "a+", encoding="utf-8") as f:
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
        with open(f"Conversation/conversation-group.txt", "a+", encoding="utf-8") as f:
            f.write(f"\n{name}: {user_message}\nYou: {gemini_response}\n")
            f.seek(0)
            data = f.read()
        db["group"].update_one(
            {"id" : "group"},
            {"$set" : {"conversation" : data}}
        )
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
    try:
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
    except Exception as e:
        print(f"Error in handle_ct function. \n\nError Code - {e}")
        await update.message.reply_text(f"Internal Error\n {e}. \nPlease contact admin or try again later.")


#function to inform all the student 
async def inform_all(query, content:ContextTypes.DEFAULT_TYPE) -> None:
    try:
        await query.edit_message_text("please wait while the bot is sending the message to all user.")
        all_users = tuple(db["all_user"].find_one({"type":"all_user"})["users"])
        ct_data = get_ct_data()
        if ct_data is None or not ct_data:
            await query.edit_message_text("⚠️ Couldn't connect to database or no CT data available.")
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
            await query.edit_message_text("ℹ️ No CTs scheduled for tomorrow.")
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
            failed = 0
            failed_list = "Failed to send message to those user:\n"
            tasks = []

            async def send_ct_routine(user):
                nonlocal failed, failed_list
                try:
                    await content.bot.send_message(chat_id=user, text=full_message, parse_mode="HTML")
                    return True
                except:
                    failed += 1
                    failed_list += str(user) + "\n"
                    return False

            for user in all_users:
                tasks.append(send_ct_routine(user))
            result = await asyncio.gather(*tasks)
            sent = sum(result)
            report = (
                    f"📊 Notification sent to {sent} users\n"
                    f"⚠️ Failed to send to {failed} users\n"
                )
            await query.edit_message_text(report)
            if failed != 0:
                await query.message.reply_text(failed_list, parse_mode="Markdown")
        except Exception as e:
            print(f"Error in inform_all function.\n\n Error Code - {e}")
    except Exception as e:
        print(f"Error in inform_all function. Error Code - {e}")


#fuction to circulate message
async def circulate_message(update : Update, content : ContextTypes.DEFAULT_TYPE):
    try:
        keyboard = [
            ["Routine", "CT"],
            ["Settings", "Resources"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False, selective=False, is_persistent=True)
 
        message_type = content.user_data.get("circulate_message_query")
        all_users = tuple(db["all_user"].find_one({"type":"all_user"})["users"])
        message = update.message.text.strip()
        msg = await update.message.reply_text("Please wait while bot is circulating the message.")
        failed = 0
        tasks = []
        failed_list = "Failed to send message to those user:\n"
        if message_type=="c_notice":
            notice = f"```NOTICE\n\n{message}\n```"
        else:
            notice = message
        async def send_notice(user):
            nonlocal failed, failed_list
            try:
                if message_type == "c_notice":
                    try:
                        await content.bot.send_message(
                            chat_id=user,
                            text=notice,
                            parse_mode="Markdown",
                            reply_markup=reply_markup
                        )
                        return True
                    except:
                        try:
                            await content.bot.send_message(
                                chat_id=user,
                                text=add_escape_character(notice),
                                parse_mode="MarkdownV2",
                                reply_markup=reply_markup
                            )
                            return True
                        except:
                            try:
                                await content.bot.send_message(
                                    chat_id=user,
                                    text=notice,
                                    reply_markup=reply_markup
                                )
                                return True
                            except Exception as e:
                                print(e)
                                failed += 1
                                failed_list += f"{user}\n"
                                return False
                else:
                    await content.bot.send_message(
                    chat_id=user,
                    text=notice,
                    parse_mode="HTML",
                    reply_markup=reply_markup
                )
                return True
            except:
                try:
                    await content.bot.send_message(
                        chat_id=user,
                        text=add_escape_character(notice),
                        parse_mode="MarkdownV2",
                        reply_markup=reply_markup
                    )
                    return True
                except:
                    try:
                        await content.bot.send_message(
                            chat_id=user,
                            text= f"NOTICE\n\n{message}" if message_type=="c_notice" else message,
                            reply_markup=reply_markup
                        )
                        return True 

                    except Exception as e:
                        failed += 1
                        failed_list += str(user) + "\n"
                        print(e)
                        return False

        for user in all_users:
            tasks.append(send_notice(user))
        result = await asyncio.gather(*tasks)
        sent = sum(result)

        report = (
                f"📊 Notification sent to {sent} users\n"
                f"⚠️ Failed to send to {failed} users\n"
            )
        await msg.edit_text(report)
        if failed != 0:
            await update.message.reply_text(failed_list, parse_mode="Markdown")
    except Exception as e:
        print(f"Error in circulate_message function.\n\n Error Code - {e}")


#function to circulate routine among all users
async def circulate_routine(query, content:ContextTypes.DEFAULT_TYPE) -> None:
    try:
        all_users = tuple(db["all_user"].find_one({"type":"all_user"})["users"])
        lab = lab_participant()
        if lab[0]:
            rt = "routine/rt1.png"
        else:
            rt = "routine/rt2.png"
        failed = 0
        tasks = []
        failed_list = "Failed to send routine to those user:\n"

        async def send_ct_routine(user):
                nonlocal failed, failed_list
                try:
                    with open(rt,"rb") as photo:
                        await content.bot.send_photo(chat_id=user, photo=photo, caption="Renewed Routine")
                    return True
                except:
                    failed += 1
                    failed_list += str(user) + "\n"
                    return False

        for user in all_users:
            tasks.append(send_ct_routine(user))
        result = await asyncio.gather(*tasks)
        sent = sum(result)
        report = (
                f"📊 Notification sent to {sent} users\n"
                f"⚠️ Failed to send to {failed} users\n"
            )
        await query.message.reply_text(report, parse_mode="HTML")
        if failed != 0:
            await query.message.reply_text(failed_list, parse_mode="Markdown")
    except Exception as e:
        print(f"Error in circulate message function.\n\nError Code - {e}")





#All the python telegram bot function

#function for editing and sending message
async def send_message(update : Update, content : ContextTypes.DEFAULT_TYPE, response, user_message, settings) -> None:
    try:
        if not response:
            await update.message.reply_text("Failed to precess your request. Try again later.")
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

    

#fuction for start command
async def start(update : Update, content : ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        ["Routine", "CT"],
        ["Settings", "Resources"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False, selective=False, is_persistent=True)
    try:
        user_id = update.effective_chat.id
        paths = [
            f"Conversation/conversation-{user_id}.txt",
            f"memory/memory-{user_id}.txt",
        ]

        for path in paths:
            if not os.path.exists(path):
                with open(path, "w", encoding = "utf-8") as f:
                    pass
        users = await asyncio.to_thread(load_all_user)
        if user_id in users:
            await update.message.reply_text("Hi there, I am your personal assistant. If you need any help feel free to ask me.", reply_markup=reply_markup)
            return
        if user_id not in users and update.message.chat.type == "private":
            keyboard = [
                [InlineKeyboardButton("Register", callback_data="c_register"), InlineKeyboardButton("Cancel", callback_data="cancel")]
            ]
            markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("You are not registerd yet.", reply_markup=markup)
        elif user_id not in users and update.message.chat.type != "private":
            await update.message.reply_text("You are not registered yet. Please register in private chat with the bot first.", reply_markup=reply_markup)
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
    for _ in range(n):
        asyncio.create_task(handle_all_messages())


#function to get response from gemini
async def user_message_handler(update:Update, content:ContextTypes.DEFAULT_TYPE, bot_name) -> None:
    try:
        global gemini_api_keys
        user_message = update.message.text.strip()
        user_id = update.effective_user.id
        if update.message.chat.type != "private" and f"{bot_name.lower()}" not in user_message.lower() and "bot" not in user_message.lower() and "@" not in user_message.lower() and "mama" not in user_message.lower() and "pika" not in user_message.lower():
            return
        else:
            settings = await get_settings(user_id)
            if not settings:
                await update.message.reply_text("You are not registered.")
                return
            if update.message.chat.type != "private":
                group_id = update.effective_chat.id
                settings = (group_id,"group",1,0,0.7,0,4)
            prompt = await create_prompt(update, content, user_message, user_id, 0)
            temp_api = list(gemini_api_keys)
            for i in range(len(gemini_api_keys)):
                try:
                    api = random.choice(temp_api)
                    temp_api.remove(api)
                    if(settings[5]):
                        response = await gemini_stream(update, content, prompt, api,settings)
                        if response.prompt_feedback and response.prompt_feedback.block_reason:
                            await update.message.reply_text(f"Your response is blocked by gemini because of {response.prompt_feedback.block_reason} Conversation history is erased.")
                            break
                        next(response).text
                        break
                    else:
                        response = await gemini_non_stream(update, content, prompt, api,settings)
                        if response == False:
                            return
                        if response.prompt_feedback and response.prompt_feedback.block_reason:
                            await update.message.reply_text(f"Your response is blocked by gemini because of {response.prompt_feedback.block_reason} Conversation history is erased.")
                            break
                        response.text
                        break
                except Exception as e:
                    print(f"Error getting gemini response for API-{gemini_api_keys.index(api)}. \n Error Code -{e}")
                    continue
            if response is not None:
                await send_message(update, content, response, user_message, settings)
            elif response != False:
                if os.path.exists(f"Conversation/conversation-{user_id}.txt"):
                    await update.message.reply_text("Failed to process your request. Try again later.")
                    with open(f"Conversation/conversation-{user_id}.txt", "w") as f:
                        pass
                print("Failed to get a response from gemini.")
    except RetryAfter as e:
        await update.message.reply_text(f"Telegram Limit hit, need to wait {e.retry_after} seconds.")
        await send_to_channel(update, content, channel_id, f"Telegram Limit hit for user {user_id}, He need to wait {e.retry_after} seconds.")


#a function to handle resources of cse 24
async def resources_handler(update:Update, content:ContextTypes.DEFAULT_TYPE):
    try:
        keyboard = [
            [InlineKeyboardButton("Drive", url="https://drive.google.com/drive/folders/1xbyCdj3XQ9AsCCF8ImI13HCo25JEhgUJ"), InlineKeyboardButton("Syllabus", url="https://drive.google.com/file/d/1pVF40-E0Oe8QI-EZp9S7udjnc0_Kquav/view?usp=drive_link")],
            [InlineKeyboardButton("Orientation Files", url = "https://drive.google.com/drive/folders/10_-xTV-FsXnndtDiw_StqH2Zy9tQcWq0"), InlineKeyboardButton("Lab Cover Page", url="https://ruet-cover-page.github.io/")],
            [InlineKeyboardButton("G. Classroom Code", callback_data="g_classroom"), InlineKeyboardButton("All Websites", callback_data="c_all_websites")],
            [InlineKeyboardButton("Cancel", callback_data="cancel")]
        ]
        resource_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("All the resources available for CSE SECTION C", reply_markup=resource_markup, parse_mode="Markdown")
    except Exception as e:
        print(f"Error in resource_handler function.\n\nError Code - {e}")
        await update.message.reply_text("Internal Error. Please contact admin or try again later.")



#config info
time_limit = 5
max_request = 5
global_time_limit = 5
global_max_request = 100
user_requests = defaultdict(list)
global_requests = []
banned_users = {}
banned_time = 120

#A function and code block to protect the bot from DDOS
async def is_ddos(update:Update,content:ContextTypes.DEFAULT_TYPE, user_id):
    try:
        now = time.time()

        #start of the main process
        if user_id in banned_users:
            if now - banned_users[user_id] > 120:  # 120 seconds ban
                del banned_users[user_id]
            else:
                await update.message.reply_text(f"You are banned for next {banned_time-(now - banned_users[user_id])} seconds due to spamming.")
                return True
        global_requests[:] = [req for req in global_requests if now - req < global_time_limit]
        global_requests.append(now)
        if len(global_requests) > global_max_request:
            await update.message.reply_text("Global rate exceeded, try again later.")
            return True
        user_requests[user_id][:] = [req for req in user_requests[user_id] if now - req < time_limit]
        user_requests[user_id].append(now)
        if len(user_requests[user_id]) > max_request:
            banned_users[user_id] = now
            await update.message.reply_text(f"Spamming Detected!!!\n\nYou are banned for the next {banned_time} seconds due to spamming.")
            return True
        return False
    except Exception as e:
        print(f"Error in is_ddos function. Error Code - {e}")





#function for all other messager that are directly send to bot without any command
async def echo(update : Update, content : ContextTypes.DEFAULT_TYPE) -> None:
    try:
        bot_name_obj = await content.bot.get_my_name()
        bot_name = bot_name_obj.name.lower()
        user_id = update.effective_user.id
        if await is_ddos(update, content, user_id):
            return
        if user_id not in all_users and update.message.chat.type == "private":
            keyboard = [
                [InlineKeyboardButton("Register", callback_data="c_register"), InlineKeyboardButton("Cancel", callback_data="cancel")]
            ]
            markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("You are not registered.", reply_markup=markup)
            return
        user_name = f"{update.effective_user.first_name or update.effective_user.last_name or "Unknown"}".strip()
        user_message = (update.message.text or "...").strip()
        if (update.message and update.message.chat.type == "private") or (update.message.chat.type != "private" and (f"@{bot_name}" in user_message.lower() or f"{bot_name}" in user_message.lower() or "mama" in user_message.lower() or "@" in user_message.lower() or "bot" in user_message.lower() or "pika" in user_message.lower())):
            await update.message.chat.send_action(action = ChatAction.TYPING)
        if user_message == "Routine" and update.message.chat.type == "private":
            await routine_handler(update, content)
            return
        elif user_message == "Settings" and update.message.chat.type == "private":
            await handle_settings(update, content)
            await update.message.delete()
            return
        elif user_message == "CT" and update.message.chat.type == "private":
            await handle_ct(update, content)
            return
        elif user_message == "Resources" and update.message.chat.type == "private":
            await resources_handler(update, content)
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
        global gemini_api_keys
        user_api = update.message.text.strip()
        await update.message.chat.send_action(action = ChatAction.TYPING)
        try:
            settings = await get_settings(update.effective_user.id)
            response = await gemini_stream(update, content,  "Checking if the gemini api is working or not", user_api, settings)
            chunk = next(response)
            if(
                user_api.startswith("AIza")
                and user_api not in gemini_api_keys
                and " " not in user_api
                and len(user_api) >= 39
                and chunk.text
            ):
                await asyncio.to_thread(db["API"].update_one,
                    {"type" : "api"},
                    {"$push" : {"gemini_api" : user_api}}
                )
                await update.message.reply_text("The API is saved successfully.")
                gemini_api_keys = await asyncio.to_thread(load_gemini_api)
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
        global gemini_api_keys
        chat_id = update.effective_chat.id
        if await is_ddos(update, content, chat_id):
            return
        if update.message.chat.type != "private":
            await update.message.reply_text("This function is only available in private chat.")
            return
        os.makedirs("media",exist_ok=True)
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
            path = f"media/{file_id}.{ext}"
            await photo_file.download_to_drive(path)
            photo = Image.open(path)
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
        os.makedirs("media",exist_ok=True)
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
            path = f"media/{file_name}"
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
                            up_video = client.files.upload(file=path) 
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
        os.makedirs("media",exist_ok=True)
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
            path =  f"media/{file_id}{ext}"
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
                        file = client.files.upload(file=path)
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
        os.makedirs("media",exist_ok=True)
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
            path = f"media/voice-{file_id}.ogg"
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
                        file = client.files.upload(file=path)
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
            os.remove(f"media/voice-{file_id}.ogg")
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
            path = f"media/{file_id}.{ext}"
            file = await sticker.get_file()
            os.makedirs("media", exist_ok=True)
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
        os.makedirs("media", exist_ok=True)
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
                ".yml"
            ]
            print(os.path.splitext(os.path.basename(file_name))[1])
            if os.path.splitext(os.path.basename(file_name))[1] not in valid_ext:
                await message.edit_text("Unsupported Format...")
                return
            file_id = update.message.document.file_unique_id
            mime = update.message.document.mime_type
            if mime == "application/pdf":
                path = f"media/{file_name}" if file_name else f"media/{file_id}.pdf"
            elif mime=="application/json":
                path = f"media/{file_name}" if file_name else f"media/{file_id}.json"
            else:
                path = f"media/{file_name}" if file_name else f"media/{file_id}.txt"
            doc_file = await update.message.document.get_file()
            await doc_file.download_to_drive(path)
            if not os.path.exists(path):
                await update.message.reply_text("Invalid file.")
                return

            await message.edit_text("🤖 Analyzing document...\nThis may take a while ⏳")
            def gemini_doc_worker(caption, path):
                if os.path.getsize(path)/(1024*1024) > 15:
                    return "File size is too long for free tier. Contact admin to activate premium subscription."
                temp_api = list(gemini_api_keys)
                for api_key in temp_api:
                    try:
                        client = genai.Client(api_key=api_key)
                        u_doc = client.files.upload(file=path)
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
        user_id = update.effective_chat.id
        with open(f"memory/memory-{update.callback_query.from_user.id}.txt", "w") as f:
            pass
        await asyncio.to_thread(db[f"{user_id}"].update_one,
            {"id" : user_id},
            {"$set" : {"memory" : None}}
        )
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
            [InlineKeyboardButton("Conversation History", callback_data="c_conv_history"), InlineKeyboardButton("Memory", callback_data="c_memory")],
            [InlineKeyboardButton("cancel", callback_data="cancel")]
        ]
        settings_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("You can change the bot configuration from here.\nBot Configuration Menu:", reply_markup=settings_markup)
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






#a function for admin call
async def admin_handler(update : Update, content : ContextTypes.DEFAULT_TYPE) -> None:
    try:
        user_id = update.effective_user.id
        if update.message.chat.type != "private":
            await update.message.reply_text("Sorry, This is not available for group.")
            return
        if user_id in all_admins:
            keyboard = [
                [InlineKeyboardButton("Circulate CT Routine", callback_data="c_circulate_ct"), InlineKeyboardButton("Take Attendance", callback_data="c_take_attendance")],
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
        query = update.callback_query
        await query.answer()
        content.user_data["circulate_message_query"] = query.data
        keyboard = [[InlineKeyboardButton("Cancel", callback_data="cancel_conv")]]
        mt_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text("Enter the message here:", reply_markup=mt_markup)
        return "CM"
    except Exception as e:
        print(f"Error in message_taker function.\n\nError Code -{e}")
        await query.edit_message_text(f"Internal Error - {e}.\n\n. Please try again later or contact admin.")
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
        await update.message.reply_text(f"Internal Error - {e}.\n\n. Please try again later or contact admin.")
        return ConversationHandler.END


#function to create background task for circulate message
async def handle_circulate_message(update:Update, content:ContextTypes.DEFAULT_TYPE) -> None:
    try:
        asyncio.create_task(circulate_message(update, content))
        return ConversationHandler.END
    except Exception as e:
        print(f"Error in handle_circulate_message function.\n\nError Code -{e}")
        await update.message.reply_text(f"Internal Error - {e}.\n\n. Please try again later or contact admin.")
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
        await update.message.reply_text(f"Internal Error - {e}.\n\n. Please try again later or contact admin.")
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
        await update.message.reply_text(f"Internal Error - {e}.\n\n. Please try again later or contact admin.")
        return ConversationHandler.END


#function to add or delete admin
async def add_or_delete_admin(update:Update, content:ContextTypes.DEFAULT_TYPE) -> None:
    try:
        global all_admins
        user_id = int(update.message.text.strip())
        action = content.user_data.get("admin_action")
        msg_id = content.user_data.get("aa_message_id")
        await content.bot.delete_message(chat_id=update.effective_chat.id, message_id=msg_id)
        global all_admins
        if action == "add_admin":
            if user_id not in all_admins:
                await asyncio.to_thread(
                    db["admin"].update_one, 
                    {"type" : "admin"},
                    {"$push" : {"admin" : user_id}}
                )
                await update.message.reply_text(f"Successfully added {user_id} user_id as Admin.")
                all_admins = await asyncio.to_thread(load_admin)
            else:
                await update.message.reply_text(f"{user_id} is already an Admin.")
            return ConversationHandler.END
        elif action == "delete_admin":
            if user_id in all_admins or str(user_id) in all_admins:
                try:
                    await asyncio.to_thread(
                        db["admin"].update_one, 
                        {"type" : "admin"},
                        {"$pull" : {"admin" : user_id}}
                    )
                except:
                    await asyncio.to_thread(
                        db["admin"].update_one, 
                        {"type" : "admin"},
                        {"$pull" : {"admin" : str(user_id)}}
                    )
                await update.message.reply_text(f"Successfully deleted {user_id} from admin.")
                all_admins = await asyncio.to_thread(load_admin)
            else:
                await update.message.reply_text(f"{user_id} is not an Admin.")
            return ConversationHandler.END
    except Exception as e:
        print(f"Error in add_or_delete_admin function.\n\nError Code -{e}")
        await update.message.reply_text(f"Internal Error - {e}.\n\n. Please try again later or contact admin.")
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
        await update.message.reply_text(f"Internal Error - {e}.\n\n. Please try again later or contact admin.")
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
        await update.message.reply_text(f"Internal Error - {e}.\n\n. Please try again later or contact admin.")
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
        await update.message.reply_text(f"Internal Error - {e}.\n\n. Please try again later or contact admin.")
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
                conn = sqlite3.connect("info/user_data.db")
                cursor = conn.cursor()
                cursor.execute("SELECT roll FROM users")
                roll = int(roll)
                rows = cursor.fetchall()
                all_rolls = tuple(row[0] for row in rows)
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
                if roll in all_rolls:
                    content.user_data["roll"] = roll
                    await update.message.reply_text("This account already exists.\n\nPlease enter your password to login:")
                    return "TUP"
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
        await update.message.reply_text(f"Internal Error - {e}.\n\n. Please try again later or contact admin.")
        return ConversationHandler.END


#function to take user password for login or confidential report
async def take_user_password(update:Update, content:ContextTypes.DEFAULT_TYPE) -> None:
    try:
        user_password = update.message.text.strip()
        conn = sqlite3.connect("info/user_data.db")
        cursor = conn.cursor()
        cursor.execute("SELECT password FROM users WHERE roll = ?", (content.user_data.get("roll"),))
        password = cursor.fetchone()[0]
        if user_password == password:
            keyboard = [[InlineKeyboardButton("Skip", callback_data="c_skip"),InlineKeyboardButton("Cancel",callback_data="cancel_conv")]]
            markup = InlineKeyboardMarkup(keyboard)
            with open("info/getting_api.shadow", "rb") as file:
                help_data = add_escape_character(fernet.decrypt(file.read()).decode("utf-8"))
                msg = await update.message.reply_text(help_data, reply_markup=markup, parse_mode="MarkdownV2")
            content.user_data["ra_message_id"] = msg.message_id
            await content.bot.delete_message(chat_id=update.effective_user.id, message_id=content.user_data.get("tg_message_id"))
            await update.message.delete()
            content.user_data["guest"] = True
            return "AH"
        else:
            await update.message.reply_text("Wrong Password..\n\nIf you are having problem contact admin. Or mail here: shadow_mist0@proton.me")
            return ConversationHandler.END
    except Exception as e:
        print(f"Error in take_user_password function.\n\nError Code - {e}")
        await update.message.reply_text("Internal Error. Please contact admin or Try Again later.")


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
        await query.edit_message_text(f"Internal Error - {e}.\n\n. Please try again later or contact admin.")
        return ConversationHandler.END


#function to take api
async def handle_api_conv(update : Update, content : ContextTypes.DEFAULT_TYPE) -> None:
    try:
        global gemini_api_keys
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
                and user_api not in gemini_api_keys
                and " " not in user_api
                and len(user_api) >= 39
                and response.text
            ):
                await asyncio.to_thread(db["API"].update_one,
                    {"type" : "api"},
                    {"$push" : {"gemini_api" : user_api}}
                )
                msg = await update.message.reply_text("The API is saved successfully.\nSet you password:", reply_markup=markup)
                gemini_api_keys = await asyncio.to_thread(load_gemini_api)
                content.user_data["user_api"] = user_api
                await content.bot.delete_message(chat_id=update.effective_user.id, message_id=content.user_data.get("ra_message_id"))
                await update.message.delete()
                content.user_data["hac_message_id"] = msg.message_id
                return "TP"
            elif user_api in gemini_api_keys:
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
        await update.message.reply_text(f"Internal Error - {e}.\n\n. Please try again later or contact admin.")
        return ConversationHandler.END


#function to confirm user password
async def confirm_password(update:Update, content:ContextTypes.DEFAULT_TYPE):
    try:
        all_persona = [os.path.splitext(os.path.basename(persona))[0] for persona in sorted(glob("persona/*txt"))]
        is_guest = content.user_data.get("guest")
        keyboard = [
            ["Routine", "CT"],
            ["Settings", "Resources"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False, selective=False, is_persistent=True)
        c_password = update.message.text.strip()
        password = content.user_data.get("password")
        if password == c_password:
            try:
                conn = sqlite3.connect("info/user_data.db")
                cursor = conn.cursor()
                if is_guest:
                    user_info = [
                        update.effective_user.id,
                        content.user_data.get("user_name"),
                        content.user_data.get("gender"),
                        0,
                        content.user_data.get("password"),
                        content.user_data.get("user_api")
                    ]
                else:
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
                persona = all_persona.index("Pikachu") if user_info[2] == "male" else all_persona.index("Aarohi")
                data = {
                    "id" : user_info[0],
                    "name" : user_info[1],
                    "memory" : None,
                    "conversation" : None,
                    "settings" : (user_info[0], user_info[1], 1, 0, 0.7, 0, persona),
                    "user_data" : user_info
                }
                await asyncio.to_thread(
                    db[f"{user_info[0]}"].insert_one,
                    data
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
                (user_info[0], user_info[1], 1, 0, 0.7, 0, persona)
                )
                conn.commit()
                conn.close()
                global all_users
                all_users = await asyncio.to_thread(load_all_user)
                if user_info[3] == 0:
                    await update.message.reply_text("You have been registered as a guest with limited functionality.", reply_markup=reply_markup)
                else:
                    await update.message.reply_text("Registration Seccessful. Now press /start", reply_markup=reply_markup)
                await content.bot.delete_message(chat_id = update.effective_user.id, message_id=content.user_data.get("tp_message_id"))
                await update.message.delete()
            except Exception as e:
                print(f"Error adding user.\n\nError code - {e}")
            if content.user_data.get("from_totp") == "true":
                del content.user_data["from_totp"]
                keyboard = [
                    [InlineKeyboardButton("Mark Attendance", callback_data="c_mark_attendance")]
                ]
                markup = InlineKeyboardMarkup(keyboard)
                if os.path.exists("info/active_attendance.txt"):
                    message = await update.message.reply_text("Redirecting to attendance circular.\n please wait...", reply_markup=markup)
                    user_message_id[f"{update.effective_user.id}"] = message.message_id
                else:
                    await update.message.reply_text("Time limit is over for attendance, please contact admin.")
            return ConversationHandler.END
        else:
            await update.message.reply_text("Passwords are not identical. Try again later.")
            await content.bot.delete_message(chat_id = update.effective_user.id, message_id=content.user_data.get("tp_message_id"))
            await update.message.delete()
    except Exception as e:
        print(f"Error in confirm_password function.\n\nError Code -{e}")
        await update.message.reply_text(f"Internal Error - {e}.\n\n. Please try again later or contact admin.")
        return ConversationHandler.END
 
    

#function to enter temperature conversation
async def temperature(update:Update, content:ContextTypes.DEFAULT_TYPE):
    try:
        settings = await get_settings(update.effective_user.id)
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
        await query.edit_message_text(f"Internal Error - {e}.\n\n. Please try again later or contact admin.")
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
            await asyncio.to_thread(
                db[f"{user_id}"].update_one,
                    {"id" : user_id},
                    {"$set" : {"settings.4":data}}
            )
            await update.message.reply_text(f"Temperature is successfully set to {data}.")
            await content.bot.delete_message(chat_id=user_id, message_id=content.user_data.get("t_message_id"))
            await update.message.delete()
            return ConversationHandler.END
    except Exception as e:
        print(f"Error in take_temperature function.\n\nError Code -{e}")
        await update.message.reply_text(f"Internal Error - {e}.\n\n. Please try again later or contact admin.")
        return ConversationHandler.END
        

#function to enter thinking conversation
async def thinking(update:Update, content:ContextTypes.DEFAULT_TYPE):
    try:
        settings = await get_settings(update.effective_user.id)
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
        await query.edit_message_text(f"Internal Error - {e}.\n\n. Please try again later or contact admin.")
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
            settings = await get_settings(update.effective_user.id)
            conn = sqlite3.connect("settings/user_settings.db")
            cursor = conn.cursor()
            if gemini_model_list[settings[2]] != "gemini-2.5-pro":
                cursor.execute("UPDATE user_settings SET thinking_budget = ? WHERE id = ?", (data, user_id))
                conn.commit()
                conn.close()
                await asyncio.to_thread(
                    db[f"{user_id}"].update_one,
                        {"id" : user_id},
                        {"$set" : {"settings.3":data}}
                )
                await update.message.reply_text(f"Thinking Budget is successfully set to {data}.")
                await content.bot.delete_message(chat_id=user_id, message_id=content.user_data.get("t_message_id"))
                await update.message.delete()
                return ConversationHandler.END
            else:
                data = data if data>=128 else 1024
                cursor.execute("UPDATE user_settings SET thinking_budget = ? WHERE id = ?", (data, user_id))
                conn.commit()
                conn.close()
                await asyncio.to_thread(
                db[f"{user_id}"].update_one,
                        {"id" : user_id},
                        {"$set" : {"settings.3":data}}
                )
                await update.message.reply_text(f"Thinking Budget is successfully set to {data}. Gemini 2.5 pro only works with thinking budget greater than 128.")
                await content.bot.delete_message(chat_id=user_id, message_id=content.user_data.get("t_message_id"))
                await update.message.delete()
                return ConversationHandler.END
    except Exception as e:
        print(f"Error in take_thinking function.\n\nError Code -{e}")
        await update.message.reply_text(f"Internal Error - {e}.\n\n. Please try again later or contact admin.")
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
        await update.message.reply_text(f"Internal Error - {e}.\n\n. Please try again later or contact admin.")
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
                    client = genai.Client(api_key=gemini_api_keys[-1])
                    response = client.models.generate_content(
                    model = data,
                    contents = "hi, respond in one word.",
                    )
                    response.text
                    await asyncio.to_thread(db["ai_model"].update_one,
                        {"type" : "gemini_model_name"},
                        {"$push" : {"model_name" : data}}
                    )
                    await update.message.reply_text(f"{data} added successfully as a model.")
                except Exception as e:
                    await update.message.reply_text(f"Invalid Model Name.\n\nError Code - {e}")
                gemini_model_list = await asyncio.to_thread(load_gemini_model)
            elif data in gemini_model_list:
                await update.message.reply_text("The model name is already registered.")
            else:
                await update.message.reply_text("The model name is invalid.")
        elif action == "c_delete_model":
            if data not in gemini_model_list:
                await update.message.reply_text(f"Sorry there is no model named {data}")
            else:
                await asyncio.to_thread(db["ai_model"].update_one,
                        {"type" : "gemini_model_name"},
                        {"$pull" : {"model_name" : data}}
                    )
                gemini_model_list = await asyncio.to_thread(load_gemini_model)
                await update.message.reply_text(f"The model named {data} is deleted successfully")
        await content.bot.delete_message(chat_id=update.effective_user.id, message_id=content.user_data.get("mm_message_id"))
        await update.message.delete()
        return ConversationHandler.END
    except Exception as e:
        print(f"Error in take_model_name function.\n\nError Code -{e}")
        await update.message.reply_text(f"Internal Error - {e}.\n\n. Please try again later or contact admin.")
        return ConversationHandler.END


#function to take attendance detail
async def take_attendance_detail(update:Update, content:ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        keybaord = [
            [InlineKeyboardButton("Cancel", callback_data="cancel_conv")]
        ]
        markup = InlineKeyboardMarkup(keybaord)
        msg = await query.edit_message_text("Enter the teacher name:", reply_markup=markup)
        content.user_data["tad_msg_id"] = msg.message_id
        return "TTN"
    except Exception as e:
        print(f"Error in take_attendance function.\n\nError code - {e}")
        return ConversationHandler.END


#function to take teachers name
async def take_teachers_name(update:Update, content:ContextTypes.DEFAULT_TYPE):
    try:
        name = update.message.text.strip()
        if name.isdigit():
            await update.message.reply_text("Operation Failed. \nName should not contain only number.")
            return ConversationHandler.END
        keybaord = [
            [InlineKeyboardButton("Cancel", callback_data="cancel_conv")]
        ]
        markup = InlineKeyboardMarkup(keybaord)
        msg = await update.message.reply_text("Enter the subject name:", reply_markup=markup)
        content.user_data["ttn_msg_id"] = msg.message_id
        content.user_data["teacher"] = name
        return "TSN"
    except Exception as e:
        print(f"Error in take_teachers_name function. Error Code - {e}")
        await update.message.reply_text("Internal Error. Contact admin or try again later.")
        return ConversationHandler.END
    

#function to take subjet name for attendance
async def take_subject_name(update:Update, content:ContextTypes.DEFAULT_TYPE):
    try:
        name = update.message.text.strip()
        if name.isdigit():
            await update.message.reply_text("Operation Failed. \nSubject name should not contain only number.")
            return ConversationHandler.END
        keybaord = [
            [InlineKeyboardButton("Cancel", callback_data="cancel_conv")]
        ]
        markup = InlineKeyboardMarkup(keybaord)
        msg = await update.message.reply_text("Enter the time limit as seconds, Make sure to give only number: ", reply_markup=markup)
        content.user_data["tsn_msg_id"] = msg.message_id
        content.user_data["subject"] = name
        return "TTL"
    except Exception as e:
        print(f"Error in take_subject_name function. Error Code - {e}")
        await update.message.reply_text("Internal Error. Contact admin or try again later.")
        return ConversationHandler.END


#function to take time limit for attendance
async def take_time_limit(update:Update, content:ContextTypes.DEFAULT_TYPE):
    try:
        ikeyboard = [
            [InlineKeyboardButton("Cancel", callback_data="cancel_conv")]
        ]
        limit = update.message.text.strip()
        if not limit.isdigit():
            await update.message.reply_text("Operation Failed. \nTime limit should only contain number.")
            return ConversationHandler.END
        imarkup = InlineKeyboardMarkup(ikeyboard)
        rkeyboard = [
            [KeyboardButton("Give location", request_location=True)]
        ]
        rmarkup = ReplyKeyboardMarkup(rkeyboard, resize_keyboard=True, is_persistent=True, selective=False, one_time_keyboard=True)
        content.user_data["time_limit"] = limit
        msg0 = await update.message.reply_text("Please give location to verify user attendance.", reply_markup=rmarkup)
        msg = await update.message.reply_text("Attendance will be allowed within 200 meter radius.", reply_markup=imarkup)
        content.user_data["ttl_msg0_id"] = msg0.message_id 
        content.user_data["ttl_msg_id"] = msg.message_id
        return "TL"
    except Exception as e:
        print(f"Error in take_time_limit function. Error Code - {e}")
        await update.message.reply_text("Internal Error. Contact admin or try again later.")
        return ConversationHandler.END
    

#function to handle attendace by given location
async def take_location(update:Update, content:ContextTypes.DEFAULT_TYPE):
    try:
        message = update.message or update.edited_message
        keyboard = [
            ["Routine", "CT"],
            ["Settings", "Resources"]
        ]
        markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False, selective=False, is_persistent=True)
        if message.location:
            location = update.message.location
        msg = await message.reply_text("Location Recieved Successfully. Please wait while bot is sending the attendance circular.", reply_markup = markup)

        #extea processing here
        date = datetime.today().strftime("%d-%m-%Y")
        collection = db[f"Attendance-{date}"]
        await content.bot.delete_message(chat_id=update.effective_user.id, message_id=content.user_data.get("tad_msg_id"))
        await content.bot.delete_message(chat_id=update.effective_user.id, message_id=content.user_data.get("ttn_msg_id"))
        await content.bot.delete_message(chat_id=update.effective_user.id, message_id=content.user_data.get("tsn_msg_id"))
        await content.bot.delete_message(chat_id=update.effective_user.id, message_id=content.user_data.get("ttl_msg_id"))
        await content.bot.delete_message(chat_id=update.effective_user.id, message_id=content.user_data.get("ttl_msg0_id"))
        teacher = content.user_data.get("teacher")
        subject = content.user_data.get("subject")
        limit = int(content.user_data.get("time_limit"))
        data = {
            "type" : f"attendance-{date}",
            "teacher" : teacher,
            "subject" : subject,
            "present" : [],
            "absent" : [],
            "distance" : []
        }
        with open(f"info/location-{date}-{subject}.txt", "w") as f:
            f.write(f"{location.latitude}\n{location.longitude}")
        with open("info/active_attendance.txt", "w") as f:
            f.write(f"{subject}-{teacher}")
        collection.insert_one(data)
        content.user_data["message_id"] = msg.message_id
        asyncio.create_task(circulate_attendance(update, content, teacher, subject, limit))
        asyncio.create_task(delete_attendace_circular(update, content, limit))
        return ConversationHandler.END
    except Exception as e:
        print(f"Error in take_location function. Error Code - {e}")
        await update.message.reply_text("Internal Error. Contact admin or try again later.")
        return ConversationHandler.END



user_message_id = {}



#function to circulate attendance to all 60 user
async def circulate_attendance(update:Update, content:ContextTypes.DEFAULT_TYPE, teacher, subject, limit):
    try:
        rkeyboard = [
            ["Routine", "CT"],
            ["Settings", "Resources"]
        ]
        rmarkup = ReplyKeyboardMarkup(rkeyboard, resize_keyboard=True, one_time_keyboard=False, selective=False, is_persistent=True)
        await content.bot.delete_message(chat_id=update.effective_user.id, message_id=content.user_data.get("message_id"))
        message = await update.message.reply_text("The attendace circular has been circulated successfully. Please wait the time limit to end..", reply_markup=rmarkup)
        all_student = tuple(db["all_user"].find_one({"type":"all_user"})["users"])
        all_students = all_users if len(all_users) > len(all_student) else all_student
        failed = 0
        tasks = []
        user_id = update.effective_user.id
        failed_list = "FAILED TO SEND ATTENDANCE TO THOSE USER:\n"
        keyboard = [
            [InlineKeyboardButton("Mark Attendance", callback_data="c_mark_attendance")]
        ]
        markup = InlineKeyboardMarkup(keyboard)
        data = (
            "📢 *IMPORTANT NOTICE*\n"
            f"📋 *Attendance*:\n"
            f"👨‍🏫 Teacher: {teacher}\n"
            f"📚 Subject: {subject}\n"
            f"⏳ Please mark your attendance in {limit} seconds!"
        )
        async def send_attendance(student):
            nonlocal failed, failed_list
            try:
                if int(student) != user_id:
                    msg = await content.bot.send_message(chat_id=student, text=data, reply_markup=markup, parse_mode="Markdown")
                    user_message_id[f"{student}"] = msg.message_id
                    return True
                else:
                    return True
            except Exception as e:
                print(e)
                failed += 1
                failed_list += f"{student}\n"
                return False
            
        for student in all_students:
            tasks.append(send_attendance(student))
            
        results = await asyncio.gather(*tasks)
        sent = sum(results)
        report = (
                f"📋 Attendance Circular sent to {sent} users\n"
                f"⚠️ Failed to send to {failed} users\n"
            )
        await update.message.reply_text(report, reply_markup=rmarkup)
        await content.bot.delete_message(chat_id=user_id, message_id=message.message_id)
        if failed != 0:
            await update.message.reply_text(failed_list)
            msg = await update.message.reply_text(data, reply_markup=markup, parse_mode="Markdown")
            user_message_id[f"{user_id}"] = msg.message_id
        else:
            msg = await update.message.reply_text(data, reply_markup=markup, parse_mode="Markdown")
            user_message_id[f"{user_id}"] = msg.message_id
    except Exception as e:
        print(f"Error in circulate_attendance function. Error Code - {e}")
        await update.message.reply_text("Internal Error. Contact admin or try again later.")
        return ConversationHandler.END


async def delete_attendace_circular(update:Update, content:ContextTypes.DEFAULT_TYPE, limit):
    try:
        await asyncio.sleep(limit+5)
        for key, value in user_message_id.items():
            try:
                await content.bot.delete_message(chat_id=int(key), message_id=value)
            except Exception as e:
                print(e)
        asyncio.create_task(process_attendance_data(update, content))
    except Exception as e:
        print(f"Error in delete_attendance_circular function.\n\nError Code - {e}")
        return ConversationHandler.END


#function to prepare pdf to send attendance data
async def process_attendance_data(update:Update, content:ContextTypes.DEFAULT_TYPE):
    try:
        message = await update.message.reply_text("Processing data...\nPlease wait...")
        os.makedirs("media", exist_ok=True)
        all_rolls = [roll for roll in range(2403121, 2403181)]
        date = datetime.today().strftime("%d-%m-%Y")
        with open("info/active_attendance.txt", "r") as f:
            list = f.read().split("-")
        present_students = tuple(db[f"Attendance-{date}"].find_one({"type" : f"attendance-{date}", "teacher" : f"{list[1]}", "subject" : f"{list[0]}"})["present"])
        student_data = db["names"].find_one({"type" : "official_data"})["data"]
        conn = sqlite3.connect("info/user_data.db")
        cursor = conn.cursor()
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=10, style="B")
        pdf.cell(190,5,"ATTENDANCE SHEET",ln=1, align="C")
        pdf.set_font("Arial",size=10,style="B")
        pdf.cell(62, 5, f"Date: {date}", align="L")
        pdf.cell(62, 5, f"Subject: {list[0]}", align="C")
        pdf.cell(62, 5, f"Teacher: {list[1]}",ln=1,align="R")
        pdf.set_font("Arial", size=8)
        pdf.cell(10,4,"SI", border=1)
        pdf.cell(60,4,"Roll", border=1)
        pdf.cell(60,4,"Name", border=1)
        pdf.cell(60,4,"Status", border=1, ln=1)
        for roll in all_rolls:
            if roll in present_students:
                pdf.set_text_color(0,0,0)
                pdf.cell(10,4,f"{roll-2403120}", border=1)
                pdf.cell(60,4,f"{roll}", border=1)
                try:
                    name = student_data[str(roll)][0]
                except:
                    name = "Unknown"
                pdf.cell(60,4,name, border=1)
                pdf.cell(60,4,"Present", border=1, ln=1)
            else:
                pdf.set_text_color(255,0,0)
                pdf.cell(10,4,f"{roll-2403120}", border=1)
                pdf.cell(60,4,f"{roll}", border=1)
                try:
                    name = student_data[str(roll)][0]
                except:
                    name = "Unknown"
                pdf.cell(60,4,name, border=1)
                pdf.cell(60,4,"Absent", border=1, ln=1)
        pdf.set_text_color(0,0,0)
        pdf.set_font("Arial", size=10, style="B")
        pdf.cell(190, 4, ln=1)
        pdf.cell(25, 6, "Present", border=1, align="C")
        pdf.cell(70, 6, f"{len(present_students)}      ({round((len(present_students)/60)*100, 2)}%)",border=1,align="C")
        pdf.cell(25, 6, "Absent", border=1 , align="C")
        pdf.cell(70, 6, f"{60 - len(present_students)}      ({round(((60 - len(present_students))/60)*100, 2)}%)", border=1, align="C")
        pdf.output(f"media/attendance-{date}-{list[0]}.pdf")
        with open(f"media/attendance-{date}-{list[0]}.pdf", "rb") as f:
            pdf_file = BytesIO(f.read())
            pdf_file.name = f"attendance-{date}-{list[0]}.pdf"
        for admin in all_admins:
            try:
                await content.bot.send_document(chat_id=admin, document=pdf_file, caption=f"Attendance sheet of {list[0]} by {list[1]} for {date}")
            except:
                pdf_file.seek(0)
                print(f"Admin-{admin} not found to send document")
            try:
                await content.bot.delete_message(chat_id=update.effective_user.id, message_id=message.message_id)
            except:
                pass
        try:
            if os.path.exists("info/active_attendance.txt"):
                os.remove("info/active_attendance.txt")
            if os.path.exists(f"info/location-{date}-{list[0]}.txt"):
                os.remove(f"info/location-{date}-{list[0]}.txt")
            if os.path.exists(f"media/attendance-{date}-{list[0]}.pdf"):
                os.remove(f"media/attendance-{date}-{list[0]}.pdf")
        except:
            pass
    except Exception as e:
        print(f"Error in process_attendance_data function.\n\nError Code - {e}")
        return ConversationHandler.END


#function to cancel conversation by cancel button
async def cancel_conversation(update: Update, content: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        await update.callback_query.delete_message()
        return ConversationHandler.END
    except Exception as e:
        print(f"Error in cancel_conversation function.\n\nError Code -{e}")
        await update.message.reply_text(f"Internal Error - {e}.\n\n. Please try again later or contact admin.")
        return ConversationHandler.END
    

#function to take location from user to validate the attendance
async def take_user_location(update:Update, content:ContextTypes.DEFAULT_TYPE):
    try:
        location_help = (
            "1. Turn on location service on your device\n"
            "2. Go to the attachment option\n"
            "3. Go to the location option\n"
            "4. Press 'Share My Live Location for...'\n"
            "5. Press share"
        )
        user_id = update.effective_user.id
        if user_id not in all_users:
            keyboard = [
                [InlineKeyboardButton("Register", callback_data="c_register"), InlineKeyboardButton("Cancel", callback_data="cancel")]
            ]
            markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("You are not registerd yet.", reply_markup=markup)
            content.user_data["from_totp"] = "true"
            return ConversationHandler.END
        if update.callback_query:
            query = update.callback_query
            await query.answer()
            await query.edit_message_text(f"Share your location to verify the attendance, Follow the steps below:\n\n{location_help}")
            return "VL"
        else:
            await update.message.reply_text(f"Follow the steps below:\n\n{location_help}")
            return "VL"
    except Exception as e:
        print(f"Error in take_user_location function.\n\nError Code -{e}")
        return ConversationHandler.END


#function to verify user location for attendance
async def verify_user_location(update:Update, content:ContextTypes.DEFAULT_TYPE):
    try:
        date = datetime.today().strftime("%d-%m-%Y")
        with open("info/active_attendance.txt", "r") as f:
            list = f.read().split("-")
        try:
            with open(f"info/location-{date}-{list[0]}.txt") as file:
                cr_location = (loc.strip() for loc in file.readlines())
        except Exception as e:
            print("The location file may not exists")
            return ConversationHandler.END
        message = update.message or update.edited_message
        if not message.location:
            await message.reply_text("Enter your location not some random message.")
            if os.path.exists(f"info/location-{date}-{list[0]}.txt"):
                return "VL"
            else:
                await message.reply_text("Time limit exceded, Contact CR if you are facing problem.")
                return ConversationHandler.END
        elif not message.location.live_period:
            await message.reply_text("Sorry static location will not work, give a live location.")
            if os.path.exists(f"info/location-{date}-{list[0]}.txt"):
                return "VL"
            else:
                await message.reply_text("Time limit exceded, Contact CR if you are facing problem.")
                return ConversationHandler.END
        if message.location and message.location.live_period:
            location = message.location
            message_time = message.date.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            message_age = (now - message_time).total_seconds()
            if message_age > 20:
                await message.reply_text("Sorry scammig is not allowed. Your location is not fresh. If there is an acitve live location sharing stop it and try again.")
                return "VL"
            if message_age < 20:
                user_location = (location.latitude, location.longitude)
                user_id = update.effective_user.id
                conn = sqlite3.connect("info/user_data.db")
                cursor = conn.cursor()
                cursor.execute("SELECT name, roll FROM users WHERE user_id = ?", (user_id,))
                info = cursor.fetchone()
                user_roll = info[1]
                conn.close()
                

                #logic to handle the location difference
                allowed_distance = 200
                distance = geodesic(cr_location, user_location).meters
                if distance >= allowed_distance:
                    await message.reply_text(f"You are not allowed to take the attendance as you are {distance} meters away from CR. If you are facing problem contact admin")
                    return ConversationHandler.END
                elif user_roll == 0:
                    await message.reply_text(f"Guest member are not allowed to take attendance.")
                else:
                    collection = db[f"Attendance-{date}"]
                    collection.update_one(
                        {"type" : f"attendance-{date}", "teacher" : f"{list[1]}", "subject" : f"{list[0]}"},
                        {"$push" : {"present" : user_roll}}
                    )
                    collection.update_one(
                        {"type" : f"attendance-{date}", "teacher" : f"{list[1]}", "subject" : f"{list[0]}"},
                        {"$push" : {"distance" : {f"{user_roll}" : distance}}}
                    )
                    await message.reply_text(f"Name: {info[0]}\nRoll: {info[1]}\nYour attendance submitted successfully.\n\nIf you are seeing wrong information here please contact admin.")
                    return ConversationHandler.END
        else:
            return ConversationHandler.END
    except Exception as e:
        print(f"Error in verify_user_location functin.\n\n Error Code - {e}")
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
        settings = await get_settings(user_id)
        c_model = tuple(model for model in gemini_model_list)
        personas = sorted(glob("persona/*txt"))
        c_persona = [os.path.splitext(os.path.basename(persona))[0] for persona in personas]
        c_persona.remove("memory_persona")

        if query.data == "c_model":
            keyboard = []
            for i in range(0, len(gemini_model_list), 2):
                row =[]
                row.append(InlineKeyboardButton(text=gemini_model_list[i], callback_data=gemini_model_list[i]))
                if i+1 < len(gemini_model_list):
                    row.append(InlineKeyboardButton(text=gemini_model_list[i+1], callback_data=gemini_model_list[i+1]))
                keyboard.append(row)
            keyboard.append([InlineKeyboardButton("Cancel", callback_data="cancel")])
            model_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(f"Current Model: {gemini_model_list[settings[2]]}\nChoose a model:", reply_markup=model_markup, parse_mode="Markdown")

        elif query.data == "c_streaming":
            keyboard = [
                [InlineKeyboardButton("ON", callback_data="c_streaming_on"), InlineKeyboardButton("OFF", callback_data="c_streaming_off")]    
            ]
            markup = InlineKeyboardMarkup(keyboard)
            settings = await get_settings(user_id)
            c_s = "ON" if settings[5] == 1 else "OFF"
            await query.edit_message_text(f"Streaming let you stream the bot response in real time.\nCurrent setting : {c_s}", reply_markup=markup)

        elif query.data == "c_streaming_on":
            conn = sqlite3.connect("settings/user_settings.db")
            cursor = conn.cursor()
            cursor.execute("UPDATE user_settings SET streaming = ? WHERE id = ?", (1, user_id))
            conn.commit()
            conn.close()
            await asyncio.to_thread(
                db[f"{user_id}"].update_one,
                    {"id" : user_id},
                    {"$set" : {"settings.5":1}}
            )
            await query.edit_message_text("Streaming has turned on.")

        elif query.data == "c_streaming_off":
            conn = sqlite3.connect("settings/user_settings.db")
            cursor = conn.cursor()
            cursor.execute("UPDATE user_settings SET streaming = ? WHERE id = ?", (0, user_id))
            conn.commit()
            conn.close()
            await asyncio.to_thread(
                db[f"{user_id}"].update_one,
                    {"id" : user_id},
                    {"$set" : {"settings.5":0}}
            )
            await query.edit_message_text("Streaming has turned off.")

        elif query.data == "c_persona":
            personas = sorted(glob("persona/*txt"))
            conn = sqlite3.connect("info/user_data.db")
            cursor = conn.cursor()
            cursor.execute("SELECT gender FROM users WHERE user_id = ?", (query.from_user.id, ))
            gender = cursor.fetchone()[0]
            if gender == "female":
                try:
                    c_persona.remove("Maria")
                except Exception as r:
                    print(f"Error in c_data part. Error Code - {e}")
            settings = await get_settings(user_id)
            keyboard = []
            for i in range(0, len(c_persona), 2):
                row = []
                name = c_persona[i]
                if name != "memory_persona":
                    row.append(InlineKeyboardButton(text=name, callback_data=name))
                if i+1 < len(c_persona):
                    name = c_persona[i+1]
                    row.append(InlineKeyboardButton(text = name, callback_data=name))
                keyboard.append(row)
            keyboard.append([InlineKeyboardButton("Cancel", callback_data="cancel")])
            markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(f"Persona will shape your bot response as personality.\n\nCurrent Persona: {os.path.splitext(os.path.basename(personas[settings[6]]))[0]}\n\nIt is recommended not to change the persona. Choose an option:", reply_markup=markup, parse_mode="Markdown")

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
            model_num = c_model.index(query.data)
            if gemini_model_list[model_num] != "gemini-2.5-pro":
                cursor.execute("UPDATE user_settings SET model = ? WHERE id = ?", (model_num, user_id))
                conn.commit()
                conn.close()
                await asyncio.to_thread(
                db[f"{user_id}"].update_one,
                        {"id" : user_id},
                        {"$set" : {"settings.2":model_num}}
                )
                await query.edit_message_text(f"AI model is successfully changed to {gemini_model_list[model_num]}.")
            elif gemini_model_list[model_num] == "gemini-2.5-pro":
                cursor.execute("UPDATE user_settings SET model = ?, thinking_budget = ? WHERE id = ? AND thinking_budget = 0", (model_num, 1024, user_id))
                conn.commit()
                conn.close()
                await asyncio.to_thread(
                db[f"{user_id}"].update_one,
                        {"id" : user_id},
                        {"$set" : {"settings.2":model_num, "settings.3" : 1024}}
                )
                await query.edit_message_text(f"AI model is successfully changed to {gemini_model_list[model_num]}.")

        elif query.data in c_persona:
            conn = sqlite3.connect("settings/user_settings.db")
            cursor = conn.cursor()
            persona_num = personas.index(f"persona/{query.data}.txt")
            cursor.execute("UPDATE user_settings SET persona = ? WHERE id = ?", (persona_num, user_id))
            conn.commit()
            conn.close()
            await reset(update, content, query)
            await asyncio.to_thread(
                db[f"{user_id}"].update_one,
                    {"id" : user_id},
                    {"$set" : {"settings.6":persona_num}}
            )
            personas = sorted(glob("persona/*txt"))
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
            asyncio.create_task(circulate_routine(query, content))

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
            with open(f"Conversation/conversation-{user_id}.txt", "rb") as file:
                if os.path.getsize(f"Conversation/conversation-{user_id}.txt") == 0:
                    await query.edit_message_text("You don't have any conversation history.")
                else:
                    await query.edit_message_text("Your conversation history:")
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
                with open("info/admin_help.shadow", "rb") as file:
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
        
        elif query.data == "c_circulate_ct":
            asyncio.create_task(inform_all(query, content))
        
        elif query.data == "c_circulate_message":
            keyboard = [
                [InlineKeyboardButton("Notice", callback_data="c_notice"), InlineKeyboardButton("Normal Message", callback_data="c_normal_message")],
                [InlineKeyboardButton("Cancel", callback_data="cancel")]
            ]
            markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(add_escape_character("Notice will send message in this format\n```NOTICE\n<Your Message>\n```\nNormal will send message as bot response.\n\nChoose an option:"), reply_markup=markup, parse_mode="MarkdownV2")


    except Exception as e:
        print(f"Error in button_handler function.\n\nError Code -{e}")
        await query.edit_message_text(f"Internal Error - {e}.\n\n. Please try again later or contact admin.")
        return ConversationHandler.END











#main function

async def main():
    try:
        app = ApplicationBuilder().token(TOKEN).request(tg_request).concurrent_updates(True).build()
        await load_all_files()

        #conversation handler to verify user attendance
        verify_attendance_conv = ConversationHandler(
            entry_points = [CallbackQueryHandler(take_user_location, pattern="^c_mark_attendance$")],
            states = {
                "VL" : [
                    MessageHandler(filters.LOCATION, verify_user_location),
                    MessageHandler(filters.TEXT & ~ filters.COMMAND, verify_user_location)
                ]
            },
            fallbacks=[CallbackQueryHandler(cancel_conversation, pattern="^cancel_conv$")]
        )

        #conversation to handle taking attendance for cse sec c
        take_attendance_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(take_attendance_detail, pattern="^c_take_attendance$")],
            states = {
                "TTN" : [MessageHandler(filters.TEXT & ~filters.COMMAND, take_teachers_name)],
                "TSN" : [MessageHandler(filters.TEXT & ~filters.COMMAND, take_subject_name)],
                "TTL" : [MessageHandler(filters.TEXT & ~filters.COMMAND, take_time_limit)],
                "TL" : [
                    MessageHandler(filters.LOCATION, take_location),
                    CallbackQueryHandler(take_location, pattern="^c_location_skip$")
                ]
            },
            fallbacks=[CallbackQueryHandler(cancel_conversation, pattern="^cancel_conv$")]
        )

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
                "TUP" : [MessageHandler(filters.TEXT & ~filters.COMMAND, take_user_password)],
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
            entry_points = [CallbackQueryHandler(message_taker, pattern="^(c_notice|c_normal_message)$")],
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
        app.add_handler(take_attendance_conv)
        app.add_handler(manage_ai_model_conv)
        app.add_handler(circulate_message_conv)
        app.add_handler(verify_attendance_conv)
        app.add_handler(CommandHandler("help", help))
        app.add_handler(CommandHandler("start",start))
        app.add_handler(CommandHandler("restart",restart))
        app.add_handler(CallbackQueryHandler(button_handler))
        app.add_handler(CommandHandler("admin", admin_handler))
        #app.add_handler(MessageHandler(filters.LOCATION, handle_location))
        app.add_handler(MessageHandler(filters.Sticker.ALL, handle_sticker))
        app.add_handler(MessageHandler(filters.Document.ALL & ~filters.ChatType.CHANNEL, handle_document))
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
