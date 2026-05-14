from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bot.handlers.user_order import catalog_florist_handler, catalog_order_handler, show_catalog_page


def _callback():
    callback = AsyncMock()
    callback.message.chat.id = 123
    callback.from_user.id = 123
    return callback


def _product(product_id, title, price, photo):
    return MagicMock(
        id=product_id,
        title=title,
        price=price,
        description=f"Описание {title}",
        photo_file_id=photo,
        is_active=True,
    )


@pytest.mark.asyncio
@patch("bot.handlers.user_order.MenuManager")
@patch("bot.handlers.user_order.async_session")
async def test_catalog_page_shows_buyer_list(mock_session_cm, mock_mm_class):
    p1 = _product(1, "Нежность", 3500, "photo-1")
    p2 = _product(2, "Весна", 4500, "photo-2")
    session = AsyncMock()
    session.scalars.return_value = [p1, p2]
    mock_session_cm.return_value.__aenter__.return_value = session
    mock_mm = AsyncMock()
    mock_mm_class.return_value = mock_mm

    await show_catalog_page(_callback(), bot=AsyncMock(), page=0)

    text = mock_mm.show_menu.call_args[1]["text"]
    markup = mock_mm.show_menu.call_args[1]["reply_markup"]
    button_texts = [button.text for row in markup.inline_keyboard for button in row]
    callbacks = [button.callback_data for row in markup.inline_keyboard for button in row if button.callback_data]

    assert "Выберите букет" in text
    assert any("Нежность" in item for item in button_texts)
    assert any("Весна" in item for item in button_texts)
    assert "product:1" in callbacks
    assert "product:2" in callbacks


@pytest.mark.asyncio
@patch("bot.handlers.user_order.MenuManager")
@patch("bot.handlers.user_order.async_session")
async def test_catalog_list_uses_generic_catalog_photo(mock_session_cm, mock_mm_class):
    session = AsyncMock()
    session.scalars.return_value = [_product(1, "Нежность", 3500, "photo-1")]
    mock_session_cm.return_value.__aenter__.return_value = session
    mock_mm = AsyncMock()
    mock_mm_class.return_value = mock_mm

    await show_catalog_page(_callback(), bot=AsyncMock(), page=0)

    assert mock_mm.show_menu.call_args[1]["photo_path"] == "assets/bot_ui/order_menu.jpg"


@pytest.mark.asyncio
@patch("bot.handlers.user_order.view_delivery_type", new_callable=AsyncMock)
@patch("bot.handlers.user_order.async_session")
async def test_order_from_product_card_uses_current_product(mock_session_cm, mock_view_delivery):
    product = _product(2, "Весна", 4500, "photo-2")
    session = AsyncMock()
    session.get.return_value = product
    mock_session_cm.return_value.__aenter__.return_value = session
    callback = _callback()
    callback.data = "catalog:order:2"
    state = AsyncMock()

    await catalog_order_handler(callback, state, bot=AsyncMock())

    state.update_data.assert_awaited_once_with(product_id=2, product_title="Весна", product_price=4500)


@pytest.mark.asyncio
@patch("bot.handlers.user_order.contact_florist_handler", new_callable=AsyncMock)
async def test_consultation_from_product_card_uses_current_product(mock_contact):
    callback = _callback()
    callback.data = "catalog:florist:2"
    state = AsyncMock()

    await catalog_florist_handler(callback, state, bot=AsyncMock())

    state.update_data.assert_awaited_once_with(product_id=2)
    mock_contact.assert_awaited_once()
