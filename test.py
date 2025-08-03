from utils.db import db, gemini_model_list, all_users
import glob
import sqlite3

personas = sorted(glob.glob("data/persona/*txt"))


db[f"5888166321"].update_one(
    {"id" : 5888166321},
    {"$set" : {"settings.2" : "gemini-2.5-flash", "settings.6" : "data/persona/Maria.txt"}}
)
