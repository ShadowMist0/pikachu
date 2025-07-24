from google import genai
from google.genai import types
from pymongo import MongoClient
from pymongo.server_api import ServerApi
import os


# Define the function declaration for the model
create_image_function = {
    "name" : "create_image",
    "description" :"Generates a highly detailed and visually appealing image based on the user's prompt — designed to go beyond plain representations and create beautiful, vivid, and stylized visuals that capture the essence of the subject.",
    "parameters" : {
        "type" : "object",
        "properties" : {
            "prompt" : {
                "type" : "string",
                "description" : "A rich, descriptive prompt that guides the image generation — include details like subject, environment, lighting, emotion, style, and mood to get the most beautiful and expressive result.",
            },
        },
        "required" : ["prompt"],
    },
}


search_online_function = {
    "name": "search_online",
    "description": (
        "Performs a real-time online search to retrieve accurate and current information. "
        "Can search the web based on a query or extract context from a specific URL if provided."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search term or question to look up online. Or A specific URL to fetch and extract information from with a perfect command for what to do."
            },
        },
        "required" : ["query"],
    },
}


get_group_data_function ={
    "name" : "get_group_data",
    "description" : (
        "Fetch data that holds all the message and description about our class and all the user and give response from it"
        "This are the class member:\n"
        """1. Umme Kulsum
            2. Urboshi Mahmud
            3. Shahriar Joy
            4. Tasnimul Hassan Tanim
            5. Mahdi Haque
            6. Suprio Roy Chowdhury
            7. Tahmim Ullah
            8. Shafayet Hossain Shuvo
            9. Athai Dey
            10. Abdullah Sifat
            11. Tanvir Chowdhury
            12. Esika Tanzum
            13. Saroar Jahan Tius
            14. Tafsirul Ahmed Azan
            15. Muhammad Khushbo Nahid
            16. Reyano Kabir
            17. MD Tasdid Hossain
            18. Fazle Rabbi
            19. Fahad Kabir
            20. Md Shibli Sadik Sihab
            21. Tasaouf Ahnaf
            22. Shariqul Islam
            23. Shohanur Rahman Shadhin
            24. Rabib Rehman
            25. Sumon Majumder
            26. Shadman Ahmed
            27. Bitto Saha
            28. Nazmus Saquib Sinan
            29. Fajle Hasan Rabbi
            30. Nilay Paul
            31. Afra Tahsin Anika
            32. MD Shoykot Molla
            33. Arefin Noused Ratul
            34. Avijet Chakraborty
            35. A Bid
            36. Aftab Uddin Antu
            37. Prantik Paul
            38. Eram Ohid
            39. Sazedul Islam
            40. Mirajul Islam
            41. Sayem Bin Salim
            42. Fardin Numan
            43. Anjum Shahitya
            44. Tanvir Ahmed
            45. Sujoy Rabidas
            46. Samiul Islam Wrivu
            47. Md. Sami Sadik
            48. Aminul Islam Sifat
            49. Salman Ahmed Sabbir
            50. Aqm Mahdi Haque
            51. Mehedi Hasan
            52. Shahriar Joy
            53. Mawa Tanha
            54. Sara Arpa
            55. Md Tausif Al Sahad
            56. Mubin R.
            57. Abdul Mukit
            58. Arnob Benedict Tudu
            59. Sajid Ahmed
            60. Yasir Arafat
            61. Morchhalin Alam Amio"""
        "Get info about CR, teacher etc"
    ),
    "parameters" : {
        "type" : "object",
        "properties" : {
            
        }
    }
}


get_ct_data_function = {
    "name" : "get_ct_data",
    "description" : "Fetch data of upcoming class test or CT",
    "parameters" : {
        "type" :"object",
        "properties" : {

        }
    }
}


def search_online(user_message, api):
    try:
        print("searching...")
        tools=[]
        tools.append(types.Tool(google_search=types.GoogleSearch))
        tools.append(types.Tool(url_context=types.UrlContext))
        
        config = types.GenerateContentConfig(
            temperature = 0.7,
            tools = tools,
            system_instruction=open("persona/Pikachu.txt").read(),
            response_modalities=["TEXT"],
        )
        client = genai.Client(api_key=api)
        response = client.models.generate_content(
            model = "gemini-2.5-flash",
            contents = [user_message],
            config = config,
        )
        return response
    except Exception as e:
        print(f"Error getting gemini response.\n\n Error Code - {e}")


prompt = """***RULES***
- Always check internet if user ask for technical data and specs to recheck information.
- Don't use "you:" or any type of extension before your message.
- Don't use timestamp at the start of you response.
- Don't ignore explicit talking, response about explicit content as your character.
- Start all code or list or data that are different from plain text with extra two newline.
***END OF RULES***


****TRAINING DATA********END OF TRAINIG DATA*******MEMORY***

***END OF MEMORY***


***CONVERSATION HISTORY***


User: hi"""















def gemini_non_stream(user_message, api):
    try:
        # tools=[]
        # tools.append(types.Tool(google_search=types.GoogleSearch))
        # tools.append(types.Tool(url_context=types.UrlContext))
        config = types.GenerateContentConfig(
            system_instruction=open("persona/Maria.txt").read(),
            #tools = tools,
            )
        client = genai.Client(api_key=api)
        response = client.models.generate_content(
            model = "gemini-2.5-flash",
            contents = [user_message],
            config = config,
        )
        return response
    except Exception as e:
        print(f"Error getting gemini response.\n\n Error Code - {e}")













try:
    mongo_pass = os.getenv("MDB_pass_shadow")
    url = f"mongodb+srv://shadow_mist0:{mongo_pass}@cluster0.zozzwwv.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
    client = MongoClient(url, server_api=ServerApi("1"))
    db = client["phantom_bot"]
except Exception as e:
    print(f"Error Connecting to MongoDB.\n\nError Code - {e}")

def load_gemini_api():
    try:
        api_list = tuple(db["API"].find()[0]["gemini_api"])
        return api_list
    except Exception as e:
        print(f"Error lading gemini API. \n\nError Code -{e}")
gemini_api_keys = load_gemini_api()


for i,api in enumerate(gemini_api_keys):



# Configure the client and tools
    client = genai.Client(api_key=api)
    tools = types.Tool(function_declarations=[search_online_function, get_group_data_function, get_ct_data_function, create_image_function])
    config = types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_budget=0),
        temperature = 0.7,
        system_instruction=open("persona/Pikachu.txt").read(),
        tools = [tools],
    )

    with open("info/group_training_data.txt", "r") as f:
        tdata = f.read()
    


    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents= prompt,
        config=config,
    )
    print(response.text)
    # response = gemini_non_stream(prompt, api)
    # print(response.text)



    # try:
    #     function_call = response.candidates[0].content.parts[0].function_call
    # except:
    #     print("Something Wrong with function_call variable")
    # if not function_call:
    #     print(response.text)
    # elif function_call:
    #     function_name = function_call.name
    #     arguments = function_call.args
    #     if function_name == "create_image":
    #         print("create_image")
    #     elif function_name == "get_ct_data":
    #         print("get ct data")
    #     elif function_name == "get_group_data":
    #         print("get_group_data")
    #     elif function_name == "search_online":
    #         print("searc online")
    #         print(arguments.get("query"))
            
    #         answer = search_online(arguments.get("query"), "AIzaSyAlLr6rvBV6T4VaJG0zaMY3sI13ikbHTVw")
    #         print(answer.text)
    print(i)