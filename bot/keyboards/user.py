from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, WebAppInfo

from bot.ui.buttons import ibtn, rbtn
from bot.ui_tokens import E, STYLE


def main_menu_kb(mini_app_url: str = "") -> InlineKeyboardMarkup:
    rows = [
        [ibtn("birthday", "День рождения", callback_data="catalog:occasion:birthday")],
        [ibtn("love", "Свидание", callback_data="catalog:occasion:date")],
        [ibtn("sorry", "Извинение", callback_data="catalog:occasion:apology")],
        [ibtn("flower", "Без повода", callback_data="catalog:occasion:just_because")],
        [ibtn("bouquet", "Все букеты", callback_data="user:catalog", style=STYLE["primary"])],
    ]
    if mini_app_url:
        rows.append([
            InlineKeyboardButton(
                text="🛍 Открыть магазин",
                web_app=WebAppInfo(url=mini_app_url),
            )
        ])
    rows.extend([
        [
            ibtn("branch", "Наши магазины", callback_data="user:branches"),
            ibtn("profile", "Мой профиль", callback_data="user:profile"),
        ],
        [ibtn("help", "Написать флористу", callback_data="user:florist_menu")],
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def entry_choice_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [ibtn("success", "Заказать букет", callback_data="order:start_flow", style=STYLE["primary"])],
        [
            ibtn("help", "Задать вопрос", callback_data="order:contact_florist"),
            ibtn("back", "Назад", callback_data="back:main"),
        ],
    ])


def delivery_type_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            ibtn("delivery", "Доставка", callback_data="order:delivery"),
            ibtn("pickup", "Самовывоз", callback_data="order:pickup"),
        ],
        [ibtn("back", "Назад", callback_data="back:product")],
    ])

def services_kb(selected: list | None = None) -> InlineKeyboardMarkup:
    selected = selected or []

    def get_text(key: str, label: str) -> str:
        return f"{E['success']} {label}" if key in selected else label

    return InlineKeyboardMarkup(inline_keyboard=[
        [
            ibtn("package", get_text("packaging", "Упаковка +300 ₽"), callback_data="service:toggle:packaging"),
            ibtn("postcard", get_text("postcard", "Открытка +150 ₽"), callback_data="service:toggle:postcard"),
        ],
        [ibtn("next", "Продолжить", callback_data="service:continue", style=STYLE["primary"])],
        [ibtn("back", "Назад", callback_data="back:time")],
    ])


def time_slots_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="12:00–14:00", callback_data="time:12:00–14:00"), InlineKeyboardButton(text="14:00–16:00", callback_data="time:14:00–16:00")],
        [InlineKeyboardButton(text="16:00–18:00", callback_data="time:16:00–18:00"), InlineKeyboardButton(text="18:00–20:00", callback_data="time:18:00–20:00")],
        [ibtn("comment", "Другое время", callback_data="time:manual")],
        [ibtn("back", "Назад", callback_data="back:date")],
    ])


def time_ambiguous_kb(suggested: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [ibtn("success", f"Да, {suggested}", callback_data=f"time:{suggested}")],
        [ibtn("comment", "Ввести другое", callback_data="time:manual")],
        [ibtn("back", "Назад", callback_data="back:date")],
    ])


