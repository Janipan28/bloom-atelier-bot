from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bot.handlers.user_order import (
    BRANCHES_CONTEXT_MAIN,
    BRANCHES_CONTEXT_ORDER_PICKUP,
    branch_detail_handler,
    contact_florist_handler,
    my_orders_handler,
    process_back,
    process_service_choice,
)
from bot.services.parsers import normalize_time_input, normalize_date_input


def _callback():
    callback = AsyncMock()
    callback.message.chat.id = 123
    callback.from_user.id = 123
    callback.from_user.username = "client"
    callback.from_user.full_name = "Client User"
    return callback


def test_time_parser_accepts_1830_variants():
    for raw in ["18:30", "18.30", "18 30", "1830", "к 18:30"]:
        result = normalize_time_input(raw)
        assert result.time_str == "18:30"


def test_time_parser_ambiguous_6_requires_confirmation():
    result = normalize_time_input("в 6")
    assert result.is_ambiguous
    assert result.suggestions == ["18:00"]


def test_time_parser_evening_suggests_slots():
    result = normalize_time_input("вечером")
    assert result.is_ambiguous
    assert result.suggestions == ["16:00–18:00", "18:00–20:00", "20:00–22:00"]


def test_past_date_rejected():
    result = normalize_date_input("10.05")
    assert result.error


@pytest.mark.asyncio
@patch("bot.handlers.user_order.notify_admin_about_florist_lead", new_callable=AsyncMock)
@patch("bot.handlers.user_order.create_florist_lead", new_callable=AsyncMock)
@patch("bot.handlers.user_order.MenuManager")
@patch("bot.handlers.user_order.async_session")
async def test_florist_flow_keeps_product_context(mock_session_cm, mock_mm_class, mock_create_lead, mock_notify):
    """Флорист теперь сначала просит написать сообщение, потом создаёт лид."""
    from bot.handlers.user_order import contact_florist_handler, process_florist_message
    state = AsyncMock()
    state.get_data.return_value = {
        "product_id": 42,
        "product_title": "Нежность",
        "source_code": "src_p42",
        "source_post_id": 7,
    }
    callback = _callback()
    session = AsyncMock()
    session.get.return_value = MagicMock(id=42, title="Нежность")
    mock_session_cm.return_value.__aenter__.return_value = session
    mock_mm_class.return_value = AsyncMock()
    mock_create_lead.return_value = MagicMock(customer=MagicMock(), id=1)

    # Шаг 1: нажали "Написать флористу" — должен показать экран ввода
    await contact_florist_handler(callback, state, bot=AsyncMock())
    state.set_state.assert_called_once()  # Устанавливает florist_message state
    mock_create_lead.assert_not_called()  # Лид ещё не создан

    # Шаг 2: пользователь написал сообщение
    message = AsyncMock()
    message.text = "Хочу букет пионов"
    message.from_user.id = 123
    message.from_user.username = "testuser"
    message.from_user.full_name = "Test User"
    message.chat.id = 123
    state.get_data.return_value = {
        "product_id": 42,
        "source_post_id": 7,
    }
    await process_florist_message(message, state, bot=AsyncMock())

    mock_create_lead.assert_called_once()
    kwargs = mock_create_lead.await_args.kwargs
    assert kwargs["product_id"] == 42
    assert kwargs["source_post_id"] == 7
    mock_notify.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.user_order.MenuManager")
@patch("bot.handlers.user_order.get_user_orders")
@patch("bot.handlers.user_order.async_session")
async def test_my_orders_hides_raw_statuses(mock_session_cm, mock_get_orders, mock_mm_class):
    order = MagicMock(
        id=24,
        status="new",
        delivery_type="Доставка",
        total_amount=5850,
        date_text="15.05",
        product=MagicMock(title="Нежность"),
    )
    mock_get_orders.return_value = [order]
    mock_session_cm.return_value.__aenter__.return_value = AsyncMock()
    mock_mm = AsyncMock()
    mock_mm_class.return_value = mock_mm

    await my_orders_handler(_callback(), bot=AsyncMock())

    text = mock_mm.show_menu.call_args[1]["text"]
    assert "pending_manual" not in text
    assert "needs_florist" not in text
    assert "manual_after_confirmation" not in text


@pytest.mark.asyncio
@patch("bot.handlers.user_order.MenuManager")
@patch("bot.handlers.user_order.get_user_orders")
@patch("bot.handlers.user_order.async_session")
async def test_my_orders_shows_total_and_product(mock_session_cm, mock_get_orders, mock_mm_class):
    order = MagicMock(
        id=24,
        status="new",
        delivery_type="Доставка",
        total_amount=5850,
        date_text="15.05",
        product=MagicMock(title="Нежность"),
    )
    mock_get_orders.return_value = [order]
    mock_session_cm.return_value.__aenter__.return_value = AsyncMock()
    mock_mm = AsyncMock()
    mock_mm_class.return_value = mock_mm

    await my_orders_handler(_callback(), bot=AsyncMock())

    text = mock_mm.show_menu.call_args[1]["text"]
    assert "Нежность" in text
    assert "от 5 850 ₽" in text


@pytest.mark.asyncio
@patch("bot.handlers.user_order.MenuManager")
@patch("bot.handlers.user_order.get_user_orders")
@patch("bot.handlers.user_order.async_session")
async def test_my_orders_empty_has_only_catalog_cta(mock_session_cm, mock_get_orders, mock_mm_class):
    mock_get_orders.return_value = []
    mock_session_cm.return_value.__aenter__.return_value = AsyncMock()
    mock_mm = AsyncMock()
    mock_mm_class.return_value = mock_mm

    await my_orders_handler(_callback(), bot=AsyncMock())

    markup = mock_mm.show_menu.call_args[1]["reply_markup"]
    texts = [button.text for row in markup.inline_keyboard for button in row]
    assert any("Выбрать букет" in text for text in texts)
    assert not any("Помочь с выбором" in text for text in texts)
