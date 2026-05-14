import re
from datetime import datetime, timedelta
from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from bot.db import async_session
from bot.keyboards.user import (
    catalog_list_kb,
    confirm_order_kb,
    date_kb,
    delivery_type_kb,
    entry_choice_kb,
    order_success_kb,
    main_menu_kb,
    phone_kb,
    services_kb,
    skip_kb,
    branches_kb,
    branch_detail_kb,
    branches_context_kb,
    branch_detail_context_kb,
    catalog_card_kb,
    product_detail_kb,
    florist_menu_kb,
    florist_write_kb,
    profile_kb,
    survey_occasion_kb,
    survey_budget_kb,
    time_slots_kb,
    time_suggestion_kb,
    edit_order_kb,
    time_ambiguous_kb,
    survey_no_results_kb,
    survey_done_kb,
    florist_lead_after_kb,
    loyalty_kb,
    demo_payment_kb,
    promo_loyalty_kb
)
from bot.states.order_states import OrderFlow
from bot.services.order_service import (
    create_order_from_fsm, 
    create_florist_lead, 
    create_survey_lead, 
    get_user_orders
)
from bot.services.catalog_service import get_products_by_occasion, get_all_products
from bot.services.notification_service import notify_admin_about_order, notify_admin_about_florist_lead
from bot.services.branch_service import list_active_branches
from bot.services.promo_service import get_active_promo, increment_promo_usage
from bot.config import get_settings
from bot.services.menu_service import MenuManager
from bot.services.message_cleanup import replace_state_error
from bot.services.parsers import normalize_date_input, normalize_time_input
from bot import strings
from bot.ui.buttons import ibtn
from bot.models import Order
from sqlalchemy import select
from bot.config import get_settings

router = Router()

DELIVERY_ESTIMATE = 500
CATALOG_PAGE_SIZE = 5
BRANCHES_CONTEXT_MAIN = "main"
BRANCHES_CONTEXT_ORDER_PICKUP = "order_pickup"


def _main_menu_text(points: int) -> str:
    """Формирует текст главного меню. Не показывает 0 бонусов — это негатив."""
    try:
        pts = int(points)
    except (TypeError, ValueError):
        pts = 0
    if pts > 0:
        bonus_line = strings.MAIN_MENU_BONUS_LINE.format(points=pts)
    else:
        bonus_line = strings.MAIN_MENU_NO_BONUS
    return strings.MAIN_MENU.format(bonus_line=bonus_line)


# ═══════════════════════════════════════════════════════════════════════════════
# ХЕЛПЕРЫ: Форматирование
# ═══════════════════════════════════════════════════════════════════════════════

def format_rub(value: int) -> str:
    return f"{value:,}".replace(",", " ") + " ₽"


def format_total(value: int, with_estimate: bool) -> str:
    return f"от {format_rub(value)}" if with_estimate else format_rub(value)


def build_product_card_text(title: str, description: str | None, price: int | None) -> str:
    safe_description = description or "Состав и детали можно уточнить у флориста."
    price_text = f"от <b>{format_rub(price)}</b>" if price else "Цена уточняется"
    return f"💐 <b>Букет «{title}»</b>\n\n{safe_description}\n\n{price_text}"


def build_services_summary(product_price: int, delivery_type: str | None, selected: list[str]) -> str:
    lines = [strings.CHOOSE_SERVICES, f"Букет: <b>{format_rub(product_price)}</b>"]
    with_estimate = delivery_type == "Доставка"
    if with_estimate:
        lines.append(f"Доставка: <b>от {format_rub(DELIVERY_ESTIMATE)}</b>")
    if "packaging" in selected:
        lines.append("Упаковка: <b>300 ₽</b>")
    if "postcard" in selected:
        lines.append("Открытка: <b>150 ₽</b>")
    total = product_price
    if with_estimate:
        total += DELIVERY_ESTIMATE
    if "packaging" in selected:
        total += 300
    if "postcard" in selected:
        total += 150
    lines.append("")
    lines.append(f"Текущая сумма: <b>{format_total(total, with_estimate)}</b>")
    return "\n".join(lines)


_MONTH_GENITIVE = {
    1: "января", 2: "февраля", 3: "марта", 4: "апреля", 5: "мая",
    6: "июня", 7: "июля", 8: "августа", 9: "сентября", 10: "октября",
    11: "ноября", 12: "декабря",
}


def format_order_date_label(date_text: str | None) -> str:
    if not date_text:
        return "без даты"
    now = datetime.now()
    today = now.strftime("%d.%m")
    tomorrow = (now + timedelta(days=1)).strftime("%d.%m")
    if date_text == today:
        return "сегодня"
    if date_text == tomorrow:
        return "завтра"
    try:
        parsed = datetime.strptime(date_text, "%d.%m")
        month_name = _MONTH_GENITIVE.get(parsed.month, "")
        return f"{parsed.day} {month_name}" if month_name else date_text
    except ValueError:
        return date_text


def selected_services_text(selected: list[str]) -> str | None:
    labels = []
    if "packaging" in selected:
        labels.append("Упаковка")
    if "postcard" in selected:
        labels.append("Открытка")
    return ", ".join(labels) if labels else None


def time_manual_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[ibtn("back", "Назад", callback_data="back:date")]]
    )


# ═══════════════════════════════════════════════════════════════════════════════
# ХЕЛПЕРЫ: Расчёт суммы и навигация
# ═══════════════════════════════════════════════════════════════════════════════

async def calculate_total(state: FSMContext):
    data = await state.get_data()
    product_price = data.get("product_price", 0) or 0
    selected = data.get("selected_services", [])
    services_sum = 0
    if "packaging" in selected:
        services_sum += 300
    if "postcard" in selected:
        services_sum += 150
    base_total = product_price + services_sum
    delivery_type = data.get("delivery_type")
    if delivery_type == "Доставка":
        base_total += DELIVERY_ESTIMATE
    discount_amount = 0
    promo_data = data.get("promo_data")
    if promo_data:
        if promo_data.get("discount_percent"):
            discount_amount = int(base_total * (promo_data["discount_percent"] / 100))
        elif promo_data.get("discount_amount"):
            discount_amount = promo_data["discount_amount"]
    points_spent = data.get("points_spent", 0)
    final_total = max(base_total - discount_amount - points_spent, 0)
    await state.update_data(calculated_total=final_total)
    return format_total(final_total, delivery_type == "Доставка")


# ═══════════════════════════════════════════════════════════════════════════════
# VIEW-ФУНКЦИИ: Отображение экранов заказа
# ═══════════════════════════════════════════════════════════════════════════════

async def view_delivery_type(chat_id, user_id, bot, session, state):
    await state.set_state(OrderFlow.choose_delivery_type)
    mm = MenuManager(bot, session)
    await mm.show_menu(
        chat_id=chat_id, user_id=user_id,
        text=strings.CHOOSE_DELIVERY_TYPE,
        reply_markup=delivery_type_kb(),
        photo_path="assets/bot_ui/delivery_pickup.jpg",
        screen_name="choose_delivery_type"
    )

async def view_date(chat_id, user_id, bot, session, state):
    await state.set_state(OrderFlow.choose_date)
    mm = MenuManager(bot, session)
    await mm.show_menu(
        chat_id=chat_id, user_id=user_id,
        text=strings.CHOOSE_DATE,
        reply_markup=date_kb(),
        screen_name="choose_date"
    )

async def view_time(chat_id, user_id, bot, session, state):
    await state.set_state(OrderFlow.choose_time)
    mm = MenuManager(bot, session)
    await mm.show_menu(
        chat_id=chat_id, user_id=user_id,
        text=strings.CHOOSE_TIME,
        reply_markup=time_manual_kb(),
        screen_name="choose_time"
    )

