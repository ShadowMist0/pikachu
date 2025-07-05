import re
import os
import time
import threading
import html
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters, ConversationHandler
from telegram.constants import ChatAction
from telegram.error import RetryAfter
from google import genai
from google.genai import types





#a flask to ignore web pulling condition

app = Flask(__name__)
@app.route('/')
def home():
    return "Bot is runnig", 200
def run_web():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
threading.Thread(target=run_web).start()





#all globals variable

#Loading all gemini model and selecting a model
with open("info/gemini_model.txt" , "r") as f:
    gemini_model_list = [line.strip() for line in f.readlines() if line.strip()]
active_model = gemini_model_list[1]

#loading the bot api
with open("API/bot_api.txt", "r") as f:
    TOKEN = f.read()

#loading persona
with open("persona/default_persona.txt", "r") as f:
    persona = f.read()

#tunig setting
think = 0
creativity = 0.7




#All the global function 

#Loading api key
def load_gemini_api():
    with open("API/gemini_api.txt", "r") as f:
        return [line.strip() for line in f.readlines() if line.strip()]

#adding escape character for markdown rule
def add_escape_character(text):
    escape_chars = r'_*\[\]()~>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)

#gemini response
def gemini(user_message, api):
    client = genai.Client(api_key=api)
    response = client.models.generate_content_stream(
        model = active_model,
        contents = [user_message],
        config = types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_budget=think),
            temperature = creativity,
            system_instruction = persona,
        ),
    )
    return response
        

#A function to delete n times convo from conversation history
def delete_n_convo(user_id, n):
    try:
        with open(f"Conversation/conversation-{user_id}.txt", "r+", encoding="utf-8") as f:
            data = f.read()
            data = data.split("You: ")
            if len(data) >= n+1:
                data = data[n:]
                f.seek(0)
                f.truncate(0)
                f.write("You: ".join(data))
    except Exception as e:
        print(f"Failed to delete conversation history \n Error Code - {e}")



#creating memory, SPECIAL_NOTE: THIS FUNCTION ALWAYS REWRITE THE WHOLE MEMORY, SO THE MEMORY SIZE IS LIMITED TO THE RESPONSE SIZE OF GEMINI, IT IS DONE THIS WAY BECAUSE OTHERWISE THERE WILL BE DUPLICATE DATA 
def create_memory(api, user_id):
    try:
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
    
        client = genai.Client(api_key=api)
        response = client.models.generate_content(
            model = "gemini-1.5-flash-8b",
            contents = data,
            config = types.GenerateContentConfig(
                temperature = 0.7,
                system_instruction =  instruction,
            ),
        )
        with open(f"memory/memory-{user_id}.txt", "w", encoding="utf-8") as f:
            f.write(response.text)
        delete_n_convo(user_id, 10)
    except Exception as e:
        print(f"Failed to create memory\n Error code-{e}")


#create the conversation history as prompt
def create_prompt(user_message, user_id):
    data = "***RULES***\n"
    with open("info/rules.txt", "r" , encoding="utf-8") as f:
        data += f.read()
        data += "\n***END OF RULES***\n\n\n"
    data += "***MEMORY***\n"
    with open(f"memory/memory-{user_id}.txt", "a+", encoding="utf-8") as f:
        f.seek(0)
        data += f.read()
        data += "\n***END OF MEMORY***\n\n\n"
    with open(f"Conversation/conversation-{user_id}.txt", "a+", encoding="utf-8") as f:
        f.seek(0)

        data += "***CONVERSATION HISTORY***\n\n"
        data += f.read()
        data += "\nUser: " + user_message

        f.seek(0)
        if(f.read().count("You: ")>12):
            create_memory(load_gemini_api()[-1], user_id)

        print(data.count("You: "))
    return data


#function to check if the code block is left opened in the chunk or not
def is_code_block_open(data):
    return data.count("```")%2 == 1


#function to check if the buffer has any code blocks
def has_codeblocks(data):
    count = data.count("```")
    if count == 0:
        return False
    elif count%2 == 1:
        return False
    else:
        return True


#functon for seperating code blocks from other context for better response and formatting
def separate_code_blocks(data):
    pattern = re.compile(r"(```.*?```)", re.DOTALL)
    parts = pattern.split(data)
    return parts








#All the python telegram bot function

