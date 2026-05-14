import asyncio
from aiogram import Bot
from bot.config import get_settings

async def publish_test_message():
    settings = get_settings()
    bot = Bot(token=settings.bot_token)
    channel_id = settings.channel_id
    print(f"Testing publishing to {channel_id}...")
    try:
        sent = await bot.send_message(chat_id=channel_id, text="🚀 Test message from Bot! If you see this, publishing works.")
        print(f"Success! Message ID: {sent.message_id}")
    except Exception as e:
        print(f"Failed: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(publish_test_message())
