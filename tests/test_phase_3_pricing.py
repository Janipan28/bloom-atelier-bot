import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.fsm.context import FSMContext
from bot.handlers.user_order import calculate_total, show_confirmation
from bot import strings

@pytest.mark.asyncio
async def test_calculate_total_basic():
    state = AsyncMock(spec=FSMContext)
    state.get_data.return_value = {"product_price": 3500, "delivery_type": "Самовывоз", "selected_services": []}

    total = await calculate_total(state)
    assert total == "3 500 ₽"

@pytest.mark.asyncio
async def test_calculate_total_with_delivery():
    state = AsyncMock(spec=FSMContext)
    state.get_data.return_value = {"product_price": 3500, "delivery_type": "Доставка", "selected_services": []}

    total = await calculate_total(state)
    assert total == "от 4 000 ₽"

@pytest.mark.asyncio
async def test_calculate_total_with_services():
    state = AsyncMock(spec=FSMContext)
    state.get_data.return_value = {
        "product_price": 3500, 
        "delivery_type": "Доставка", 
        "selected_services": ["packaging", "postcard"]
    }
    
    total = await calculate_total(state)
    # 3500 + 500 (delivery) + 300 (pkg) + 150 (card) = 4450
    assert total == "от 4 450 ₽"

@pytest.mark.asyncio
@patch("bot.handlers.user_order.MenuManager")
@patch("bot.handlers.user_order.async_session")
async def test_confirmation_shows_breakdown(mock_session_cm, mock_mm_class):
    mock_mm = AsyncMock()
    mock_mm_class.return_value = mock_mm
    mock_session_cm.return_value.__aenter__.return_value = AsyncMock()
    
    state = AsyncMock(spec=FSMContext)
    state.get_data.return_value = {
        "product_title": "Букет Тест",
        "product_price": 3500,
        "delivery_type": "Доставка",
        "selected_services": ["packaging", "postcard"],
        "date_text": "15.05",
        "time_text": "18:00",
        "delivery_address": "ул. Тестовая",
        "phone": "79990000000"
    }
    
    await show_confirmation(chat_id=123, user_id=456, state=state, bot=AsyncMock())
    
    text = mock_mm.show_menu.call_args[1]["text"]
    assert "Букет Тест" in text
    assert "Доставка — <b>от 500 ₽</b>" in text
    assert "Упаковка — <b>300 ₽</b>" in text
    assert "Открытка — <b>150 ₽</b>" in text
    assert "<b>Итого: от 4 450 ₽</b>" in text
