from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from sqlalchemy.ext.asyncio import AsyncSession

from bot import strings
from bot.config import get_settings
from bot.keyboards.admin import staff_consultation_kb, staff_order_kb
from bot.models import Order
from bot.services.formatting import h


def _staff_chat_id() -> int:
    settings = get_settings()
    return int(settings.staff_channel_id or settings.admin_chat_id)


def _reply_url(order: Order) -> str | None:
    customer = getattr(order, "customer", None)
    if not customer or not customer.telegram_user_id:
        return None
    bot_username = get_settings().bot_username.lstrip("@")
    return f"https://t.me/{bot_username}?start=staff_reply_{order.id}"


def _source_label(order: Order) -> str:
    if getattr(order, "source_post_id", None) and getattr(order, "product", None):
        return f"пост · {order.product.title}"
    if getattr(order, "source_post_id", None):
        return "пост"
    if getattr(order, "product", None):
        return f"бот · {order.product.title}"
    return "бот"


def _services_lines(order: Order) -> list[str]:
    lines = []
    if getattr(order, "product", None) and order.product.price:
        lines.append(f"Букет — {order.product.price:,} ₽".replace(",", " "))
    if order.delivery_type == "Доставка":
        lines.append("Доставка — от 500 ₽")
    elif order.delivery_type == "Самовывоз":
        lines.append("Самовывоз — 0 ₽")
    if order.additional_services:
        for item in [part.strip() for part in order.additional_services.split(",") if part.strip()]:
            if item.lower().startswith("упаков"):
                lines.append("Упаковка — 300 ₽")
            elif item.lower().startswith("открыт"):
                lines.append("Открытка — 150 ₽")
            else:
                lines.append(item)
    return lines


def _order_status_label(status: str) -> str:
    return strings.ORDER_STATUS_LABELS.get(status, status)


def _consultation_status_label(status: str) -> str:
    return strings.CONSULTATION_STATUS_LABELS.get(status, status)


def render_staff_order_card(order: Order) -> str:
    customer = order.customer
    payment_label = order.payment_status or "pending_manual"
    payment_text = {
        "pending_manual": "после подтверждения",
        "waiting_payment": "ожидает оплату",
        "payment_link_sent": "ссылка отправлена",
        "paid": "оплачен",
        "cancelled": "отменена",
    }.get(payment_label, payment_label)
    lines = [
        f"🌸 <b>Заказ №{order.id}</b>",
        "",
        f"Статус: {_order_status_label(order.status)}",
        f"Оплата: {payment_text}",
        "",
        f"Клиент: @{h(customer.username)}" if customer.username else f"Клиент: {h(customer.full_name or '—')}",
        f"Телефон: {h(order.phone or customer.phone or '—')}",
        f"Источник: {h(_source_label(order))}",
        "",
        f"Букет: {h(order.product.title if getattr(order, 'product', None) else 'Индивидуальный заказ')}",
        f"Получение: {h(order.delivery_type or '—')}",
        f"Дата: {h(order.date_text or '—')}",
        f"Время: {h(order.time_text or '—')}",
        f"Адрес: {h(order.delivery_address or '—')}",
        "",
        "Состав заказа:",
    ]
    lines.extend(h(item) for item in (_services_lines(order) or ["—"]))
    if order.card_text and order.card_text != "-":
        lines.extend(["", f"Открытка: {h(order.card_text)}"])
    if getattr(order, "promo_code", None) and order.promo_code != "-":
        lines.append(f"Промокод: {h(order.promo_code)}")
    
    points_spent = getattr(order, "points_spent", 0)
    if points_spent and points_spent > 0:
        lines.append(f"Списано баллов: {points_spent} ₽")
    
    if order.total_amount:
        total_prefix = "от " if order.delivery_type == "Доставка" else ""
        lines.extend(["", f"Итого: {total_prefix}{str(f'{order.total_amount:,}').replace(',', ' ')} ₽"])
    
    if order.comment and order.comment != "-":
        lines.extend(["", f"Комментарий: {h(order.comment)}"])
    return "\n".join(lines)


def render_staff_consultation_card(order: Order) -> str:
    customer = order.customer
    interest = order.product.title if getattr(order, "product", None) else "общий вопрос"
    comment = order.comment if isinstance(order.comment, str) else None
    return "\n".join([
        f"🌿 <b>Консультация №{order.id}</b>",
        "",
        f"Статус: {_consultation_status_label(order.status)}",
        f"Клиент: @{h(customer.username)}" if customer.username else f"Клиент: {h(customer.full_name or '—')}",
        f"Источник: {h(_source_label(order))}",
        f"Интерес: {h(interest)}",
        "",
        "Комментарий:",
        h(comment or "Клиент хочет уточнить детали у флориста."),
    ])


async def upsert_staff_order_card(bot: Bot, session: AsyncSession, order: Order) -> int:
    chat_id = _staff_chat_id()
    reply_url = _reply_url(order)
    is_consultation = order.status in {"needs_florist", "consultation_in_progress", "consultation_closed"}
    text = render_staff_consultation_card(order) if is_consultation else render_staff_order_card(order)
    markup = (
        staff_consultation_kb(order.id, reply_url=reply_url)
        if is_consultation
        else staff_order_kb(order.id, order.status, reply_url=reply_url)
    )

    if order.admin_message_id:
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=order.admin_message_id,
                text=text,
                reply_markup=markup,
                parse_mode="HTML",
            )
            return order.admin_message_id
        except TelegramBadRequest:
            pass

    sent = await bot.send_message(chat_id=chat_id, text=text, reply_markup=markup, parse_mode="HTML")
    order.admin_message_id = sent.message_id
    await session.commit()
    return sent.message_id


async def notify_admin_about_order(bot: Bot, session: AsyncSession, order: Order) -> int:
    if _staff_chat_id() == 0:
        return 0
    return await upsert_staff_order_card(bot, session, order)


async def notify_admin_about_florist_lead(bot: Bot, session: AsyncSession, lead: Order) -> int:
    if _staff_chat_id() == 0:
        return 0
    return await upsert_staff_order_card(bot, session, lead)


def customer_status_message(order: Order, status: str) -> str | None:
    messages = {
        "accepted": "Ваш заказ принят. Флорист проверяет наличие и детали доставки.",
        "waiting_payment": "Заказ ждёт оплату. Флорист свяжется с вами по способу оплаты.",
        "paid": "Оплата получена. Передали заказ флористу.",
        "in_progress": "Ваш букет собирают.",
        "ready_for_pickup": "Ваш букет готов к выдаче.",
        "in_delivery": "Букет передан в доставку.",
        "delivered": "Заказ выполнен. Спасибо, что выбрали Bloom Atelier.",
        "cancelled": "Заказ отменён. Если это ошибка, напишите флористу.",
        "consultation_in_progress": "Флорист взял ваш запрос в работу. Скоро вам напишут и помогут с выбором.",
        "consultation_closed": "Консультация завершена. Будем рады помочь снова.",
    }
    return messages.get(status)
