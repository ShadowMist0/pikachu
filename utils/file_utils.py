import os
import shutil
import sqlite3
import asyncio
from utils.db import all_users, db, all_user_info
from utils.config import g_ciphers, secret_nonce, fernet
from cryptography.hazmat.primitives.ciphers.aead import AESGCM



#function to create settings file MongoDB to offline for optimization
def create_settings_file():
    try:
        print("settings, ", end="")
        shutil.rmtree("data/settings", ignore_errors=True)
        os.makedirs("data/settings", exist_ok=True)
        conn = sqlite3.connect("data/settings/user_settings.db")
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_settings(
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                model TEXT,
                thinking_budget INTEGER,
                temperature REAL,
                streaming INTEGER,
                persona TEXT
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
        shutil.rmtree("data/Conversation", ignore_errors=True)
        os.makedirs("data/Conversation", exist_ok=True)
        for user in all_users:
            conv_data = db[f"{user}"].find()[0]["conversation"]
            with open(f"data/Conversation/conversation-{user}.shadow", "wb") as file:
                if conv_data:
                    file.write(conv_data)
                else:
                    pass
        try:
            conv_data = db["group"].find()[0]["conversation"]
            with open(f"data/Conversation/conversation-group.txt", "w") as file:
                file.write(conv_data)
        except:
            print("Group conversation doesn't exist")
            with open(f"data/Conversation/conversation-group.txt", "w") as file:
                pass
    except Exception as e:
        print(f"Error in create_conversation_file function. \n\n Error Code  {e}")


#function to create offline file for memory
def create_memory_file():
    try:
        print("memory, ", end="")
        shutil.rmtree("data/memory", ignore_errors=True)
        os.makedirs("data/memory", exist_ok=True)
        for user in all_users:
            mem_data = db[f"{user}"].find()[0]["memory"]
            with open(f"data/memory/memory-{user}.shadow", "wb") as file:
                if mem_data:
                    file.write(mem_data)
                else:
                    pass
        try:
            mem_data = db["group"].find()[0]["memory"]
            with open(f"data/memory/memory-group.txt", "w") as file:
                file.write(mem_data)
        except:
            with open(f"data/memory/memory-group.txt", "w") as file:
                pass
    except Exception as e:
        print(f"Error in create_memory_file function. \n\n Error Code  {e}")


#function to create offline file for memory
def create_persona_file():
    try:
        print("persona, ", end="")
        shutil.rmtree("data/persona", ignore_errors=True)
        os.makedirs("data/persona", exist_ok=True)
        personas = [persona for persona in db["persona"].find({"type":"persona"})]
        for persona in personas:
            with open(f"data/persona/{persona["name"]}.shadow", "wb") as f:
                f.write(g_ciphers.encrypt(secret_nonce, persona["persona"].encode("utf-8"), None))
    except Exception as e:
        print(f"Error in create_persona_file function. \n\n Error Code  {e}")

    
#function to create user_data file MongoDB to offline for optimization
def create_user_data_file():
    try:
        print("user_data, ", end="")
        if os.path.exists("data/info/user_data.db"):
            try:
                os.remove("data/info/user_data.db")
            except:
                pass
        os.makedirs("data/info", exist_ok=True)
        conn = sqlite3.connect("data/info/user_data.db")
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users(
                user_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                gender TEXT,
                roll INTEGER,
                password TEXT,
                api TEXT,
                secret_key TEXT,
                nonce TEXT
            )
        """)
        for user in all_users:
            user_data = tuple(data for data in db[f"{user}"].find_one({"id":user})["user_data"])
            cursor.execute("""
                INSERT OR IGNORE INTO users 
                (user_id, name, gender, roll, password, api, secret_key, nonce)
                VALUES (?,?,?,?,?,?,?,?)
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
        shutil.rmtree("data/admin", ignore_errors=True)
        os.makedirs("data/admin", exist_ok=True)
        content = db["admin"].find_one({"type" : "admin"})["admin_password"]
        content = fernet.encrypt(content.encode())
        with open("data/admin/admin_password.shadow", "wb") as f:
            f.write(content)
    except Exception as e:
        print(f"Error in create_admin_pass_file function.\n\nError Code - {e}")


#function to create routine folder offline
def create_routine_file():
    try:
        print("routine, ", end="")
        shutil.rmtree("data/routine", ignore_errors=True)
        os.makedirs("data/routine", exist_ok=True)
        with open("data/routine/lab_routine.txt", "w") as f:
            data = db["routine"].find_one({"type" : "routine"})["lab_routine"]
            f.write(data)
        with open("data/routine/rt1.png", "wb") as f:
            data = db["routine"].find_one({"type" : "routine"})["rt1"]
            f.write(data)
        with open("data/routine/rt2.png", "wb") as f:
            data = db["routine"].find_one({"type" : "routine"})["rt2"]
            f.write(data)
    except Exception as e:
        print(f"Error in create_routine_file function. Error Code - {e}")


#function to create info file locally from MongoDB
def create_info_file():
    try:
        print("Creating info, ", end="")
        shutil.rmtree("data/info", ignore_errors=True)
        os.makedirs("data/info",exist_ok=True)
        colllection = db["info"]
        for file in colllection.find({"type" : "info"}):
            file_name = file["name"]
            path = f"data/info/{file_name}.shadow"
            with open(path, "wb") as f:
                f.write(g_ciphers.encrypt(secret_nonce, file["data"].encode("utf-8"), None))
    except Exception as e:
        print(f"Error in create_info_file function.\n\nError Code - {e}")


#calling all those function to create offline file from MongoDB
async def load_all_files():
    try:
        print("Loading all files and folder...")
        os.makedirs("ext", exist_ok=True)
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
