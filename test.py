from utils.db import db, gemini_model_list, all_users
import glob, os
import sqlite3

personas = sorted(glob.glob("data/persona/*txt"))

col = db["persona"]
for persona in personas:
    with open(persona, "r") as file:
        data = file.read()
    name = os.path.splitext(os.path.basename(persona))[0]
    print(name)
    col.update_one(
        {"name" : name},
        {"$set" : {"persona" : data}}
    )