async def view_services(chat_id, user_id, bot, session, state, selected=None):
    if selected is None:
        data = await state.get_data()
        selected = data.get("selected_services", [])
    await state.set_state(OrderFlow.choose_services)
    mm = MenuManager(bot, session)
    data = await state.get_data()
    product_price = data.get("product_price", 0) or 0
    await mm.show_menu(
        chat_id=chat_id, user_id=user_id,
        text=build_services_summary(product_price, data.get("delivery_type"), selected),
        reply_markup=services_kb(selected),
        photo_path="assets/bot_ui/order_confirm.jpg",
        screen_name="choose_services"
    )

async def render_branches_list(chat_id, user_id, bot, session, state, context: str):
    await state.update_data(branches_context=context)
    branches = await list_active_branches(session)
    if not branches:
        await view_delivery_type(chat_id, user_id, bot, session, state)
        return
    if context == BRANCHES_CONTEXT_ORDER_PICKUP:
        await state.set_state(OrderFlow.choose_branch)
    mm = MenuManager(bot, session)
    await mm.show_menu(
        chat_id=chat_id, user_id=user_id,
        text="📍 <b>Наши магазины</b>\n\nВыберите точку, чтобы посмотреть адрес, график и маршрут.",
        reply_markup=branches_context_kb(
            branches,
            "back:branches" if context == BRANCHES_CONTEXT_MAIN else "back:delivery_type",
        ),
        photo_path="assets/bot_ui/branches.jpg",
        screen_name="branches_list",
    )

async def view_card_text(chat_id, user_id, bot, session, state):
    await state.set_state(OrderFlow.get_card_text)
    mm = MenuManager(bot, session)
    await mm.show_menu(
        chat_id=chat_id, user_id=user_id,
        text=strings.GET_CARD_TEXT,
        reply_markup=skip_kb("skip:card", "back:services"),
        screen_name="get_card_text"
    )

async def view_comment(chat_id, user_id, bot, session, state):
    await state.set_state(OrderFlow.get_comment)
    mm = MenuManager(bot, session)
    data = await state.get_data()
    back_cb = "back:card_text" if "postcard" in data.get("selected_services", []) else "back:services"
    await mm.show_menu(
        chat_id=chat_id, user_id=user_id,
        text=strings.GET_COMMENT,
        reply_markup=skip_kb("skip:comment", back_cb),
        screen_name="get_comment"
    )

async def view_address(chat_id, user_id, bot, session, state):
    await state.set_state(OrderFlow.get_address)
    mm = MenuManager(bot, session)
    await mm.show_menu(
        chat_id=chat_id, user_id=user_id,
        text=strings.GET_ADDRESS,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[ibtn("back", "Назад", callback_data="back:comment")]]),
        screen_name="get_address"
    )

async def view_phone(chat_id, user_id, bot, session, state):
    await state.set_state(OrderFlow.get_phone)
    mm = MenuManager(bot, session)
    await mm.cleanup_menu(user_id, chat_id)
    await bot.send_message(
        chat_id=chat_id,
        text=strings.GET_PHONE,
        reply_markup=phone_kb()
    )

async def view_promo(chat_id, user_id, bot, session, state):
    await state.set_state(OrderFlow.get_promo)
    mm = MenuManager(bot, session)
    await mm.show_menu(
        chat_id=chat_id, user_id=user_id,
        text=strings.GET_PROMO,
        reply_markup=skip_kb("skip:promo", "back:phone"),
        screen_name="get_promo"
    )

async def view_spend_loyalty(chat_id, user_id, bot, session, state):
    await state.set_state(OrderFlow.spend_loyalty)
    from bot.services.order_service import get_or_create_customer
    customer = await get_or_create_customer(session, user_id, "", "")
    mm = MenuManager(bot, session)
    await mm.show_menu(
        chat_id=chat_id, user_id=user_id,
        text=strings.SPEND_LOYALTY.format(points=customer.loyalty_points),
        reply_markup=loyalty_kb(customer.loyalty_points),
        screen_name="spend_loyalty"
    )

async def view_promo_and_loyalty(chat_id, user_id, bot, session, state):
    """Объединённый экран: промокод + баллы лояльности."""
    await state.set_state(OrderFlow.promo_and_loyalty)
    from bot.services.order_service import get_or_create_customer
    customer = await get_or_create_customer(session, user_id, "", "")
    data = await state.get_data()
    promo_data = data.get("promo_data")
    points_spent = data.get("points_spent", 0)
    total_text = await calculate_total(state)
    text_lines = [
        "🎟 <b>Скидки и баллы</b>\n",
        f"Сумма заказа: <b>{total_text}</b>\n",
    ]
    if promo_data:
        discount = f"{promo_data['discount_percent']}%" if promo_data.get("discount_percent") else f"{promo_data.get('discount_amount')} ₽"
        text_lines.append(f"✅ Промокод: <b>{promo_data.get('title') or data.get('promo_code')}</b> (−{discount})")
    if customer.loyalty_points > 0:
        text_lines.append(f"\n✨ Ваши баллы: <b>{customer.loyalty_points} ₽</b>")
        if points_spent > 0:
            text_lines.append(f"Списано: <b>{points_spent} ₽</b>")
    elif customer.loyalty_points == 0 and not promo_data:
        text_lines.append("\nУ вас пока нет баллов и промокодов — можно пропустить.")
    text = "\n".join(text_lines)
    mm = MenuManager(bot, session)
    await mm.show_menu(
        chat_id=chat_id, user_id=user_id,
        text=text,
        reply_markup=promo_loyalty_kb(
            points=customer.loyalty_points,
            has_promo=bool(promo_data),
            points_spent=points_spent,
        ),
        screen_name="promo_and_loyalty"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# ПОДТВЕРЖДЕНИЕ И НАВИГАЦИЯ
# ═══════════════════════════════════════════════════════════════════════════════

async def show_confirmation(chat_id, user_id, state: FSMContext, bot: Bot):
    data = await state.get_data()
    product_price = data.get("product_price", 0) or 0
    delivery_type = data.get("delivery_type", "—")
    services = data.get("selected_services", [])
    
    total_text = await calculate_total(state)
    
    title = data.get("product_title", "Индивидуальный заказ")
    address_label = "Адрес" if delivery_type == "Доставка" else "Точка"
    summary = strings.CONFIRM_ORDER
    summary += (
        f"Букет «{title}» — {format_rub(product_price)}\n"
        f"{'Доставка' if delivery_type == 'Доставка' else 'Самовывоз'} — <b>{'от ' + format_rub(DELIVERY_ESTIMATE) if delivery_type == 'Доставка' else '0 ₽'}</b>\n"
    )
    if "packaging" in services:
        summary += "Упаковка — <b>300 ₽</b>\n"
    if "postcard" in services:
        summary += "Открытка — <b>150 ₽</b>\n"
        if data.get("card_text") and data.get("card_text") != "-":
            summary += f"Текст открытки: {data.get('card_text')}\n"
    summary += (
        f"\nДата: {data.get('date_text', '—')}\n"
        f"Время: {data.get('time_text', '—')}\n"
        f"{address_label}: {data.get('delivery_address', '—')}\n"
        f"Телефон: {data.get('phone', '—')}\n"
    )
    
    promo_data = data.get("promo_data")
    if promo_data:
        discount = f"{promo_data['discount_percent']}%" if promo_data.get("discount_percent") else f"{promo_data.get('discount_amount')} ₽"
        summary += f"\n🎟 Промокод: <b>{promo_data.get('title') or data.get('promo_code')}</b> (-{discount})\n"
        
    points_spent = data.get("points_spent", 0)
    if points_spent > 0:
        summary += f"✨ Списано баллов: <b>{points_spent} ₽</b>\n"
        
    if data.get("comment") and data.get("comment") != "-":
        summary += f"\nКомментарий: {data.get('comment')}\n"
        
    summary += (
        f"\n<b>Итого: {total_text}</b>\n\n"
        "Оплата: после подтверждения флористом.\n"
        "Флорист подтвердит наличие, точную доставку и способ оплаты."
    )
    
    await state.set_state(OrderFlow.confirm)
    
    async with async_session() as session:
        mm = MenuManager(bot, session)
        await mm.show_menu(
            chat_id=chat_id,
            user_id=user_id,
            text=summary,
            reply_markup=confirm_order_kb(),
            photo_path="assets/bot_ui/order_confirm.jpg",
            screen_name="confirm"
        )

async def next_step(chat_id, user_id, bot, state, after_step):
    data = await state.get_data()
    if data.get("is_editing"):
        await state.update_data(is_editing=False)
        await show_confirmation(chat_id, user_id, state, bot)
        return

    async with async_session() as session:
        if after_step == "delivery_type":
            if data.get("delivery_type") == "Самовывоз":
                await render_branches_list(chat_id, user_id, bot, session, state, BRANCHES_CONTEXT_ORDER_PICKUP)
            else:
                await view_date(chat_id, user_id, bot, session, state)
        elif after_step == "date":
            await view_time(chat_id, user_id, bot, session, state)
        elif after_step == "time":
            await view_services(chat_id, user_id, bot, session, state)
        elif after_step == "services":
            selected = data.get("selected_services", [])
            if "postcard" in selected:
                await view_card_text(chat_id, user_id, bot, session, state)
            else:
                await view_comment(chat_id, user_id, bot, session, state)
        elif after_step == "card_text":
            await view_comment(chat_id, user_id, bot, session, state)
        elif after_step == "comment":
            if data.get("delivery_type") == "Доставка":
                await view_address(chat_id, user_id, bot, session, state)
            else:
                await view_phone(chat_id, user_id, bot, session, state)
        elif after_step == "address":
            await view_phone(chat_id, user_id, bot, session, state)
        elif after_step == "phone":
            await view_promo_and_loyalty(chat_id, user_id, bot, session, state)
        elif after_step == "promo":
            await view_promo_and_loyalty(chat_id, user_id, bot, session, state)
        elif after_step == "loyalty":
            await show_confirmation(chat_id, user_id, state, bot)
        elif after_step == "promo_and_loyalty":
            await show_confirmation(chat_id, user_id, state, bot)


# --- КАТАЛОГ И ВЫБОР ТОВАРА ---

async def show_catalog_page(callback: CallbackQuery, bot: Bot, page: int = 0):
    async with async_session() as session:
        from bot.models import Product
        products = await session.scalars(select(Product).where(Product.is_active == True))
        products_list = list(products)
        total = len(products_list)
        
        if total == 0:
            mm = MenuManager(bot, session)
            await mm.show_menu(
                chat_id=callback.message.chat.id, user_id=callback.from_user.id,
                text="💐 <b>Каталог пока пуст</b>\n\nМожно сразу написать флористу и попросить помочь с выбором.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [ibtn("help", "Спросить флориста", callback_data="order:contact_florist")],
                    [ibtn("back", "Назад", callback_data="back:main")]
                ]),
                photo_path="assets/bot_ui/main_menu.jpg",
                screen_name="catalog_empty"
            )
            return

        total_pages = (total + CATALOG_PAGE_SIZE - 1) // CATALOG_PAGE_SIZE
        page = max(0, min(page, total_pages - 1))
        start = page * CATALOG_PAGE_SIZE
        page_products = products_list[start:start + CATALOG_PAGE_SIZE]
        end = start + len(page_products)
        text = "💐 <b>Выберите букет</b>\n\n"
        if total_pages > 1:
            text += f"Букеты {start + 1}–{end} из {total}"
        
        mm = MenuManager(bot, session)
        await mm.show_menu(
            chat_id=callback.message.chat.id, user_id=callback.from_user.id,
            text=text,
            reply_markup=catalog_list_kb(page_products, page, total_pages),
            photo_path="assets/bot_ui/order_menu.jpg",
            screen_name=f"catalog_page_{page}"
        )

