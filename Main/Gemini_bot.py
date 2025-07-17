import asyncio
import sqlite3
from pymongo import MongoClient
from glob import glob
from pymongo.server_api import ServerApi
from cryptography.fernet import Fernet
import os

key = os.getenv("decryption_key")
fernet = Fernet(key)


url = "mongodb+srv://shadow_mist0:shadow_mist@cluster0.zozzwwv.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(url, server_api=ServerApi("1"))

db = client["phantom_bot"]


files = sorted(glob("persona/*shadow"))


conn = sqlite3.connect("info/user_data.db")
cursor = conn.cursor()

collection = db[f"group"]
collection.insert_one(
    {"id" : "group",
     "memory" : None,
     "conversation" : None
     }
)
