import logging
from aiogram import Bot, Router
from aiogram.types import Message
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from bot.db import async_session
from bot.keyboards.channel import build_channel_post_keyboard
from bot.services.source_service import create_or_get_channel_post

router = Router()
logger = logging.getLogger(__name__)


@router.channel_post()
async def on_channel_post(message: Message, bot: Bot) -> None:
    caption = message.caption or message.text

    async with async_session() as session:
        post = await create_or_get_channel_post(
            session=session,
            chat_id=message.chat.id,
            message_id=message.message_id,
            caption=caption,
        )

    existing_rows = []
    if message.reply_markup and message.reply_markup.inline_keyboard:
        existing_rows = [list(row) for row in message.reply_markup.inline_keyboard]

    # Избегаем дублирования кнопки, если она уже содержит этот source_code
    for row in existing_rows:
        for button in row:
            if button.url and post.source_code in button.url:
                return

    keyboard = build_channel_post_keyboard(post.source_code, keep_rows=existing_rows)

    try:
        await bot.edit_message_reply_markup(
            chat_id=message.chat.id,
            message_id=message.message_id,
            reply_markup=keyboard,
        )
        logger.info(f"Added deep-link button to post {message.message_id} in channel {message.chat.id}")
    except TelegramForbiddenError:
        logger.error("Bot has no rights to edit channel posts")
    except TelegramBadRequest as e:
        logger.error(f"Cannot edit reply markup for channel post: {e}")
