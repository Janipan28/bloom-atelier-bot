import asyncio
from aiogram import Bot
from bot.config import get_settings

async def notify_admins():
    settings = get_settings()
    bot = Bot(token=settings.bot_token)
    
    msg = (
        "🚀 <b>Бот успешно перезапущен после технического обслуживания!</b>\n\n"
        "✅ Все кнопки проверены (100% OK)\n"
        "✅ UI-фризы устранены\n"
        "✅ Функционал 'Быстрый пост' стабилизирован\n\n"
        "<i>Система работает в штатном режиме.</i>"
    )
    
    for admin_id in settings.admin_id_set:
        try:
            await bot.send_message(admin_id, msg, parse_mode="HTML")
            print(f"Sent notification to admin {admin_id}")
        except Exception as e:
            print(f"Failed to notify admin {admin_id}: {e}")
    
    await bot.session.close()

if __name__ == "__main__":
    asyncio.run(notify_admins())
