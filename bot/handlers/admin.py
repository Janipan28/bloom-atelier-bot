import logging
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from bot.config import get_settings
from bot.keyboards.admin import admin_menu_kb, admin_order_list_kb, florist_lead_kb, order_status_kb
from bot.keyboards.user import main_menu_kb
from bot.db import async_session
from bot.services.admin_service import get_basic_stats, get_recent_orders, get_recent_consultations
from bot.services.menu_service import MenuManager
from bot.services.order_service import get_or_create_customer
from bot.models import Order, OrderStatus
from bot import strings
from bot.handlers.user_order import _main_menu_text
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from bot import strings

router = Router()

CONSULTATION_STATUSES = {OrderStatus.NEEDS_FLORIST.value, "consultation_in_progress", "consultation_closed"}

def is_admin(user_id: int) -> bool:
    return user_id in get_settings().admin_id_set


@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext, bot: Bot) -> None:
    logging.info(f"Admin command received from user {message.from_user.id}")
    if not is_admin(message.from_user.id):
        logging.warning(f"Access denied for user {message.from_user.id}. Admin IDs: {get_settings().admin_id_set}")
        return

    await state.clear()
    async with async_session() as session:
        mm = MenuManager(bot, session)
        await mm.cleanup_menu(message.from_user.id, message.chat.id)
        stats = await get_basic_stats(session)

    logging.info(f"Showing dashboard to admin {message.from_user.id}")
    await message.answer(
        strings.ADMIN_DASHBOARD.format(
            new_orders=stats["new_orders"],
            florist_requests=stats["florist_requests"],
            total_orders=stats["total_orders"],
            total_customers=stats["total_customers"]
        ),
        reply_markup=admin_menu_kb(stats, admin_url=get_settings().admin_panel_url),
    )


