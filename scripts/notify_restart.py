import asyncio
from aiogram import Bot
from bot.config import get_settings

async def main():
    settings = get_settings()
    if settings.bot_token == "YOUR_BOT_TOKEN" or not settings.bot_token:
        print("Bot token not set")
        return
        
    if settings.admin_chat_id == 0:
        print("Admin chat ID not set")
        return
        
    bot = Bot(token=settings.bot_token)
    try:
        await bot.send_message(
            chat_id=settings.admin_chat_id,
            text="🔄 <b>Бот перезапущен и стабилизирован.</b>\n\nВсе системы работают в штатном режиме. UI переведен на MenuManager.",
            parse_mode="HTML"
        )
        print("Notification sent successfully")
    except Exception as e:
        print(f"Error sending notification: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
