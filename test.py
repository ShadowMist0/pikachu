from utils.db import db, all_users, gemini_api_keys
import sqlite3
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from glob import glob


# 





def load_all_user_settings():
    try:
        print("Loading all user settings...")
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


all_settings = load_all_user_settings()
print(all_settings[5888166321])