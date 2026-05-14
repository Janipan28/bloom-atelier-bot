from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from bot.config import get_settings


def build_channel_post_keyboard(source_code: str, keep_rows: list[list[InlineKeyboardButton]] | None = None) -> InlineKeyboardMarkup:
    settings = get_settings()
    rows = []

    if keep_rows:
        rows.extend(keep_rows)

    order_url = f"https://t.me/{settings.bot_username}?start={source_code}"
    rows.append([InlineKeyboardButton(text=settings.default_order_button_text, url=order_url)])

    if settings.mini_app_url:
        rows.append([InlineKeyboardButton(text="Открыть магазин", url=settings.mini_app_url)])

    return InlineKeyboardMarkup(inline_keyboard=rows)
