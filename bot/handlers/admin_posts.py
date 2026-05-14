import logging
import re
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from bot.config import get_settings
from bot.db import async_session
from bot.models import ChannelPost, Product, OrderStatus
from bot.states.admin_states import AdminPostFlow
from bot.keyboards.admin import admin_posts_menu_kb, post_buttons_kb, post_preview_kb, admin_menu_kb
from bot.services.post_builder import build_flower_post_html, build_preview_text
from bot.services.admin_service import get_basic_stats, get_all_posts
from bot.services.menu_service import MenuManager
from bot.services.message_cleanup import replace_state_error, safe_delete_message
from bot.services.formatting import build_post_caption, h, code
from bot import strings
from sqlalchemy import select


logger = logging.getLogger(__name__)
router = Router()

def is_admin(user_id: int) -> bool:
    return user_id in get_settings().admin_id_set


async def reject_non_admin(callback: CallbackQuery) -> bool:
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return True
    return False

@router.callback_query(F.data == "admin:posts")
async def admin_posts_handler(callback: CallbackQuery, bot: Bot):
    if await reject_non_admin(callback):
        return
    await callback.answer()
    async with async_session() as session:
        mm = MenuManager(bot, session)
        await mm.show_menu(
            chat_id=callback.message.chat.id,
            user_id=callback.from_user.id,
            text="📝 <b>Управление постами</b>\n\nВыберите действие:",
            reply_markup=admin_posts_menu_kb(),
            screen_name="admin_posts"
        )

@router.callback_query(F.data == "admin:post_quick")
async def admin_post_quick_start(callback: CallbackQuery, state: FSMContext, bot: Bot):
    if await reject_non_admin(callback):
        return
    await callback.answer()
    await state.set_state(AdminPostFlow.get_photo)
    async with async_session() as session:
        mm = MenuManager(bot, session)
        await mm.show_menu(
            chat_id=callback.message.chat.id,
            user_id=callback.from_user.id,
            text="📸 <b>Быстрый пост</b>\n\nОтправьте фото букета.\nПосле этого я помогу быстро собрать пост для канала.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="↩️ В админ-панель", callback_data="admin:main")]]),
            screen_name="post_quick_start"
        )

@router.message(AdminPostFlow.get_photo, F.photo | F.document)
async def process_post_photo(message: Message, state: FSMContext):
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
    if message.caption:
        await state.update_data(title_candidate=message.caption)

    await state.set_state(AdminPostFlow.get_title)
    await message.answer(
        "Фото получил.\n\nТеперь напишите <b>название букета</b>.\nНапример: <i>Букет «Нежность»</i>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Пропустить", callback_data="post_skip:title")],
            [InlineKeyboardButton(text="↩️ Назад", callback_data="admin:post_quick")]
        ]),
        parse_mode="HTML"
    )

@router.message(AdminPostFlow.get_photo)
async def process_post_photo_invalid(message: Message, state: FSMContext):
    await replace_state_error(
        message,
        state,
        "📸 Сейчас нужно отправить фото букета.\n\n"
        "Можно отправить обычным изображением или файлом JPG/PNG.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="↩️ В админку", callback_data="admin:main")]])
    )

@router.callback_query(AdminPostFlow.get_title, F.data == "post_skip:title")
@router.message(AdminPostFlow.get_title, F.text)
async def process_post_title(event, state: FSMContext):
    if isinstance(event, CallbackQuery):
        await event.answer()
    title = event.text if isinstance(event, Message) else "Красивый букет"
    await state.update_data(title=title)
    await state.set_state(AdminPostFlow.get_price)
    
    msg_text = "Укажите <b>цену</b> (только цифры).\nНапример: <i>4900</i>"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Цена по запросу", callback_data="post_skip:price")],
        [InlineKeyboardButton(text="↩️ Назад", callback_data="admin:post_quick")]
    ])
    
    if isinstance(event, Message):
        await safe_delete_message(event)
        await event.answer(msg_text, reply_markup=kb, parse_mode="HTML")
    else:
        await event.message.edit_text(msg_text, reply_markup=kb, parse_mode="HTML")

