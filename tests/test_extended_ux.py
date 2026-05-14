import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram import Bot
from aiogram.fsm.context import FSMContext
from bot.handlers.user_order import (
    show_catalog_handler,
    start_order_flow,
    process_service_choice,
    process_services_continue,
    process_no_services,
    process_phone,
    process_address,
    show_confirmation,
    contact_florist_handler,
    process_date_manual,
    process_time_manual
)
from bot.handlers.admin import (
    cmd_admin,
    admin_orders_handler,
    admin_order_view_handler
)
from bot.states.order_states import OrderFlow
from bot.keyboards.user import entry_choice_kb, delivery_type_kb, branches_kb, date_kb
from bot import strings

@pytest.fixture
def mock_state():
    state = AsyncMock(spec=FSMContext)
    state.get_data.return_value = {}
    return state

@pytest.fixture
def mock_callback():
    cb = AsyncMock()
    cb.message = AsyncMock()
    cb.from_user = MagicMock(id=123, username="testuser", full_name="Test User")
    return cb

@pytest.fixture
def mock_message():
    msg = AsyncMock()
    msg.chat.id = 123
    msg.from_user.id = 123
    msg.text = "test_text"
    return msg

# --- USER TESTS ---

@pytest.mark.asyncio
@patch("bot.handlers.user_order.MenuManager")
@patch("bot.handlers.user_order.async_session")
@patch("bot.handlers.user_order.list_active_branches")
async def test_branch_buttons_show_address(mock_list_branches, mock_session_cm, mock_mm_class, mock_callback):
    mock_mm = AsyncMock()
    mock_mm_class.return_value = mock_mm
    
    branch1 = MagicMock(id=1, title="Bloom Atelier · Центр", address="ул. Цветочная, 10")
    mock_list_branches.return_value = [branch1]
    mock_session_cm.return_value.__aenter__.return_value = AsyncMock()
    
    from bot.handlers.user_order import show_branches_handler
    await show_branches_handler(mock_callback, bot=AsyncMock())
    
    markup = mock_mm.show_menu.call_args[1]["reply_markup"]
    btn_text = markup.inline_keyboard[0][0].text
    assert "ул. Цветочная, 10" in btn_text

@pytest.mark.asyncio
@patch("bot.handlers.user_order.MenuManager")
@patch("bot.handlers.user_order.async_session")
async def test_catalog_pagination_shows_counter(mock_session_cm, mock_mm_class, mock_callback):
    mock_mm = AsyncMock()
    mock_mm_class.return_value = mock_mm
    
    p1 = MagicMock(id=1, title="B1", price=100, is_active=True, description="D1")
    p2 = MagicMock(id=2, title="B2", price=200, is_active=True, description="D2")
    
    mock_session = AsyncMock()
    # Mock scalars result
    mock_scalars = MagicMock()
    mock_scalars.__iter__.return_value = [p1, p2]
    mock_session.scalars.return_value = [p1, p2] # For simplicity in this handler
    mock_session_cm.return_value.__aenter__.return_value = mock_session
    
    await show_catalog_handler(mock_callback, bot=AsyncMock())
    
    text = mock_mm.show_menu.call_args[1]["text"]
    assert "Выберите букет" in text

@pytest.mark.asyncio
@patch("bot.handlers.user_order.MenuManager")
@patch("bot.handlers.user_order.async_session")
async def test_date_validation_rejected_32_05(mock_session_cm, mock_mm_class, mock_message, mock_state):
    mock_mm = AsyncMock()
    mock_mm.delete_user_message = AsyncMock()
    mock_mm_class.return_value = mock_mm
    mock_session_cm.return_value.__aenter__.return_value = AsyncMock()

    mock_message.text = "32.05"
    await process_date_manual(mock_message, mock_state, bot=AsyncMock())
    mock_message.answer.assert_called_with("Не хочу ошибиться с датой.\n\nНапишите дату в формате 15.05, 15/05 или 15 мая, или выберите кнопку ниже.", reply_markup=date_kb())

# --- ADMIN TESTS ---

@pytest.mark.asyncio
@patch("bot.handlers.admin.get_basic_stats")
@patch("bot.handlers.admin.async_session")
@patch("bot.handlers.admin.is_admin")
async def test_admin_dashboard_no_raw_status(mock_is_admin, mock_session_cm, mock_get_stats, mock_message):
    mock_is_admin.return_value = True
    mock_get_stats.return_value = {
        "new_orders": 1, "florist_requests": 0, "delivery_orders": 0, "pickup_orders": 0,
        "total_customers": 1, "total_orders": 1, "total_branches": 1, "total_promos": 1
    }
    await cmd_admin(mock_message, state=AsyncMock(), bot=AsyncMock())
    text = mock_message.answer.call_args[0][0]
    assert "needs_florist" not in text

@pytest.mark.asyncio
@patch("bot.handlers.admin.MenuManager")
@patch("bot.handlers.admin.get_recent_orders")
@patch("bot.handlers.admin.async_session")
@patch("bot.handlers.admin.is_admin")
async def test_admin_orders_has_back_button(mock_is_admin, mock_session_cm, mock_get_orders, mock_mm_class, mock_callback):
    mock_is_admin.return_value = True
    mock_mm = AsyncMock()
    mock_mm_class.return_value = mock_mm
    mock_get_orders.return_value = [MagicMock(id=1, status="new")]
    await admin_orders_handler(mock_callback, bot=AsyncMock())
    markup = mock_mm.show_menu.call_args[1]["reply_markup"]
    assert markup.inline_keyboard[-1][0].callback_data == "admin:main"

@pytest.mark.asyncio
@patch("bot.handlers.admin.is_admin", return_value=True)
@patch("bot.handlers.admin.async_session")
async def test_admin_order_detail_has_back_to_orders(mock_session_cm, mock_is_admin, mock_callback):
    order = MagicMock(id=1, status="new", phone="123", delivery_type="D", customer=MagicMock(username="u"), product_id=1, comment="C", total_amount=1000)
    mock_session = AsyncMock()
    mock_session.get.return_value = order
    # Also mock scalar for session.scalar(...)
    mock_session.scalar = AsyncMock(return_value=order)
    mock_session_cm.return_value.__aenter__.return_value = mock_session
    
    mock_callback.data = "admin_order_view:1"
    mock_mm = AsyncMock()
    with patch("bot.handlers.admin.MenuManager", return_value=mock_mm):
        await admin_order_view_handler(mock_callback, bot=AsyncMock())
    markup = mock_mm.show_menu.call_args[1]["reply_markup"]
    found = False
    for row in markup.inline_keyboard:
        for btn in row:
            if btn.callback_data == "admin:orders":
                found = True
    assert found
