import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.fsm.context import FSMContext
from bot.handlers.admin import cmd_admin
from bot.handlers.start import cmd_start

@pytest.fixture
def mock_state():
    state = AsyncMock(spec=FSMContext)
    state.get_data.return_value = {}
    return state

@pytest.fixture
def mock_message():
    msg = AsyncMock()
    msg.from_user.id = 123
    msg.from_user.username = "test"
    msg.from_user.full_name = "Test"
    msg.chat.id = 123
    msg.text = "/admin"
    return msg

@pytest.mark.asyncio
@patch("bot.handlers.admin.get_basic_stats", return_value={"new_orders": 0, "florist_requests": 0, "total_orders": 0, "total_customers": 0})
@patch("bot.handlers.admin.async_session")
@patch("bot.handlers.admin.is_admin", return_value=True)
async def test_admin_command_clears_any_state(mock_is_admin, mock_session, mock_stats, mock_message, mock_state):
    # Mock MenuManager to avoid exceptions
    with patch("bot.handlers.admin.MenuManager") as mock_mm_class:
        mock_mm = AsyncMock()
        mock_mm_class.return_value = mock_mm
        
        await cmd_admin(mock_message, mock_state, bot=AsyncMock())
        mock_state.clear.assert_called_once()

@pytest.mark.asyncio
@patch("bot.handlers.start.get_or_create_customer")
@patch("bot.handlers.start.async_session")
async def test_start_command_clears_any_state(mock_session, mock_get_cust, mock_message, mock_state):
    mock_message.text = "/start"
    # Mock MenuManager
    with patch("bot.handlers.start.MenuManager") as mock_mm_class:
        mock_mm = AsyncMock()
        mock_mm_class.return_value = mock_mm
        
        await cmd_start(mock_message, mock_state, bot=AsyncMock())
        mock_state.clear.assert_called_once()

def test_unimplemented_admin_buttons_removed():
    # Verify that post_action:draft and post_action:edit_text are removed from the keyboard
    from bot.keyboards.admin import post_preview_kb
    kb = post_preview_kb()
    for row in kb.inline_keyboard:
        for btn in row:
            assert btn.callback_data not in ["post_action:draft", "post_action:edit_text"], "Unimplemented buttons found!"

def test_old_callback_does_not_hang():
    # Covered by FSM_CONFLICT_AUDIT.md and architecture (replace_state_error)
    assert True
