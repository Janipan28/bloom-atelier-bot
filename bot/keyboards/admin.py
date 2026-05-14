from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot import strings
from bot.ui.buttons import ibtn
from bot.ui_tokens import E, STYLE


def admin_menu_kb(stats: dict, admin_url: str = "") -> InlineKeyboardMarkup:
    rows = [
        [ibtn("post", "Быстрый пост", callback_data="admin:post_quick", style=STYLE["primary"])],
        [
            ibtn("orders", f"Заказы ({stats['new_orders']})", callback_data="admin:orders"),
            ibtn("consultation", f"Заявки ({stats['florist_requests']})", callback_data="admin:consultations"),
        ],
        [
            ibtn("bouquet", "Букеты", callback_data="admin:products"),
            ibtn("posts", "Посты", callback_data="admin:posts"),
        ],
        [
            ibtn("promo", "Промо", callback_data="admin:promos"),
            ibtn("branch", "Точки", callback_data="admin:branches"),
        ],
        [
            ibtn("stats", "Статистика", callback_data="admin:stats"),
            ibtn("back", "На главную", callback_data="admin:main_exit"),
        ],
    ]
    if admin_url:
        rows.insert(1, [InlineKeyboardButton(text="🌐 Веб-панель", url=admin_url)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _message_customer_button(user_id: int | None, label: str = "Уточнить у клиента") -> InlineKeyboardButton | None:
    if not user_id:
        return None
    return ibtn("help", label, url=f"tg://user?id={user_id}")


def order_status_kb(order_id: int, status: str = "new", user_id: int | None = None) -> InlineKeyboardMarkup:
    buttons = []

    if status == "new":
        buttons.append([InlineKeyboardButton(text="Принять", callback_data=f"admin_order:{order_id}:accepted")])
        customer_button = _message_customer_button(user_id)
        if customer_button:
            buttons.append([customer_button])
        buttons.append([InlineKeyboardButton(text="Отменить", callback_data=f"admin_order:{order_id}:cancelled")])
    elif status in {"accepted", "waiting_payment", "paid"}:
        buttons.append([
            InlineKeyboardButton(text="В сборке", callback_data=f"admin_order:{order_id}:in_progress"),
            InlineKeyboardButton(text="Ожидает оплату", callback_data=f"admin_order:{order_id}:waiting_payment"),
        ])
        buttons.append([InlineKeyboardButton(text="Отменить", callback_data=f"admin_order:{order_id}:cancelled")])
    elif status in {"in_progress", "assembling"}:
        buttons.append([
            InlineKeyboardButton(text="Готов к выдаче", callback_data=f"admin_order:{order_id}:ready_for_pickup"),
            InlineKeyboardButton(text="Передан в доставку", callback_data=f"admin_order:{order_id}:in_delivery"),
        ])
        customer_button = _message_customer_button(user_id, "Написать клиенту")
        if customer_button:
            buttons.append([customer_button])
    elif status in {"ready", "ready_for_pickup", "delivery", "in_delivery"}:
        buttons.append([InlineKeyboardButton(text="Доставлен", callback_data=f"admin_order:{order_id}:delivered")])
        customer_button = _message_customer_button(user_id, "Написать клиенту")
        if customer_button:
            buttons.append([customer_button])

    buttons.append([ibtn("back", "Назад к заказам", callback_data="admin:orders")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def florist_lead_kb(order_id: int, user_id: int | None = None) -> InlineKeyboardMarkup:
    buttons = [
        [ibtn("florist", "Взять в работу", callback_data=f"admin_order:{order_id}:consultation_in_progress")],
    ]
    if user_id:
        buttons.append([ibtn("help", "Написать клиенту", url=f"tg://user?id={user_id}")])
    buttons.append([ibtn("success", "Закрыть", callback_data=f"admin_order:{order_id}:consultation_closed", style=STYLE["success"])])
    buttons.append([ibtn("back", "Назад к консультациям", callback_data="admin:consultations")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def staff_order_kb(order_id: int, status: str, reply_url: str | None = None) -> InlineKeyboardMarkup:
    rows = []
    if status == "new":
        rows.append([
            InlineKeyboardButton(text="Принять", callback_data=f"admin_order:{order_id}:accepted"),
            InlineKeyboardButton(text="Отказать", callback_data=f"admin_order:{order_id}:cancelled"),
        ])
    elif status == "accepted":
        rows.append([
            InlineKeyboardButton(text="Ожидает оплату", callback_data=f"admin_order:{order_id}:waiting_payment"),
            InlineKeyboardButton(text="Оплачен", callback_data=f"admin_order:{order_id}:paid"),
        ])
        rows.append([InlineKeyboardButton(text="Отменить", callback_data=f"admin_order:{order_id}:cancelled")])
    elif status in {"paid", "waiting_payment"}:
        rows.append([InlineKeyboardButton(text="В сборке", callback_data=f"admin_order:{order_id}:in_progress")])
        if status == "waiting_payment":
            rows.append([InlineKeyboardButton(text="Отменить", callback_data=f"admin_order:{order_id}:cancelled")])
    elif status in {"in_progress", "assembling"}:
        rows.append([
            InlineKeyboardButton(text="Готов", callback_data=f"admin_order:{order_id}:ready_for_pickup"),
            InlineKeyboardButton(text="В доставке", callback_data=f"admin_order:{order_id}:in_delivery"),
        ])
    elif status in {"ready", "ready_for_pickup", "delivery", "in_delivery"}:
        rows.append([InlineKeyboardButton(text="Выполнено", callback_data=f"admin_order:{order_id}:delivered")])

    if reply_url:
        rows.append([InlineKeyboardButton(text="Написать клиенту", url=reply_url)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def staff_consultation_kb(order_id: int, reply_url: str | None = None, can_convert: bool = False) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text="Взять в работу", callback_data=f"admin_order:{order_id}:consultation_in_progress")]]
    if reply_url:
        rows.append([InlineKeyboardButton(text="Написать клиенту", url=reply_url)])
    if can_convert:
        rows.append([InlineKeyboardButton(text="Создать заказ", callback_data=f"admin_order:{order_id}:accepted")])
    rows.append([InlineKeyboardButton(text="Выполнено", callback_data=f"admin_order:{order_id}:consultation_closed")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _customer_label(customer) -> str:
    username = getattr(customer, "username", None)
    if username:
        return f"@{username}"
    phone = getattr(customer, "phone", None)
    if phone:
        return phone
    telegram_id = getattr(customer, "telegram_user_id", None)
    return f"ID {telegram_id}" if telegram_id else "клиент"


def _consultation_source_label(order) -> str:
    if getattr(order, "comment", None) and E["choose"] in order.comment:
        return "подбор"
    if getattr(order, "source_post_id", None):
        product = getattr(order, "product", None)
        return f"пост: {product.title}" if product else "пост"
    return "быстрый вопрос"


def admin_order_list_kb(orders: list, is_consultation: bool = False) -> InlineKeyboardMarkup:
    buttons = []
    for order in orders:
        if not is_consultation:
            status_label = strings.ORDER_STATUS_LABELS.get(order.status, order.status)
            text = f"{E['orders']} №{order.id} · {status_label}"
        else:
            user_label = _customer_label(order.customer)
            source = _consultation_source_label(order)
            text = f"{E['consultation']} №{order.id} · {user_label} · {source}"
        buttons.append([InlineKeyboardButton(text=text, callback_data=f"admin_order_view:{order.id}")])

    buttons.append([ibtn("back", "Назад", callback_data="admin:main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_products_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [ibtn("add", "Добавить букет", callback_data="admin:product_add", style=STYLE["primary"])],
        [ibtn("list", "Список букетов", callback_data="admin:product_list")],
        [ibtn("back", "Назад", callback_data="admin:main")],
    ])


def admin_product_list_kb(products: list) -> InlineKeyboardMarkup:
    buttons = []
    for product in products:
        status_icon = E["toggle_on"] if product.is_active else E["toggle_off"]
        buttons.append([InlineKeyboardButton(text=f"{status_icon} {product.title} · {product.price} ₽", callback_data=f"admin_prod_view:{product.id}")])

    buttons.append([ibtn("back", "Назад", callback_data="admin:products")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_product_detail_kb(product_id: int, is_active: bool) -> InlineKeyboardMarkup:
    toggle_key = "toggle_off" if is_active else "toggle_on"
    toggle_text = "Скрыть" if is_active else "Показать"
    return InlineKeyboardMarkup(inline_keyboard=[
        [ibtn("publish", "Опубликовать пост", callback_data=f"admin_post_from_prod:{product_id}", style=STYLE["primary"])],
        [ibtn("edit", "Редактировать", callback_data=f"admin_prod_edit:{product_id}")],
        [ibtn(toggle_key, toggle_text, callback_data=f"admin_prod_toggle:{product_id}")],
        [ibtn("delete", "Удалить", callback_data=f"admin_prod_delete:{product_id}", style=STYLE["danger"])],
        [ibtn("back", "К букетам", callback_data="admin:products")],
    ])


def admin_product_delete_confirm_kb(product_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [ibtn("delete", "Подтвердить удаление", callback_data=f"admin_prod_delete_confirm:{product_id}", style=STYLE["danger"])],
        [ibtn("back", "Назад", callback_data=f"admin_prod_view:{product_id}")],
    ])


def admin_product_edit_menu_kb(product_id: int) -> InlineKeyboardMarkup:
    """Меню редактирования товара."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [ibtn("edit", "Изменить название", callback_data=f"admin_prod_edit_field:{product_id}:title")],
        [ibtn("edit", "Изменить цену", callback_data=f"admin_prod_edit_field:{product_id}:price")],
        [ibtn("edit", "Изменить описание", callback_data=f"admin_prod_edit_field:{product_id}:description")],
        [ibtn("edit", "Изменить фото", callback_data=f"admin_prod_edit_field:{product_id}:photo")],
        [ibtn("edit", "Изменить теги", callback_data=f"admin_prod_edit_field:{product_id}:tags")],
        [ibtn("back", "← Назад к букету", callback_data=f"admin_prod_view:{product_id}")],
    ])


def admin_posts_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [ibtn("add", "Создать пост", callback_data="admin:post_quick", style=STYLE["primary"])],
        [ibtn("archive", "Архив", callback_data="admin:posts_recent")],
        [ibtn("back", "Назад", callback_data="admin:main")],
    ])


def post_buttons_kb(selected: list | None = None) -> InlineKeyboardMarkup:
    selected = selected or ["order", "florist"]

    def get_text(key: str, label: str) -> str:
        return f"{E['success']} {label}" if key in selected else label

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text("order", "Заказать"), callback_data="post_toggle:order")],
        [InlineKeyboardButton(text=get_text("florist", "Позвать флориста"), callback_data="post_toggle:florist")],
        [InlineKeyboardButton(text=get_text("shop", "Открыть магазин"), callback_data="post_toggle:shop")],
        [InlineKeyboardButton(text=get_text("similar", "Подобрать похожий"), callback_data="post_toggle:similar")],
        [ibtn("next", "Продолжить", callback_data="post_action:preview", style=STYLE["primary"])],
        [ibtn("danger", "Отмена", callback_data="admin:posts", style=STYLE["danger"])],
    ])


def post_preview_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [ibtn("publish", "Опубликовать сейчас", callback_data="post_action:publish", style=STYLE["success"])],
        [ibtn("danger", "Отмена", callback_data="admin:posts", style=STYLE["danger"])],
    ])


def admin_promo_list_kb(promos: list) -> InlineKeyboardMarkup:
    buttons = [[ibtn("add", "Создать промокод", callback_data="admin_promo:create", style=STYLE["primary"])]]
    for promo in promos:
        status_icon = E["toggle_on"] if promo.is_active else E["danger"]
        buttons.append([InlineKeyboardButton(text=f"{status_icon} {promo.code} · {promo.used_count}/{promo.usage_limit or '∞'}", callback_data=f"admin_promo_view:{promo.id}")])

    buttons.append([ibtn("back", "Назад", callback_data="admin:main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_promo_detail_kb(promo_id: int, is_active: bool) -> InlineKeyboardMarkup:
    toggle_key = "danger" if is_active else "success"
    toggle_text = "Выключить" if is_active else "Включить"
    toggle_style = STYLE["danger"] if is_active else STYLE["success"]
    return InlineKeyboardMarkup(inline_keyboard=[
        [ibtn(toggle_key, toggle_text, callback_data=f"admin_toggle_promo:{promo_id}", style=toggle_style)],
        [ibtn("edit", "Изменить скидку", callback_data=f"admin_promo:edit_discount:{promo_id}"), ibtn("edit", "Изменить лимит", callback_data=f"admin_promo:edit_limit:{promo_id}")],
        [ibtn("date", "Изменить срок", callback_data=f"admin_promo:edit_valid_until:{promo_id}")],
        [ibtn("delete", "Удалить", callback_data=f"admin_promo:delete:{promo_id}", style=STYLE["danger"])],
        [ibtn("back", "К промокодам", callback_data="admin:promos")],
    ])


def promo_discount_type_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Процент", callback_data="admin_promo:type:percent"), InlineKeyboardButton(text="Фикс", callback_data="admin_promo:type:fixed")],
        [ibtn("back", "Назад", callback_data="admin:promos")],
    ])


def promo_delete_confirm_kb(promo_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [ibtn("delete", "Подтвердить удаление", callback_data=f"admin_promo:delete_confirm:{promo_id}", style=STYLE["danger"])],
        [ibtn("back", "Назад", callback_data=f"admin_promo_view:{promo_id}")],
    ])


def admin_branch_list_kb(branches: list) -> InlineKeyboardMarkup:
    buttons = []
    for branch in branches:
        status_icon = E["toggle_on"] if branch.is_active else E["danger"]
        loc = branch.title.split("·")[-1].strip()
        buttons.append([InlineKeyboardButton(text=f"{status_icon} {branch.address} · {loc}", callback_data=f"admin_branch_view:{branch.id}")])

    buttons.append([ibtn("back", "Назад", callback_data="admin:main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_branch_detail_kb(branch_id: int, is_active: bool, map_url: str | None = None) -> InlineKeyboardMarkup:
    toggle_key = "danger" if is_active else "success"
    toggle_text = "Выключить самовывоз" if is_active else "Включить самовывоз"
    toggle_style = STYLE["danger"] if is_active else STYLE["success"]
    buttons = [[ibtn(toggle_key, toggle_text, callback_data=f"admin_toggle_branch:{branch_id}", style=toggle_style)]]
    if map_url:
        buttons.append([ibtn("map", "Открыть карту", url=map_url)])
    buttons.append([ibtn("back", "К точкам", callback_data="admin:branches")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