@router.callback_query(F.data == "admin:main")
async def admin_main_handler(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    await callback.answer()
    if not is_admin(callback.from_user.id):
        return
    await state.clear()
    async with async_session() as session:
        stats = await get_basic_stats(session)
        mm = MenuManager(bot, session)
        await mm.show_menu(
            chat_id=callback.message.chat.id,
            user_id=callback.from_user.id,
            text=strings.ADMIN_DASHBOARD.format(
                new_orders=stats["new_orders"],
                florist_requests=stats["florist_requests"],
                total_orders=stats["total_orders"],
                total_customers=stats["total_customers"]
            ),
            reply_markup=admin_menu_kb(stats, admin_url=get_settings().admin_panel_url),
            screen_name="admin_dashboard"
        )

@router.callback_query(F.data == "admin:orders")
async def admin_orders_handler(callback: CallbackQuery, bot: Bot) -> None:
    await callback.answer()
    if not is_admin(callback.from_user.id): return
    async with async_session() as session:
        orders = await get_recent_orders(session, limit=10)
        mm = MenuManager(bot, session)
        if not orders:
            stats = await get_basic_stats(session)
            await mm.show_menu(
                chat_id=callback.message.chat.id,
                user_id=callback.from_user.id,
                text="Заказов пока нет.",
                reply_markup=admin_menu_kb(stats, admin_url=get_settings().admin_panel_url),
                screen_name="admin_dashboard"
            )
            return
        await mm.show_menu(
            chat_id=callback.message.chat.id,
            user_id=callback.from_user.id,
            text="📦 <b>Список заказов:</b>",
            reply_markup=admin_order_list_kb(orders),
            screen_name="admin_orders"
        )


@router.callback_query(F.data == "admin:consultations")
async def admin_consultations_handler(callback: CallbackQuery, bot: Bot) -> None:
    await callback.answer()
    if not is_admin(callback.from_user.id): return
    async with async_session() as session:
        consultations = await get_recent_consultations(session, limit=10)
        mm = MenuManager(bot, session)
        if not consultations:
            stats = await get_basic_stats(session)
            await mm.show_menu(
                chat_id=callback.message.chat.id,
                user_id=callback.from_user.id,
                text="Заявок флористу пока нет.",
                reply_markup=admin_menu_kb(stats, admin_url=get_settings().admin_panel_url),
                screen_name="admin_dashboard"
            )
            return
        await mm.show_menu(
            chat_id=callback.message.chat.id,
            user_id=callback.from_user.id,
            text="👩‍🌾 <b>Заявки флористу</b>",
            reply_markup=admin_order_list_kb(consultations, is_consultation=True),
            screen_name="admin_consultations"
        )


@router.callback_query(F.data.startswith("admin_order_view:"))
async def admin_order_view_handler(callback: CallbackQuery, bot: Bot) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.answer()
    order_id = int(callback.data.split(":")[1])
    async with async_session() as session:
        # Use selectinload for customer and related objects
        order = await session.scalar(
            select(Order)
            .where(Order.id == order_id)
            .options(selectinload(Order.customer), selectinload(Order.product))
        )
        if not order:
            return
        
        # Check if it's a consultation status
        is_cons = order.status in CONSULTATION_STATUSES
        labels = strings.CONSULTATION_STATUS_LABELS if is_cons else strings.ORDER_STATUS_LABELS
        status_label = labels.get(order.status, order.status)
        
        if is_cons:
            source_text = "из поста" if order.source_post_id else "через бота"
            interest = order.product.title if getattr(order, "product", None) else "общий вопрос"
            if order.comment and "✨" in order.comment:
                source_text = "подбор букета"
                interest = "индивидуальный подбор"

            text = (
                f"👩‍🌾 <b>Консультация №{order.id}</b>\n\n"
                f"Статус: <b>{status_label}</b>\n"
                f"Клиент: @{order.customer.username or '—'} (ID {order.customer.telegram_user_id})\n"
                f"Источник: {source_text}\n"
                f"Интерес: {interest}\n"
                f"Комментарий: {order.comment or '—'}\n"
            )
            mm = MenuManager(bot, session)
            await mm.show_menu(
                chat_id=callback.message.chat.id,
                user_id=callback.from_user.id,
                text=text,
                reply_markup=florist_lead_kb(order.id, order.customer.telegram_user_id),
                screen_name=f"admin_cons_{order.id}"
            )
        else:
            sum_val = order.total_amount
            sum_text = f"<b>{sum_val:,} ₽</b>".replace(",", " ") if sum_val else "<b>уточняется</b>"
            text = (
                f"📦 <b>Заказ №{order.id}</b>\n\n"
                f"Статус: <b>{status_label}</b>\n"
                f"Клиент: {order.phone or '—'}\n"
                f"Получение: {order.delivery_type or '—'}\n"
                f"Адрес/Точка: {order.delivery_address or '—'}\n"
                f"Службы: {order.additional_services or '—'}\n"
                f"Сумма: {sum_text}\n"
                f"Текст открытки: {order.card_text or '—'}\n"
                f"Комментарий: {order.comment or '—'}\n"
            )
            mm = MenuManager(bot, session)
            await mm.show_menu(
                chat_id=callback.message.chat.id,
                user_id=callback.from_user.id,
                text=text,
                reply_markup=order_status_kb(order.id, order.status, order.customer.telegram_user_id),
                photo_path=order.product.photo_file_id if getattr(order, "product", None) else None,
                screen_name=f"admin_order_{order.id}"
            )


@router.callback_query(F.data == "admin:stats")
async def admin_stats_handler(callback: CallbackQuery, bot: Bot) -> None:
    await callback.answer()
    if not is_admin(callback.from_user.id): return
    async with async_session() as session:
        stats = await get_basic_stats(session)
        mm = MenuManager(bot, session)

        text = (
            "📊 <b>Статистика магазина</b>\n\n"
            f"👥 Клиентов: <b>{stats['total_customers']}</b>\n"
            f"📦 Заказов: <b>{stats['total_orders']}</b>\n"
            f"👩‍🌾 Консультаций: <b>{stats['total_consultations']}</b>\n"
            f"💐 Букетов: <b>{stats['total_products']}</b>\n"
            f"📝 Постов: <b>{stats['total_posts']}</b>\n"
            f"📍 Точек: <b>{stats['total_branches']}</b>\n"
            f"🎟 Промокодов: <b>{stats['total_promos']}</b>\n\n"
            "<b>Источники заявок:</b>\n"
            f"— Из постов: <b>{stats['sources']['posts']}</b>\n"
            f"— Из каталога: <b>{stats['sources']['catalog']}</b>\n"
            f"— Из подбора: <b>{stats['sources']['survey']}</b>\n"
            f"— Через флориста: <b>{stats['sources']['florist']}</b>\n\n"
            "<b>Заказы по статусам:</b>\n"
        )
        for st, count in stats['order_status_counts'].items():
            label = strings.ORDER_STATUS_LABELS.get(st, st)
            text += f"— {label}: <b>{count}</b>\n"

        text += "\n<b>Консультации по статусам:</b>\n"
        for st, count in stats['cons_status_counts'].items():
            label = strings.CONSULTATION_STATUS_LABELS.get(st, st)
            text += f"— {label}: <b>{count}</b>\n"

        await mm.show_menu(
            chat_id=callback.message.chat.id,
            user_id=callback.from_user.id,
            text=text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="↩️ Назад", callback_data="admin:main")]]),
            screen_name="admin_stats"
        )

