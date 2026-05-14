from unittest.mock import AsyncMock


def test_main_menu_copy_is_not_gpt_style():
    from bot import strings

    assert "говорят о чувствах без слов" not in strings.MAIN_MENU
    assert "Выберите повод или посмотрите все букеты" in strings.MAIN_MENU
    assert "Bloom Atelier" in strings.MAIN_MENU


def test_main_menu_buttons_are_buyer_actions():
    from bot.keyboards.user import main_menu_kb

    texts = [button.text for row in main_menu_kb().inline_keyboard for button in row]
    # Новое главное меню с поводами и профилем
    assert any("День рождения" in text for text in texts)
    assert any("Свидание" in text for text in texts)
    assert any("Все букеты" in text for text in texts)
    assert any("Наши магазины" in text for text in texts)
    assert any("Мой профиль" in text for text in texts)
    assert any("Написать флористу" in text for text in texts)


def test_confirmation_mentions_manual_payment():
    from bot import strings

    assert "по оплате" in strings.ORDER_SUCCESS


def test_client_buttons_do_not_use_banned_emoji():
    from bot.keyboards.user import main_menu_kb

    banned = {"🔥", "🚀", "📸", "📊", "🎟"}
    texts = [button.text for row in main_menu_kb().inline_keyboard for button in row]
    for text in texts:
        assert not any(text.startswith(f"{emoji} ") for emoji in banned)


def test_florist_screen_explains_use_cases():
    from bot import strings
    # Новый текст флориста — просит написать сообщение
    assert "флорист" in strings.FLORIST_MENU.lower()
    assert "вопрос" in strings.FLORIST_MENU.lower() or "сообщение" in strings.FLORIST_MENU.lower()


def test_product_card_has_clear_cta():
    from bot.keyboards.user import product_detail_kb

    texts = [button.text for row in product_detail_kb(5).inline_keyboard for button in row]
    assert any("Заказать букет" in text for text in texts)
    assert any("Задать вопрос" in text for text in texts)
    assert any("Назад к букетам" in text for text in texts)


async def _fake_state(data):
    state = AsyncMock()
    state.get_data = AsyncMock(return_value=data)
    state.set_state = AsyncMock()
    return state


def test_survey_does_not_claim_filtering_if_no_filters():
    from bot import strings

    assert "идеальный вариант" not in strings.SURVEY_START
    assert "флорист предложит подходящие варианты" in strings.SURVEY_START
    assert "Заявка на подбор отправлена" in strings.SURVEY_DONE


def test_my_orders_empty_has_clear_cta():
    from bot import strings
    from bot.keyboards.user import main_menu_kb

    assert "Можно выбрать готовый букет" in strings.MY_ORDERS_EMPTY
    callbacks = [button.callback_data for row in main_menu_kb().inline_keyboard for button in row]
    assert "user:catalog" in callbacks


def test_florist_followup_has_order_cta():
    from bot.keyboards.user import florist_lead_after_kb

    callbacks = [button.callback_data for row in florist_lead_after_kb().inline_keyboard for button in row if button.callback_data]
    assert "order:start_flow" in callbacks


def test_confirmation_has_manual_payment_text():
    from bot import strings

    assert "по оплате" in strings.ORDER_SUCCESS


def test_final_success_explains_next_step():
    from bot import strings

    assert "подтвердит доставку" in strings.ORDER_SUCCESS
    assert "5–10 минут" in strings.ORDER_SUCCESS


def _admin_button_texts(markup):
    return [button.text for row in markup.inline_keyboard for button in row]


def _admin_button_callbacks(markup):
    return [button.callback_data for row in markup.inline_keyboard for button in row if button.callback_data]


def test_admin_order_status_buttons_are_contextual():
    from bot.keyboards.admin import order_status_kb

    new_markup = order_status_kb(order_id=24, status="new", user_id=777)
    new_texts = _admin_button_texts(new_markup)
    new_callbacks = _admin_button_callbacks(new_markup)

    assert new_texts == ["Принять", "Уточнить у клиента", "Отменить", "↩️ Назад к заказам"]
    assert "admin_order:24:delivered" not in new_callbacks
    assert "admin_order:24:in_delivery" not in new_callbacks

    accepted_callbacks = _admin_button_callbacks(order_status_kb(order_id=24, status="accepted", user_id=777))
    assert accepted_callbacks == [
        "admin_order:24:in_progress",
        "admin_order:24:waiting_payment",
        "admin_order:24:cancelled",
        "admin:orders",
    ]

    progress_markup = order_status_kb(order_id=24, status="in_progress", user_id=777)
    progress_texts = _admin_button_texts(progress_markup)
    progress_callbacks = _admin_button_callbacks(progress_markup)

    assert progress_texts == ["Готов к выдаче", "Передан в доставку", "Написать клиенту", "↩️ Назад к заказам"]
    assert "admin_order:24:delivered" not in progress_callbacks
