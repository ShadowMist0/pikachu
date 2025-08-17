import os
import sys
import io
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
import utils.db as db_utils
from utils.file_utils import load_all_files
from utils.message_utils import run_workers, queue as message_queue
from bot.command_handler import(
    restart,
    start,
    help,
    admin_handler
)
from bot.media_handler import(
    handle_media,
    handle_location,
    run_media_workers,
    media_queue
)


#code to ignore warning about per_message in conv handler and increase poll size
warnings.filterwarnings("ignore",category=PTBUserWarning)

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
tg_request = HTTPXRequest(connection_pool_size=50, pool_timeout=30)


# Setting this to your publicly accessible URL

#WEBHOOK_URL = "https://25cd458b3705.ngrok-free.app"        #local testing
WEBHOOK_URL = "https://pikachu-zhx7.onrender.com"               #original render url



async def main():
    try:
        await db_utils.initialize_bot()
        await load_all_files()
        await db_utils.populate_db_caches()

        bot_app = ApplicationBuilder().token(db_utils.TOKEN).request(tg_request).concurrent_updates(True).build()

        # Add webhook handler to the FastAPI app
        @web_app.post(f"/{db_utils.TOKEN}")
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

        workers = await run_workers(12)
        media_workers = await run_media_workers(6)
        
        # --- WEBHOOK MODE (Currently Active) ---
        # This runs the bot with webhooks.
        async with bot_app:
            await bot_app.start()
            # Set webhook
            await bot_app.bot.set_webhook(
                url=f"{WEBHOOK_URL}/{db_utils.TOKEN}",
                allowed_updates=Update.ALL_TYPES
            )
            # Run the web server
            await server.serve()
            
            # On shutdown, stop the bot and delete the webhook
            for _ in workers:
                await message_queue.put(None)
            for _ in media_workers:
                await media_queue.put(None)
            
            await asyncio.gather(*workers, *media_workers)

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
    # import cProfile
    # import pstats
    # import atexit

    # s = io.StringIO()

    # print("Starting profiler...")
    # profiler = cProfile.Profile()
    # profiler.enable()

    # def save_profiler_stats():
    #     profiler.disable()
    #     print("Saving profiler stats to profile.stats...")
    #     profiler.dump_stats("Logs/profile.stats")
    #     print("Profiler stats saved. ❤️")

    #     s = io.StringIO()
    #     stats = pstats.Stats("Logs/profile.stats", stream=s)

    #     # Only include functions from your bot's files
    #     # Replace "pikachu" with the unique part of your module/folder name
    #     stats.sort_stats("cumulative")
    #     s.write("--- Top 100 Functions by Cumulative Time ---\n")
    #     stats.print_stats("pikachu")  # filters functions containing "pikachu" in path or name
    #     s.write("\n\n")

    #     stats.sort_stats("tottime")
    #     s.write("--- Top 100 Functions by Total Time ---\n")
    #     stats.print_stats("pikachu")  # same filter here

    #     with open("Logs/log.txt", "w") as file:
    #         file.write(s.getvalue())

    #     os.remove("Logs/profile.stats")
    #     print("Successfully saved the log file ✅")

    # atexit.register(save_profiler_stats)


    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nCaught keyboard interrupt. Exiting.")
