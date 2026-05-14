import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from bot.config import get_settings
from bot.db import async_session
from bot.models import Product, Order, ChannelPost
from bot.states.admin_states import AdminProductFlow
from bot.keyboards.admin import (
    admin_products_menu_kb,
    admin_product_list_kb,
    admin_product_detail_kb,
    admin_product_delete_confirm_kb,
    admin_product_edit_menu_kb,
)
from bot.services.admin_service import get_all_products
from bot.services.menu_service import MenuManager
from bot.services.message_cleanup import replace_state_error, safe_delete_message
from bot import strings
from sqlalchemy import select, func

router = Router()

def is_admin(user_id: int) -> bool:
    return user_id in get_settings().admin_id_set

@router.callback_query(F.data == "admin:products")
async def admin_products_handler(callback: CallbackQuery, bot: Bot):
    await callback.answer()
    if not is_admin(callback.from_user.id): return
    async with async_session() as session:
        mm = MenuManager(bot, session)
        await mm.show_menu(
            chat_id=callback.message.chat.id,
            user_id=callback.from_user.id,
            text="💐 <b>Управление товарами (букетами)</b>\n\nЗдесь вы можете добавить новые букеты или отредактировать текущие.",
            reply_markup=admin_products_menu_kb(),
            screen_name="admin_products"
        )

@router.callback_query(F.data == "admin:product_add")
async def admin_product_add_handler(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.answer()
    if not is_admin(callback.from_user.id): return
    await state.set_state(AdminProductFlow.get_photo)
    async with async_session() as session:
        mm = MenuManager(bot, session)
        await mm.show_menu(
            chat_id=callback.message.chat.id,
            user_id=callback.from_user.id,
            text="📸 <b>Добавление букета</b>\n\nОтправьте фото букета:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Отмена", callback_data="admin:products")]]),
            screen_name="admin_product_add"
        )

@router.message(AdminProductFlow.get_photo, F.photo | F.document)
async def process_prod_photo(message: Message, state: FSMContext):
    photo_id = None
    if message.photo:
        photo_id = message.photo[-1].file_id
    elif message.document:
        if message.document.mime_type and message.document.mime_type.startswith("image/"):
            photo_id = message.document.file_id
        else:
            await message.answer(
                "📸 <b>Сейчас нужно отправить фото букета.</b>\n\n"
                "Можно отправить обычным изображением или файлом JPG/PNG.",
                parse_mode="HTML"
            )
            return
        
    if not photo_id:
        await message.answer("📸 <b>Сейчас нужно отправить фото букета.</b>\n\nМожно отправить обычным изображением или файлом JPG/PNG.")
        return

    await state.update_data(photo_id=photo_id)
    await state.set_state(AdminProductFlow.get_title)
    await message.answer("Фото получил.\n\nТеперь напишите <b>название букета</b>.\nНапример: Букет «Нежность»")

@router.message(AdminProductFlow.get_photo)
async def process_prod_photo_invalid(message: Message, state: FSMContext):
    await replace_state_error(
        message,
        state,
        "📸 Сейчас нужно отправить фото букета.\n\n"
        "Можно отправить обычным изображением или файлом JPG/PNG.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Отмена", callback_data="admin:products")]])
    )

@router.message(AdminProductFlow.get_title, F.text)
async def process_prod_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await safe_delete_message(message)
    await state.set_state(AdminProductFlow.get_price)
    await message.answer("Укажите <b>цену</b> (только цифры):")

@router.message(AdminProductFlow.get_price, F.text)
async def process_prod_price(message: Message, state: FSMContext):
    try:
        import re
        price = int(re.sub(r'\D', '', message.text))
    except:
        await replace_state_error(message, state, "Введите число.")
        return
    await state.update_data(price=price)
    await safe_delete_message(message)
    await state.set_state(AdminProductFlow.get_description)
    await message.answer("Добавьте <b>описание</b> (состав, повод):")

@router.message(AdminProductFlow.get_description, F.text)
async def process_prod_desc(message: Message, state: FSMContext):
    data = await state.get_data()
    await safe_delete_message(message)
    async with async_session() as session:
        product = Product(
            title=data['title'],
            price=data['price'],
            description=message.text,
            photo_file_id=data['photo_id'],
            is_active=True
        )
        session.add(product)
        await session.commit()
        await message.answer(f"✅ Букет <b>{product.title}</b> успешно добавлен в базу.", parse_mode="HTML",
                             reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="↩️ К букетам", callback_data="admin:products")]]))
    await state.clear()

@router.callback_query(F.data == "admin:product_list")
async def admin_product_list_handler(callback: CallbackQuery, bot: Bot):
    await callback.answer()
    if not is_admin(callback.from_user.id): return
    async with async_session() as session:
        products = await get_all_products(session)
        mm = MenuManager(bot, session)
        await mm.show_menu(
            chat_id=callback.message.chat.id,
            user_id=callback.from_user.id,
            text="📋 <b>Список ваших букетов</b>",
            reply_markup=admin_product_list_kb(products),
            screen_name="admin_product_list"
        )

