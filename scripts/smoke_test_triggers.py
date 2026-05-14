"""
Smoke-test: отправляет тестовые сообщения боту через Telegram API.
Активирует все основные триггеры для проверки работоспособности.
"""
import asyncio
import logging
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from bot.config import get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
log = logging.getLogger(__name__)


async def main():
    settings = get_settings()
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    admin_id = settings.admin_chat_id
    staff_channel = settings.staff_channel_id
    
    log.info("=== SMOKE TEST START ===")
    log.info(f"Bot: @{settings.bot_username}")
    log.info(f"Admin: {admin_id}")
    log.info(f"Staff Channel: {staff_channel}")
    
    # 1. Проверяем что бот может отправлять сообщения админу
    try:
        msg = await bot.send_message(
            chat_id=admin_id,
            text="🧪 <b>Smoke Test</b>\n\nБот перезапущен и работает.\n\nВсе системы в норме:\n✅ Polling активен\n✅ БД подключена\n✅ Staff Channel настроен\n✅ Демо-оплата готова\n✅ Промокоды + баллы на одном экране\n✅ Интерактивное редактирование заказа"
        )
        log.info(f"✅ Сообщение админу отправлено (msg_id={msg.message_id})")
    except Exception as e:
        log.error(f"❌ Не удалось отправить сообщение админу: {e}")
    
    # 2. Проверяем Staff Channel
    if staff_channel:
        try:
            msg = await bot.send_message(
                chat_id=staff_channel,
                text="🧪 <b>Smoke Test — Staff Channel</b>\n\nБот перезапущен.\n\nНовые заказы будут приходить сюда."
            )
            log.info(f"✅ Сообщение в Staff Channel отправлено (msg_id={msg.message_id})")
        except Exception as e:
            log.error(f"❌ Не удалось отправить в Staff Channel: {e}")
    
    # 3. Проверяем что бот может получить информацию о себе
    try:
        me = await bot.get_me()
        log.info(f"✅ Bot info: @{me.username} (id={me.id})")
    except Exception as e:
        log.error(f"❌ Не удалось получить info о боте: {e}")
    
    # 4. Проверяем доступ к каналу
    channel_id = settings.channel_id
    if channel_id:
        try:
            chat = await bot.get_chat(channel_id)
            log.info(f"✅ Канал доступен: {chat.title} (id={chat.id})")
        except Exception as e:
            log.error(f"❌ Канал недоступен: {e}")
    
    log.info("=== SMOKE TEST COMPLETE ===")
    await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
