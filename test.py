from utils.db import db, gemini_model_list, all_users
import glob, os
import sqlite3


user_id = 5924191438
db[f"{user_id}"].update_one(
    {"id" : user_id},
    {"$set" : {"memory" : None}}
)
