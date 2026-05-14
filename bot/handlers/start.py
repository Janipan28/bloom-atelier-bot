from aiogram import Bot, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bot.db import async_session
from bot.keyboards.user import entry_choice_kb, main_menu_kb, product_detail_kb
from bot.config import get_settings
from bot.ui.buttons import ibtn
from bot.services.menu_service import MenuManager
from bot.states.order_states import OrderFlow
from bot.services.order_service import get_or_create_customer
from bot.states.admin_states import AdminReplyFlow
from bot.handlers.admin import is_admin
from bot.handlers.admin_reply import activate_reply_session
from bot.models import Order
from bot import strings
from bot.handlers.user_order import _main_menu_text
from sqlalchemy import select

router = Router()


def florist_entry_choice_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [ibtn("help", "Задать вопрос", callback_data="order:contact_florist", style="primary")],
        [
            ibtn("success", "Заказать букет", callback_data="order:start_flow"),
            ibtn("back", "Назад", callback_data="back:main"),
        ],
    ])


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, bot: Bot) -> None:
    # Register customer
    async with async_session() as session:
        await get_or_create_customer(
            session=session,
            telegram_user_id=message.from_user.id,
            username=message.from_user.username,
            full_name=message.from_user.full_name
        )

    args = message.text.split(maxsplit=1)
    payload = args[1].strip() if len(args) > 1 else None
    is_florist_link = bool(payload and payload.startswith("ask_"))
    source_code = payload[4:] if is_florist_link else payload
    await state.clear()

    async with async_session() as session:
        mm = MenuManager(bot, session)

        if payload and payload.startswith("staff_reply_") and is_admin(message.from_user.id):
            order_id = int(payload.split("_")[-1])
            order = await session.scalar(select(Order).where(Order.id == order_id))
            if order:
                reply_session = await activate_reply_session(message.from_user.id, order.id)
                if not reply_session:
                    await mm.delete_user_message(message)
                    return
                await state.set_state(AdminReplyFlow.get_message)
                await state.update_data(reply_session_id=reply_session.id)
                await mm.cleanup_menu(message.from_user.id, message.chat.id)
                await message.answer(
                    f"Ответ клиенту по заказу №{order.id}\n\nНапишите сообщение следующим сообщением. Оно уйдёт клиенту от имени бота."
                )
                await mm.delete_user_message(message)
                return
        
        if source_code:
            from bot.models import ChannelPost, Product
            post = await session.scalar(select(ChannelPost).where(ChannelPost.source_code == source_code))

            if post:
                await state.clear()
                # Пытаемся получить инфо о товаре
                product_info = ""
                photo_path = "assets/bot_ui/order_menu.jpg"
                
                if post.product_id:
                    product = await session.get(Product, post.product_id)
                    if product:
                        product_info = f"💐 <b>{product.title}</b>\nот <b>{product.price} ₽</b>\n\n"
                        await state.update_data(product_id=product.id, product_title=product.title, product_price=product.price)
                        if product.photo_file_id:
                            photo_path = product.photo_file_id

                await state.update_data(source_code=source_code, source_post_id=post.id)

                if is_florist_link:
                    await state.set_state(OrderFlow.entry_choice)
                    florist_text = (
                        f"{product_info}"
                        "💬 <b>Вопрос по этому букету</b>\n\n"
                        "Передадим флористу ссылку на пост и информацию о букете, чтобы он сразу понял, о каком варианте речь."
                    )
                    await mm.show_menu(
                        chat_id=message.chat.id,
                        user_id=message.from_user.id,
                        text=florist_text,
                        reply_markup=florist_entry_choice_kb(),
                        photo_path=photo_path,
                        screen_name="entry_choice_florist"
                    )
                else:
                    if post.product_id and product_info:
                        product = await session.get(Product, post.product_id)
                        if product:
                            text = f"💐 <b>Букет «{product.title}»</b>\n\n{product.description or 'Состав и детали можно уточнить у флориста.'}\n\nот <b>{product.price} ₽</b>"
                            await mm.show_menu(
                                chat_id=message.chat.id,
                                user_id=message.from_user.id,
                                text=text,
                                reply_markup=product_detail_kb(product.id),
                                photo_path=photo_path,
                                screen_name=f"product_{product.id}"
                            )
                        else:
                            await state.set_state(OrderFlow.entry_choice)
                            await mm.show_menu(
                                chat_id=message.chat.id,
                                user_id=message.from_user.id,
                                text=f"{product_info}{strings.ENTRY_CHOICE}",
                                reply_markup=entry_choice_kb(),
                                photo_path=photo_path,
                                screen_name="entry_choice"
                            )
                    else:
                        await state.set_state(OrderFlow.entry_choice)
                        await mm.show_menu(
                            chat_id=message.chat.id,
                            user_id=message.from_user.id,
                            text=f"{product_info}{strings.ENTRY_CHOICE}",
                            reply_markup=entry_choice_kb(),
                            photo_path=photo_path,
                            screen_name="entry_choice"
                        )
                await mm.delete_user_message(message)
                return
            else:
                await state.clear()
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [ibtn("bouquet", "Выбрать букет", callback_data="user:catalog")],
                    [ibtn("help", "Спросить флориста", callback_data="order:contact_florist")],
                    [ibtn("back", "Главное меню", callback_data="back:main")]
                ])
                text = (
                    "Этот букет уже недоступен или ссылка устарела.\n\n"
                    "Можно выбрать другой букет или сразу написать флористу."
                )
                await mm.show_menu(
                    chat_id=message.chat.id,
                    user_id=message.from_user.id,
                    text=text,
                    reply_markup=kb,
                    photo_path="assets/bot_ui/main_menu.jpg",
                    screen_name="broken_link"
                )
                await mm.delete_user_message(message)
                return

        customer = await get_or_create_customer(
            session=session,
            telegram_user_id=message.from_user.id,
            username=message.from_user.username,
            full_name=message.from_user.full_name
        )
        await mm.show_menu(
            chat_id=message.chat.id,
            user_id=message.from_user.id,
            text=_main_menu_text(customer.loyalty_points),
            reply_markup=main_menu_kb(mini_app_url=get_settings().mini_app_url),
            photo_path="assets/bot_ui/main_menu.jpg",
            screen_name="main_menu"
        )

        await mm.delete_user_message(message)
