import shutil
import os

shutil.rmtree("admin")
shutil.rmtree("Conversation")
shutil.rmtree("memory")
shutil.rmtree("persona")
shutil.rmtree("routine")
shutil.rmtree("settings")
 
os.remove("info/user_data.db")