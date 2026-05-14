from types import SimpleNamespace

from bot.services.notification_service import _staff_chat_id, render_staff_order_card


def test_staff_channel_id_prefers_dedicated_channel(monkeypatch):
    monkeypatch.setattr(
        "bot.services.notification_service.get_settings",
        lambda: SimpleNamespace(staff_channel_id=-1001234567890, admin_chat_id=2030011909),
    )
    assert _staff_chat_id() == -1001234567890


def test_render_staff_order_card_shows_human_labels_and_postcard():
    order = SimpleNamespace(
        id=24,
        status="accepted",
        payment_status="pending_manual",
        delivery_type="Доставка",
        date_text="завтра",
        time_text="18:30",
        delivery_address="ул. Ленина, 42",
        phone="+79990000000",
        card_text="С любовью",
        additional_services="Упаковка, Открытка",
        total_amount=5850,
        comment="Позвонить за 15 минут",
        source_post_id=5,
        promo_code=None,
        points_spent=0,
        customer=SimpleNamespace(username="client", full_name="Client User", phone="+79990000000", telegram_user_id=123456),
        product=SimpleNamespace(title="Нежность", price=4900),
    )

    text = render_staff_order_card(order)

    assert "Статус: заказ принят" in text
    assert "Открытка: С любовью" in text
    assert "Источник: пост" in text
    assert "Итого: от 5 850 ₽" in text