@router.callback_query(AdminPostFlow.get_price, F.data == "post_skip:price")
@router.message(AdminPostFlow.get_price, F.text)
async def process_post_price(event, state: FSMContext):
    if isinstance(event, CallbackQuery):
        await event.answer()
    price = None
    if isinstance(event, Message):
        try:
            price = int(re.sub(r'\D', '', event.text))
        except:
            await replace_state_error(event, state, "Пожалуйста, введите только цифры для цены.")
            return
        await safe_delete_message(event)
    
    await state.update_data(price=price)
    await state.set_state(AdminPostFlow.get_description)
    
    msg_text = (
        "Добавить короткое <b>описание</b>?\n\n"
        "Можно написать состав или повод.\n"
        "Например: <i>Пионы, эвкалипт. Для свидания.</i>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Сгенерировать текст", callback_data="post_action:gen_text")],
        [InlineKeyboardButton(text="Пропустить", callback_data="post_skip:desc")],
        [InlineKeyboardButton(text="↩️ Назад", callback_data="admin:post_quick")]
    ])
    
    if isinstance(event, Message):
        await event.answer(msg_text, reply_markup=kb, parse_mode="HTML")
    else:
        await event.message.edit_text(msg_text, reply_markup=kb, parse_mode="HTML")

@router.callback_query(AdminPostFlow.get_description, F.data.in_({"post_action:gen_text", "post_skip:desc"}))
@router.message(AdminPostFlow.get_description, F.text)
async def process_post_description(event: Message | CallbackQuery, state: FSMContext, bot: Bot):
    if isinstance(event, CallbackQuery):
        await event.answer()
        data = await state.get_data()
        if event.data == "post_action:gen_text":
            desc = build_flower_post_html(data.get('title'), data.get('price'), "Великолепный букет от наших флористов.")
            await state.update_data(full_text=desc, description="Великолепный букет от наших флористов.")
        else:
            desc = build_flower_post_html(data.get('title'), data.get('price'), "")
            await state.update_data(full_text=desc, description="")
    else:
        # User sent text description
        data = await state.get_data()
        desc = build_flower_post_html(data.get('title'), data.get('price'), event.text)
        await state.update_data(full_text=desc, description=event.text)
        await safe_delete_message(event)

    await state.set_state(AdminPostFlow.choose_buttons)
    async with async_session() as session:
        mm = MenuManager(bot, session)
        chat_id = event.message.chat.id if isinstance(event, CallbackQuery) else event.chat.id
        user_id = event.from_user.id
        await mm.show_menu(
            chat_id=chat_id,
            user_id=user_id,
            text="🔘 <b>Выберите кнопки под постом:</b>",
            reply_markup=post_buttons_kb(),
            screen_name="post_choose_buttons"
        )

@router.callback_query(AdminPostFlow.choose_buttons, F.data.startswith("post_toggle:"))
async def toggle_post_btn(callback: CallbackQuery, state: FSMContext):
    if await reject_non_admin(callback):
        return
    await callback.answer()
    btn = callback.data.split(":")[1]
    data = await state.get_data()
    selected = data.get("selected_buttons", ["order", "florist"])
    
    if btn in selected:
        selected.remove(btn)
    else:
        selected.append(btn)
        
    await state.update_data(selected_buttons=selected)
    await callback.message.edit_reply_markup(reply_markup=post_buttons_kb(selected))

