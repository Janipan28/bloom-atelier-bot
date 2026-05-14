import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.fsm.context import FSMContext
from bot.handlers.start import cmd_start
from bot.handlers.user_order import (
    show_catalog_handler,
    start_order_flow,
    process_service_choice,
    process_services_continue,
    process_no_services,
    process_phone,
    process_address,
    show_confirmation,
    contact_florist_handler
)
from bot.states.order_states import OrderFlow
from bot.keyboards.user import entry_choice_kb, delivery_type_kb
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

# 1. /start создает active menu
@pytest.mark.asyncio
@patch("bot.handlers.start.MenuManager")
@patch("bot.handlers.start.async_session")
async def test_1_start_creates_active_menu(mock_session_cm, mock_mm_class, mock_message, mock_state):
    mock_mm = AsyncMock()
    mock_mm_class.return_value = mock_mm
    mock_session_cm.return_value.__aenter__.return_value = AsyncMock()
    
    mock_message.text = "/start"
    await cmd_start(mock_message, mock_state, bot=AsyncMock())
    
    mock_mm.show_menu.assert_called_once()
    assert mock_mm.show_menu.call_args[1]["screen_name"] == "main_menu"
    mock_mm.delete_user_message.assert_called_once_with(mock_message)

# 2. Повторный /start заменяет active menu
@pytest.mark.asyncio
@patch("bot.handlers.start.MenuManager")
@patch("bot.handlers.start.async_session")
async def test_2_restart_clears_state(mock_session_cm, mock_mm_class, mock_message, mock_state):
    mock_mm_class.return_value = AsyncMock()
    mock_session_cm.return_value.__aenter__.return_value = AsyncMock()
    mock_message.text = "/start"
    
    await cmd_start(mock_message, mock_state, bot=AsyncMock())
    mock_state.clear.assert_called_once()

# 3. Заказ из поста сохраняет source_code
@pytest.mark.asyncio
@patch("bot.handlers.start.MenuManager")
@patch("bot.handlers.start.async_session")
async def test_3_start_with_source_code(mock_session_cm, mock_mm_class, mock_message, mock_state):
    mock_mm = AsyncMock()
    mock_mm_class.return_value = mock_mm
    
    mock_session = AsyncMock()
    post_mock = MagicMock(id=10, product_id=None)
    mock_session.scalar.return_value = post_mock
    mock_session_cm.return_value.__aenter__.return_value = mock_session
    
    mock_message.text = "/start src_123"
    await cmd_start(mock_message, mock_state, bot=AsyncMock())
    
    mock_state.update_data.assert_called_with(source_code="src_123", source_post_id=10)
    mock_state.set_state.assert_called_with(OrderFlow.entry_choice)

# 4. Каталог показывает товары
@pytest.mark.asyncio
@patch("bot.handlers.user_order.MenuManager")
@patch("bot.handlers.user_order.async_session")
async def test_4_catalog_shows_products(mock_session_cm, mock_mm_class, mock_callback):
    mock_mm = AsyncMock()
    mock_mm_class.return_value = mock_mm
    mock_session = AsyncMock()
    mock_session.scalars.return_value = [MagicMock(id=1, title="B1", price=100, is_active=True, description="D1")]
    mock_session_cm.return_value.__aenter__.return_value = mock_session
    
    await show_catalog_handler(mock_callback, bot=AsyncMock())
    
    mock_mm.show_menu.assert_called_once()
    assert "Выберите букет" in mock_mm.show_menu.call_args[1]["text"]

# 5. Телефон не спрашивается первым шагом
@pytest.mark.asyncio
@patch("bot.handlers.user_order.MenuManager")
@patch("bot.handlers.user_order.async_session")
async def test_5_phone_not_first(mock_session_cm, mock_mm_class, mock_callback, mock_state):
    mock_mm = AsyncMock()
    mock_mm_class.return_value = mock_mm
    mock_session_cm.return_value.__aenter__.return_value = AsyncMock()
    
    mock_state.get_data.return_value = {"product_id": 1}
    await start_order_flow(mock_callback, mock_state, bot=AsyncMock())
    mock_state.set_state.assert_called_with(OrderFlow.choose_delivery_type)
    assert mock_mm.show_menu.call_args[1]["text"] == strings.CHOOSE_DELIVERY_TYPE

# 6. Открытка не спрашивается без выбора услуги
@pytest.mark.asyncio
@patch("bot.handlers.user_order.MenuManager")
@patch("bot.handlers.user_order.async_session")
async def test_6_no_postcard_skips_text(mock_session_cm, mock_mm_class, mock_callback, mock_state):
    mock_mm = AsyncMock()
    mock_mm_class.return_value = mock_mm
    mock_session_cm.return_value.__aenter__.return_value = AsyncMock()
    mock_state.get_data.return_value = {"selected_services": []}
    
    await process_no_services(mock_callback, mock_state, bot=AsyncMock())
    
    # After process_no_services, it calls next_step("card_text") which leads to comment
    mock_state.update_data.assert_any_call(selected_services=[])
    assert mock_mm.show_menu.call_args[1]["screen_name"] == "get_comment"

