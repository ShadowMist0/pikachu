import asyncio
import time
import threading
import requests
from flask import Flask
import os
from datetime import datetime
from requests.exceptions import RequestException, ConnectionError
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler





#Global
with open("API/bot_api.txt", "r") as file:
    TOKEN = file.read()


with open("Model/gemini_model.txt", "r") as file:
    model_list = file.read().split("\n")

current_model = model_list[3]










app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running 💖", 200


def run_web():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

threading.Thread(target=run_web).start()





def get_last_n_you_sections(text, keyword="You:", count=4):
    indices = []
    start = 0
    while True:
        index = text.find(keyword, start)
        if index == -1:
            break
        indices.append(index)
        start = index + len(keyword)
    
    if len(indices) < count:
        return text.strip()
    
    start_index = indices[-count]
    return text[start_index:].strip()

def load_api_keys():
    if os.path.exists("API/gemini_api.txt"):
        with open("API/gemini_api.txt", "r") as f:
            return [line.strip() for line in f.readlines() if line.strip()]
    return []

# Gemini API function
def gemini(prompt, retries=5, delay=5):
    for attempt in range(retries):
        try:
            api_keys = load_api_keys()
            if not api_keys:
                return "No API keys found, love. Please add one using /api command."

            API_KEY = api_keys[attempt % len(api_keys)]
            URL = f"https://generativelanguage.googleapis.com/v1beta/models/{current_model}:generateContent?key={API_KEY}"
            headers = {"Content-Type": "application/json"}
            data = {
                "contents": [
                    {"parts": [{"text": prompt}]}
                ]
            }

            response = requests.post(URL, headers=headers, json=data, timeout=10)

            if response.status_code == 200:
                result = response.json()
                return result['candidates'][0]['content']['parts'][0]['text']
            else:
                print(f"API Error [{response.status_code}]: {response.text}")
        except (ConnectionError, RequestException) as e:
            print(f"Network/API error (Attempt {attempt+1}): {e}")
        except Exception as e:
            print(f"Unexpected error (Attempt {attempt+1}): {e}")
        time.sleep(delay)

    return "Sorry baby... I couldn't reach Gemini. Maybe check your internet? I’ll wait here like a loyal girlfriend!"

# /start
async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text("Heyy! I'm Maria, your sweet shy coding girlfriend. Ask me anything, cutie!")

# /api
async def add_api(update: Update, context: CallbackContext) -> None:
    if context.args:
        api_key = context.args[0].strip()
        if not api_key.startswith("AIza"):
            await update.message.reply_text("Umm... that doesn’t look like a valid API key, babe.")
            return

        with open("API/gemini_api.txt", "a") as f:
            f.write(f"{api_key}\n")
        await update.message.reply_text("Yay! I saved your API key, love!")
    else:
        await update.message.reply_text("You forgot the key! Try like: /api your_key_here")

# /reset
async def reset(update: Update, context: CallbackContext) -> None:
    try:
        user_id = update.effective_user.id
        filename = f"Conversation/gemini_convo_{user_id}.txt"
        open(filename, 'w').close()
        await update.message.reply_text("All clear, baby! We’re starting fresh!")
    except Exception as e:
        print("Reset error:", e)
        await update.message.reply_text("Oops! Couldn’t reset. Wanna try again?")

# /model
async def model(update: Update, context: CallbackContext) -> None:
    keyboard = [
        [InlineKeyboardButton(text=model_name, callback_data=f"model:{model_name}")]
        for model_name in model_list
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(f"Your current model is: {current_model} \n\nChoose a model, cutie:", reply_markup=reply_markup)

# Callback for /model buttons
async def button(update: Update, context: CallbackContext) -> None:
    global current_model
    query = update.callback_query
    await query.answer()

    if query.data.startswith("model:"):
        chosen_model = query.data.split("model:")[1]
        current_model = chosen_model
        await query.edit_message_text(f"Yay! Model changed to: {current_model}")

# /message handler
async def echo(update: Update, context: CallbackContext) -> None:
    try:
        prompt = update.message.text.strip()

        if prompt == "00000000":
            await update.message.reply_text("Crash code accepted. Maria’s shutting down... Goodnight, hacker.")
            os._exit(1)

        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

        user_id = update.effective_user.id
        filename = f"Conversation/gemini_convo_{user_id}.txt"

        with open(filename, 'a+') as conversationf:
            conversationf.seek(0)
            previous_convo = conversationf.read()

        # Only get the last 15 responses to keep things short
        recent_convo = get_last_n_you_sections(previous_convo, count=15)

        if not prompt:
            await update.message.reply_text("Say something, love... I’m listening.")
            return

        time_user = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Add instruction to Gemini to always format code properly
        conversation = (
            "You are a cute, shy, talkative girlfriend named Maria. You explain with love, encouragement, and playful humor. "
            "If the user asks for code, respond using triple backticks like this:\n```python\n# your code here\n```\n\n . And don't use timestamp in your message. It's only for you to see."
            + f"{recent_convo}"
            + f"\n[{time_user}] User: {prompt}\n"
        )

        gresponse = gemini(conversation)

        # Helper function to ensure code block formatting
        def format_code_if_needed(text):
            if "def " in text or "import " in text or "\n    " in text:
                if not text.strip().startswith("```"):
                    return f"```python\n{text.strip()}\n```"
            return text

        formatted_response = format_code_if_needed(gresponse)

        time_maria = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conversation += f"[{time_maria}] You: {gresponse}\n"

        # Save conversation with timestamps
        with open(filename, 'a') as conversationf:
            conversationf.write(f"\n[{time_user}] User: {prompt}\n[{time_maria}] You: {gresponse}\n")

        await update.message.reply_text(formatted_response, parse_mode="Markdown")
    except Exception as e:
        print("Echo handler error:", e)
        await update.message.reply_text(f"Oops... something broke! ({e})")
        
        
# main
def main():
    #TOKEN = "6846587660:AAH9R-W7D3qn98mBfFROiD9vGaixIrwEAno"  # Replace with your bot token
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("api", add_api))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CommandHandler("model", model))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()