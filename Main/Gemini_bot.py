from telegram.ext import ApplicationBuilder
import asyncio

async def set_webhook():
    application = ApplicationBuilder().token("6846587660:AAH9R-W7D3qn98mBfFROiD9vGaixIrwEAno").build()
    await application.bot.set_webhook(url="https://nyx-bot-zqru.onrender.com/webhook/6846587660:AAH9R-W7D3qn98mBfFROiD9vGaixIrwEAno")

asyncio.run(set_webhook())
