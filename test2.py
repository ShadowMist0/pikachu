import asyncio
import os
from google import genai
from google.genai import types
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from google.genai.types import GenerateContentResponse



#connecting to MongoDB database
try:
    mongo_pass = os.getenv("MDB_pass_shadow")
    url = f"mongodb+srv://shadow_mist0:{mongo_pass}@cluster0.zozzwwv.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
    client = MongoClient(url, server_api=ServerApi("1"))
    db = client["phantom_bot"]
except Exception as e:
    print(f"Error Connecting to MongoDB.\n\nError Code - {e}")

#Loading api key
def load_gemini_api():
    try:
        api_list = tuple(db["API"].find()[0]["gemini_api"])
        return api_list
    except Exception as e:
        print(f"Error lading gemini API. \n\nError Code -{e}")
gemini_api_keys = load_gemini_api()


def create_memory(api, user_id):
    try:
        if user_id > 0:
            with open("persona/memory_persona.txt", "r", encoding="utf-8") as f:
                instruction = f.read()
            with open(f"memory/memory-{user_id}.txt", "a+", encoding = "utf-8") as f:
                f.seek(0)
                data = "***PREVIOUS MEMORY***\n\n"
                data += f.read()
                data += "\n\n***END OF MEMORY***\n\n"
            with open(f"Conversation/conversation-{user_id}.txt", "a+", encoding = "utf-8") as f:
                f.seek(0)
                data += "\n\n***CONVERSATION HISTORY***"
                data += f.read()
                data += "\n\n***END OF CONVERSATION***\n\n"
        elif user_id < 0:
            group_id = user_id
            with open("persona/Maria.txt", "r") as f:
                instruction = f.read() 
            with open("persona/memory_persona.txt", "r") as f:
                instruction += f.read()
            with open(f"memory/memory-group.txt", "a+", encoding = "utf-8") as f:
                f.seek(0)
                data = "***PREVIOUS MEMORY***\n\n"
                data += f.read()
                data += "\n\n***END OF MEMORY***\n\n"
            with open(f"Conversation/conversation-group.txt", "a+", encoding = "utf-8") as f:
                f.seek(0)
                data += "\n\n***CONVERSATION HISTORY***"
                data += f.read()
                data += "\n\n***END OF CONVERSATION***\n\n"
        client = genai.Client(api_key=api)
        response = client.models.generate_content(
            model = "gemini-2.5-flash",
            contents = data,
            config = types.GenerateContentConfig(
                thinking_config = types.ThinkingConfig(thinking_budget=1024),
                temperature = 0.7,
                system_instruction =  instruction,
            ),
        )
        if response.text is not None:
            if user_id > 0:
                # with open(f"memory/memory-{user_id}.txt", "a+", encoding="utf-8") as f:
                #     f.write(response.text)
                #     f.seek(0)
                #     memory = f.read()
                # await asyncio.to_thread(db[f"{user_id}"].update_one,
                #     {"id" : user_id},
                #     {"$set" : {"memory" : memory}}
                # )
                #await asyncio.to_thread(delete_n_convo, user_id, 10)
                print(response.text)
            elif user_id < 0:
                # group_id = user_id
                # with open(f"memory/memory-group.txt", "a+", encoding="utf-8") as f:
                #     f.write(response.text)
                #     f.seek(0)
                #     memory = f.read()
                # await asyncio.to_thread(db[f"group"].update_one,
                #     {"id" : "group"},
                #     {"$set" : {"memory" : memory}}
                # )
                #await asyncio.to_thread(delete_n_convo, group_id,100)
                print(response.text)
            return True
        else:
            if response.prompt_feedback and response.prompt_feedback.block_reason:
                print(f"Blocked due to {response.prompt_feedback.block_reason}")
            return False
    except Exception as e:
        print(f"Failed to create memory\n Error code-{e}")



#function to create memory in background
def background_memory_creation(user_id, chat_type):
    try:
        if chat_type == "private":
            for api in gemini_api_keys:
                result = create_memory(api, user_id)
                if result:
                    break
        elif chat_type != "private":
            group_id = 0000000
            for api in gemini_api_keys:
                result = create_memory(api, group_id)
                if result:
                    break
    except Exception as e:
        print(f"Error in background_memory_creation function.\n\n Error Code -{e}")


background_memory_creation(6226239719, "private")