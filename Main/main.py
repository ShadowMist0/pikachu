import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import asyncio
import warnings
import threading
from telegram.request import HTTPXRequest
from telegram._utils.warnings import PTBUserWarning
from telegram import Update
from telegram.ext import(
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler,
)
from routes.web_panel import run_web
from utils.db import TOKEN
from utils.file_utils import load_all_files
from utils.message_utils import run_workers
from bot.command_handler import(
    restart,
    start,
    help,
    admin_handler
)
from bot.media_handler import(
    handle_media,
    handle_location
)
from conv.conv_tool import(
    api_conv_handler,
    register_conv,
    thinking_conv,
    temperature_conv,
    take_attendance_conv,
    manage_ai_model_conv,
    manage_admin_conv,
    circulate_message_conv,
    verify_attendance_conv
)
from bot.callback import button_handler
from bot.echo import echo




#code to ignore warning about per_message in conv handler and increase poll size
warnings.filterwarnings("ignore",category=PTBUserWarning)
tg_request = HTTPXRequest(connection_pool_size=50, pool_timeout=30)







async def main():
    try:
        threading.Thread(target=run_web).start()
        app = ApplicationBuilder().token(TOKEN).request(tg_request).concurrent_updates(True).build()
        await load_all_files()    
        app.add_handler(register_conv)
        app.add_handler(api_conv_handler)
        app.add_handler(thinking_conv)
        app.add_handler(temperature_conv)
        app.add_handler(manage_admin_conv)
        app.add_handler(take_attendance_conv)
        app.add_handler(manage_ai_model_conv)
        app.add_handler(circulate_message_conv)
        app.add_handler(verify_attendance_conv)
        app.add_handler(CommandHandler("help", help))
        app.add_handler(CommandHandler("start",start))
        app.add_handler(CommandHandler("restart",restart))
        app.add_handler(CallbackQueryHandler(button_handler))
        app.add_handler(CommandHandler("admin", admin_handler))
        app.add_handler(MessageHandler(filters.LOCATION, handle_location))
        app.add_handler(MessageHandler(
            (filters.PHOTO |
            filters.Document.ALL | 
            filters.AUDIO |
            filters.VOICE |
            filters.VIDEO |
            filters.Sticker.ALL) &
            ~filters.ChatType.CHANNEL, handle_media
        ))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.ChatType.CHANNEL, echo))
        # with open("data/info/webhook_url.shadow", "rb") as file:
        #     url = fernet.decrypt(file.read().strip()).decode("utf-8")
        # app.run_webhook(
        #     listen = "0.0.0.0",
        #     port = int(os.environ.get("PORT", 10000)),
        #     webhook_url = url
        #)
        await run_workers(60)
        await app.initialize()
        await app.start()
        await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        await asyncio.Event().wait()
        #app.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        print(f"Error in main function. Error Code - {e}")


if __name__=="__main__":
    asyncio.run(main())
