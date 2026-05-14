import logging

from aiogram import F, Bot, Router
from aiogram.types import CallbackQuery
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from bot.config import get_settings
from bot.db import async_session
from bot.models import Order, OrderStatus
from bot.services.loyalty_service import credit_loyalty_points
from bot.services.notification_service import customer_status_message, upsert_staff_order_card

logger = logging.getLogger(__name__)
router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in get_settings().admin_id_set


@router.callback_query(F.data.startswith("admin_order:"))
async def admin_change_status_handler(callback: CallbackQuery, bot: Bot) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.answer()
    _, order_id_raw, new_status = callback.data.split(":", 2)
    order_id = int(order_id_raw)

    async with async_session() as session:
        order = await session.scalar(
            select(Order).where(Order.id == order_id).options(selectinload(Order.customer), selectinload(Order.product))
        )
        if not order:
            return

        order.status = new_status
        await session.commit()
        
        if new_status == OrderStatus.DELIVERED.value:
            await credit_loyalty_points(session, order_id)
        
        await session.refresh(order)
        await upsert_staff_order_card(bot, session, order)

        message = customer_status_message(order, new_status)
        if message:
            try:
                await bot.send_message(order.customer.telegram_user_id, message, parse_mode="HTML")
            except Exception as exc:
                logger.error("Failed to notify user %s: %s", order.customer.telegram_user_id, exc)

    if getattr(callback.message.chat, "type", "") == "private":
        callback.data = f"admin_order_view:{order_id}"
        from bot.handlers.admin import admin_order_view_handler

        await admin_order_view_handler(callback, bot)