@router.callback_query(F.data.startswith("admin_prod_view:"))
async def admin_product_view_handler(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.answer()
    prod_id = int(callback.data.split(":")[1])
    async with async_session() as session:
        product = await session.get(Product, prod_id)
        if not product: return
        mm = MenuManager(bot, session)
        text = (
            f"💐 <b>{product.title}</b>\n\n"
            f"💰 Цена: {product.price} ₽\n"
            f"📝 Описание: {product.description or 'Нет'}\n"
            f"👁 Статус: {'Показывается' if product.is_active else 'Скрыт'}"
        )
        await mm.show_menu(
            chat_id=callback.message.chat.id,
            user_id=callback.from_user.id,
            text=text,
            reply_markup=admin_product_detail_kb(product.id, product.is_active),
            photo_path=product.photo_file_id or "assets/bot_ui/order_menu.jpg",
            screen_name=f"admin_prod_{product.id}"
        )
@router.callback_query(F.data.startswith("admin_prod_toggle:"))
async def admin_product_toggle_handler(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.answer()
    prod_id = int(callback.data.split(":")[1])
    async with async_session() as session:
        product = await session.get(Product, prod_id)
        if product:
            product.is_active = not product.is_active
            await session.commit()
            await admin_product_view_handler(callback, bot)

@router.callback_query(F.data.startswith("admin_prod_delete:"))
async def admin_product_delete_handler(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.answer()
    prod_id = int(callback.data.split(":")[1])
    async with async_session() as session:
        product = await session.get(Product, prod_id)
        if product:
            mm = MenuManager(bot, session)
            text = (
                f"🗑 <b>Удалить букет?</b>\n\n"
                f"Будет удалён товар <b>{product.title}</b>.\n"
                f"Это действие нельзя отменить."
            )
            await mm.show_menu(
                chat_id=callback.message.chat.id,
                user_id=callback.from_user.id,
                text=text,
                reply_markup=admin_product_delete_confirm_kb(product.id),
                photo_path=product.photo_file_id or "assets/bot_ui/order_menu.jpg",
                screen_name=f"admin_prod_delete_{product.id}"
            )


@router.callback_query(F.data.startswith("admin_prod_delete_confirm:"))
async def admin_product_delete_confirm_handler(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.answer()
    prod_id = int(callback.data.split(":")[1])
    async with async_session() as session:
        product = await session.get(Product, prod_id)
        if product:
            related_orders = await session.scalar(
                select(func.count(Order.id)).where(Order.product_id == product.id)
            )
            related_posts = await session.scalar(
                select(func.count(ChannelPost.id)).where(ChannelPost.product_id == product.id)
            )
            if (related_orders or 0) > 0 or (related_posts or 0) > 0:
                product.is_active = False
            else:
                await session.delete(product)
            await session.commit()
    await admin_product_list_handler(callback, bot)


# --- РЕДАКТИРОВАНИЕ ТОВАРА ---

@router.callback_query(F.data.startswith("admin_prod_edit:"))
async def admin_product_edit_handler(callback: CallbackQuery, bot: Bot):
    """Показать меню редактирования товара."""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.answer()
    prod_id = int(callback.data.split(":")[1])
    async with async_session() as session:
        product = await session.get(Product, prod_id)
        if not product:
            return
        mm = MenuManager(bot, session)
        text = (
            f"✏️ <b>Редактирование: {product.title}</b>\n\n"
            f"Выберите что хотите изменить:"
        )
        await mm.show_menu(
            chat_id=callback.message.chat.id,
            user_id=callback.from_user.id,
            text=text,
            reply_markup=admin_product_edit_menu_kb(product.id),
            photo_path=product.photo_file_id or "assets/bot_ui/order_menu.jpg",
            screen_name=f"admin_prod_edit_menu_{product.id}"
        )


@router.callback_query(F.data.startswith("admin_prod_edit_field:"))
async def admin_product_edit_field_handler(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Начать редактирование конкретного поля."""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.answer()
    
    parts = callback.data.split(":")
    prod_id = int(parts[1])
    field = parts[2]
    
    await state.update_data(edit_product_id=prod_id, edit_field=field)
    
    async with async_session() as session:
        product = await session.get(Product, prod_id)
        if not product:
            return
        
        mm = MenuManager(bot, session)
        
        if field == "title":
            await state.set_state(AdminProductFlow.edit_title)
            text = f"✏️ <b>Изменение названия</b>\n\nТекущее: <b>{product.title}</b>\n\nНапишите новое название:"
        elif field == "price":
            await state.set_state(AdminProductFlow.edit_price)
            text = f"✏️ <b>Изменение цены</b>\n\nТекущая: <b>{product.price} ₽</b>\n\nНапишите новую цену (только цифры):"
        elif field == "description":
            await state.set_state(AdminProductFlow.edit_description)
            text = f"✏️ <b>Изменение описания</b>\n\nТекущее:\n{product.description or 'Нет'}\n\nНапишите новое описание:"
        elif field == "photo":
            await state.set_state(AdminProductFlow.edit_photo)
            text = f"✏️ <b>Изменение фото</b>\n\nОтправьте новое фото букета:"
        elif field == "tags":
            await state.set_state(AdminProductFlow.edit_tags)
            text = (
                f"✏️ <b>Изменение тегов</b>\n\n"
                f"Текущие: <code>{product.tags or 'Нет'}</code>\n\n"
                f"Напишите теги через запятую.\n"
                f"Доступные: birthday, date, apology, just_because\n\n"
                f"Пример: <code>birthday,date</code>"
            )
        else:
            return
        
        await mm.show_menu(
            chat_id=callback.message.chat.id,
            user_id=callback.from_user.id,
            text=text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отмена", callback_data=f"admin_prod_edit:{prod_id}")]
            ]),
            photo_path=product.photo_file_id or "assets/bot_ui/order_menu.jpg",
            screen_name=f"admin_prod_edit_{field}_{prod_id}"
        )


@router.message(AdminProductFlow.edit_title, F.text)
async def process_edit_title(message: Message, state: FSMContext, bot: Bot):
    """Обработать новое название."""
    data = await state.get_data()
    prod_id = data.get("edit_product_id")
    
    async with async_session() as session:
        product = await session.get(Product, prod_id)
        if product:
            product.title = message.text
            await session.commit()
            await safe_delete_message(message)
            await message.answer(
                f"✅ Название изменено на: <b>{message.text}</b>",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="↩️ К букету", callback_data=f"admin_prod_view:{prod_id}")]
                ])
            )
    await state.clear()


@router.message(AdminProductFlow.edit_price, F.text)
async def process_edit_price(message: Message, state: FSMContext, bot: Bot):
    """Обработать новую цену."""
    try:
        import re
        price = int(re.sub(r'\D', '', message.text))
    except:
        await replace_state_error(message, state, "Введите число.")
        return
    
    data = await state.get_data()
    prod_id = data.get("edit_product_id")
    
    async with async_session() as session:
        product = await session.get(Product, prod_id)
        if product:
            product.price = price
            await session.commit()
            await safe_delete_message(message)
            await message.answer(
                f"✅ Цена изменена на: <b>{price} ₽</b>",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="↩️ К букету", callback_data=f"admin_prod_view:{prod_id}")]
                ])
            )
    await state.clear()


@router.message(AdminProductFlow.edit_description, F.text)
async def process_edit_description(message: Message, state: FSMContext, bot: Bot):
    """Обработать новое описание."""
    data = await state.get_data()
    prod_id = data.get("edit_product_id")
    
    async with async_session() as session:
        product = await session.get(Product, prod_id)
        if product:
            product.description = message.text
            await session.commit()
            await safe_delete_message(message)
            await message.answer(
                f"✅ Описание изменено",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="↩️ К букету", callback_data=f"admin_prod_view:{prod_id}")]
                ])
            )
    await state.clear()


@router.message(AdminProductFlow.edit_photo, F.photo | F.document)
async def process_edit_photo(message: Message, state: FSMContext, bot: Bot):
    """Обработать новое фото."""
    photo_id = None
    if message.photo:
        photo_id = message.photo[-1].file_id
    elif message.document:
        if message.document.mime_type and message.document.mime_type.startswith("image/"):
            photo_id = message.document.file_id
        else:
            await message.answer("📸 Отправьте фото (изображение или файл JPG/PNG).")
            return
    
    if not photo_id:
        await message.answer("📸 Отправьте фото букета.")
        return
    
    data = await state.get_data()
    prod_id = data.get("edit_product_id")
    
    async with async_session() as session:
        product = await session.get(Product, prod_id)
        if product:
            product.photo_file_id = photo_id
            await session.commit()
            await safe_delete_message(message)
            await message.answer(
                f"✅ Фото изменено",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="↩️ К букету", callback_data=f"admin_prod_view:{prod_id}")]
                ])
            )
    await state.clear()


@router.message(AdminProductFlow.edit_tags, F.text)
async def process_edit_tags(message: Message, state: FSMContext, bot: Bot):
    """Обработать новые теги."""
    data = await state.get_data()
    prod_id = data.get("edit_product_id")
    
    async with async_session() as session:
        product = await session.get(Product, prod_id)
        if product:
            product.tags = message.text.strip()
            await session.commit()
            await safe_delete_message(message)
            await message.answer(
                f"✅ Теги изменены на: <code>{message.text}</code>",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="↩️ К букету", callback_data=f"admin_prod_view:{prod_id}")]
                ])
            )
    await state.clear()
