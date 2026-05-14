import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from bot.config import get_settings
from bot.db import init_db
from bot.handlers import admin, admin_emoji, admin_orders, admin_posts, admin_products, admin_promos, admin_reply, channel_posts, start, user_order


from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    settings = get_settings()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    # Используем MemoryStorage для состояний FSM (для локального теста достаточно)
    dp = Dispatcher(storage=MemoryStorage())

    # Инициализация БД
    await init_db()

    # Подключение роутеров
    dp.include_router(start.router)
    dp.include_router(admin.router)
    dp.include_router(admin_emoji.router)
    dp.include_router(admin_posts.router)
    dp.include_router(admin_products.router)
    dp.include_router(admin_orders.router)
    dp.include_router(admin_promos.router)
    dp.include_router(admin_reply.router)
    dp.include_router(channel_posts.router)
    dp.include_router(user_order.router)

    logging.info(f"Bot authorized as @{settings.bot_username}")
    
    # Удаляем вебхук перед запуском polling
    await bot.delete_webhook(drop_pending_updates=True)

    try:
        await dp.start_polling(
            bot,
            allowed_updates=["message", "callback_query", "channel_post"],
        )
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
