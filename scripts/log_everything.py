import asyncio
from aiogram import Bot, Dispatcher
from bot.config import get_settings

async def main():
    settings = get_settings()
    bot = Bot(token=settings.bot_token)
    dp = Dispatcher()

    @dp.update()
    async def on_update(update):
        print(f"UPDATE_JSON: {update.model_dump_json()}")
        if update.message and update.message.forward_from_chat:
            print(f"🎯 TARGET_ID: {update.message.forward_from_chat.id}")

    print("POLLING_STARTED")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
