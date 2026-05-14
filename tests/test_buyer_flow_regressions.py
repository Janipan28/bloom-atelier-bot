from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bot.handlers.user_order import (
    BRANCHES_CONTEXT_MAIN,
    BRANCHES_CONTEXT_ORDER_PICKUP,
    branch_detail_handler,
    process_back,
    process_service_choice,
    show_confirmation,
)


def _callback(data: str):
    callback = AsyncMock()
    callback.data = data
    callback.message.chat.id = 123
    callback.from_user.id = 123
    callback.from_user.username = "client"
    callback.from_user.full_name = "Client User"
    return callback


@pytest.mark.asyncio
@patch("bot.handlers.user_order.view_services", new_callable=AsyncMock)
async def test_services_toggle_packaging_updates_button(mock_view_services):
    state = AsyncMock()
    state.get_data.return_value = {
        "product_price": 4900,
        "delivery_type": "Доставка",
        "selected_services": [],
    }

    await process_service_choice(_callback("service:toggle:packaging"), state, bot=AsyncMock())

    state.update_data.assert_awaited_with(selected_services=["packaging"])
    assert mock_view_services.await_args.args[5] == ["packaging"]


@pytest.mark.asyncio
@patch("bot.handlers.user_order.view_services", new_callable=AsyncMock)
async def test_services_toggle_second_click_removes_service(mock_view_services):
    state = AsyncMock()
    state.get_data.return_value = {
        "product_price": 4900,
        "delivery_type": "Доставка",
        "selected_services": ["packaging"],
    }

    await process_service_choice(_callback("service:toggle:packaging"), state, bot=AsyncMock())

    state.update_data.assert_awaited_with(selected_services=[])
    assert mock_view_services.await_args.args[5] == []


@pytest.mark.asyncio
@patch("bot.handlers.user_order.cancel_order", new_callable=AsyncMock)
async def test_branches_from_main_back_returns_main(mock_cancel_order):
    state = AsyncMock()
    state.get_data.return_value = {"branches_context": BRANCHES_CONTEXT_MAIN}

    await process_back(_callback("back:branches"), state, bot=AsyncMock())

    mock_cancel_order.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.user_order.view_delivery_type", new_callable=AsyncMock)
@patch("bot.handlers.user_order.async_session")
async def test_branches_from_order_back_returns_delivery_type(mock_session_cm, mock_view_delivery):
    state = AsyncMock()
    state.get_data.return_value = {"branches_context": BRANCHES_CONTEXT_ORDER_PICKUP}
    mock_session_cm.return_value.__aenter__.return_value = AsyncMock()

    await process_back(_callback("back:branches"), state, bot=AsyncMock())

    mock_view_delivery.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.user_order.MenuManager")
@patch("bot.handlers.user_order.async_session")
async def test_branch_card_from_main_has_no_select_button(mock_session_cm, mock_mm_class):
    state = AsyncMock()
    state.get_data.return_value = {"branches_context": BRANCHES_CONTEXT_MAIN}
    branch = MagicMock(
        id=3,
        title="Store",
        address="ул. Цветочная, 10",
        work_hours="10:00–21:00",
        yandex_maps_url="https://maps.example",
    )
    session = AsyncMock()
    session.get.return_value = branch
    mock_session_cm.return_value.__aenter__.return_value = session
    mock_mm = AsyncMock()
    mock_mm_class.return_value = mock_mm

    await branch_detail_handler(_callback("branch_info:3"), state, bot=AsyncMock())

    markup = mock_mm.show_menu.call_args.kwargs["reply_markup"]
    texts = [button.text for row in markup.inline_keyboard for button in row]
    assert not any("Забрать отсюда" in text for text in texts)


@pytest.mark.asyncio
@patch("bot.handlers.user_order.MenuManager")
@patch("bot.handlers.user_order.async_session")
async def test_branch_card_from_order_has_select_button(mock_session_cm, mock_mm_class):
    state = AsyncMock()
    state.get_data.return_value = {"branches_context": BRANCHES_CONTEXT_ORDER_PICKUP}
    branch = MagicMock(
        id=3,
        title="Store",
        address="ул. Цветочная, 10",
        work_hours="10:00–21:00",
        yandex_maps_url="https://maps.example",
    )
    session = AsyncMock()
    session.get.return_value = branch
    mock_session_cm.return_value.__aenter__.return_value = session
    mock_mm = AsyncMock()
    mock_mm_class.return_value = mock_mm

    await branch_detail_handler(_callback("branch_info:3"), state, bot=AsyncMock())

    markup = mock_mm.show_menu.call_args.kwargs["reply_markup"]
    texts = [button.text for row in markup.inline_keyboard for button in row]
    assert any("Забрать отсюда" in text for text in texts)


@pytest.mark.asyncio
@patch("bot.handlers.user_order.MenuManager")
@patch("bot.handlers.user_order.async_session")
async def test_confirmation_shows_postcard_text(mock_session_cm, mock_mm_class):
    state = AsyncMock()
    state.get_data.return_value = {
        "product_price": 4900,
        "delivery_type": "Доставка",
        "selected_services": ["postcard"],
        "card_text": "С любовью",
        "product_title": "Нежность",
        "date_text": "завтра",
        "time_text": "18:30",
        "delivery_address": "ул. Ленина, 42",
        "phone": "+79990000000",
        "comment": "-",
    }
    mock_session_cm.return_value.__aenter__.return_value = AsyncMock()
    mock_mm = AsyncMock()
    mock_mm_class.return_value = mock_mm

    await show_confirmation(chat_id=123, user_id=123, state=state, bot=AsyncMock())

    text = mock_mm.show_menu.call_args.kwargs["text"]
    assert "Текст открытки: С любовью" in text