def time_suggestion_kb(suggestions: list[str]) -> InlineKeyboardMarkup:
    rows = []
    row = []
    for suggestion in suggestions:
        row.append(InlineKeyboardButton(text=suggestion, callback_data=f"time:{suggestion}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([ibtn("comment", "Ввести точное время", callback_data="time:manual")])
    rows.append([ibtn("back", "Назад", callback_data="back:date")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def date_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            ibtn("date", "Сегодня", callback_data="date:today"),
            ibtn("date", "Завтра", callback_data="date:tomorrow"),
        ],
        [ibtn("comment", "Другая дата", callback_data="date:manual")],
        [ibtn("back", "Назад", callback_data="back:delivery_or_branch")],
    ])


def phone_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[rbtn("phone", "Отправить контакт", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def skip_kb(skip_callback: str, back_callback: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Пропустить", callback_data=skip_callback)],
        [ibtn("back", "Назад", callback_data=back_callback)],
    ])


def branches_kb(branches: list) -> InlineKeyboardMarkup:
    buttons = []
    for branch in branches:
        buttons.append([ibtn("branch", branch.address, callback_data=f"branch_info:{branch.id}")])
    buttons.append([ibtn("back", "Назад", callback_data="back:delivery_type")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def branch_detail_kb(branch_id: int, maps_url: str | None = None, has_product: bool = False) -> InlineKeyboardMarkup:
    buttons = []
    if has_product:
        buttons.append([ibtn("success", "Забрать отсюда", callback_data=f"branch_select:{branch_id}", style=STYLE["success"])])
    if maps_url:
        buttons.append([ibtn("map", "Посмотреть на карте", url=maps_url)])
    buttons.append([ibtn("back", "К списку точек", callback_data="user:branches")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def catalog_card_kb(product_id: int, index: int, total: int, occasion: str | None = None) -> InlineKeyboardMarkup:
    """Карусель каталога с навигацией и счётчиком."""
    nav_row = []
    
    if total > 1:
        if index > 0:
            callback_prefix = f"catalog:occasion:{occasion}:" if occasion else "catalog:page:"
            nav_row.append(ibtn("prev", "←", callback_data=f"{callback_prefix}{index-1}"))
        
        nav_row.append(InlineKeyboardButton(text=f"{index+1} / {total}", callback_data="noop:catalog_counter"))
        
        if index < total - 1:
            callback_prefix = f"catalog:occasion:{occasion}:" if occasion else "catalog:page:"
            nav_row.append(ibtn("next", "→", callback_data=f"{callback_prefix}{index+1}"))
    
    buttons = []
    if nav_row:
        buttons.append(nav_row)
    
    buttons.extend([
        [ibtn("success", "Заказать букет", callback_data=f"catalog:order:{product_id}", style=STYLE["primary"])],
        [ibtn("back", "← В главное меню", callback_data="back:main")],
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def branches_context_kb(branches: list, back_callback: str) -> InlineKeyboardMarkup:
    buttons = []
    for branch in branches:
        buttons.append([ibtn("branch", branch.address, callback_data=f"branch_info:{branch.id}")])
    buttons.append([ibtn("back", "Назад", callback_data=back_callback)])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def branch_detail_context_kb(
    branch_id: int,
    maps_url: str | None = None,
    has_product: bool = False,
    back_callback: str = "back:branches_list",
) -> InlineKeyboardMarkup:
    buttons = []
    if has_product:
        buttons.append([ibtn("success", "Забрать отсюда", callback_data=f"branch_select:{branch_id}", style=STYLE["success"])])
    if maps_url:
        buttons.append([ibtn("map", "Посмотреть на карте", url=maps_url)])
    buttons.append([ibtn("back", "К списку точек", callback_data=back_callback)])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def catalog_list_kb(products: list, page: int, total_pages: int) -> InlineKeyboardMarkup:
    rows = []
    for product in products:
        price_str = f"{product.price} ₽" if product.price is not None else "цена уточняется"
        rows.append([ibtn("bouquet", f"{product.title} · {price_str}", callback_data=f"product:{product.id}")])

    if total_pages > 1:
        nav_row = []
        if page > 0:
            nav_row.append(ibtn("prev", "", callback_data=f"catalog:page:{page-1}"))
        nav_row.append(InlineKeyboardButton(text=f"{page+1}/{total_pages}", callback_data="noop:catalog_page"))
        if page < total_pages - 1:
            nav_row.append(ibtn("next", "", callback_data=f"catalog:page:{page+1}"))
        rows.append(nav_row)

    rows.append([ibtn("choose", "Помочь с выбором", callback_data="user:survey")])
    rows.append([ibtn("back", "Назад", callback_data="back:main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def product_detail_kb(product_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [ibtn("success", "Заказать букет", callback_data=f"catalog:order:{product_id}", style=STYLE["primary"])],
        [ibtn("help", "Задать вопрос", callback_data=f"catalog:florist:{product_id}")],
        [ibtn("back", "Назад к букетам", callback_data="user:catalog")],
    ])


def florist_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [ibtn("help", "Написать флористу", callback_data="order:contact_florist", style=STYLE["primary"])],
        [ibtn("back", "Назад", callback_data="back:main")],
    ])

def profile_kb(channel_url: str | None = None) -> InlineKeyboardMarkup:
    buttons = [
        [ibtn("orders", "Мои заказы", callback_data="user:my_orders")],
    ]
    if channel_url:
        buttons.append([ibtn("posts", "Наш канал", url=channel_url)])
    buttons.append([ibtn("back", "Назад", callback_data="back:main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def florist_write_kb() -> InlineKeyboardMarkup:
    """Клавиатура после того как пользователь написал флористу."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [ibtn("bouquet", "Выбрать букет", callback_data="user:catalog")],
        [ibtn("back", "В главное меню", callback_data="back:main")],
    ])


def survey_recommendations_kb(product_id: int, index: int, total: int) -> InlineKeyboardMarkup:
    nav_row = []
    if index > 0:
        nav_row.append(ibtn("prev", "", callback_data=f"survey_nav:{index-1}"))
    if index < total - 1:
        nav_row.append(ibtn("next", "", callback_data=f"survey_nav:{index+1}"))

    rows = []
    if nav_row:
        rows.append(nav_row)
    rows.extend([
        [ibtn("success", "Заказать букет", callback_data=f"catalog:order:{product_id}", style=STYLE["primary"])],
        [ibtn("help", "Задать вопрос", callback_data=f"catalog:florist:{product_id}")],
        [ibtn("back", "Назад", callback_data="back:survey_budget")],
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def survey_no_results_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [ibtn("help", "Написать флористу", callback_data="order:contact_florist", style=STYLE["primary"])],
        [ibtn("bouquet", "Выбрать букет", callback_data="user:catalog")],
        [ibtn("back", "Назад", callback_data="back:survey_budget")],
    ])


def survey_done_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [ibtn("bouquet", "Выбрать букет", callback_data="user:catalog", style=STYLE["primary"])],
        [ibtn("back", "В главное меню", callback_data="back:main")],
    ])


def florist_lead_after_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [ibtn("success", "Оформить заказ", callback_data="order:start_flow", style=STYLE["primary"])],
        [ibtn("comment", "Добавить комментарий", callback_data="florist:add_comment")],
        [ibtn("bouquet", "Выбрать букет", callback_data="user:catalog")],
        [ibtn("back", "В главное меню", callback_data="back:main")],
    ])


def survey_occasion_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [ibtn("birthday", "День рождения", callback_data="survey:occasion:birthday"), ibtn("love", "Свидание", callback_data="survey:occasion:date")],
        [ibtn("sorry", "Извинение", callback_data="survey:occasion:apology"), ibtn("flower", "Без повода", callback_data="survey:occasion:just_because")],
        [ibtn("office", "Корпоратив", callback_data="survey:occasion:office"), ibtn("other", "Другое", callback_data="survey:occasion:other")],
        [ibtn("back", "Назад", callback_data="back:main")],
    ])


def survey_budget_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="до 3 000 ₽", callback_data="survey:budget:under_3k"), InlineKeyboardButton(text="3 000–5 000 ₽", callback_data="survey:budget:3k_5k")],
        [InlineKeyboardButton(text="5 000–8 000 ₽", callback_data="survey:budget:5k_8k"), InlineKeyboardButton(text="8 000 ₽+", callback_data="survey:budget:over_8k")],
        [ibtn("back", "Назад", callback_data="back:survey_occasion")],
    ])


def confirm_order_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [ibtn("success", "Отправить заявку", callback_data="order:confirm", style=STYLE["success"])],
        [ibtn("edit", "Изменить детали", callback_data="order:edit")],
    ])


def edit_order_kb(data: dict | None = None) -> InlineKeyboardMarkup:
    """Меню редактирования с текущими значениями полей."""
    if not data:
        data = {}

    delivery = data.get("delivery_type", "—")
    date_text = data.get("date_text", "—")
    time_text = data.get("time_text", "—")
    services = data.get("selected_services", [])
    services_label = ", ".join(s.capitalize() for s in services) if services else "нет"
    address = data.get("delivery_address", "—")
    if len(address) > 20:
        address = address[:18] + "…"
    phone = data.get("phone", "—")

    return InlineKeyboardMarkup(inline_keyboard=[
        [ibtn("delivery", f"📦 {delivery}", callback_data="edit:delivery_type")],
        [ibtn("date", f"📅 {date_text}, {time_text}", callback_data="edit:date")],
        [ibtn("package", f"🎁 {services_label}", callback_data="edit:services")],
        [ibtn("branch", f"📍 {address}", callback_data="edit:address")],
        [ibtn("phone", f"📱 {phone}", callback_data="edit:phone")],
        [ibtn("promo", "🎟 Промокод / Баллы", callback_data="edit:promo")],
        [ibtn("back", "← Назад к подтверждению", callback_data="edit:done")],
    ])


def order_success_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [ibtn("orders", "Мои заказы", callback_data="user:my_orders")],
        [ibtn("bouquet", "Выбрать ещё букет", callback_data="user:catalog")],
    ])


def loyalty_kb(points: int) -> InlineKeyboardMarkup:
    buttons = []
    if points > 0:
        buttons.append([ibtn("success", f"Списать {points} ₽", callback_data=f"loyalty:spend:{points}")])
    buttons.append([ibtn("danger", "Не списывать", callback_data="loyalty:skip")])
    buttons.append([ibtn("back", "Назад", callback_data="back:promo")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def promo_loyalty_kb(points: int, has_promo: bool = False, points_spent: int = 0) -> InlineKeyboardMarkup:
    """Объединённый экран: промокод + баллы лояльности."""
    buttons = []

    if not has_promo:
        buttons.append([ibtn("promo", "Ввести промокод", callback_data="promo:enter")])

    if points > 0 and points_spent == 0:
        buttons.append([ibtn("success", f"✨ Списать {points} баллов", callback_data=f"loyalty:spend:{points}")])
    elif points_spent > 0:
        buttons.append([ibtn("danger", f"✨ Отменить списание ({points_spent} ₽)", callback_data="loyalty:cancel")])

    buttons.append([ibtn("next", "Продолжить", callback_data="promo_loyalty:continue", style=STYLE["primary"])])
    buttons.append([ibtn("back", "Назад", callback_data="back:phone")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def demo_payment_kb(order_id: int) -> InlineKeyboardMarkup:
    """Демо-кнопка оплаты. Нажатие симулирует успешную оплату."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [ibtn("success", "💳 Оплатить", callback_data=f"demo_pay:{order_id}", style=STYLE["success"])],
    ])
