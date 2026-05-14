from unittest.mock import AsyncMock, patch

import pytest

from bot.handlers.admin_orders import admin_change_status_handler
from bot.handlers.admin_posts import process_post_publish
from bot.handlers.admin_products import admin_product_delete_confirm_handler


@pytest.mark.asyncio
@patch("bot.handlers.admin_orders.async_session")
@patch("bot.handlers.admin_orders.is_admin", return_value=False)
async def test_non_admin_cannot_change_order_status(mock_is_admin, mock_session_cm):
    callback = AsyncMock()
    callback.from_user.id = 999
    callback.data = "admin_order:1:paid"
    bot = AsyncMock()

    await admin_change_status_handler(callback, bot)

    callback.answer.assert_awaited_once_with("Нет доступа", show_alert=True)
    mock_session_cm.assert_not_called()
    bot.send_message.assert_not_called()


@pytest.mark.asyncio
@patch("bot.handlers.admin_products.async_session")
@patch("bot.handlers.admin_products.is_admin", return_value=False)
async def test_non_admin_cannot_confirm_product_delete(mock_is_admin, mock_session_cm):
    callback = AsyncMock()
    callback.from_user.id = 999
    callback.data = "admin_prod_delete_confirm:1"
    bot = AsyncMock()

    await admin_product_delete_confirm_handler(callback, bot)

    callback.answer.assert_awaited_once_with("Нет доступа", show_alert=True)
    mock_session_cm.assert_not_called()


@pytest.mark.asyncio
@patch("bot.handlers.admin_posts.get_settings")
@patch("bot.handlers.admin_posts.is_admin", return_value=False)
async def test_non_admin_cannot_publish_post(mock_is_admin, mock_settings):
    callback = AsyncMock()
    callback.from_user.id = 999
    callback.data = "post_action:publish"
    callback.message = AsyncMock()
    callback.message.chat.id = 100
    callback.answer = AsyncMock()
    state = AsyncMock()
    state.get_data = AsyncMock(return_value={})

    await process_post_publish(callback, state, bot=AsyncMock())

    callback.answer.assert_awaited_once_with("Нет доступа", show_alert=True)


@pytest.mark.asyncio
@patch("bot.handlers.admin_products.admin_product_list_handler", new_callable=AsyncMock)
@patch("bot.handlers.admin_products.async_session")
@patch("bot.handlers.admin_products.is_admin", return_value=True)
async def test_product_with_links_is_soft_hidden_not_deleted(mock_is_admin, mock_session_cm, mock_list_handler):
    product = AsyncMock()
    product.id = 5
    product.is_active = True

    session = AsyncMock()
    session.get.return_value = product
    session.scalar = AsyncMock(side_effect=[1, 0])
    mock_session_cm.return_value.__aenter__.return_value = session

    callback = AsyncMock()
    callback.from_user.id = 1
    callback.data = "admin_prod_delete_confirm:5"

    await admin_product_delete_confirm_handler(callback, bot=AsyncMock())

    assert product.is_active is False
    session.delete.assert_not_called()
    session.commit.assert_awaited()