@router.callback_query(F.data == "user:catalog")
async def show_catalog_handler(callback: CallbackQuery, bot: Bot):
    await callback.answer()
    await show_catalog_page(callback, bot, page=0)

@router.callback_query(F.data.startswith("catalog:page:"))
async def catalog_nav_handler(callback: CallbackQuery, bot: Bot):
    await callback.answer()
    page = int(callback.data.split(":")[2])
    await show_catalog_page(callback, bot, page=page)


@router.callback_query(F.data == "noop:catalog_page")
async def noop_catalog_page(callback: CallbackQuery):
    await callback.answer()

@router.callback_query(F.data == "noop:catalog_counter")
async def noop_catalog_counter(callback: CallbackQuery):
    await callback.answer()

# --- КАТАЛОГ ПО ПОВОДАМ (КАРУСЕЛЬ) ---

@router.callback_query(F.data.startswith("catalog:occasion:"))
async def catalog_occasion_handler(callback: CallbackQuery, bot: Bot, state: FSMContext):
    """Показать каталог отфильтрованный по поводу (карусель)."""
    await callback.answer()
    
    parts = callback.data.split(":")
    occasion = parts[2]
    index = int(parts[3]) if len(parts) > 3 else 0
    
    async with async_session() as session:
        products = await get_products_by_occasion(session, occasion)
        
        if not products:
            mm = MenuManager(bot, session)
            await mm.show_menu(
                chat_id=callback.message.chat.id,
                user_id=callback.from_user.id,
                text=f"💐 <b>{strings.OCCASION_TITLES.get(occasion, 'Букеты')}</b>\n\nПока нет букетов для этого повода.\n\nМожно посмотреть все букеты или написать флористу.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [ibtn("bouquet", "Все букеты", callback_data="user:catalog")],
                    [ibtn("help", "Спросить флориста", callback_data="order:contact_florist")],
                    [ibtn("back", "← В главное меню", callback_data="back:main")]
                ]),
                photo_path="assets/bot_ui/order_menu.jpg",
                screen_name=f"catalog_occasion_{occasion}_empty"
            )
            return
        
        # Показываем карусель
        index = max(0, min(index, len(products) - 1))
        product = products[index]
        
        # Сохраняем в state для возможности заказа
        await state.update_data(
            catalog_occasion=occasion,
            catalog_index=index,
            catalog_products=[p.id for p in products]
        )
        
        text = build_product_card_text(product.title, product.description, product.price)
        photo = product.photo_file_id or "assets/bot_ui/order_menu.jpg"
        
        mm = MenuManager(bot, session)
        await mm.show_menu(
            chat_id=callback.message.chat.id,
            user_id=callback.from_user.id,
            text=text,
            reply_markup=catalog_card_kb(product.id, index, len(products), occasion),
            photo_path=photo,
            screen_name=f"catalog_occasion_{occasion}_{index}"
        )

@router.callback_query(F.data.startswith("catalog:order:"))
async def catalog_order_handler(callback: CallbackQuery, state: FSMContext, bot: Bot):
    product_id = int(callback.data.split(":")[2])
    async with async_session() as session:
        from bot.models import Product
        product = await session.get(Product, product_id)
        if product and product.is_active:
            await state.update_data(product_id=product.id, product_title=product.title, product_price=product.price)
            # Горячий покупатель из поста — сразу в флоу, без Entry Choice
            data = await state.get_data()
            source_code = data.get("source_code")
            if source_code:
                await view_delivery_type(callback.message.chat.id, callback.from_user.id, bot, session, state)
            else:
                # Из каталога — показываем Entry Choice
                mm = MenuManager(bot, session)
                await mm.show_menu(
                    chat_id=callback.message.chat.id,
                    user_id=callback.from_user.id,
                    text=strings.ENTRY_CHOICE,
                    reply_markup=entry_choice_kb(),
                    photo_path="assets/bot_ui/choose_help.jpg",
                    screen_name="entry_choice"
                )
        elif product and not product.is_active:
            await callback.answer("Этот букет больше не доступен.", show_alert=True)
            return
    await callback.answer()

