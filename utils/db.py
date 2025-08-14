from utils.config import db
import sqlite3






#loading the bot api
def get_token():
    try:
        TOKENs = db["API"].find()[0]["bot_api"]
        return TOKENs
    except Exception as e:
        print(f"Error Code -{e}")


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


#function to load all admin
def load_admin():
    try:
        admins = tuple(int(admin) for admin in db["admin"].find()[0]["admin"])
        return admins
    except Exception as e:
        print(f"Error in load_admin function.\n\nError Code - {e}")


#function to load all gemini model
def load_gemini_model():
    try:
        models = tuple(db["ai_model"].find()[0]["model_name"])
        return models
    except Exception as e:
        print(f"Error Loading Gemini Model.\n\nError Code -{e}")
        return None
    

#fucntion to load gemini_api
def load_gemini_api():
    try:
        api_list = tuple(db["API"].find()[0]["gemini_api"])
        return api_list
    except Exception as e:
        print(f"Error lading gemini API. \n\nError Code -{e}")


#function to load all user settings as dictionary
def load_all_user_settings():
    try:
        user_settings = {}
        conn = sqlite3.connect("data/settings/user_settings.db")
        c = conn.cursor()
        c.execute("select * from user_settings")
        for settings in c.fetchall():
            user_settings[settings[0]] = settings
        conn.close()
        return user_settings
    except Exception as e:
        print(f"Error in load_all_user_settings function.\n\nError Code - {e}")






premium_users = ("5888166321", "6226239719")  # Example premium user IDs
gemini_api_keys = list(load_gemini_api())
gemini_model_list = load_gemini_model()
all_users = load_all_user()
all_admins = load_admin()
all_settings = load_all_user_settings()
TOKEN = get_token()[2]