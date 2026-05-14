from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bot.handlers.admin import admin_order_view_handler, admin_stats_handler
from bot.handlers.admin_orders import admin_change_status_handler
from bot.keyboards.admin import admin_order_list_kb, florist_lead_kb


RAW_CONSULTATION_STATUSES = (
    "needs_florist",
    "consultation_in_progress",
    "consultation_closed",
    "under_3k",
    "bright",
)


def _button_texts(markup):
    return [button.text for row in markup.inline_keyboard for button in row]


@pytest.fixture
def consultation_order():
    customer = MagicMock(username="client", telegram_user_id=777, phone="+79990000000")
    product = MagicMock(title="Нежность")
    return MagicMock(
        id=9,
        status="needs_florist",
        customer=customer,
        source_post_id=12,
        product=product,
        product_id=3,
        comment="Хочу похожий букет",
    )


def test_consultation_list_button_contains_user_and_source(consultation_order):
    markup = admin_order_list_kb([consultation_order], is_consultation=True)
    text = markup.inline_keyboard[0][0].text

    assert "№9" in text
    assert "@client" in text
    assert "пост: Нежность" in text
    for raw in RAW_CONSULTATION_STATUSES:
        assert raw not in text


def test_consultation_detail_has_consultation_buttons_only():
    markup = florist_lead_kb(order_id=9, user_id=777)
    texts = _button_texts(markup)

    assert texts == [
        "Взять в работу",
        "Написать клиенту",
        "✅ Закрыть",
        "↩️ Назад к консультациям",
    ]


def test_consultation_does_not_show_order_status_buttons():
    markup = florist_lead_kb(order_id=9, user_id=777)
    texts = " ".join(_button_texts(markup))

    assert "Принять" not in texts
    assert "Ожидает оплату" not in texts
    assert "Создать заказ" not in texts


@pytest.mark.asyncio
@patch("bot.handlers.admin.is_admin", return_value=True)
@patch("bot.handlers.admin.async_session")
async def test_no_raw_consultation_status_in_admin_ui(mock_session_cm, mock_is_admin, consultation_order):
    consultation_order.status = "consultation_in_progress"
    session = AsyncMock()
    session.scalar.return_value = consultation_order
    mock_session_cm.return_value.__aenter__.return_value = session
    callback = AsyncMock()
    callback.data = "admin_order_view:9"

    mock_mm = AsyncMock()
    with patch("bot.handlers.admin.MenuManager", return_value=mock_mm):
        await admin_order_view_handler(callback, bot=AsyncMock())

    text = mock_mm.show_menu.call_args[1]["text"]
    assert "флорист смотрит запрос" in text
    for raw in RAW_CONSULTATION_STATUSES:
        assert raw not in text


@pytest.mark.asyncio
@patch("bot.handlers.admin.get_basic_stats")
@patch("bot.handlers.admin.async_session")
@patch("bot.handlers.admin.is_admin")
async def test_consultation_stats_use_human_labels(mock_is_admin, mock_session_cm, mock_get_stats):
    mock_is_admin.return_value = True
    mock_get_stats.return_value = {
        "total_customers": 1,
        "total_orders": 1,
        "total_consultations": 2,
        "total_products": 1,
        "total_posts": 1,
        "total_branches": 1,
        "total_promos": 1,
        "sources": {"posts": 0, "catalog": 0, "survey": 0, "florist": 2},
        "order_status_counts": {"new": 1},
        "cons_status_counts": {"needs_florist": 1, "consultation_in_progress": 1},
    }
    callback = AsyncMock()
    callback.from_user.id = 456

    mock_mm = AsyncMock()
    with patch("bot.handlers.admin.MenuManager", return_value=mock_mm):
        await admin_stats_handler(callback, bot=AsyncMock())

    text = mock_mm.show_menu.call_args[1]["text"]
    assert "новая консультация" in text
    assert "флорист смотрит запрос" in text
    for raw in ("needs_florist", "consultation_in_progress"):
        assert raw not in text


@pytest.mark.asyncio
@patch("bot.handlers.admin_orders.is_admin", return_value=True)
@patch("bot.handlers.admin.admin_order_view_handler", new_callable=AsyncMock)
@patch("bot.handlers.admin_orders.async_session")
async def test_consultation_status_update_sends_human_message(mock_session_cm, mock_refresh, mock_is_admin):
    customer = MagicMock(telegram_user_id=777)
    order = MagicMock(id=9, status="needs_florist", customer=customer)
    session = AsyncMock()
    session.scalar.return_value = order
    mock_session_cm.return_value.__aenter__.return_value = session
    callback = AsyncMock()
    callback.data = "admin_order:9:consultation_in_progress"
    bot = AsyncMock()

    await admin_change_status_handler(callback, bot)

    sent_text = bot.send_message.call_args[0][1]
    assert "Флорист взял ваш запрос в работу" in sent_text
    assert "Статус вашего заказа" not in sent_text
    assert "consultation_in_progress" not in sent_text
