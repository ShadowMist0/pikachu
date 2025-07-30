from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from utils.utils import is_ddos,send_to_channel
from telegram.constants import ChatAction
from bot.info_handler import routine_handler, handle_ct, resources_handler, handle_settings
from utils.db import all_users
from utils.config import channel_id
from utils.message_utils import queue









#function for all other messager that are directly send to bot without any command
async def echo(update : Update, content : ContextTypes.DEFAULT_TYPE) -> None:
    try:
        bot_name_obj = await content.bot.get_my_name()
        bot_name = bot_name_obj.name.lower()
        user_id = update.effective_user.id
        if await is_ddos(update, content, user_id):
            return
        if user_id not in all_users and update.message.chat.type == "private":
            keyboard = [
                [InlineKeyboardButton("Register", callback_data="c_register"), InlineKeyboardButton("Cancel", callback_data="cancel")]
            ]
            markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("You are not registered.", reply_markup=markup)
            return
        user_name = f"{update.effective_user.first_name or update.effective_user.last_name or "Unknown"}".strip()
        user_message = (update.message.text or "...").strip()
        if (update.message and update.message.chat.type == "private") or (update.message.chat.type != "private" and (f"@{bot_name}" in user_message.lower() or f"{bot_name}" in user_message.lower() or "mama" in user_message.lower() or "@" in user_message.lower() or "bot" in user_message.lower() or "pika" in user_message.lower())):
            await update.message.chat.send_action(action = ChatAction.TYPING)
        if user_message == "Routine" and update.message.chat.type == "private":
            await routine_handler(update, content)
            return
        elif user_message == "Settings" and update.message.chat.type == "private":
            await handle_settings(update, content)
            await update.message.delete()
            return
        elif user_message == "CT" and update.message.chat.type == "private":
            await handle_ct(update, content)
            return
        elif user_message == "Resources" and update.message.chat.type == "private":
            await resources_handler(update, content)
            await update.message.delete()
            return
        else:
            #await user_message_handler(update, content, bot_name)
            await queue.put((update, content, bot_name))
    except Exception as e:
        print(f"Error in echo function.\n\n Error Code - {e}")
        await send_to_channel(update, content, channel_id, f"Error in echo function \n\nError Code -{e}")

