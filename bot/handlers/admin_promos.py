from datetime import datetime

from aiogram import F, Bot, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from bot.db import async_session
from bot.handlers.admin import is_admin
from bot.keyboards.admin import (
    admin_promo_detail_kb,
    admin_promo_list_kb,
    promo_delete_confirm_kb,
    promo_discount_type_kb,
)
from bot.models import PromoCode
from bot.services.menu_service import MenuManager
from bot.services.promo_service import (
    create_promo,
    deactivate_or_delete_promo,
    list_promos,
    update_promo_discount,
    update_promo_limit,
    update_promo_valid_until,
)
from bot.states.admin_states import AdminPromoFlow

router = Router()


def _parse_limit(raw: str) -> int | None:
    raw = raw.strip().lower()
    if raw in {"-", "∞", "inf", "без лимита"}:
        return None
    return max(int(raw), 0)


def _parse_valid_until(raw: str) -> datetime | None:
    raw = raw.strip().lower()
    if raw in {"-", "без срока"}:
        return None
    return datetime.strptime(raw, "%d.%m.%Y")


@router.callback_query(F.data == "admin:promos")
async def promo_list(callback: CallbackQuery, bot: Bot) -> None:
    await callback.answer()
    if not is_admin(callback.from_user.id):
        return
    await _show_promo_list(bot, callback.message.chat.id, callback.from_user.id)


@router.callback_query(F.data.startswith("admin_promo_view:"))
async def promo_view(callback: CallbackQuery, bot: Bot) -> None:
    await callback.answer()
    if not is_admin(callback.from_user.id):
        return
    promo_id = int(callback.data.split(":")[1])
    await _show_promo_detail(bot, callback.message.chat.id, callback.from_user.id, promo_id)


@router.callback_query(F.data.startswith("admin_toggle_promo:"))
async def promo_toggle(callback: CallbackQuery, bot: Bot) -> None:
    await callback.answer()
    if not is_admin(callback.from_user.id):
        return
    promo_id = int(callback.data.split(":")[1])
    async with async_session() as session:
        promo = await session.get(PromoCode, promo_id)
        if promo:
            promo.is_active = not promo.is_active
            await session.commit()
    await _show_promo_detail(bot, callback.message.chat.id, callback.from_user.id, promo_id)


async def _show_promo_list(bot: Bot, chat_id: int, user_id: int) -> None:
    async with async_session() as session:
        promos = await list_promos(session)
        mm = MenuManager(bot, session)
        await mm.show_menu(
            chat_id=chat_id,
            user_id=user_id,
            text="🎟 <b>Управление промокодами</b>",
            reply_markup=admin_promo_list_kb(promos),
            screen_name="admin_promos",
        )


async def _show_promo_detail(bot: Bot, chat_id: int, user_id: int, promo_id: int) -> None:
    async with async_session() as session:
        promo = await session.get(PromoCode, promo_id)
        if not promo:
            await _show_promo_list(bot, chat_id, user_id)
            return
        mm = MenuManager(bot, session)
        discount_text = f"{promo.discount_percent}%" if promo.discount_percent else f"{promo.discount_amount or 0} ₽"
        valid_until = promo.valid_until.strftime("%d.%m.%Y") if promo.valid_until else "без срока"
        await mm.show_menu(
            chat_id=chat_id,
            user_id=user_id,
            text=(
                f"🎟 <b>Промокод: {promo.code}</b>\n\n"
                f"Скидка: {discount_text}\n"
                f"Использований: {promo.used_count} / {promo.usage_limit or '∞'}\n"
                f"Срок: {valid_until}\n"
                f"Статус: {'активен' if promo.is_active else 'выключен'}"
            ),
            reply_markup=admin_promo_detail_kb(promo.id, promo.is_active),
            screen_name=f"admin_promo_{promo.id}",
        )


