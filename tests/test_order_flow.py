import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.fsm.context import FSMContext
from bot.handlers.user_order import (
    show_catalog_handler, 
    start_order_flow, 
    process_service_choice, 
    process_services_continue,
    process_date_manual,
    process_time_manual
)
from bot.states.order_states import OrderFlow
from bot import strings

@pytest.mark.asyncio
@patch("bot.handlers.user_order.MenuManager")
@patch("bot.handlers.user_order.async_session")
async def test_show_catalog_handler(mock_session, mock_mm_class):
    mock_mm = AsyncMock()
    mock_mm_class.return_value = mock_mm
    
    callback = AsyncMock()
    callback.message = AsyncMock()
    callback.from_user = MagicMock(id=123)
    
    mock_session_inst = AsyncMock()
    mock_session_inst.scalars.return_value = []
    mock_session.return_value.__aenter__.return_value = mock_session_inst
    
    await show_catalog_handler(callback, bot=AsyncMock())
    
    mock_mm.show_menu.assert_called_once()
    assert "Каталог пока пуст" in mock_mm.show_menu.call_args[1]["text"]

@pytest.mark.asyncio
@patch("bot.handlers.user_order.MenuManager")
@patch("bot.handlers.user_order.async_session")
async def test_start_order_flow_no_product(mock_session, mock_mm_class):
    mock_mm = AsyncMock()
    mock_mm_class.return_value = mock_mm
    
    callback = AsyncMock()
    callback.message = AsyncMock()
    callback.from_user = MagicMock(id=123)
    state = AsyncMock(spec=FSMContext)
    state.get_data.return_value = {} # No product_id
    
    mock_session_inst = AsyncMock()
    mock_session_inst.scalars.return_value = [MagicMock(id=1, title="B1", price=100, is_active=True, description="D1")]
    mock_session.return_value.__aenter__.return_value = mock_session_inst
    
    await start_order_flow(callback, state, bot=AsyncMock())
    
    # Should redirect to catalog
    mock_mm.show_menu.assert_called_once()
    assert "Выберите букет" in mock_mm.show_menu.call_args[1]["text"]

@pytest.mark.asyncio
@patch("bot.handlers.user_order.MenuManager")
@patch("bot.handlers.user_order.async_session")
async def test_process_date_manual_invalid(mock_session_cm, mock_mm_class):
    mock_mm = AsyncMock()
    mock_mm_class.return_value = mock_mm
    mock_session_cm.return_value.__aenter__.return_value = AsyncMock()
    
    message = AsyncMock()
    message.text = "invalid date"
    state = AsyncMock(spec=FSMContext)
    
    await process_date_manual(message, state, bot=AsyncMock())
    
    message.answer.assert_called_once()
    assert "Не хочу ошибиться с датой" in message.answer.call_args[0][0]

@pytest.mark.asyncio
@patch("bot.handlers.user_order.MenuManager")
@patch("bot.handlers.user_order.async_session")
async def test_process_date_manual_valid(mock_session_cm, mock_mm_class):
    mock_mm = AsyncMock()
    mock_mm.delete_user_message = AsyncMock()
    mock_mm_class.return_value = mock_mm
    mock_session_cm.return_value.__aenter__.return_value = AsyncMock()
    
    message = AsyncMock()
    message.text = "15.05"
    message.chat.id = 123
    message.from_user.id = 123
    state = AsyncMock(spec=FSMContext)
    state.get_data.return_value = {}
    
    await process_date_manual(message, state, bot=AsyncMock())
    
    state.update_data.assert_any_call(date_text="15.05")
    # Because of next_step, the next state is choose_time
    state.set_state.assert_called_with(OrderFlow.choose_time)

@pytest.mark.asyncio
@patch("bot.handlers.user_order.MenuManager")
@patch("bot.handlers.user_order.async_session")
async def test_process_time_manual_valid(mock_session_cm, mock_mm_class):
    mock_mm = AsyncMock()
    mock_mm.delete_user_message = AsyncMock()
    mock_mm_class.return_value = mock_mm
    mock_session_cm.return_value.__aenter__.return_value = AsyncMock()
    
    message = AsyncMock()
    message.text = "18:30"
    message.chat.id = 123
    message.from_user.id = 123
    state = AsyncMock(spec=FSMContext)
    state.get_data.return_value = {}
    
    await process_time_manual(message, state, bot=AsyncMock())
    
    state.update_data.assert_any_call(time_text="18:30")
    state.set_state.assert_called_with(OrderFlow.choose_services)
