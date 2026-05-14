from __future__ import annotations

from typing import Any

from aiogram.types import InlineKeyboardButton, KeyboardButton

from bot.ui_tokens import CE, E


def icon_key_text(key: str, text: str) -> str:
    emoji = E.get(key, "")
    return f"{emoji} {text}".strip()


def ibtn(
    key: str,
    text: str,
    callback_data: str | None = None,
    url: str | None = None,
    web_app: Any = None,
    style: str | None = None,
) -> InlineKeyboardButton:
    custom_id = CE.get(key)
    return InlineKeyboardButton(
        text=text if custom_id else icon_key_text(key, text),
        icon_custom_emoji_id=custom_id,
        style=style,
        callback_data=callback_data,
        url=url,
        web_app=web_app,
    )


def rbtn(
    key: str,
    text: str,
    request_contact: bool = False,
    style: str | None = None,
) -> KeyboardButton:
    custom_id = CE.get(key)
    return KeyboardButton(
        text=text if custom_id else icon_key_text(key, text),
        icon_custom_emoji_id=custom_id,
        style=style,
        request_contact=request_contact,
    )
