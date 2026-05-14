from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bot.handlers.admin import cmd_admin
from bot.handlers.admin_products import process_prod_price, process_prod_title
from bot.handlers.start import cmd_start
from bot.handlers.user_order import handle_text_on_callback_states


@pytest.mark.asyncio
@patch("bot.handlers.admin.get_basic_stats")
@patch("bot.handlers.admin.MenuManager")
@patch("bot.handlers.admin.async_session")
@patch("bot.handlers.admin.is_admin")
async def test_admin_command_clears_quick_post_state(mock_is_admin, mock_session_cm, mock_mm_class, mock_get_stats):
    mock_is_admin.return_value = True
    mock_get_stats.return_value = {"new_orders": 0, "florist_requests": 0, "total_orders": 0, "total_customers": 0}
    mock_mm = AsyncMock()
    mock_mm_class.return_value = mock_mm
    message = AsyncMock()
    message.from_user.id = 456
    message.chat.id = 456
    state = AsyncMock()

    await cmd_admin(message, state, bot=AsyncMock())

    state.clear.assert_awaited_once()
    mock_mm.cleanup_menu.assert_awaited_once_with(456, 456)
    message.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.admin.get_basic_stats")
@patch("bot.handlers.admin.MenuManager")
@patch("bot.handlers.admin.async_session")
@patch("bot.handlers.admin.is_admin")
async def test_admin_command_clears_bouquet_create_state(mock_is_admin, mock_session_cm, mock_mm_class, mock_get_stats):
    mock_is_admin.return_value = True
    mock_get_stats.return_value = {"new_orders": 0, "florist_requests": 0, "total_orders": 0, "total_customers": 0}
    mock_mm = AsyncMock()
    mock_mm_class.return_value = mock_mm
    message = AsyncMock()
    message.from_user.id = 456
    message.chat.id = 456
    state = AsyncMock()
    state.get_state.return_value = "AdminProductFlow:get_photo"

    await cmd_admin(message, state, bot=AsyncMock())

    state.clear.assert_awaited_once()
    mock_mm.cleanup_menu.assert_awaited_once_with(456, 456)
    message.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.admin.get_basic_stats")
@patch("bot.handlers.admin.MenuManager")
@patch("bot.handlers.admin.async_session")
@patch("bot.handlers.admin.is_admin")
async def test_admin_command_clears_user_order_state(mock_is_admin, mock_session_cm, mock_mm_class, mock_get_stats):
    mock_is_admin.return_value = True
    mock_get_stats.return_value = {"new_orders": 0, "florist_requests": 0, "total_orders": 0, "total_customers": 0}
    mock_mm = AsyncMock()
    mock_mm_class.return_value = mock_mm
    message = AsyncMock()
    message.from_user.id = 456
    message.chat.id = 456
    state = AsyncMock()
    state.get_state.return_value = "OrderFlow:confirm"

    await cmd_admin(message, state, bot=AsyncMock())

    state.clear.assert_awaited_once()
    message.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.start.get_or_create_customer", new_callable=AsyncMock)
@patch("bot.handlers.start.MenuManager")
@patch("bot.handlers.start.async_session")
async def test_start_command_clears_user_order_state(mock_session_cm, mock_mm_class, mock_customer):
    mock_mm = AsyncMock()
    mock_mm_class.return_value = mock_mm
    message = AsyncMock()
    message.text = "/start"
    message.from_user.id = 123
    message.from_user.username = "client"
    message.from_user.full_name = "Client"
    message.chat.id = 123
    state = AsyncMock()

    await cmd_start(message, state, bot=AsyncMock())

    state.clear.assert_awaited_once()
    mock_mm.show_menu.assert_awaited_once()
    mock_mm.delete_user_message.assert_awaited_once_with(message)


@pytest.mark.asyncio
@patch("bot.handlers.start.get_or_create_customer", new_callable=AsyncMock)
@patch("bot.handlers.start.MenuManager")
@patch("bot.handlers.start.async_session")
async def test_start_command_clears_admin_state(mock_session_cm, mock_mm_class, mock_customer):
    mock_mm = AsyncMock()
    mock_mm_class.return_value = mock_mm
    message = AsyncMock()
    message.text = "/start"
    message.from_user.id = 123
    message.from_user.username = "admin"
    message.from_user.full_name = "Admin"
    message.chat.id = 123
    state = AsyncMock()
    state.get_state.return_value = "AdminPostFlow:get_photo"

    await cmd_start(message, state, bot=AsyncMock())

    state.clear.assert_awaited_once()
    mock_mm.show_menu.assert_awaited_once()