@router.callback_query(F.data == "admin_promo:create")
async def promo_create_start(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    await callback.answer()
    if not is_admin(callback.from_user.id):
        return
    await state.clear()
    await state.set_state(AdminPromoFlow.get_code)
    async with async_session() as session:
        mm = MenuManager(bot, session)
        await mm.show_menu(
            chat_id=callback.message.chat.id,
            user_id=callback.from_user.id,
            text="🎟 <b>Новый промокод</b>\n\nВведите код. Например: SPRING2026",
            screen_name="promo_create_code",
        )


@router.message(AdminPromoFlow.get_code, F.text)
async def promo_create_code(message: Message, state: FSMContext, bot: Bot) -> None:
    await state.update_data(code=message.text.strip().upper())
    await state.set_state(AdminPromoFlow.choose_discount_type)
    async with async_session() as session:
        mm = MenuManager(bot, session)
        await mm.delete_user_message(message)
        await mm.show_menu(
            chat_id=message.chat.id,
            user_id=message.from_user.id,
            text="Выберите тип скидки",
            reply_markup=promo_discount_type_kb(),
            screen_name="promo_create_type",
        )


@router.callback_query(AdminPromoFlow.choose_discount_type, F.data.startswith("admin_promo:type:"))
async def promo_create_type(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    await callback.answer()
    discount_type = callback.data.split(":")[2]
    await state.update_data(discount_type=discount_type)
    await state.set_state(AdminPromoFlow.get_discount_value)
    async with async_session() as session:
        mm = MenuManager(bot, session)
        prompt = "Введите процент скидки числом" if discount_type == "percent" else "Введите сумму скидки в ₽"
        await mm.show_menu(
            chat_id=callback.message.chat.id,
            user_id=callback.from_user.id,
            text=prompt,
            screen_name="promo_create_value",
        )


@router.message(AdminPromoFlow.get_discount_value, F.text)
async def promo_create_value(message: Message, state: FSMContext, bot: Bot) -> None:
    await state.update_data(discount_value=int(message.text.strip()))
    await state.set_state(AdminPromoFlow.get_usage_limit)
    async with async_session() as session:
        mm = MenuManager(bot, session)
        await mm.delete_user_message(message)
        await mm.show_menu(
            chat_id=message.chat.id,
            user_id=message.from_user.id,
            text="Введите лимит использований или `-` без лимита",
            screen_name="promo_create_limit",
        )


@router.message(AdminPromoFlow.get_usage_limit, F.text)
async def promo_create_limit(message: Message, state: FSMContext, bot: Bot) -> None:
    await state.update_data(usage_limit=_parse_limit(message.text))
    await state.set_state(AdminPromoFlow.get_valid_until)
    async with async_session() as session:
        mm = MenuManager(bot, session)
        await mm.delete_user_message(message)
        await mm.show_menu(
            chat_id=message.chat.id,
            user_id=message.from_user.id,
            text="Введите срок в формате DD.MM.YYYY или `-` без срока",
            screen_name="promo_create_valid_until",
        )


@router.message(AdminPromoFlow.get_valid_until, F.text)
async def promo_create_valid_until(message: Message, state: FSMContext, bot: Bot) -> None:
    data = await state.get_data()
    async with async_session() as session:
        promo = await create_promo(
            session,
            code=data["code"],
            discount_type=data["discount_type"],
            discount_value=int(data["discount_value"]),
            usage_limit=data.get("usage_limit"),
            valid_until=_parse_valid_until(message.text),
        )
        await state.clear()
        await message.delete()
    await _show_promo_detail(bot, message.chat.id, message.from_user.id, promo.id)


@router.callback_query(F.data.startswith("admin_promo:edit_discount:"))
async def promo_edit_discount_start(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    await callback.answer()
    promo_id = int(callback.data.split(":")[2])
    await state.set_state(AdminPromoFlow.edit_discount)
    await state.update_data(promo_id=promo_id)
    async with async_session() as session:
        mm = MenuManager(bot, session)
        await mm.show_menu(callback.message.chat.id, callback.from_user.id, "Введите новую скидку. `10%` или `500`", screen_name="promo_edit_discount")


@router.message(AdminPromoFlow.edit_discount, F.text)
async def promo_edit_discount(message: Message, state: FSMContext, bot: Bot) -> None:
    raw = message.text.strip()
    promo_id = (await state.get_data())["promo_id"]
    discount_type = "percent" if raw.endswith("%") else "fixed"
    value = int(raw.rstrip("%"))
    async with async_session() as session:
        promo = await session.get(PromoCode, promo_id)
        await update_promo_discount(session, promo, discount_type, value)
        await state.clear()
        await message.delete()
    await _show_promo_detail(bot, message.chat.id, message.from_user.id, promo_id)


@router.callback_query(F.data.startswith("admin_promo:edit_limit:"))
async def promo_edit_limit_start(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    await callback.answer()
    promo_id = int(callback.data.split(":")[2])
    await state.set_state(AdminPromoFlow.edit_limit)
    await state.update_data(promo_id=promo_id)
    async with async_session() as session:
        mm = MenuManager(bot, session)
        await mm.show_menu(callback.message.chat.id, callback.from_user.id, "Введите новый лимит или `-` без лимита", screen_name="promo_edit_limit")


@router.message(AdminPromoFlow.edit_limit, F.text)
async def promo_edit_limit(message: Message, state: FSMContext, bot: Bot) -> None:
    promo_id = (await state.get_data())["promo_id"]
    async with async_session() as session:
        promo = await session.get(PromoCode, promo_id)
        await update_promo_limit(session, promo, _parse_limit(message.text))
        await state.clear()
        await message.delete()
    await _show_promo_detail(bot, message.chat.id, message.from_user.id, promo_id)


@router.callback_query(F.data.startswith("admin_promo:edit_valid_until:"))
async def promo_edit_valid_until_start(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    await callback.answer()
    promo_id = int(callback.data.split(":")[2])
    await state.set_state(AdminPromoFlow.edit_valid_until)
    await state.update_data(promo_id=promo_id)
    async with async_session() as session:
        mm = MenuManager(bot, session)
        await mm.show_menu(callback.message.chat.id, callback.from_user.id, "Введите новую дату DD.MM.YYYY или `-`", screen_name="promo_edit_valid_until")


@router.message(AdminPromoFlow.edit_valid_until, F.text)
async def promo_edit_valid_until(message: Message, state: FSMContext, bot: Bot) -> None:
    promo_id = (await state.get_data())["promo_id"]
    async with async_session() as session:
        promo = await session.get(PromoCode, promo_id)
        await update_promo_valid_until(session, promo, _parse_valid_until(message.text))
        await state.clear()
        await message.delete()
    await _show_promo_detail(bot, message.chat.id, message.from_user.id, promo_id)


@router.callback_query(F.data.startswith("admin_promo:delete:"))
async def promo_delete_start(callback: CallbackQuery, bot: Bot) -> None:
    await callback.answer()
    promo_id = int(callback.data.split(":")[2])
    async with async_session() as session:
        mm = MenuManager(bot, session)
        await mm.show_menu(
            chat_id=callback.message.chat.id,
            user_id=callback.from_user.id,
            text="Удалить промокод? Если он уже использовался, он будет только деактивирован.",
            reply_markup=promo_delete_confirm_kb(promo_id),
            screen_name=f"promo_delete_{promo_id}",
        )


@router.callback_query(F.data.startswith("admin_promo:delete_confirm:"))
async def promo_delete_confirm(callback: CallbackQuery, bot: Bot) -> None:
    await callback.answer()
    promo_id = int(callback.data.split(":")[3])
    async with async_session() as session:
        promo = await session.get(PromoCode, promo_id)
        if promo:
            await deactivate_or_delete_promo(session, promo)
    await _show_promo_list(bot, callback.message.chat.id, callback.from_user.id)