@router.callback_query(F.data == "admin:branches")
async def admin_branches_handler(callback: CallbackQuery, bot: Bot) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    async with async_session() as session:
        from bot.models import Branch
        branches = await session.scalars(select(Branch))
        mm = MenuManager(bot, session)
        from bot.keyboards.admin import admin_branch_list_kb
        await mm.show_menu(
            chat_id=callback.message.chat.id,
            user_id=callback.from_user.id,
            text="📍 <b>Управление точками самовывоза</b>",
            reply_markup=admin_branch_list_kb(list(branches)),
            screen_name="admin_branches"
        )
    await callback.answer()

@router.callback_query(F.data.startswith("admin_branch_view:"))
async def admin_branch_view_handler(callback: CallbackQuery, bot: Bot) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    branch_id = int(callback.data.split(":")[1])
    async with async_session() as session:
        from bot.models import Branch
        branch = await session.get(Branch, branch_id)
        if not branch: return
        mm = MenuManager(bot, session)
        from bot.keyboards.admin import admin_branch_detail_kb
        text = (
            f"📍 <b>{branch.title}</b>\n\n"
            f"Адрес: {branch.address}\n"
            f"Часы работы: {branch.work_hours}\n"
            f"Статус: {'активен' if branch.is_active else 'выключен'}"
        )
        await mm.show_menu(
            chat_id=callback.message.chat.id,
            user_id=callback.from_user.id,
            text=text,
            reply_markup=admin_branch_detail_kb(branch.id, branch.is_active, branch.yandex_maps_url),
            screen_name=f"admin_branch_{branch.id}"
        )
    await callback.answer()

@router.callback_query(F.data.startswith("admin_toggle_branch:"))
async def admin_toggle_branch_handler(callback: CallbackQuery, bot: Bot) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.answer()
    branch_id = int(callback.data.split(":")[1])
    async with async_session() as session:
        from bot.models import Branch
        branch = await session.get(Branch, branch_id)
        if branch:
            branch.is_active = not branch.is_active
            await session.commit()
    await admin_branch_view_handler(callback, bot)


@router.callback_query(F.data == "admin:main_exit")
async def admin_exit_handler(callback: CallbackQuery, bot: Bot):
    await callback.answer()
    if not is_admin(callback.from_user.id):
        return
    async with async_session() as session:
        mm = MenuManager(bot, session)
        customer = await get_or_create_customer(
            session=session,
            telegram_user_id=callback.from_user.id,
            username=callback.from_user.username,
            full_name=callback.from_user.full_name,
        )
        await mm.show_menu(
            chat_id=callback.message.chat.id,
            user_id=callback.from_user.id,
            text=_main_menu_text(customer.loyalty_points),
            reply_markup=main_menu_kb(mini_app_url=get_settings().mini_app_url),
            photo_path="assets/bot_ui/main_menu.jpg",
            screen_name="main_menu"
        )
    await callback.answer()