@router.callback_query(F.data.startswith("catalog:florist:"))
async def catalog_florist_handler(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.answer()
    product_id = int(callback.data.split(":")[2])
    await state.update_data(product_id=product_id)
    await contact_florist_handler(callback, state, bot)

@router.callback_query(F.data.startswith("product:"))
async def product_detail_handler(callback: CallbackQuery, state: FSMContext, bot: Bot):
    product_id = int(callback.data.split(":")[1])
    async with async_session() as session:
        from bot.models import Product
        product = await session.get(Product, product_id)
        if product and product.is_active:
            await state.update_data(product_id=product.id, product_title=product.title, product_price=product.price)
            mm = MenuManager(bot, session)
            text = build_product_card_text(product.title, product.description, product.price)
            photo = product.photo_file_id or "assets/bot_ui/order_menu.jpg"
            await mm.show_menu(
                chat_id=callback.message.chat.id,
                user_id=callback.from_user.id,
                text=text,
                reply_markup=product_detail_kb(product.id),
                photo_path=photo,
                screen_name=f"product_{product.id}"
            )
        elif product and not product.is_active:
            await callback.answer("Этот букет больше не доступен.", show_alert=True)
            return
    await callback.answer()

# --- ФЛОРИСТ И ПОДБОР ---

@router.callback_query(F.data == "user:florist_menu")
async def florist_menu_handler(callback: CallbackQuery, bot: Bot):
    await callback.answer()
    async with async_session() as session:
        mm = MenuManager(bot, session)
        await mm.show_menu(
            chat_id=callback.message.chat.id,
            user_id=callback.from_user.id,
            text=strings.FLORIST_MENU,
            reply_markup=florist_menu_kb(),
            photo_path="assets/bot_ui/florist.jpg",
            screen_name="florist_menu"
        )

@router.callback_query(F.data == "user:survey")
async def start_survey_handler(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.answer()
    await state.clear()
    await state.set_state(OrderFlow.survey_occasion)
    async with async_session() as session:
        mm = MenuManager(bot, session)
        await mm.show_menu(
            chat_id=callback.message.chat.id,
            user_id=callback.from_user.id,
            text=strings.SURVEY_START + "\n\n" + strings.SURVEY_OCCASION,
            reply_markup=survey_occasion_kb(),
            photo_path="assets/bot_ui/choose_help.jpg",
            screen_name="survey_occasion"
        )

@router.callback_query(OrderFlow.survey_occasion, F.data.startswith("survey:occasion:"))
async def process_survey_occasion(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.answer()
    occasion = callback.data.split(":")[2]
    await state.update_data(occasion=occasion)
    await state.set_state(OrderFlow.survey_budget)
    async with async_session() as session:
        mm = MenuManager(bot, session)
        await mm.show_menu(
            chat_id=callback.message.chat.id,
            user_id=callback.from_user.id,
            text=strings.SURVEY_BUDGET,
            reply_markup=survey_budget_kb(),
            photo_path="assets/bot_ui/choose_help.jpg",
            screen_name="survey_budget"
        )

@router.callback_query(OrderFlow.survey_budget, F.data.startswith("survey:budget:"))
async def process_survey_budget(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.answer()
    budget = callback.data.split(":")[2]
    await state.update_data(budget=budget)
    async with async_session() as session:
        data = await state.get_data()
        lead = await create_survey_lead(
            session=session,
            user_id=callback.from_user.id,
            username=callback.from_user.username,
            full_name=callback.from_user.full_name,
            survey_data=data,
        )
        await notify_admin_about_florist_lead(bot, session, lead)
        mm = MenuManager(bot, session)
        await mm.show_menu(
            chat_id=callback.message.chat.id,
            user_id=callback.from_user.id,
            text=strings.SURVEY_DONE,
            reply_markup=survey_done_kb(),
            photo_path="assets/bot_ui/choose_help.jpg",
            screen_name="survey_done"
        )
    await state.clear()


@router.callback_query(F.data.startswith("survey_nav:"))
async def survey_nav_handler(callback: CallbackQuery, bot: Bot):
    await callback.answer()
    await show_catalog_handler(callback, bot)

# --- МОИ ЗАКАЗЫ ---

@router.callback_query(F.data == "user:my_orders")
async def my_orders_handler(callback: CallbackQuery, bot: Bot):
    await callback.answer()
    async with async_session() as session:
        orders = await get_user_orders(session, callback.from_user.id)
        mm = MenuManager(bot, session)
        
        if not orders:
            await mm.show_menu(
                chat_id=callback.message.chat.id,
                user_id=callback.from_user.id,
                text=strings.MY_ORDERS_EMPTY,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [ibtn("bouquet", "Выбрать букет", callback_data="user:catalog")],
                    [ibtn("back", "Назад", callback_data="back:main")],
                ]),
                photo_path="assets/bot_ui/main_menu.jpg",
                screen_name="my_orders_empty"
            )
        else:
            text = strings.MY_ORDERS_LIST
            for o in orders:
                status_label = strings.ORDER_STATUS_LABELS.get(o.status, o.status)
                product_title = o.product.title if getattr(o, "product", None) else "Индивидуальный заказ"
                sum_text = format_total(o.total_amount, o.delivery_type == "Доставка") if o.total_amount else "сумма уточняется"
                date_label = format_order_date_label(o.date_text)
                text += (
                    f"№{o.id} · {date_label} · {status_label}\n"
                    f"{product_title} · {sum_text}\n\n"
                )
            
            await mm.show_menu(
                chat_id=callback.message.chat.id,
                user_id=callback.from_user.id,
                text=text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [ibtn("bouquet", "Выбрать букет", callback_data="user:catalog")],
                    [ibtn("back", "Назад", callback_data="back:main")],
                ]),
                photo_path="assets/bot_ui/main_menu.jpg",
                screen_name="my_orders_list"
            )


@router.callback_query(F.data == "user:profile")
async def profile_handler(callback: CallbackQuery, bot: Bot):
    """Профиль пользователя: бонусы + мои заказы + ссылка на канал."""
    await callback.answer()
    async with async_session() as session:
        from bot.services.order_service import get_or_create_customer
        customer = await get_or_create_customer(
            session, callback.from_user.id,
            callback.from_user.username or "",
            callback.from_user.full_name or ""
        )
        if customer.loyalty_points > 0:
            bonus_line = strings.PROFILE_BONUS_LINE.format(points=customer.loyalty_points)
        else:
            bonus_line = strings.PROFILE_NO_BONUS

        text = strings.PROFILE_TEXT.format(bonus_line=bonus_line)

        settings = get_settings()
        channel_url = None
        if settings.channel_id:
            cid = str(settings.channel_id)
            # Превращаем -100XXXXXXXXXX в https://t.me/c/XXXXXXXXXX
            if cid.startswith("-100"):
                channel_url = f"https://t.me/c/{cid[4:]}"

        mm = MenuManager(bot, session)
        await mm.show_menu(
            chat_id=callback.message.chat.id,
            user_id=callback.from_user.id,
            text=text,
            reply_markup=profile_kb(channel_url=channel_url),
            photo_path="assets/bot_ui/main_menu.jpg",
            screen_name="profile"
        )

# --- АДРЕСА ---

@router.callback_query(F.data == "user:branches")
async def show_branches_handler(callback: CallbackQuery, state: FSMContext | None = None, bot: Bot | None = None):
    await callback.answer()
    if bot is None:
        bot = callback.bot
    async with async_session() as session:
        mm = MenuManager(bot, session)
        branches = await list_active_branches(session)
        if state is not None:
            await state.update_data(branches_context=BRANCHES_CONTEXT_MAIN)
        if branches:
            if state is not None:
                await render_branches_list(
                    callback.message.chat.id,
                    callback.from_user.id,
                    bot,
                    session,
                    state,
                    BRANCHES_CONTEXT_MAIN,
                )
            else:
                await mm.show_menu(
                    chat_id=callback.message.chat.id,
                    user_id=callback.from_user.id,
                    text="📍 <b>Наши магазины</b>\n\nВыберите точку, чтобы посмотреть адрес, график и маршрут.",
                    reply_markup=branches_context_kb(branches, "back:branches"),
                    photo_path="assets/bot_ui/branches.jpg",
                    screen_name="branches_list",
                )
            return
        
        if not branches:
            await mm.show_menu(
                chat_id=callback.message.chat.id,
                user_id=callback.from_user.id,
                text="📍 <b>Самовывоз временно недоступен</b>\n\nСейчас можно оформить доставку или написать флористу.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [ibtn("delivery", "Оформить доставку", callback_data="order:delivery")],
                    [ibtn("help", "Написать флористу", callback_data="order:contact_florist")],
                    [ibtn("back", "Назад", callback_data="back:main")],
                ]),
                photo_path="assets/bot_ui/branches.jpg",
                screen_name="branches_empty"
            )
        else:
            await mm.show_menu(
                chat_id=callback.message.chat.id,
                user_id=callback.from_user.id,
                text="📍 <b>Наши магазины</b>\n\nВыберите точку, чтобы посмотреть адрес, график и маршрут.",
                reply_markup=branches_kb(branches),
                photo_path="assets/bot_ui/branches.jpg",
                screen_name="branches_list"
            )

