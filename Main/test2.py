import re
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from google import genai
from google.genai import types



#all globals variable

#Loading all gemini model and selecting a model
with open("Model/gemini_model.txt" , "r") as f:
    gemini_model_list = [line.strip() for line in f.readlines() if line.strip()]
active_model = gemini_model_list[1]

#loading the bot api
with open("API/bot_api.txt", "r") as f:
    TOKEN = f.read()

#Loading gemini api key and selecting one
with open("API/gemini_api.txt" , "r") as f:
    gemini_api_list = [line.strip() for line in f.readlines() if line.strip()]
active_gemini_api = gemini_api_list[3]

#Set thinking on or off
think = 0

#Setting the creativity of the response
creativity = 1.0

#Loading the persona
with open("persona/default_persona.txt", "r") as f:
    persona = f.read()


#function to add escape character for text formatting
def escape_markdown(text):
    escape_chars = r'_*\[\]()~>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)




#getting gemini response
def gemini(user_message):
    client = genai.Client(api_key=active_gemini_api)
    response = client.models.generate_content_stream(
        model = active_model,
        contents = [user_message],
        config = types.GenerateContentConfig(
            thinking_config = types.ThinkingConfig(thinking_budget=think),
            temperature = creativity,
            system_instruction = persona,
        ),
    )
    return response



#All the telegram bot command and function are here

async def start(update : Update, content : ContextTypes.DEFAULT_TYPE) -> None:
    message = await update.message.reply_text("Typing...")
    gemini_response = gemini("hey there, can you write a python program to print hello world?")
    sent_message = ""
    count = 0
    for chunk in gemini_response:
        sent_message += escape_markdown(chunk.text)
        try:
            await message.edit_text(sent_message, parse_mode="MarkdownV2")
        except Exception as e:
            print(f"Editing Error {e}")

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.run_polling()
