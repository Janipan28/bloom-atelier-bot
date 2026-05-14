from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from bot.handlers.user_order import process_time_manual
from bot.services.parsers import normalize_date_input, normalize_time_input


def test_date_parser_accepts_15_may():
    result = normalize_date_input("15 мая", now=datetime(2026, 5, 12, 10, 0))

    assert result.error is None
    assert result.date_str == "15.05"


def test_date_parser_rejects_31_02():
    result = normalize_date_input("31.02", now=datetime(2026, 1, 10, 10, 0))

    assert result.error


def test_date_parser_rejects_past_date():
    result = normalize_date_input("10.05", now=datetime(2026, 5, 12, 10, 0))

    assert result.error == "Дата уже прошла."


def test_time_parser_accepts_18_30_dot():
    result = normalize_time_input("18.30")

    assert result.time_str == "18:30"


def test_time_parser_accepts_1830():
    result = normalize_time_input("1830")

    assert result.time_str == "18:30"


def test_time_parser_accepts_18():
    result = normalize_time_input("18")

    assert result.time_str == "18:00"


def test_time_parser_asks_confirmation_for_v_6():
    result = normalize_time_input("в 6")

    assert result.is_ambiguous
    assert result.suggestions == ["18:00"]


def test_time_parser_suggests_slots_for_evening():
    result = normalize_time_input("вечером")

    assert result.is_ambiguous
    assert "18:00–20:00" in result.suggestions
    assert "20:00–22:00" in result.suggestions


@pytest.mark.asyncio
async def test_time_handler_suggests_slots_for_evening():
    message = AsyncMock()
    message.text = "вечером"
    state = AsyncMock()

    await process_time_manual(message, state, bot=AsyncMock())

    text = message.answer.call_args[0][0]
    markup = message.answer.call_args[1]["reply_markup"]
    buttons = [button.text for row in markup.inline_keyboard for button in row]
    assert "Вечером обычно удобно так" in text
    assert "18:00–20:00" in buttons
    assert "20:00–22:00" in buttons
