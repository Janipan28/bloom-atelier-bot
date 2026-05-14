import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from bot.handlers.start import cmd_start
from bot.services.menu_service import MenuManager
from bot import strings
from bot.handlers.user_order import _main_menu_text

@pytest.mark.asyncio
@patch("bot.handlers.start.get_or_create_customer")
@patch("bot.handlers.start.MenuManager")
@patch("bot.handlers.start.async_session")
async def test_cmd_start_deletes_message(mock_session_cm, mock_mm_class, mock_get_customer):
    # Setup mocks
    mock_mm = AsyncMock()
    mock_mm_class.return_value = mock_mm
    
    mock_session = AsyncMock()
    mock_session_cm.return_value.__aenter__.return_value = mock_session
    mock_customer = MagicMock(loyalty_points=120)
    mock_get_customer.return_value = mock_customer
    
    message = AsyncMock()
    message.text = "/start"
    message.chat.id = 123
    message.from_user.id = 456
    
    state = AsyncMock()
    bot = AsyncMock()
    
    await cmd_start(message, state, bot)
    
    # Verify MenuManager was used to show main menu
    mock_mm.show_menu.assert_called_once()
    assert mock_mm.show_menu.call_args[1]["text"] == _main_menu_text(120)
    
    # Verify user message was deleted via MenuManager
    mock_mm.delete_user_message.assert_called_once_with(message)