@router.message(AdminPostFlow.choose_buttons, F.text)
async def process_post_desc_edit(message: Message, state: FSMContext, bot: Bot):
    # Allow user to update description even at button selection step
    data = await state.get_data()
    desc = build_flower_post_html(data.get('title'), data.get('price'), message.text)
    await state.update_data(full_text=desc, description=message.text)
    await safe_delete_message(message)
    
    async with async_session() as session:
        mm = MenuManager(bot, session)
        await mm.show_menu(
            chat_id=message.chat.id,
            user_id=message.from_user.id,
            text=f"✅ <b>Описание обновлено!</b>\n\n🔘 <b>Выберите кнопки под постом:</b>",
            reply_markup=post_buttons_kb(data.get("selected_buttons", ["order", "florist"])),
            screen_name="post_choose_buttons"
        )

@router.callback_query(AdminPostFlow.choose_buttons, F.data == "post_action:preview")
async def process_post_preview(callback: CallbackQuery, state: FSMContext):
    if await reject_non_admin(callback):
        return
    await callback.answer()
    data = await state.get_data()
    preview = build_preview_text(data['full_text'], ",".join(data.get("selected_buttons", [])))
    
    await state.set_state(AdminPostFlow.preview)
    await callback.message.delete()
    await callback.message.answer_photo(
        data['photo_id'],
        caption=preview,
        reply_markup=post_preview_kb(),
        parse_mode="HTML"
    )

@router.callback_query(AdminPostFlow.preview, F.data == "post_action:publish")
async def process_post_publish(callback: CallbackQuery, state: FSMContext, bot: Bot):
    if await reject_non_admin(callback):
        return
    data = await state.get_data()
    settings = get_settings()

    channel_id = settings.channel_id
    if not channel_id or str(channel_id) in ("0", ""):
        await callback.answer("❌ Ошибка: CHANNEL_ID не настроен в .env", show_alert=True)
        return

    # Защита от двойного клика
    current_data = await state.get_data()
    if current_data.get("publish_in_progress"):
        await callback.answer("⏳ Публикация уже идет...", show_alert=True)
        return
    
    await state.update_data(publish_in_progress=True)
    await callback.answer("🚀 Публикую пост...")

    async with async_session() as session:
        title = data.get("title") or "Без названия"
        price = data.get("price")
        description = data.get("description")

        product = Product(
            title=title,
            price=price,
            description=description,
            photo_file_id=data.get("photo_id"),
            is_active=False,
        )
        session.add(product)
        await session.flush()

        source_code = f"src_p{product.id}"
        bot_user = await bot.get_me()
        order_url = f"https://t.me/{bot_user.username}?start={source_code}"
        florist_url = f"https://t.me/{bot_user.username}?start=ask_{source_code}"

        caption = build_post_caption(title=title, price=price, description=description)

        selected = data.get("selected_buttons", ["order", "florist"])
        kb_list = []
        if "order" in selected:
            kb_list.append([InlineKeyboardButton(text="💐 Заказать", url=order_url)])
        if "florist" in selected:
            kb_list.append([InlineKeyboardButton(text="👩‍🌾 Задать вопрос флористу", url=florist_url)])
        if "shop" in selected:
            kb_list.append([InlineKeyboardButton(text="🛍 Открыть каталог", url=order_url)])
        if not kb_list:
            kb_list.append([InlineKeyboardButton(text="💐 Заказать", url=order_url)])

        channel_markup = InlineKeyboardMarkup(inline_keyboard=kb_list)

        try:
            sent = await bot.send_photo(
                chat_id=channel_id,
                photo=data["photo_id"],
                caption=caption,
                reply_markup=channel_markup,
                parse_mode="HTML",
            )

            cp = ChannelPost(
                chat_id=int(str(channel_id).replace("-100", "-100")),
                message_id=sent.message_id,
                source_code=source_code,
                product_id=product.id,
                caption=caption,
            )
            session.add(cp)
            product.is_active = True
            await session.commit()
            await state.clear()

            channel_id_str = str(channel_id)
            post_link_kb = []
            if channel_id_str.startswith("-100"):
                clean_id = channel_id_str[4:]
                post_link_kb.append([InlineKeyboardButton(
                    text="👀 Открыть пост в канале",
                    url=f"https://t.me/c/{clean_id}/{sent.message_id}"
                )])
            post_link_kb.append([InlineKeyboardButton(text="↩️ В админку", callback_data="admin:main")])

            await callback.message.answer(
                f"✅ <b>Пост опубликован!</b>\n\n"
                f"💐 Букет: <b>{h(title)}</b>\n"
                f"📝 Source: {code(source_code)}\n"
                f"🔗 Deep link: {code(order_url)}\n\n"
                f"Теперь клики на кнопку 'Заказать' в посте откроют этот букет.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=post_link_kb),
                parse_mode="HTML",
            )

        except Exception as e:
            await session.rollback()
            logger.error(f"Failed to publish to channel {channel_id}: {e}", exc_info=True)
            await state.update_data(publish_in_progress=False)
            await callback.message.answer(
                f"❌ <b>Ошибка публикации:</b>\n<code>{e}</code>\n\n"
                f"Проверьте:\n"
                f"• Бот добавлен в канал как администратор\n"
                f"• Бот имеет право публиковать сообщения\n"
                f"• CHANNEL_ID корректный (для приватного канала нужен числовой ID вида -100xxx)",
                parse_mode="HTML"
            )

