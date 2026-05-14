import asyncio
from aiogram import Bot, Dispatcher
from bot.config import get_settings

async def main():
    settings = get_settings()
    bot = Bot(token=settings.bot_token)
    dp = Dispatcher()

    @dp.channel_post()
    async def on_post(message):
        print(f"ID_FOUND: {message.chat.id} (Channel: {message.chat.title})")
        import os
        os._exit(0)

    @dp.message()
    async def on_msg(message):
        print(f"ID_FOUND: {message.chat.id} (Chat/Group: {message.chat.title or message.chat.full_name})")
        import os
        os._exit(0)

    @dp.my_chat_member()
    async def on_member(event):
        print(f"MEMBER_UPDATE: {event.chat.id} ({event.chat.title})")

    print("Listening for EVERYTHING... Please post in the channel/group AGAIN.")
    await dp.start_polling(bot, allowed_updates=["message", "channel_post", "my_chat_member"])

if __name__ == "__main__":
    asyncio.run(main())
