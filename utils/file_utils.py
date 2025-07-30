import os
import shutil
import sqlite3
import asyncio
from utils.db import all_users, db
from utils.config import fernet





#function to create settings file MongoDB to offline for optimization
def create_settings_file():
    try:
        print("settings, ", end="")
        shutil.rmtree("ext/settings", ignore_errors=True)
        os.makedirs("ext/settings", exist_ok=True)
        conn = sqlite3.connect("ext/settings/user_settings.db")
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
        shutil.rmtree("ext/Conversation", ignore_errors=True)
        os.makedirs("ext/Conversation", exist_ok=True)
        for user in all_users:
            conv_data = db[f"{user}"].find()[0]["conversation"]
            with open(f"ext/Conversation/conversation-{user}.txt", "w") as file:
                if conv_data:
                    file.write(conv_data)
                else:
                    pass
        try:
            conv_data = db["group"].find()[0]["conversation"]
            with open(f"ext/Conversation/conversation-group.txt", "w") as file:
                file.write(conv_data)
        except:
            print("Group conversation doesn't exist")
            with open(f"ext/Conversation/conversation-group.txt", "w") as file:
                pass
    except Exception as e:
        print(f"Error in create_conversation_file function. \n\n Error Code  {e}")


#function to create offline file for memory
def create_memory_file():
    try:
        print("memory, ", end="")
        shutil.rmtree("ext/memory", ignore_errors=True)
        os.makedirs("ext/memory", exist_ok=True)
        for user in all_users:
            mem_data = db[f"{user}"].find()[0]["memory"]
            with open(f"ext/memory/memory-{user}.txt", "w") as file:
                if mem_data:
                    file.write(mem_data)
                else:
                    pass
        try:
            mem_data = db["group"].find()[0]["memory"]
            with open(f"ext/memory/memory-group.txt", "w") as file:
                file.write(mem_data)
        except:
            with open(f"ext/memory/memory-group.txt", "w") as file:
                pass
    except Exception as e:
        print(f"Error in create_memory_file function. \n\n Error Code  {e}")


#function to create offline file for memory
def create_persona_file():
    try:
        print("persona, ", end="")
        shutil.rmtree("ext/persona", ignore_errors=True)
        os.makedirs("ext/persona", exist_ok=True)
        personas = [persona for persona in db["persona"].find({"type":"persona"})]
        for persona in personas:
            with open(f"ext/persona/{persona["name"]}.txt", "w") as f:
                f.write(persona["persona"])
    except Exception as e:
        print(f"Error in create_persona_file function. \n\n Error Code  {e}")

    
#function to create user_data file MongoDB to offline for optimization
def create_user_data_file():
    try:
        print("user_data, ", end="")
        if os.path.exists("ext/info/user_data.db"):
            try:
                os.remove("ext/info/user_data.db")
            except:
                pass
        os.makedirs("ext/info", exist_ok=True)
        conn = sqlite3.connect("ext/info/user_data.db")
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
        shutil.rmtree("ext/admin", ignore_errors=True)
        os.makedirs("ext/admin", exist_ok=True)
        content = db["admin"].find_one({"type" : "admin"})["admin_password"]
        content = fernet.encrypt(content.encode())
        with open("ext/admin/admin_password.shadow", "wb") as f:
            f.write(content)
    except Exception as e:
        print(f"Error in create_admin_pass_file function.\n\nError Code - {e}")


#function to create routine folder offline
def create_routine_file():
    try:
        print("routine, ", end="")
        shutil.rmtree("ext/routine", ignore_errors=True)
        os.makedirs("ext/routine", exist_ok=True)
        with open("ext/routine/lab_routine.txt", "w") as f:
            data = db["routine"].find_one({"type" : "routine"})["lab_routine"]
            f.write(data)
        with open("ext/routine/rt1.png", "wb") as f:
            data = db["routine"].find_one({"type" : "routine"})["rt1"]
            f.write(data)
        with open("ext/routine/rt2.png", "wb") as f:
            data = db["routine"].find_one({"type" : "routine"})["rt2"]
            f.write(data)
    except Exception as e:
        print(f"Error in create_routine_file function. Error Code - {e}")


#function to create info file locally from MongoDB
def create_info_file():
    try:
        print("Creating info, ", end="")
        shutil.rmtree("ext/info", ignore_errors=True)
        os.makedirs("ext/info",exist_ok=True)
        colllection = db["info"]
        for file in colllection.find({"type" : "info"}):
            file_name = file["name"]
            path = f"ext/info/{file_name}.txt" if file_name == "group_training_data" else f"ext/info/{file_name}.shadow"
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
