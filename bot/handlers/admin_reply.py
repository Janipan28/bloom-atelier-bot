from datetime import datetime, timedelta

from aiogram import F, Bot, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy import select

from bot.db import async_session
from bot.models import Order, StaffReplySession
from bot.states.admin_states import AdminReplyFlow

router = Router()


@router.message(AdminReplyFlow.get_message, F.text)
async def send_staff_reply(message: Message, state: FSMContext, bot: Bot) -> None:
    data = await state.get_data()
    reply_session_id = data.get("reply_session_id")
    if not reply_session_id:
        await state.clear()
        return

    async with async_session() as session:
        reply_session = await session.get(StaffReplySession, reply_session_id)
        if not reply_session or not reply_session.is_active or reply_session.expires_at < datetime.utcnow():
            await state.clear()
            await message.answer("Сессия ответа истекла. Откройте заказ заново.")
            return

        order = await session.get(Order, reply_session.entity_id)
        if not order:
            await state.clear()
            await message.answer("Заказ или консультация не найдены.")
            return

        await bot.send_message(
            reply_session.customer_id,
            f"💬 <b>Сообщение от флориста по заказу №{order.id}</b>\n\n{message.text}",
            parse_mode="HTML",
        )
        reply_session.is_active = False
        await session.commit()

    await state.clear()
    await message.answer("Сообщение отправлено клиенту.")


async def activate_reply_session(admin_id: int, order_id: int) -> StaffReplySession | None:
    async with async_session() as session:
        order = await session.scalar(select(Order).where(Order.id == order_id))
        if not order:
            return None
        existing = await session.scalars(
            select(StaffReplySession).where(StaffReplySession.admin_id == admin_id, StaffReplySession.is_active == True)
        )
        for row in list(existing):
            row.is_active = False

        reply_session = StaffReplySession(
            admin_id=admin_id,
            customer_id=order.customer.telegram_user_id,
            entity_type="order",
            entity_id=order.id,
            expires_at=datetime.utcnow() + timedelta(minutes=15),
            is_active=True,
        )
        session.add(reply_session)
        await session.commit()
        await session.refresh(reply_session)
        return reply_session
