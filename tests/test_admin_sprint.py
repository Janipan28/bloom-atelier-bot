import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, PhotoSize
from bot.handlers.admin_posts import process_post_photo, process_post_title, process_post_price
from bot.handlers.admin import admin_stats_handler
from bot.states.admin_states import AdminPostFlow
from bot import strings

@pytest.fixture
def mock_state():
    state = AsyncMock(spec=FSMContext)
    state.get_data.return_value = {}
    return state

@pytest.mark.asyncio
@patch("bot.handlers.admin_posts.async_session")
async def test_quick_post_photo_saved(mock_session, mock_state):
    message = AsyncMock()
    message.photo = [MagicMock(spec=PhotoSize, file_id="photo123")]
    # Explicitly ensure message methods are awaitable
    message.answer = AsyncMock()
    
    with patch("bot.handlers.admin_posts.isinstance", return_value=True):
        await process_post_photo(message, mock_state)
    
    mock_state.update_data.assert_any_call(photo_id="photo123")
    mock_state.set_state.assert_called_with(AdminPostFlow.get_title)

@pytest.mark.asyncio
@patch("bot.handlers.admin_posts.async_session")
async def test_quick_post_title_saved(mock_session, mock_state):
    message = AsyncMock()
    message.text = "Bouquet Name"
    message.answer = AsyncMock()
    
    with patch("bot.handlers.admin_posts.isinstance", return_value=True):
        await process_post_title(message, mock_state)
    
    mock_state.update_data.assert_called_with(title="Bouquet Name")
    mock_state.set_state.assert_called_with(AdminPostFlow.get_price)

@pytest.mark.asyncio
@patch("bot.handlers.admin_posts.async_session")
async def test_quick_post_price_validation(mock_session, mock_state):
    message = AsyncMock()
    message.text = "4900"
    message.answer = AsyncMock()
    
    with patch("bot.handlers.admin_posts.isinstance", return_value=True):
        await process_post_price(message, mock_state)
    
    mock_state.update_data.assert_called_with(price=4900)

@pytest.mark.asyncio
@patch("bot.handlers.admin.MenuManager")
@patch("bot.handlers.admin.get_basic_stats")
@patch("bot.handlers.admin.async_session")
@patch("bot.handlers.admin.is_admin")
async def test_admin_stats_shows_sources(mock_is_admin, mock_session_cm, mock_get_stats, mock_mm_class):
    mock_is_admin.return_value = True
    mock_mm = AsyncMock()
    mock_mm_class.return_value = mock_mm
    mock_get_stats.return_value = {
        "total_customers": 10, "total_orders": 20, "total_consultations": 5,
        "total_branches": 2, "total_promos": 3, "total_products": 5, "total_posts": 4,
        "sources": {"posts": 10, "catalog": 5, "survey": 5, "florist": 0},
        "order_status_counts": {"new": 1},
        "cons_status_counts": {}
    }

    callback = AsyncMock()
    callback.from_user.id = 123
    callback.message = AsyncMock()

    await admin_stats_handler(callback, bot=AsyncMock())
    text = mock_mm.show_menu.call_args[1]["text"]
    assert "Из постов: <b>10</b>" in text
    assert "Из каталога: <b>5</b>" in text