@router.callback_query(F.data == "admin:posts_recent")
async def admin_posts_recent(callback: CallbackQuery, bot: Bot):
    if await reject_non_admin(callback):
        return
    async with async_session() as session:
        posts = await get_all_posts(session, limit=5)
        mm = MenuManager(bot, session)
        if not posts:
            await callback.answer("Постов пока нет", show_alert=True)
            return
        
        text = "🕘 <b>Последние посты:</b>\n\n"
        buttons = []
        for p in posts:
            text += f"№{p.id} · {p.source_code}\n"
            buttons.append([InlineKeyboardButton(text=f"Пост №{p.id}", callback_data=f"admin_post_view:{p.id}")])
        
        buttons.append([InlineKeyboardButton(text="↩️ Назад", callback_data="admin:posts")])
        await mm.show_menu(
            chat_id=callback.message.chat.id,
            user_id=callback.from_user.id,
            text=text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
            screen_name="admin_posts_recent"
        )
    await callback.answer()

@router.callback_query(F.data.startswith("admin_post_view:"))
async def admin_post_view_handler(callback: CallbackQuery, bot: Bot):
    if await reject_non_admin(callback):
        return
    post_id = int(callback.data.split(":")[1])
    async with async_session() as session:
        from bot.models import ChannelPost
        post = await session.get(ChannelPost, post_id)
        if not post: return
        mm = MenuManager(bot, session)
        text = (
            f"📝 <b>Пост №{post.id}</b>\n\n"
            f"ID сообщения в канале: {post.message_id}\n"
            f"Source Code: <code>{post.source_code}</code>\n"
            f"Букет ID: {post.product_id}\n"
        )
        await mm.show_menu(
            chat_id=callback.message.chat.id,
            user_id=callback.from_user.id,
            text=text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="↩️ К списку", callback_data="admin:posts_recent")]
            ]),
            screen_name=f"admin_post_{post.id}"
        )
    await callback.answer()

@router.callback_query(F.data.startswith("admin_post_from_prod:"))
async def admin_post_from_prod_handler(callback: CallbackQuery, state: FSMContext, bot: Bot):
    if await reject_non_admin(callback):
        return
    product_id = int(callback.data.split(":")[1])
    async with async_session() as session:
        product = await session.get(Product, product_id)
        if not product: return
        
        await state.update_data(
            photo_id=product.photo_file_id,
            title=product.title,
            price=product.price,
            full_text=product.description or ""
        )
        await state.set_state(AdminPostFlow.choose_buttons)
        mm = MenuManager(bot, session)
        await mm.show_menu(
            chat_id=callback.message.chat.id,
            user_id=callback.from_user.id,
            text="🔘 <b>Выберите кнопки под постом:</b>",
            reply_markup=post_buttons_kb(),
            screen_name="post_choose_buttons"
        )
    await callback.answer()
