from utils.db import db, all_users

for user in all_users:
    c = db[f"{user}"]
    settings = c.find_one({"id" : user})["settings"]
    print(settings)
    c.update_one(
        {"id" : user},
        {"$set" : {"settings.4" : 2.0}}
    )
