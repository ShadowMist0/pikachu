import os
import asyncio
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import(
    ContextTypes
)
from utils.file_utils import load_all_files
from utils.utils import send_to_channel
from utils.db import(
    load_all_user,
    all_admins
)
from utils.config import(
    channel_id,
    fernet,
    g_ciphers,
    secret_nonce
)




#a function to restart renew all the bot info
async def restart(update:Update, content:ContextTypes.DEFAULT_TYPE) -> None:
    try:
        await update.message.reply_text("Restarting please wait....")
        await load_all_files()
        await update.message.reply_text("Restart Successful.")
    except Exception as e:
        print(f"Error in restart function.\n\nError Code - {e}")



#fuction for start command
async def start(update : Update, content : ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        ["Routine", "Schedule"],
        ["⚙️Settings", "🔗Resources"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False, selective=False, is_persistent=True)
    try:
        user_id = update.effective_chat.id
        paths = [
            f"data/Conversation/conversation-{user_id}.shadow",
            f"data/memory/memory-{user_id}.shadow",
        ]

        for path in paths:
            if not os.path.exists(path):
                with open(path, "wb", encoding = "utf-8") as f:
                    pass
        users = await asyncio.to_thread(load_all_user)
        if user_id in users:
            await update.message.reply_text("Hi there, I am your personal assistant. If you need any help feel free to ask me.", reply_markup=reply_markup)
            return
        if user_id not in users and update.message.chat.type == "private":
            keyboard = [
                [InlineKeyboardButton("Register", callback_data="c_register"), InlineKeyboardButton("Cancel", callback_data="cancel")]
            ]
            markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("You are not registerd yet.", reply_markup=markup)
        elif user_id not in users and update.message.chat.type != "private":
            await update.message.reply_text("You are not registered yet. Please register in private chat with the bot first.", reply_markup=reply_markup)
    except Exception as e:
        print(f"Error in start function. \n Error Code - {e}")
        await send_to_channel(update, content, channel_id, f"Error in start function \n\nError Code -{e}")


#function to handle help command
async def help(update: Update, content : ContextTypes.DEFAULT_TYPE) -> None:
    try:
        keyboard = [
            [InlineKeyboardButton("Admin Help", callback_data="c_admin_help"), InlineKeyboardButton("Cancel", callback_data="cancel")],
            [InlineKeyboardButton("Read Documentation", url = "https://github.com/sifat1996120/Phantom_bot")]
        ]
        help_markup = InlineKeyboardMarkup(keyboard)
        with open("data/info/help.shadow", "rb") as file:
            await update.message.reply_text(g_ciphers.decrypt(secret_nonce, file.read(), None).decode("utf-8"), reply_markup=help_markup)
    except Exception as e:
        print(f"Error in help function. \n\n Error Code - {e}")
        await send_to_channel(update, content, channel_id, f"Error in help function. \n\n Error Code - {e}")



#a function for admin call
async def admin_handler(update : Update, content : ContextTypes.DEFAULT_TYPE) -> None:
    try:
        user_id = update.effective_user.id
        if update.message.chat.type != "private":
            await update.message.reply_text("Sorry, This is not available for group.")
            return
        if user_id in all_admins:
            keyboard = [
                [InlineKeyboardButton("Circulate CT Routine", callback_data="c_circulate_ct"), InlineKeyboardButton("Take Attendance", callback_data="c_take_attendance")],
                [InlineKeyboardButton("Circulate Message", callback_data="c_circulate_message"), InlineKeyboardButton("Show All User", callback_data="c_show_all_user")],
                [InlineKeyboardButton("Circulate Routine", callback_data="c_circulate_routine"), InlineKeyboardButton("Toggle Routine", callback_data="c_toggle_routine")],
                [InlineKeyboardButton("Manage Admin", callback_data="c_manage_admin"), InlineKeyboardButton("Manage AI Model", callback_data="c_manage_ai_model")],
                [InlineKeyboardButton("cancel", callback_data="cancel")]
            ]
            admin_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("Given operation will circulate among all registered user.", parse_mode="Markdown", reply_markup=admin_markup)
            await update.message.delete()
        else:
            await update.message.reply_text("Sorry you are not an Admin.")
    except Exception as e:
        print(f"Error in admin_handler function.\n\n Error Code - {e}")
        await send_to_channel(update, content, channel_id, f"Error in admin_handler function.\n\n Error Code - {e}")


