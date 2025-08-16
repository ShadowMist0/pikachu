import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import asyncio
import warnings
import uvicorn
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
from routes.web_panel_fastapi import app as web_app
from utils.db import (
    TOKEN,
    populate_db_caches,
    all_user_info,
    all_settings
)
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
    handle_location,
    run_media_workers
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
from fastapi import Request, Response




#code to ignore warning about per_message in conv handler and increase poll size
warnings.filterwarnings("ignore",category=PTBUserWarning)
tg_request = HTTPXRequest(connection_pool_size=50, pool_timeout=30)


# Setting this to your publicly accessible URL

WEBHOOK_URL = "https://40cf9d48b77a.ngrok-free.app"              #local testing
#WEBHOOK_URL = "https://pikachu-zhx7.onrender.com"               #original render url




async def main():
    try:
        bot_app = ApplicationBuilder().token(TOKEN).request(tg_request).concurrent_updates(True).build()
        await load_all_files()
        await populate_db_caches()

        # Add webhook handler to the FastAPI app
        @web_app.post(f"/{TOKEN}")
        async def telegram_webhook(request: Request):
            """Handle incoming telegram updates"""
            update_data = await request.json()
            update = Update.de_json(update_data, bot_app.bot)
            await bot_app.process_update(update)
            return Response(status_code=200)

        bot_app.add_handler(register_conv)
        bot_app.add_handler(api_conv_handler)
        bot_app.add_handler(thinking_conv)
        bot_app.add_handler(temperature_conv)
        bot_app.add_handler(manage_admin_conv)
        bot_app.add_handler(take_attendance_conv)
        bot_app.add_handler(manage_ai_model_conv)
        bot_app.add_handler(circulate_message_conv)
        bot_app.add_handler(verify_attendance_conv)
        bot_app.add_handler(CommandHandler("help", help))
        bot_app.add_handler(CommandHandler("start",start))
        bot_app.add_handler(CommandHandler("restart",restart))
        bot_app.add_handler(CallbackQueryHandler(button_handler))
        bot_app.add_handler(CommandHandler("admin", admin_handler))
        bot_app.add_handler(MessageHandler(filters.LOCATION, handle_location))
        bot_app.add_handler(MessageHandler(
            (filters.PHOTO |
            filters.Document.ALL | 
            filters.AUDIO |
            filters.VOICE |
            filters.VIDEO |
            filters.Sticker.ALL) &
            ~filters.ChatType.CHANNEL, handle_media
        ))
        bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.ChatType.CHANNEL, echo))
        
        # Setup Uvicorn server to run our FastAPI app
        config = uvicorn.Config(web_app, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)), log_level="info")
        server = uvicorn.Server(config)

        await run_workers(12)
        await run_media_workers(6)
        
        # --- WEBHOOK MODE (Currently Active) ---
        # This runs the bot with webhooks.
        async with bot_app:
            await bot_app.start()
            # Set webhook
            await bot_app.bot.set_webhook(
                url=f"{WEBHOOK_URL}/{TOKEN}",
                allowed_updates=Update.ALL_TYPES
            )
            # Run the web server
            await server.serve()
            # On shutdown, stop the bot and delete the webhook
            await bot_app.bot.delete_webhook()
            await bot_app.stop()

        # --- POLLING MODE (Currently Inactive) ---

        # await bot_app.initialize()
        # await bot_app.start()
        # # This will run the bot and the web server concurrently
        # await asyncio.gather(
        #     bot_app.updater.start_polling(allowed_updates=Update.ALL_TYPES),
        #     server.serve()
        # )

    except Exception as e:
        print(f"Error in main function. Error Code - {e}")


if __name__=="__main__":
    asyncio.run(main())