@router.callback_query(F.data.startswith("branch_info:"))
async def branch_detail_handler(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.answer()
    branch_id = int(callback.data.split(":")[1])
    async with async_session() as session:
        from bot.models import Branch
        branch = await session.get(Branch, branch_id)
        if branch:
            text = (
                f"📍 <b>{branch.title}</b>\n\n"
                f"🏠 Адрес: {branch.address}\n"
                f"⏰ График: {branch.work_hours}\n"
                f"🏪 Самовывоз: доступен сегодня"
            )
            
            data = await state.get_data()
            has_product = data.get("branches_context") == BRANCHES_CONTEXT_ORDER_PICKUP
            text = (
                f"📍 <b>{branch.title}</b>\n\n"
                f"Адрес: {branch.address}\n"
                f"График: {branch.work_hours}"
            )
            
            mm = MenuManager(bot, session)
            await mm.show_menu(
                chat_id=callback.message.chat.id,
                user_id=callback.from_user.id,
                text=text,
                reply_markup=branch_detail_context_kb(branch.id, branch.yandex_maps_url, has_product),
                photo_path="assets/bot_ui/branches.jpg",
                screen_name=f"branch_{branch.id}"
            )

# --- ФЛОУ ЗАКАЗА ---

@router.callback_query(F.data == "order:start_flow")
async def start_order_flow(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.answer()
    data = await state.get_data()
    if not data.get("product_id") and not data.get("source_code"):
        await show_catalog_handler(callback, bot)
        return

    async with async_session() as session:
        await view_delivery_type(callback.message.chat.id, callback.from_user.id, bot, session, state)

@router.callback_query(F.data == "order:contact_florist")
@router.callback_query(F.data == "user:contact_admin")
async def contact_florist_handler(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Показываем экран с просьбой написать сообщение флористу."""
    await callback.answer()
    await state.set_state(OrderFlow.florist_message)
    async with async_session() as session:
        mm = MenuManager(bot, session)
        await mm.show_menu(
            chat_id=callback.message.chat.id,
            user_id=callback.from_user.id,
            text=strings.FLORIST_ASK_MESSAGE,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [ibtn("back", "Назад", callback_data="back:main")]
            ]),
            photo_path="assets/bot_ui/florist.jpg",
            screen_name="florist_ask_message"
        )


@router.message(OrderFlow.florist_message, F.text)
async def process_florist_message(message: Message, state: FSMContext, bot: Bot):
    """Получаем сообщение от пользователя и отправляем флористу."""
    user_text = message.text.strip()
    data = await state.get_data()
    await state.clear()

    async with async_session() as session:
        lead = await create_florist_lead(
            session=session,
            user_id=message.from_user.id,
            username=message.from_user.username,
            full_name=message.from_user.full_name,
            source_post_id=data.get("source_post_id"),
            product_id=data.get("product_id"),
        )
        # Сохраняем текст сообщения как комментарий
        lead.comment = user_text
        await session.commit()

        if data.get("product_id"):
            from bot.models import Product
            lead.product = await session.get(Product, data["product_id"])

        await notify_admin_about_florist_lead(bot, session, lead)

        # Удаляем сообщение пользователя
        try:
            await message.delete()
        except Exception:
            pass

        mm = MenuManager(bot, session)
        await mm.show_menu(
            chat_id=message.chat.id,
            user_id=message.from_user.id,
            text=strings.FLORIST_WAIT,
            reply_markup=florist_write_kb(),
            photo_path="assets/bot_ui/florist.jpg",
            screen_name="florist_wait"
        )

@router.callback_query(F.data == "florist:add_comment")
async def florist_add_comment(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.answer()
    await state.set_state(OrderFlow.get_comment)
    async with async_session() as session:
        mm = MenuManager(bot, session)
        await mm.show_menu(
            chat_id=callback.message.chat.id,
            user_id=callback.from_user.id,
            text="💬 <b>Напишите комментарий для флориста</b>\n\nНапример: «нужен похожий букет до 5 000 ₽».",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[ibtn("danger", "Отмена", callback_data="user:florist_menu")]]),
            screen_name="florist_add_comment"
        )

@router.callback_query(OrderFlow.choose_delivery_type, F.data.startswith("order:"))
@router.callback_query(F.data == "order:delivery") 
async def process_delivery_type(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.answer()
    async with async_session() as session:
        if callback.data == "order:delivery":
            await state.update_data(delivery_type="Доставка")
            await next_step(callback.message.chat.id, callback.from_user.id, bot, state, "delivery_type")
        elif callback.data == "order:pickup":
            await state.update_data(delivery_type="Самовывоз", delivery_address="Самовывоз из мастерской")
            branches = await list_active_branches(session)
            
            if not branches:
                await next_step(callback.message.chat.id, callback.from_user.id, bot, state, "delivery_type")
            else:
                await render_branches_list(
                    callback.message.chat.id,
                    callback.from_user.id,
                    bot,
                    session,
                    state,
                    BRANCHES_CONTEXT_ORDER_PICKUP,
                )

@router.callback_query(OrderFlow.choose_branch, F.data.startswith("branch_select:"))
async def process_branch_selection(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.answer()
    branch_id = int(callback.data.split(":")[1])
    async with async_session() as session:
        from bot.models import Branch
        branch = await session.get(Branch, branch_id)
        if branch:
            await state.update_data(branch_id=branch.id, delivery_address=f"Самовывоз: {branch.title}")
        # Фикс: идём сразу на дату, не через next_step("delivery_type") который снова показывал магазины
        await view_date(callback.message.chat.id, callback.from_user.id, bot, session, state)

# --- DATE & TIME HANDLERS ---

@router.callback_query(OrderFlow.choose_date, F.data.startswith("date:"))
async def process_date_kb(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.answer()
    date_val = callback.data.split(":")[1]
    if date_val == "manual":
        async with async_session() as session:
            mm = MenuManager(bot, session)
            await mm.show_menu(
                chat_id=callback.message.chat.id,
                user_id=callback.from_user.id,
                text="Когда подготовить букет?\n\nНапишите дату в формате 15.05, 15/05 или 15 мая.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[ibtn("back", "Назад", callback_data="back:delivery_or_branch")]]),
                screen_name="date_manual"
            )
        return

    if date_val == "today":
        date_text = datetime.now().strftime("%d.%m")
    elif date_val == "tomorrow":
        date_text = (datetime.now() + timedelta(days=1)).strftime("%d.%m")
    else:
        date_text = date_val

    await state.update_data(date_text=date_text)
    await callback.message.answer(f"📅 Дата: <b>{date_text}</b>")
    
    async with async_session() as session:
        await view_time(callback.message.chat.id, callback.from_user.id, bot, session, state)

@router.message(OrderFlow.choose_date, F.text)
async def process_date_text(message: Message, state: FSMContext, bot: Bot):
    res = normalize_date_input(message.text)
    if res.error:
        await message.answer(
            "Не хочу ошибиться с датой.\n\nНапишите дату в формате 15.05, 15/05 или 15 мая, или выберите кнопку ниже.",
            reply_markup=date_kb()
        )
        return
        
    await state.update_data(date_text=res.date_str)
    await message.answer(f"📅 Понял дату: <b>{res.date_str}</b>")
    
    async with async_session() as session:
        await view_time(message.chat.id, message.from_user.id, bot, session, state)

@router.callback_query(OrderFlow.choose_time, F.data.startswith("time:"))
async def process_time_kb(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.answer()
    choice = callback.data.split(":")[1]
    if choice == "manual":
        async with async_session() as session:
            mm = MenuManager(bot, session)
            await mm.show_menu(
                chat_id=callback.message.chat.id,
                user_id=callback.from_user.id,
                text="К какому времени?\n\nНапишите время в чат. Например: 18:30, 18.30, к 18, вечером.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[ibtn("back", "Назад", callback_data="back:date")]]),
                screen_name="time_manual"
            )
        return

    time_val = choice
    await state.update_data(time_text=time_val)
    await callback.message.answer(f"🕒 Время: <b>{time_val}</b>")
    
    async with async_session() as session:
        await view_services(callback.message.chat.id, callback.from_user.id, bot, session, state)
    await callback.answer()

@router.message(OrderFlow.choose_time, F.text)
async def process_time_text(message: Message, state: FSMContext, bot: Bot):
    res = normalize_time_input(message.text)
    
    if res.error:
        await message.answer(
            "Не смог распознать время. Напишите, например, <b>18:30</b>, <b>к 18</b> или <b>вечером</b>.",
            reply_markup=time_manual_kb()
        )
        return
        
    if res.is_ambiguous:
        if res.suggestions and any("–" in item for item in res.suggestions):
            await message.answer(
                "Вечером обычно удобно так:",
                reply_markup=time_suggestion_kb(res.suggestions)
            )
            return
        suggested = res.suggestions[0]
        await message.answer(
            f"Вы имели в виду <b>{suggested}</b>?",
            reply_markup=time_ambiguous_kb(suggested)
        )
        return

    await state.update_data(time_text=res.time_str)
    await message.answer(f"🕒 Время записал: <b>{res.time_str}</b>")
    
    async with async_session() as session:
        await view_services(message.chat.id, message.from_user.id, bot, session, state)

@router.callback_query(OrderFlow.choose_services, F.data.startswith("service:"))
async def process_service_choice(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.answer()
    action = callback.data.split(":")[1]
    data = await state.get_data()
    selected = data.get("selected_services", [])

    if action == "toggle":
        service = callback.data.split(":")[2]
        if service in selected:
            selected.remove(service)
        else:
            selected.append(service)
        await state.update_data(selected_services=selected)
        async with async_session() as session:
            await view_services(callback.message.chat.id, callback.from_user.id, bot, session, state, selected)
    elif action == "none":
        await state.update_data(selected_services=[])
        await next_step(callback.message.chat.id, callback.from_user.id, bot, state, "services")
    elif action == "continue":
        await next_step(callback.message.chat.id, callback.from_user.id, bot, state, "services")

@router.callback_query(OrderFlow.get_card_text, F.data == "skip:card")
async def skip_card(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.answer()
    await state.update_data(card_text="-")
    await next_step(callback.message.chat.id, callback.from_user.id, bot, state, "card_text")

@router.message(OrderFlow.get_card_text, F.text)
async def process_card_text(message: Message, state: FSMContext, bot: Bot):
    await state.update_data(card_text=message.text)
    async with async_session() as session:
        mm = MenuManager(bot, session)
        await mm.delete_user_message(message)
    await next_step(message.chat.id, message.from_user.id, bot, state, "card_text")

@router.callback_query(OrderFlow.get_comment, F.data == "skip:comment")
async def skip_comment(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.answer()
    await state.update_data(comment="-")
    await next_step(callback.message.chat.id, callback.from_user.id, bot, state, "comment")

@router.message(OrderFlow.get_comment, F.text)
async def process_comment(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    # If it's a comment for lead, update lead in DB
    lead_id = data.get("current_lead_id")
    if lead_id:
        async with async_session() as session:
            from bot.models import Order
            lead = await session.get(Order, lead_id)
            if lead:
                lead.comment = message.text
                await session.commit()
            await message.answer("✅ Комментарий добавлен. Флорист скоро свяжется с вами.")
            await state.update_data(current_lead_id=None)
            await cancel_order(None, state, bot, message)
            return

    await state.update_data(comment=message.text)
    async with async_session() as session:
        mm = MenuManager(bot, session)
        await mm.delete_user_message(message)
    await next_step(message.chat.id, message.from_user.id, bot, state, "comment")

@router.message(OrderFlow.get_address, F.text)
async def process_address(message: Message, state: FSMContext, bot: Bot):
    await state.update_data(delivery_address=message.text)
    async with async_session() as session:
        mm = MenuManager(bot, session)
        await mm.delete_user_message(message)
    await next_step(message.chat.id, message.from_user.id, bot, state, "address")

_PHONE_RE = re.compile(r"^\+?[\d\s\-\(\)]{7,15}$")


@router.message(OrderFlow.get_phone, F.contact | F.text)
async def process_phone(message: Message, state: FSMContext, bot: Bot):
    if message.contact:
        phone = message.contact.phone_number
    else:
        raw = (message.text or "").strip()
        if not _PHONE_RE.match(raw):
            await message.answer(
                "Пожалуйста, введите корректный номер телефона.\n\nНапример: +7 999 123-45-67 или нажмите кнопку «Отправить контакт».",
                reply_markup=phone_kb(),
            )
            return
        phone = raw
    await state.update_data(phone=phone)
    async with async_session() as session:
        mm = MenuManager(bot, session)
        await mm.delete_user_message(message)
    await next_step(message.chat.id, message.from_user.id, bot, state, "phone")

@router.callback_query(OrderFlow.get_promo, F.data == "skip:promo")
async def skip_promo(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.answer()
    await state.update_data(promo_code="-")
    # Возвращаемся на объединённый экран
    async with async_session() as session:
        await view_promo_and_loyalty(
            callback.message.chat.id, callback.from_user.id, bot, session, state
        )

@router.message(OrderFlow.get_promo, F.text)
async def process_promo(message: Message, state: FSMContext, bot: Bot):
    promo_code = message.text.strip().upper()
    async with async_session() as session:
        promo = await get_active_promo(session, promo_code)
        mm = MenuManager(bot, session)
        await mm.delete_user_message(message)
        
        if promo:
            await state.update_data(
                promo_code=promo_code,
                promo_data={
                    "title": promo.title,
                    "discount_percent": promo.discount_percent,
                    "discount_amount": promo.discount_amount,
                    "free_delivery": promo.free_delivery
                }
            )
            await message.answer(strings.PROMO_APPLIED.format(
                title=promo.title or promo.code,
                discount=f"{promo.discount_percent}%" if promo.discount_percent else f"{promo.discount_amount} ₽"
            ))
        else:
            await state.update_data(promo_code="-", promo_data=None)
            await message.answer(strings.PROMO_NOT_FOUND)
            
    # Возвращаемся на объединённый экран с обновлённой суммой
    async with async_session() as session:
        await view_promo_and_loyalty(
            message.chat.id, message.from_user.id, bot, session, state
        )


# --- LOYALTY ---
@router.callback_query(OrderFlow.spend_loyalty, F.data.startswith("loyalty:spend:"))
async def process_loyalty_spend_callback(callback: CallbackQuery, state: FSMContext, bot: Bot):
    points = int(callback.data.split(":")[2])
    await state.update_data(points_spent=points)
    await callback.answer(strings.POINTS_APPLIED.format(points=points))
    await next_step(callback.message.chat.id, callback.from_user.id, bot, state, "loyalty")

@router.callback_query(OrderFlow.spend_loyalty, F.data == "loyalty:skip")
async def process_loyalty_skip(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await state.update_data(points_spent=0)
    await callback.answer()
    await next_step(callback.message.chat.id, callback.from_user.id, bot, state, "loyalty")

@router.message(OrderFlow.spend_loyalty, F.text)
async def process_loyalty_spend_message(message: Message, state: FSMContext, bot: Bot):
    if not message.text.isdigit():
        await message.answer("Пожалуйста, введите число или выберите вариант кнопкой.")
        return
    
    points_to_spend = int(message.text)
    async with async_session() as session:
        from bot.services.order_service import get_or_create_customer
        customer = await get_or_create_customer(session, message.from_user.id, "", "")
        
        if points_to_spend > customer.loyalty_points:
            await message.answer(f"У вас всего {customer.loyalty_points} ₽. Введите сумму меньше или равно балансу.")
            return
            
        await state.update_data(points_spent=points_to_spend)
        await message.answer(strings.POINTS_APPLIED.format(points=points_to_spend))
        
        mm = MenuManager(bot, session)
        await mm.delete_user_message(message)
        
    await next_step(message.chat.id, message.from_user.id, bot, state, "loyalty")


# --- ОБЪЕДИНЁННЫЙ ЭКРАН: ПРОМОКОД + БАЛЛЫ ---

@router.callback_query(OrderFlow.promo_and_loyalty, F.data == "promo:enter")
async def promo_enter_handler(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Переключаем в режим ввода промокода."""
    await callback.answer()
    await state.set_state(OrderFlow.get_promo)
    async with async_session() as session:
        mm = MenuManager(bot, session)
        await mm.show_menu(
            chat_id=callback.message.chat.id,
            user_id=callback.from_user.id,
            text="🎟 <b>Введите промокод</b>\n\nНапишите код сообщением в чат.",
            reply_markup=skip_kb("skip:promo", "back:promo_loyalty"),
            screen_name="enter_promo"
        )


@router.callback_query(OrderFlow.promo_and_loyalty, F.data.startswith("loyalty:spend:"))
async def promo_loyalty_spend_handler(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Списать баллы на объединённом экране."""
    points = int(callback.data.split(":")[2])
    await state.update_data(points_spent=points)
    await callback.answer(f"✅ Списано {points} ₽")
    # Перерисовываем экран с обновлённой суммой
    async with async_session() as session:
        await view_promo_and_loyalty(
            callback.message.chat.id, callback.from_user.id, bot, session, state
        )


@router.callback_query(OrderFlow.promo_and_loyalty, F.data == "loyalty:cancel")
async def promo_loyalty_cancel_spend_handler(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Отменить списание баллов."""
    await state.update_data(points_spent=0)
    await callback.answer("Списание отменено")
    async with async_session() as session:
        await view_promo_and_loyalty(
            callback.message.chat.id, callback.from_user.id, bot, session, state
        )


@router.callback_query(OrderFlow.promo_and_loyalty, F.data == "promo_loyalty:continue")
async def promo_loyalty_continue_handler(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Продолжить к подтверждению."""
    await callback.answer()
    await next_step(callback.message.chat.id, callback.from_user.id, bot, state, "promo_and_loyalty")


@router.callback_query(OrderFlow.get_promo, F.data == "back:promo_loyalty")
async def back_to_promo_loyalty(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Вернуться из ввода промокода на объединённый экран."""
    await callback.answer()
    async with async_session() as session:
        await view_promo_and_loyalty(
            callback.message.chat.id, callback.from_user.id, bot, session, state
        )


# --- EDIT ORDER ---
@router.callback_query(OrderFlow.confirm, F.data == "order:edit")
async def show_edit_menu(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    async with async_session() as session:
        mm = MenuManager(bot, session)
        await mm.show_menu(
            chat_id=callback.message.chat.id,
            user_id=callback.from_user.id,
            text="✏️ <b>Что хотите изменить?</b>\n\nНажмите на поле — измените его и вернётесь к подтверждению.",
            reply_markup=edit_order_kb(data),
            screen_name="edit_menu"
        )
    await callback.answer()

@router.callback_query(OrderFlow.edit, F.data.startswith("edit:"))
async def edit_field(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.answer()
    field = callback.data.split(":")[1]
    
    if field == "done":
        await state.update_data(is_editing=False)
        await show_confirmation(callback.message.chat.id, callback.from_user.id, state, bot)
        await callback.answer()
        return

    await state.update_data(is_editing=True)
    async with async_session() as session:
        if field == "delivery_type":
            await view_delivery_type(callback.message.chat.id, callback.from_user.id, bot, session, state)
        elif field == "date":
            await view_date(callback.message.chat.id, callback.from_user.id, bot, session, state)
        elif field == "time":
            await view_time(callback.message.chat.id, callback.from_user.id, bot, session, state)
        elif field == "services":
            await view_services(callback.message.chat.id, callback.from_user.id, bot, session, state)
        elif field == "address":
            data = await state.get_data()
            if data.get("delivery_type") == "Доставка":
                await view_address(callback.message.chat.id, callback.from_user.id, bot, session, state)
            else:
                branches = await list_active_branches(session)
                if branches:
                    await render_branches_list(
                        callback.message.chat.id,
                        callback.from_user.id,
                        bot,
                        session,
                        state,
                        BRANCHES_CONTEXT_ORDER_PICKUP,
                    )
        elif field == "phone":
            await view_phone(callback.message.chat.id, callback.from_user.id, bot, session, state)
        elif field == "promo":
            await view_promo_and_loyalty(callback.message.chat.id, callback.from_user.id, bot, session, state)
            
    await callback.answer()


@router.callback_query(OrderFlow.confirm, F.data == "order:confirm")
async def confirm_order(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.answer()
    data = await state.get_data()
    async with async_session() as session:
        promo_code = data.get("promo_code")
        if promo_code and promo_code != "-":
            promo = await get_active_promo(session, promo_code)
            if promo:
                used = await increment_promo_usage(session, promo)
                if not used:
                    # Promo limit was reached by a concurrent request
                    await callback.message.answer("⚠️ Промокод уже исчерпан. Заказ оформлен без скидки.")
                    await state.update_data(promo_code="-", promo_data=None)
                    data = await state.get_data()

        # Calculate final total for DB
        total_str = await calculate_total(state)
        # Handle cases where total_str might be "от 1 200 ₽"
        clean_total_str = total_str.replace("от ", "").replace(" ₽", "").replace(" ", "").replace(",", "")
        try:
            total_val = int(clean_total_str)
        except ValueError:
            total_val = 0

        order = await create_order_from_fsm(
            session=session,
            user_id=callback.from_user.id,
            username=callback.from_user.username,
            full_name=callback.from_user.full_name,
            data={
                **data,
                "total_amount": total_val,
                "payment_status": "pending_payment",
                "payment_method": "demo",
                "additional_services": selected_services_text(data.get("selected_services", [])),
            }
        )
        await session.refresh(order, attribute_names=["customer", "product"])

        # Deduct loyalty points atomically within same transaction
        points_spent = data.get("points_spent", 0)
        if points_spent > 0:
            if order.customer.loyalty_points >= points_spent:
                order.customer.loyalty_points -= points_spent
            else:
                points_spent = order.customer.loyalty_points
                order.customer.loyalty_points = 0
            order.points_spent = points_spent

        await session.commit()
        await notify_admin_about_order(bot, session, order)

        # Показываем экран с кнопкой "Оплатить" (демо)
        payment_text = (
            f"🌸 <b>Заказ №{order.id} оформлен</b>\n\n"
            f"Сумма к оплате: <b>{format_total(total_val, data.get('delivery_type') == 'Доставка')}</b>\n\n"
            "Нажмите кнопку ниже для оплаты."
        )
        reply_markup = demo_payment_kb(order.id)

        mm = MenuManager(bot, session)
        await mm.show_menu(
            chat_id=callback.message.chat.id,
            user_id=callback.from_user.id,
            text=payment_text,
            reply_markup=reply_markup,
            photo_path="assets/bot_ui/main_menu.jpg",
            screen_name="demo_payment"
        )
    await state.clear()


@router.callback_query(F.data.startswith("demo_pay:"))
async def demo_payment_handler(callback: CallbackQuery, bot: Bot):
    """Демо-оплата: нажал кнопку → заказ оплачен."""
    await callback.answer("✅ Оплата прошла успешно!", show_alert=True)
    order_id = int(callback.data.split(":")[1])

    async with async_session() as session:
        order = await session.get(Order, order_id)
        if order:
            order.status = "paid"
            order.payment_status = "paid"
            await session.commit()
            await session.refresh(order, attribute_names=["customer", "product"])

            # Обновляем карточку в Staff Channel
            await notify_admin_about_order(bot, session, order)

            # Уведомляем клиента об успешной оплате
            success_text = (
                f"✅ <b>Оплата прошла успешно!</b>\n\n"
                f"Заказ №{order.id} передан флористу.\n"
                "Мы начнём собирать ваш букет и напишем, когда он будет готов.\n\n"
                "Обычно отвечаем в течение 5–10 минут."
            )
            reply_markup = order_success_kb()

            mm = MenuManager(bot, session)
            await mm.show_menu(
                chat_id=callback.message.chat.id,
                user_id=callback.from_user.id,
                text=success_text,
                reply_markup=reply_markup,
                photo_path="assets/bot_ui/main_menu.jpg",
                screen_name="order_success"
            )


# --- НАВИГАЦИЯ НАЗАД ---
@router.callback_query(F.data.startswith("back:"))
async def process_back(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.answer()
    step = callback.data.split(":")[1]
    if step == "main":
        await cancel_order(callback, state, bot)
        return
    
    async with async_session() as session:
        if step == "product":
            data = await state.get_data()
            if data.get("product_id"):
                callback.data = f"product:{data['product_id']}"
                await product_detail_handler(callback, state, bot)
            else:
                await show_catalog_handler(callback, bot)
        elif step == "delivery_type":
            await view_delivery_type(callback.message.chat.id, callback.from_user.id, bot, session, state)
        elif step == "delivery_or_branch":
            data = await state.get_data()
            if data.get("delivery_type") == "Доставка":
                await view_delivery_type(callback.message.chat.id, callback.from_user.id, bot, session, state)
            else:
                branches = await list_active_branches(session)
                if not branches:
                    await view_delivery_type(callback.message.chat.id, callback.from_user.id, bot, session, state)
                else:
                    await render_branches_list(
                        callback.message.chat.id,
                        callback.from_user.id,
                        bot,
                        session,
                        state,
                        BRANCHES_CONTEXT_ORDER_PICKUP,
                    )
        elif step == "branches":
            data = await state.get_data()
            if data.get("branches_context") == BRANCHES_CONTEXT_ORDER_PICKUP:
                await view_delivery_type(callback.message.chat.id, callback.from_user.id, bot, session, state)
            else:
                await cancel_order(callback, state, bot)
        elif step == "branches_list":
            data = await state.get_data()
            await render_branches_list(
                callback.message.chat.id,
                callback.from_user.id,
                bot,
                session,
                state,
                data.get("branches_context", BRANCHES_CONTEXT_MAIN),
            )
        elif step == "date":
            await view_date(callback.message.chat.id, callback.from_user.id, bot, session, state)
        elif step == "time":
            await view_time(callback.message.chat.id, callback.from_user.id, bot, session, state)
        elif step == "services":
            await view_services(callback.message.chat.id, callback.from_user.id, bot, session, state)
        elif step == "card_text":
            await view_card_text(callback.message.chat.id, callback.from_user.id, bot, session, state)
        elif step == "comment":
            await view_comment(callback.message.chat.id, callback.from_user.id, bot, session, state)
        elif step == "address":
            await view_address(callback.message.chat.id, callback.from_user.id, bot, session, state)
        elif step == "phone":
            await view_phone(callback.message.chat.id, callback.from_user.id, bot, session, state)
        elif step == "promo":
            await view_phone(callback.message.chat.id, callback.from_user.id, bot, session, state)
        elif step == "loyalty":
            await view_promo(callback.message.chat.id, callback.from_user.id, bot, session, state)
        elif step == "promo_loyalty":
            await view_promo_and_loyalty(callback.message.chat.id, callback.from_user.id, bot, session, state)
        elif step == "survey_occasion":
            await state.set_state(OrderFlow.survey_occasion)
            mm = MenuManager(bot, session)
            await mm.show_menu(
                chat_id=callback.message.chat.id,
                user_id=callback.from_user.id,
                text=strings.SURVEY_START + "\n\n" + strings.SURVEY_OCCASION,
                reply_markup=survey_occasion_kb(),
                photo_path="assets/bot_ui/choose_help.jpg",
                screen_name="survey_occasion"
            )
        elif step == "survey_budget":
            await state.set_state(OrderFlow.survey_budget)
            mm = MenuManager(bot, session)
            await mm.show_menu(
                chat_id=callback.message.chat.id,
                user_id=callback.from_user.id,
                text=strings.SURVEY_BUDGET,
                reply_markup=survey_budget_kb(),
                photo_path="assets/bot_ui/choose_help.jpg",
                screen_name="survey_budget"
            )

@router.callback_query(F.data == "order:cancel")
async def cancel_order(callback: CallbackQuery, state: FSMContext, bot: Bot, message_override=None):
    if callback: await callback.answer()
    await state.clear()
    async with async_session() as session:
        from bot.services.order_service import get_or_create_customer
        msg = callback.message if callback else message_override
        user_id = callback.from_user.id if callback else msg.chat.id
        customer = await get_or_create_customer(session, user_id, "", "")
        
        mm = MenuManager(bot, session)
        await mm.show_menu(
            chat_id=msg.chat.id, user_id=user_id,
            text=_main_menu_text(customer.loyalty_points),
            reply_markup=main_menu_kb(mini_app_url=get_settings().mini_app_url),
            photo_path="assets/bot_ui/main_menu.jpg",
            screen_name="main_menu"
        )


# --- ОШИБКИ И НЕВЕРНЫЕ ФОРМАТЫ ---

@router.message(F.photo | F.sticker | F.document | F.audio | F.video | F.voice | F.video_note)
async def handle_non_text(message: Message, state: FSMContext, bot: Bot):
    current_state = await state.get_state()
    # Ignore if in AdminPostFlow or AdminProductFlow which expect photos
    if current_state and (current_state.startswith("AdminPostFlow:") or current_state.startswith("AdminProductFlow:")):
        return
        
    async with async_session() as session:
        mm = MenuManager(bot, session)
        await mm.delete_user_message(message)
        await replace_state_error(message, state, strings.NON_TEXT_ERROR, parse_mode=None)


@router.message(OrderFlow.choose_delivery_type)
@router.message(OrderFlow.choose_branch)
@router.message(OrderFlow.choose_services)
@router.message(OrderFlow.confirm)
@router.message(OrderFlow.survey_occasion)
@router.message(OrderFlow.survey_budget)
async def handle_text_on_callback_states(message: Message, state: FSMContext, bot: Bot):
    async with async_session() as session:
        mm = MenuManager(bot, session)
        await mm.delete_user_message(message)
        await replace_state_error(message, state, strings.WRONG_TEXT_ERROR, parse_mode=None)

async def process_no_services(callback: CallbackQuery, state: FSMContext, bot: Bot):
    # This is a proxy for the tests, actually mapped to "service:none" in process_service_choice
    # But some older tests might call it directly, so let's keep it compatible
    await state.update_data(selected_services=[])
    await next_step(callback.message.chat.id, callback.from_user.id, bot, state, "services")

async def process_services_continue(callback: CallbackQuery, state: FSMContext, bot: Bot):
    # Proxy for tests
    await next_step(callback.message.chat.id, callback.from_user.id, bot, state, "services")

async def process_date_manual(message: Message, state: FSMContext, bot: Bot):
    # Proxy for tests calling old manual input handler
    await process_date_text(message, state, bot)

async def process_time_manual(message: Message, state: FSMContext, bot: Bot):
    # Proxy for tests calling old manual input handler
    await process_time_text(message, state, bot)
