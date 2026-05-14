from bot.keyboards.admin import (
    admin_promo_detail_kb,
    admin_promo_list_kb,
    promo_delete_confirm_kb,
    promo_discount_type_kb,
    staff_consultation_kb,
    staff_order_kb,
)


def _texts(markup):
    return [button.text for row in markup.inline_keyboard for button in row]


def test_staff_order_keyboard_changes_by_status():
    new_texts = _texts(staff_order_kb(24, "new", reply_url="https://t.me/test"))
    paid_texts = _texts(staff_order_kb(24, "paid", reply_url="https://t.me/test"))

    assert "Принять" in new_texts
    assert "Отказать" in new_texts
    assert "В сборке" in paid_texts
    assert "Написать клиенту" in paid_texts


def test_staff_consultation_keyboard_has_operational_actions():
    texts = _texts(staff_consultation_kb(8, reply_url="https://t.me/test"))
    assert texts == ["Взять в работу", "Написать клиенту", "Выполнено"]


def test_admin_promo_list_has_create_cta():
    texts = _texts(admin_promo_list_kb([]))
    assert any("Создать промокод" in text for text in texts)


def test_admin_promo_detail_has_edit_and_delete_actions():
    texts = _texts(admin_promo_detail_kb(1, True))
    assert any("Изменить скидку" in text for text in texts)
    assert any("Изменить лимит" in text for text in texts)
    assert any("Изменить срок" in text for text in texts)
    assert any("Удалить" in text for text in texts)


def test_promo_support_keyboards_exist():
    assert any("Процент" in text for text in _texts(promo_discount_type_kb()))
    assert any("Подтвердить удаление" in text for text in _texts(promo_delete_confirm_kb(1)))
