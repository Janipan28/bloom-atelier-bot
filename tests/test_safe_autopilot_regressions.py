from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bot.keyboards.admin import admin_order_list_kb
from bot.keyboards.user import confirm_order_kb
from bot.services.order_service import create_order_from_fsm


def test_admin_order_list_uses_human_status_label():
    order = MagicMock(id=1, status="new")

    markup = admin_order_list_kb([order])

    text = markup.inline_keyboard[0][0].text
    assert "заявка отправлена" in text
    assert " · new" not in text


def test_confirmation_has_no_payment_button():
    markup = confirm_order_kb()

    callbacks = [button.callback_data for row in markup.inline_keyboard for button in row]
    assert "order:pay" not in callbacks
    assert "order:pay_info" not in callbacks


@pytest.mark.asyncio
@patch("bot.services.order_service.get_or_create_customer")
async def test_create_order_from_fsm_persists_product_total_and_payment_status(mock_customer):
    customer = MagicMock(id=10)
    mock_customer.return_value = customer
    session = AsyncMock()
    session.add = MagicMock()

    await create_order_from_fsm(
        session=session,
        user_id=123,
        username="client",
        full_name="Client",
        data={
            "product_id": 5,
            "source_post_id": 7,
            "delivery_type": "Доставка",
            "phone": "+79990000000",
            "total_amount": 4450,
            "payment_status": "pending_manual",
            "payment_method": "manual_after_confirmation",
        },
    )

    order = session.add.call_args[0][0]
    assert order.product_id == 5
    assert order.total_amount == 4450
    assert order.payment_status == "pending_manual"
    assert order.payment_method == "manual_after_confirmation"
