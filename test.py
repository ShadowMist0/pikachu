from utils.db import db, gemini_model_list, all_users
import glob, os
import sqlite3


conn = sqlite3.connect("user_media/user_media.db")
c = conn.cursor()
c.execute("select media_path from user_media")
paths = c.fetchall()
for path in paths:
    print(path[0])
c.execute("delete from user_media where media_path = ?", (path[0],))