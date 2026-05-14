from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram import Bot
from aiogram.types import Message

from bot.config import get_settings

router = Router()
MAX_MESSAGE_LEN = 3500


class AdminEmojiProbe(StatesGroup):
    waiting_for_custom_emoji = State()


def is_admin(user_id: int) -> bool:
    return user_id in get_settings().admin_id_set


async def _send_chunked_html(message: Message, header: str, rows: list[str]) -> None:
    if not rows:
        await message.answer(header, parse_mode="HTML")
        return

    chunk = header
    for row in rows:
        candidate = f"{chunk}\n{row}" if chunk else row
        if len(candidate) > MAX_MESSAGE_LEN:
            await message.answer(chunk, parse_mode="HTML")
            chunk = row
        else:
            chunk = candidate

    if chunk:
        await message.answer(chunk, parse_mode="HTML")


@router.message(Command("emoji_probe"))
async def emoji_probe(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return

    await state.set_state(AdminEmojiProbe.waiting_for_custom_emoji)
    await message.answer(
        "Отправьте следующим сообщением premium/custom emoji, которые хотите использовать в боте.\n\n"
        "Можно отправить несколько emoji сразу."
    )


@router.message(AdminEmojiProbe.waiting_for_custom_emoji, F.entities)
async def collect_custom_emoji_ids(message: Message, state: FSMContext, bot: Bot) -> None:
    if not is_admin(message.from_user.id):
        await state.clear()
        return

    text = message.text or message.caption or ""
    entities = message.entities or message.caption_entities or []
    ids: list[str] = []

    for entity in entities:
        if entity.type == "custom_emoji" and entity.custom_emoji_id:
            ids.append(entity.custom_emoji_id)

    if not ids:
        await message.answer(
            "Не нашёл custom emoji в сообщении. Отправьте именно premium/custom emoji, а не обычный Unicode-смайл.",
            parse_mode="HTML",
        )
        return

    unique_ids = list(dict.fromkeys(ids))
    sticker_map = {}
    try:
        stickers = await bot.get_custom_emoji_stickers(unique_ids)
    except Exception:
        stickers = []

    for sticker in stickers:
        sticker_map[sticker.custom_emoji_id] = sticker

    rows: list[str] = []
    for entity in entities:
        if entity.type != "custom_emoji" or not entity.custom_emoji_id:
            continue
        visual = entity.extract_from(text)
        sticker = sticker_map.get(entity.custom_emoji_id)
        emoji = sticker.emoji if sticker and sticker.emoji else visual
        set_name = f" [{sticker.set_name}]" if sticker and sticker.set_name else ""
        rows.append(f"{emoji}{set_name} -> <code>{entity.custom_emoji_id}</code>")

    await state.clear()
    await _send_chunked_html(message, "Нашёл custom emoji IDs:\n", rows)


@router.message(AdminEmojiProbe.waiting_for_custom_emoji)
async def collect_custom_emoji_ids_no_entities(message: Message) -> None:
    if not is_admin(message.from_user.id):
        return

    await message.answer(
        "В сообщении нет custom emoji. Отправьте premium/custom emoji из набора Telegram.",
    )