# 7. Открытка спрашивается при выборе услуги
@pytest.mark.asyncio
@patch("bot.handlers.user_order.MenuManager")
@patch("bot.handlers.user_order.async_session")
async def test_7_postcard_asks_text(mock_session_cm, mock_mm_class, mock_callback, mock_state):
    mock_mm = AsyncMock()
    mock_mm_class.return_value = mock_mm
    mock_session_cm.return_value.__aenter__.return_value = AsyncMock()
    
    mock_state.get_data.return_value = {"selected_services": ["postcard"]}
    
    await process_services_continue(mock_callback, mock_state, bot=AsyncMock())
    
    assert mock_mm.show_menu.call_args[1]["screen_name"] == "get_card_text"

# 10. "Позвать флориста" создает lead
@pytest.mark.asyncio
@patch("bot.handlers.user_order.notify_admin_about_florist_lead")
@patch("bot.handlers.user_order.create_florist_lead")
@patch("bot.handlers.user_order.MenuManager")
@patch("bot.handlers.user_order.async_session")
async def test_10_florist_lead_creation(mock_session_cm, mock_mm_class, mock_create, mock_notify, mock_callback, mock_state):
    """Флорист теперь двухшаговый: сначала экран ввода, потом создание лида."""
    from bot.handlers.user_order import process_florist_message
    mock_mm = AsyncMock()
    mock_mm_class.return_value = mock_mm
    mock_session_cm.return_value.__aenter__.return_value = AsyncMock()
    mock_create.return_value = MagicMock(id=1, customer=MagicMock())

    # Шаг 1: нажали кнопку — показывает экран ввода, лид НЕ создаётся
    await contact_florist_handler(mock_callback, mock_state, bot=AsyncMock())
    mock_create.assert_not_called()

    # Шаг 2: пользователь написал сообщение — лид создаётся
    mock_message = AsyncMock()
    mock_message.text = "Хочу букет"
    mock_message.from_user.id = 123
    mock_message.from_user.username = "u"
    mock_message.from_user.full_name = "U"
    mock_message.chat.id = 123
    mock_state.get_data.return_value = {}
    await process_florist_message(mock_message, mock_state, bot=AsyncMock())

    mock_create.assert_called_once()
    mock_notify.assert_called_once()

# 11. Финальное подтверждение содержит нужные поля
@pytest.mark.asyncio
@patch("bot.handlers.user_order.MenuManager")
@patch("bot.handlers.user_order.async_session")
async def test_11_final_confirmation(mock_session_cm, mock_mm_class, mock_message, mock_state):
    mock_mm = AsyncMock()
    mock_mm_class.return_value = mock_mm
    mock_session_cm.return_value.__aenter__.return_value = AsyncMock()
    
    mock_state.get_data.return_value = {
        "delivery_type": "Доставка",
        "date_text": "Завтра",
        "time_text": "12:00",
        "delivery_address": "ул. Пушкина",
        "phone": "12345",
        "selected_services": ["packaging", "postcard"],
        "card_text": "С любовью",
        "comment": "Быстрее",
        "promo_code": "TEST"
    }

    await show_confirmation(mock_message.chat.id, mock_message.from_user.id, mock_state, AsyncMock())

    text = mock_mm.show_menu.call_args[1]["text"]
    assert "Доставка" in text
    assert "Завтра" in text
    assert "12:00" in text
    assert "ул. Пушкина" in text
    assert "12345" in text
    assert "Упаковка" in text
    assert "Открытка" in text
    assert "Оплата: после подтверждения флористом." in text
# 14. /admin возвращает dashboard
from bot.handlers.admin import cmd_admin
@pytest.mark.asyncio
@patch("bot.handlers.admin.get_basic_stats")
@patch("bot.handlers.admin.async_session")
@patch("bot.handlers.admin.is_admin")
async def test_14_admin_dashboard(mock_is_admin, mock_session_cm, mock_get_stats, mock_message):
    mock_is_admin.return_value = True
    mock_session_cm.return_value.__aenter__.return_value = AsyncMock()
    mock_get_stats.return_value = {
        "new_orders": 1,
        "florist_requests": 2,
        "delivery_orders": 3,
        "pickup_orders": 4,
        "total_customers": 10,
        "total_orders": 20,
        "total_branches": 2,
        "total_promos": 5,
        "status_counts": {},
        "sources": {"posts": 0, "catalog": 0, "survey": 0}
    }

    await cmd_admin(mock_message, state=AsyncMock(), bot=AsyncMock())
    assert mock_message.answer.called
    text = mock_message.answer.call_args[0][0]
    assert "Панель управления" in text
    assert "Новых заказов: <b>1</b>" in text
