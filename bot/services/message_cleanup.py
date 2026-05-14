from aiogram.fsm.context import FSMContext
from aiogram.types import Message


async def safe_delete_message(message: Message) -> None:
    try:
        await message.delete()
    except Exception:
        pass


async def replace_state_error(
    message: Message,
    state: FSMContext,
    text: str,
    *,
    reply_markup=None,
    parse_mode: str | None = "HTML",
    key: str = "last_error_message_id",
) -> None:
    data = await state.get_data()
    previous_id = data.get(key)
    if previous_id:
        try:
            await message.bot.delete_message(message.chat.id, previous_id)
        except Exception:
            pass

    sent = await message.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)
    await state.update_data(**{key: getattr(sent, "message_id", None)})
