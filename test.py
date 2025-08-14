from utils.db import db, all_users, gemini_api_keys
import sqlite3
from cryptography.hazmat.primitives.ciphers.aead import AESGCM



all_user = tuple(int(user) for user in db.list_collection_names() if user.isdigit())

for user in all_user:
    key = AESGCM.generate_key(bit_length=256)
    settings = db[f"{user}"].find()[0]["user_data"]
    # db[f"{user}"].update_one(
    #     {"id":user},
    #     {"$pop":{"user_data":1}}
    # )
    print(settings)