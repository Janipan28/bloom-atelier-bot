import asyncio
import logging
import os
import sys
import urllib.parse
from typing import Optional

from aiogram import Bot, Dispatcher, Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramUnauthorizedError
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from dotenv import load_dotenv


load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ORDER_URL = os.getenv("ORDER_URL", "").strip()
BUTTON_TEXT = os.getenv("BUTTON_TEXT", "Заказать").strip()
ORDER_TEXT = os.getenv("ORDER_TEXT", "").strip()

CATALOG_URL = os.getenv("CATALOG_URL", "").strip()
CATALOG_BUTTON_TEXT = os.getenv("CATALOG_BUTTON_TEXT", "Каталог").strip()

TARGET_CHANNEL_ID_RAW = os.getenv("TARGET_CHANNEL_ID", "").strip()


def get_final_order_url() -> str:
    """Формирует ссылку для заказа с предзаполненным текстом, если он указан."""
    if not ORDER_TEXT:
        return ORDER_URL
    
    encoded_text = urllib.parse.quote(ORDER_TEXT)
    # Если это ссылка на пользователя в t.me
    if "t.me/" in ORDER_URL:
        # Убираем лишние параметры, если они есть
        base_url = ORDER_URL.split('?')[0]
        return f"{base_url}?text={encoded_text}"
    
    return ORDER_URL


FINAL_ORDER_URL = get_final_order_url()


def parse_optional_int(value: str) -> Optional[int]:
    if not value:
        return None

    try:
        return int(value)
    except ValueError:
        raise ValueError("TARGET_CHANNEL_ID must be an integer, for example: -1001234567890")


TARGET_CHANNEL_ID = parse_optional_int(TARGET_CHANNEL_ID_RAW)

router = Router()


def validate_config() -> None:
    errors: list[str] = []

    if not BOT_TOKEN:
        errors.append("BOT_TOKEN is empty. Add it to .env")

    if not ORDER_URL:
        errors.append("ORDER_URL is empty. Add it to .env")

    if ORDER_URL and not (
        ORDER_URL.startswith("https://")
        or ORDER_URL.startswith("http://")
        or ORDER_URL.startswith("tg://")
    ):
        errors.append("ORDER_URL must start with https://, http:// or tg://")

    if not BUTTON_TEXT:
        errors.append("BUTTON_TEXT is empty")

    if errors:
        for error in errors:
            logging.error(error)
        raise RuntimeError("Invalid configuration. Fix .env and restart the bot.")


def keyboard_has_order_button(reply_markup: Optional[InlineKeyboardMarkup]) -> bool:
    if not reply_markup or not reply_markup.inline_keyboard:
        return False

    for row in reply_markup.inline_keyboard:
        for button in row:
            # Проверяем наличие любой из кнопок, чтобы не дублировать
            if (button.text == BUTTON_TEXT and button.url == FINAL_ORDER_URL) or \
               (button.text == CATALOG_BUTTON_TEXT and button.url == CATALOG_URL):
                return True

    return False


def build_keyboard_with_buttons(
    existing_markup: Optional[InlineKeyboardMarkup],
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    if existing_markup and existing_markup.inline_keyboard:
        for row in existing_markup.inline_keyboard:
            copied_row: list[InlineKeyboardButton] = []
            for button in row:
                copied_row.append(button)
            rows.append(copied_row)

    # Создаем ряд с двумя кнопками
    button_row: list[InlineKeyboardButton] = []
    
    if CATALOG_URL:
        button_row.append(
            InlineKeyboardButton(
                text=CATALOG_BUTTON_TEXT,
                url=CATALOG_URL,
            )
        )

    button_row.append(
        InlineKeyboardButton(
            text=BUTTON_TEXT,
            url=FINAL_ORDER_URL,
        )
    )

    rows.append(button_row)

    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.channel_post()
async def handle_channel_post(message: Message, bot: Bot) -> None:
    if TARGET_CHANNEL_ID is not None and message.chat.id != TARGET_CHANNEL_ID:
        logging.info(
            "Skipped post %s from channel %s because TARGET_CHANNEL_ID=%s",
            message.message_id,
            message.chat.id,
            TARGET_CHANNEL_ID,
        )
        return

    if keyboard_has_order_button(message.reply_markup):
        logging.info(
            "Skipped post %s in channel %s: buttons already exist",
            message.message_id,
            message.chat.id,
        )
        return

    keyboard = build_keyboard_with_buttons(message.reply_markup)

    try:
        await bot.edit_message_reply_markup(
            chat_id=message.chat.id,
            message_id=message.message_id,
            reply_markup=keyboard,
        )

        logging.info(
            "Added buttons to post %s in channel %s",
            message.message_id,
            message.chat.id,
        )

    except TelegramForbiddenError as error:
        logging.error(
            "Forbidden. Bot probably has no admin rights or no can_edit_messages permission. "
            "Channel: %s, post: %s, error: %s",
            message.chat.id,
            message.message_id,
            error,
        )

    except TelegramBadRequest as error:
        logging.error(
            "Bad request while editing reply markup. "
            "Channel: %s, post: %s, error: %s",
            message.chat.id,
            message.message_id,
            error,
        )

    except Exception:
        logging.exception(
            "Unexpected error while processing post %s in channel %s",
            message.message_id,
            message.chat.id,
        )


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    validate_config()

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)

    try:
        me = await bot.get_me()
        logging.info("Bot authorized as @%s, id=%s", me.username, me.id)

        # Important for local polling tests:
        # If a webhook was previously set, polling may not receive updates correctly.
        await bot.delete_webhook(drop_pending_updates=True)
        logging.info("Webhook deleted. Starting polling...")

        await dp.start_polling(
            bot,
            allowed_updates=["channel_post"],
        )

    except TelegramUnauthorizedError:
        logging.error("Unauthorized. BOT_TOKEN is invalid.")
        raise

    except KeyboardInterrupt:
        logging.info("Bot stopped by user.")

    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as error:
        logging.error("Bot stopped with error: %s", error)
        sys.exit(1)