@pytest.mark.asyncio
async def test_invalid_admin_input_does_not_duplicate_errors():
    message = AsyncMock()
    message.text = "не число"
    message.chat.id = 456
    message.bot = AsyncMock()
    first_error = MagicMock(message_id=100)
    second_error = MagicMock(message_id=101)
    message.answer.side_effect = [first_error, second_error]
    state = AsyncMock()
    state.get_data.side_effect = [{}, {"last_error_message_id": 100}]

    await process_prod_price(message, state)
    await process_prod_price(message, state)

    message.bot.delete_message.assert_awaited_once_with(456, 100)
    assert message.answer.await_count == 2
    state.update_data.assert_any_await(last_error_message_id=100)
    state.update_data.assert_any_await(last_error_message_id=101)


@pytest.mark.asyncio
@patch("bot.handlers.user_order.MenuManager")
@patch("bot.handlers.user_order.async_session")
async def test_invalid_user_input_does_not_duplicate_errors(mock_session_cm, mock_mm_class):
    mock_mm = AsyncMock()
    mock_mm_class.return_value = mock_mm
    mock_session_cm.return_value.__aenter__.return_value = AsyncMock()
    message = AsyncMock()
    message.chat.id = 123
    message.bot = AsyncMock()
    first_error = MagicMock(message_id=200)
    second_error = MagicMock(message_id=201)
    message.answer.side_effect = [first_error, second_error]
    state = AsyncMock()
    state.get_data.side_effect = [{}, {"last_error_message_id": 200}]

    await handle_text_on_callback_states(message, state, bot=AsyncMock())
    await handle_text_on_callback_states(message, state, bot=AsyncMock())

    message.bot.delete_message.assert_awaited_once_with(123, 200)
    assert message.answer.await_count == 2
    state.update_data.assert_any_await(last_error_message_id=200)
    state.update_data.assert_any_await(last_error_message_id=201)


@pytest.mark.asyncio
async def test_old_admin_prompt_removed_or_replaced():
    message = AsyncMock()
    message.text = "Букет Нежность"
    state = AsyncMock()

    await process_prod_title(message, state)

    message.delete.assert_awaited_once()
    state.set_state.assert_awaited_once()
    message.answer.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.user_order.MenuManager")
@patch("bot.handlers.user_order.async_session")
async def test_old_user_prompt_removed_or_replaced(mock_session_cm, mock_mm_class):
    mock_mm = AsyncMock()
    mock_mm_class.return_value = mock_mm
    mock_session_cm.return_value.__aenter__.return_value = AsyncMock()
    message = AsyncMock()
    message.chat.id = 123
    message.bot = AsyncMock()
    sent_error = MagicMock(message_id=300)
    message.answer.return_value = sent_error
    state = AsyncMock()
    state.get_data.return_value = {}

    await handle_text_on_callback_states(message, state, bot=AsyncMock())

    mock_mm.delete_user_message.assert_awaited_once_with(message)
    message.answer.assert_awaited_once()
    state.update_data.assert_awaited_once_with(last_error_message_id=300)


@pytest.mark.asyncio
@patch("bot.handlers.admin.get_basic_stats")
@patch("bot.handlers.admin.MenuManager")
@patch("bot.handlers.admin.async_session")
@patch("bot.handlers.admin.is_admin")
async def test_admin_after_stuck_photo_state_returns_dashboard(mock_is_admin, mock_session_cm, mock_mm_class, mock_get_stats):
    mock_is_admin.return_value = True
    mock_get_stats.return_value = {"new_orders": 1, "florist_requests": 2, "total_orders": 3, "total_customers": 4}
    mock_mm = AsyncMock()
    mock_mm_class.return_value = mock_mm
    message = AsyncMock()
    message.from_user.id = 456
    message.chat.id = 456
    state = AsyncMock()
    state.get_state.return_value = "AdminPostFlow:get_photo"

    await cmd_admin(message, state, bot=AsyncMock())

    text = message.answer.call_args[0][0]
    assert "Панель управления" in text
    state.clear.assert_awaited_once()


@pytest.mark.asyncio
@patch("bot.handlers.start.get_or_create_customer", new_callable=AsyncMock)
@patch("bot.handlers.start.MenuManager")
@patch("bot.handlers.start.async_session")
async def test_start_after_stuck_checkout_state_returns_main_menu(mock_session_cm, mock_mm_class, mock_customer):
    mock_mm = AsyncMock()
    mock_mm_class.return_value = mock_mm
    message = AsyncMock()
    message.text = "/start"
    message.from_user.id = 123
    message.from_user.username = "client"
    message.from_user.full_name = "Client"
    message.chat.id = 123
    state = AsyncMock()
    state.get_state.return_value = "OrderFlow:confirm"

    await cmd_start(message, state, bot=AsyncMock())

    state.clear.assert_awaited_once()
    assert mock_mm.show_menu.call_args[1]["screen_name"] == "main_menu"