#fuction for start command
async def start(update : Update, content : ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    paths = [
        f"Conversation/conversation-{user_id}.txt",
        f"memory/memory-{user_id}.txt",
        f"settings/settings-{user_id}.txt"
    ]

    for path in paths:
        if not os.path.exists(path):
            with open(path, "w", encoding = "utf-8") as f:
                pass


    await update.message.reply_text("Hi there, I am your personal assistant. If you need any help feel free to ask me.")


#function for all other messager that are directly send to bot without any command
async def echo(update : Update, content : ContextTypes.DEFAULT_TYPE) -> None:
    try:
        await update.message.chat.send_action(action=ChatAction.TYPING)
        gemini_api_keys = load_gemini_api()
        message = await update.message.reply_text("Typing...")
        for i in range(0, len(gemini_api_keys)):
            try:
                user_id = update.effective_user.id
                user_message = (update.message.text or "").strip()
                prompt = create_prompt(user_message,user_id)
                response = gemini(prompt, gemini_api_keys[i])
                buffer = ""
                last_sent = ""
                sent_message = ""
                for chunk in response:
                    if chunk.text is not None:
                        if chunk.text.strip():
                            if (len(buffer+chunk.text)<4096):
                                buffer += chunk.text
                                sent_message += chunk.text
                                await message.edit_text(buffer)
                            else:
                                if(is_code_block_open(buffer)):
                                    buffer += "\n```"
                                    await message.edit_text(add_escape_character(buffer), parse_mode="MarkdownV2")
                                    buffer = "```\n"
                                else:
                                    buffer += "\n                   ..."
                                    await message.edit_text(buffer, parse_mode="HTML")
                                    buffer = ""
                                buffer += chunk.text
                                sent_message += chunk.text
                                message = await update.message.reply_text(buffer)
                    else:
                        continue
                buffer += "\n."

                if(has_codeblocks(buffer)):
                    buffer = separate_code_blocks(buffer)
                    for i, block in enumerate(buffer):
                        if block.startswith("```") and block.endswith("```") and i != 0:
                            await update.message.reply_text(add_escape_character(block), parse_mode="MarkdownV2")
                        elif block.startswith("```") and block.endswith("```") and i == 0:
                            await message.edit_text(add_escape_character(block), parse_mode = "MarkdownV2")
                        elif i == 0:
                            await message.edit_text(block, parse_mode = "HTML")
                        else:
                            await update.message.reply_text(block, parse_mode = "HTML")
                else:
                    await message.edit_text(buffer, parse_mode="HTML")
                
                with open(f"Conversation/conversation-{user_id}.txt", "a+") as file:
                    file.write(f"User: {user_message}\n")
                    file.write(f"You: {sent_message}\n")

                #This break is to preventing multiple answer from api as we are using try to try all api available
                break

            except RetryAfter as e:
                await update.message.reply_text(f"Telegram Limit hit, need to wait {e.retry_after} seconds.")
            except Exception as e:
                print(f"Failed to fetch data from API-{i}, Error Code - {e}\n\n")
    except Exception as e:
        print(f"Error code - {e}\n\n")



#function for the command reset
async def reset(update : Update, content : ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    try:
        if os.path.exists(f"Conversation/conversation-{user_id}.txt"):
            with open(f"Conversation/conversation-{user_id}.txt", "w") as f:
                pass
            await update.message.reply_text("All clear, Now we are starting fresh.")
        else:
            await update.message.reply_text("It seems you don't have a conversation at all.")
    except Exception as e:
        await update.message.reply_text(f"Sorry, The operation failed. Here's the error message:\n<pre>{html.escape(str(e))}</pre>", parse_mode="HTML")


#function for the command api
async def api(update : Update, content : ContextTypes.DEFAULT_TYPE) -> None:
    with open("info/getting_api.txt") as f:
        for line in f.readlines():
            if line.strip():
                await update.message.reply_text(line.strip())
    return 1


#function to handle api
async def handle_api(update : Update, content : ContextTypes.DEFAULT_TYPE) -> None:
    with open("API/gemini_api.txt", "r", encoding="utf-8") as f:
        existing_apis = f.read()
    existing_apis = set(line.strip() for line in existing_apis.splitlines() if line.strip())
    user_api = update.message.text.strip()
    await update.message.chat.send_action(action = ChatAction.TYPING)
    try:
        response = gemini("Checking if the gemini api is working or not", user_api)
        chunk = next(response)
        if(
            user_api.startswith("AIza")
            and user_api not in existing_apis
            and " " not in user_api
            and len(user_api) >= 39
            and chunk.text
        ):
            with open("API/gemini_api.txt", "a") as f:
                f.write(f"\n{user_api}")
            await update.message.reply_text("The API is saved successfully.")
            return ConversationHandler.END
        else:
            await update.message.reply_text("Sorry, This is an invalid or Duplicate API, try again with a valid API.")
            return ConversationHandler.END
    except Exception as e:
        await update.message.reply_text(f"Sorry, The API didn't work properly.\n Error Code - {e}")
        return ConversationHandler.END
            









#main function

def main():
    conv_handler = ConversationHandler(
        entry_points = [CommandHandler("api", api)],
        states = {
            1 : [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_api)]
        },
        fallbacks = [],
    )
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start",start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(conv_handler)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    app.run_polling()


if __name__=="__main__":
    main()