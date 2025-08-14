from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import(
    ContextTypes,
    ConversationHandler,
)
from utils.utils import get_settings, add_escape_character
from glob import glob
import os
from utils.db import gemini_model_list, all_admins, all_settings, load_all_user_settings
from utils.config import db,fernet
import sqlite3
import asyncio
from circulation.circulate import circulate_routine, inform_all
from ext.user_content_tools import see_memory, delete_memory, reset






#A function to handle button response
async def button_handler(update:Update, content:ContextTypes.DEFAULT_TYPE) -> None:
    try:
        global all_settings
        query = update.callback_query
        await query.answer()
        try:
            user_id = update.effective_user.id
        except:
            user_id = query.from_user.id
        settings = await get_settings(user_id)
        c_model = tuple(model for model in gemini_model_list)
        personas = sorted(glob("data/persona/*txt"))
        personas.remove("data/persona/memory_persona.txt")

        if query.data == "c_model":
            keyboard = []
            for i in range(0, len(gemini_model_list), 2):
                row =[]
                row.append(InlineKeyboardButton(text=gemini_model_list[i], callback_data=gemini_model_list[i]))
                if i+1 < len(gemini_model_list):
                    row.append(InlineKeyboardButton(text=gemini_model_list[i+1], callback_data=gemini_model_list[i+1]))
                keyboard.append(row)
            keyboard.append([InlineKeyboardButton("Cancel", callback_data="cancel")])
            model_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(f"Current Model: {settings[2]}\nChoose a model:", reply_markup=model_markup, parse_mode="Markdown")

        elif query.data == "c_streaming":
            keyboard = [
                [InlineKeyboardButton("ON", callback_data="c_streaming_on"), InlineKeyboardButton("OFF", callback_data="c_streaming_off")]    
            ]
            markup = InlineKeyboardMarkup(keyboard)
            settings = await get_settings(user_id)
            c_s = "ON" if settings[5] == 1 else "OFF"
            await query.edit_message_text(f"Streaming let you stream the bot response in real time.\nCurrent setting : {c_s}", reply_markup=markup)

        elif query.data == "c_persona":
            conn = sqlite3.connect("data/info/user_data.db")
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (query.from_user.id, ))
            user = cursor.fetchone()
            if user[3] == 0:
                try:
                    personas.remove("data/persona/Maria.txt")
                except Exception as e:
                    print(f"Error in c_data part. Error Code - {e}")
            settings = await get_settings(user_id)
            keyboard = []
            for i in range(0, len(personas), 2):
                row = []
                name = os.path.splitext(os.path.basename(personas[i]))[0]
                row.append(InlineKeyboardButton(text=name, callback_data=personas[i]))
                if i+1 < len(personas):
                    name = os.path.splitext(os.path.basename(personas[i+1]))[0]
                    row.append(InlineKeyboardButton(text = name, callback_data=personas[i+1]))
                keyboard.append(row)
            keyboard.append([InlineKeyboardButton("Cancel", callback_data="cancel")])
            markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(f"Persona will shape your bot response as personality.\n\nCurrent Persona: {os.path.splitext(os.path.basename(settings[6]))[0]}\n\nIt is recommended not to change the persona. Choose an option:", reply_markup=markup, parse_mode="Markdown")

        elif query.data == "c_memory":
            keyboard = [
                [InlineKeyboardButton("Show Memory", callback_data="c_show_memory"), InlineKeyboardButton("Delete Memory", callback_data="c_delete_memory")],
                [InlineKeyboardButton("Cancel", callback_data="cancel")]
            ]
            memory_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("Memory is created based on you conversation history to provide more personalized response.", reply_markup=memory_markup, parse_mode="Markdown")

        elif query.data == "c_conv_history":
            keyboard = [
                [InlineKeyboardButton("Show", callback_data="c_ch_show"), InlineKeyboardButton("Reset", callback_data="c_ch_reset")],
                [InlineKeyboardButton("Cancel", callback_data="cancel")]
            ]
            ch_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("Conversation history holds your conversation with the bot.", reply_markup=ch_markup, parse_mode="Markdown")

        elif query.data in c_model :
            conn = sqlite3.connect("data/settings/user_settings.db")
            cursor = conn.cursor()
            model = query.data
            if model != "gemini-2.5-pro":
                cursor.execute("UPDATE user_settings SET model = ? WHERE id = ?", (model, user_id))
                conn.commit()
                conn.close()
                await asyncio.to_thread(
                db[f"{user_id}"].update_one,
                        {"id" : user_id},
                        {"$set" : {"settings.2":model}}
                )
                await query.edit_message_text(f"AI model is successfully changed to {model}.")
                new_settings = load_all_user_settings()
                all_settings.clear()
                all_settings.update(new_settings)
            elif model == "gemini-2.5-pro":
                cursor.execute("UPDATE user_settings SET model = ?, thinking_budget = ? WHERE id = ? AND thinking_budget < 128", (model, 1024, user_id))
                conn.commit()
                conn.close()
                await asyncio.to_thread(
                db[f"{user_id}"].update_one,
                        {"id" : user_id},
                        {"$set" : {"settings.2":model, "settings.3" : 1024}}
                )
                await query.edit_message_text(f"AI model is successfully changed to {model}.")

        elif query.data in personas:
            conn = sqlite3.connect("data/settings/user_settings.db")
            cursor = conn.cursor()
            persona = query.data
            cursor.execute("UPDATE user_settings SET persona = ? WHERE id = ?", (persona, user_id))
            conn.commit()
            conn.close()
            await reset(update, content, query)
            await asyncio.to_thread(
                db[f"{user_id}"].update_one,
                    {"id" : user_id},
                    {"$set" : {"settings.6":persona}}
            )
            personas = sorted(glob("data/persona/*txt"))
            await query.edit_message_text(f"Persona is successfully changed to {os.path.splitext(os.path.basename(persona))[0]}.")
            new_settings = load_all_user_settings()
            all_settings.clear()
            all_settings.update(new_settings)

        elif query.data == "g_classroom":
            await query.edit_message_text("CSE Google classroom code: ```2o2ea2k3```\n\nMath G. Classroom code: ```aq4vazqi```\n\nChemistry G. Classroom code: ```wnlwjtbg```", parse_mode="Markdown")

        elif query.data == "c_all_websites":
            keyboard = [
                [InlineKeyboardButton("CSE 24 Website", url="https://csearchive.vercel.app/")],
                [InlineKeyboardButton("Facebook", url="https://www.facebook.com/profile.php?id=61574730479807"), InlineKeyboardButton("Profiles", url="https://ruetcse24.vercel.app/profiles")],
                [InlineKeyboardButton("Cancel", callback_data="cancel")]
            ]
            aw_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("CSE 24 RELATED ALL WEBSITES:", reply_markup=aw_markup)

        elif query.data == "c_circulate_routine":
            await query.edit_message_text("Please wait while bot is circulating the routine.")
            asyncio.create_task(circulate_routine(query, content))

        elif query.data == "c_toggle_routine":
            keyboard = [
                [InlineKeyboardButton("Sure", callback_data="c_tr_sure"), InlineKeyboardButton("Cancel", callback_data="c_tr_cancel")]
            ]
            tr_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("Are you sure you want to toggle the routine?", reply_markup=tr_markup)

        elif query.data == "c_tr_sure":
            with open("data/routine/lab_routine.txt", "r+", encoding="utf-8") as f:
                active = f.read()
                f.seek(0)
                f.truncate(0)
                if active == "first":
                    f.write("second")
                elif active=="second":
                    f.write("first")
                await query.edit_message_text("Routine Succesfully Toggled.")

        elif query.data == "c_tr_cancel":
            await query.edit_message_text("Thanks.")

        elif query.data == "cancel":
            await query.delete_message()

        elif query.data == "c_show_memory":
            await see_memory(update, content, query)

        elif query.data == "c_delete_memory":
            await delete_memory(update, content, query)

        elif query.data == "c_ch_show":
            with open(f"data/Conversation/conversation-{user_id}.txt", "rb") as file:
                if os.path.getsize(f"data/Conversation/conversation-{user_id}.txt") == 0:
                    await query.edit_message_text("You don't have any conversation history.")
                else:
                    await query.edit_message_text("Your conversation history:")
                    await content.bot.send_document(chat_id=user_id, document=file)

        elif query.data == "c_ch_reset":
            await reset(update, content, query)

        elif query.data == "c_admin_help":
            if user_id in all_admins:
                keyboard = [
                    [InlineKeyboardButton("Read Documentation", url = "https://github.com/sifat1996120/Phantom_bot")],
                        [InlineKeyboardButton("Cancel", callback_data="cancel")]
                ]
                markup = InlineKeyboardMarkup(keyboard)
                with open("data/info/admin_help.shadow", "rb") as file:
                    help_data = fernet.decrypt(file.read()).decode("utf-8")
                    help_data = help_data if help_data else "Sorry no document. Try again later."
                await query.edit_message_text(help_data, reply_markup=markup)
            else:
                await query.edit_message_text("Sorry you are not a Admin.")
        
        elif query.data == "c_manage_ai_model":
            keyboard = [
                [InlineKeyboardButton("Add Model", callback_data="c_add_model"), InlineKeyboardButton("Delete Model", callback_data="c_delete_model")],
                [InlineKeyboardButton("Cancel", callback_data="cancel")]
            ]
            markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("From here you can manage the AI model this bot use to provide response.\n\nChoose an option:", reply_markup=markup, parse_mode="Markdown")

        elif query.data == "c_show_all_user":
            conn = sqlite3.connect("data/info/user_data.db")
            cursor = conn.cursor()
            cursor.execute("SELECT user_id from users")
            rows = cursor.fetchall()
            users = tuple(row[0] for row in rows)
            user_data = "All registered users are listed below:\n"
            for i, user in enumerate(users):
                user_data += f"{i+1}. {user}\n"
            await query.edit_message_text(user_data)
        
        elif query.data == "c_circulate_ct":
            asyncio.create_task(inform_all(query, content))
        
        elif query.data == "c_circulate_message":
            keyboard = [
                [InlineKeyboardButton("Notice", callback_data="c_notice"), InlineKeyboardButton("Normal Message", callback_data="c_normal_message")],
                [InlineKeyboardButton("Cancel", callback_data="cancel")]
            ]
            markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(add_escape_character("Notice will send message in this format\n```NOTICE\n<Your Message>\n```\nNormal will send message as bot response.\n\nChoose an option:"), reply_markup=markup, parse_mode="MarkdownV2")


    except Exception as e:
        print(f"Error in button_handler function.\n\nError Code -{e}")
        await query.edit_message_text(f"Internal Error - {e}.\n\n. Please try again later or contact admin.")
        return ConversationHandler.END



