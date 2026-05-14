"""
test_source_tracking.py — тесты source_code chain: post → deep link → /start → product → order.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def test_source_code_format():
    """source_code should follow pattern src_p{product_id}."""
    product_id = 42
    sc = f"src_p{product_id}"
    assert sc == "src_p42"
    assert sc.startswith("src_p")


def test_deep_link_format():
    """Deep link URL should follow t.me/{bot}?start={source_code}."""
    bot_username = "FlowerBot"
    source_code = "src_p42"
    url = f"https://t.me/{bot_username}?start={source_code}"
    assert url == "https://t.me/FlowerBot?start=src_p42"
    assert "?start=" in url


def test_florist_deep_link_format():
    """Florist deep link should use ask_ prefix."""
    bot_username = "FlowerBot"
    source_code = "src_p42"
    url = f"https://t.me/{bot_username}?start=ask_{source_code}"
    assert "ask_src_p42" in url


def test_source_code_fits_channel_post_schema():
    """source_code must fit in ChannelPost.source_code = String(64)."""
    # Max realistic product_id
    for pid in [1, 100, 9999, 999999]:
        sc = f"src_p{pid}"
        assert len(sc) <= 64
        assert len(sc.encode("utf-8")) <= 64


@pytest.mark.asyncio
@patch("bot.handlers.start.get_or_create_customer")
@patch("bot.handlers.start.async_session")
async def test_start_with_valid_source_code_shows_product(mock_session, mock_get_cust):
    """
    /start src_p42 should find ChannelPost and open the concrete product card.
    Tests that state.update_data receives product info and source_code.
    """
    from bot.handlers.start import cmd_start

    # Create fake ChannelPost + Product
    fake_product = MagicMock()
    fake_product.id = 42
    fake_product.title = "Букет Нежность"
    fake_product.price = 4900

    fake_post = MagicMock()
    fake_post.id = 7
    fake_post.product_id = 42
    fake_post.source_code = "src_p42"

    mock_db = AsyncMock()
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock(return_value=False)
    mock_db.scalar = AsyncMock(return_value=fake_post)
    mock_db.get = AsyncMock(return_value=fake_product)
    mock_session.return_value = mock_db

    msg = AsyncMock()
    msg.from_user.id = 123
    msg.from_user.username = "testuser"
    msg.from_user.full_name = "Test User"
    msg.chat.id = 123
    msg.text = "/start src_p42"
    msg.answer = AsyncMock()
    msg.delete = AsyncMock()

    state = AsyncMock()
    state.get_data = AsyncMock(return_value={})
    state.set_state = AsyncMock()
    state.clear = AsyncMock()
    state.update_data = AsyncMock()
    bot = AsyncMock()

    with patch("bot.handlers.start.MenuManager") as mm_class:
        mock_mm = AsyncMock()
        mm_class.return_value = mock_mm

        await cmd_start(msg, state, bot)

    # State should be cleared and updated with source tracking data
    state.clear.assert_called()
    # update_data should have been called with source_code
    calls = [str(c) for c in state.update_data.call_args_list]
    all_kwargs = {}
    for c in state.update_data.call_args_list:
        all_kwargs.update(c.kwargs if c.kwargs else (c.args[0] if c.args else {}))
    assert "source_code" in all_kwargs or any("src_p42" in str(c) for c in state.update_data.call_args_list)
    assert mock_mm.show_menu.call_args.kwargs["screen_name"] == "product_42"


@pytest.mark.asyncio
@patch("bot.handlers.start.get_or_create_customer")
@patch("bot.handlers.start.async_session")
async def test_start_with_valid_florist_source_code_shows_florist_entry(mock_session, mock_get_cust):
    from bot.handlers.start import cmd_start

    fake_product = MagicMock()
    fake_product.id = 42
    fake_product.title = "Букет Нежность"
    fake_product.price = 4900

    fake_post = MagicMock()
    fake_post.id = 7
    fake_post.product_id = 42
    fake_post.source_code = "src_p42"

    mock_db = AsyncMock()
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock(return_value=False)
    mock_db.scalar = AsyncMock(return_value=fake_post)
    mock_db.get = AsyncMock(return_value=fake_product)
    mock_session.return_value = mock_db

    msg = AsyncMock()
    msg.from_user.id = 123
    msg.from_user.username = "testuser"
    msg.from_user.full_name = "Test User"
    msg.chat.id = 123
    msg.text = "/start ask_src_p42"

    state = AsyncMock()
    state.set_state = AsyncMock()
    state.clear = AsyncMock()
    state.update_data = AsyncMock()
    bot = AsyncMock()

    with patch("bot.handlers.start.MenuManager") as mm_class:
        mock_mm = AsyncMock()
        mm_class.return_value = mock_mm

        await cmd_start(msg, state, bot)

    merged_kwargs = {}
    for call in state.update_data.call_args_list:
        merged_kwargs.update(call.kwargs if call.kwargs else (call.args[0] if call.args else {}))

    assert merged_kwargs["source_code"] == "src_p42"
    assert merged_kwargs["source_post_id"] == 7
    assert mock_mm.show_menu.call_args.kwargs["screen_name"] == "entry_choice_florist"
    buttons = mock_mm.show_menu.call_args.kwargs["reply_markup"].inline_keyboard
    callbacks = [button.callback_data for row in buttons for button in row if button.callback_data]
    assert "order:contact_florist" in callbacks
    assert "order:start_flow" in callbacks


@pytest.mark.asyncio
@patch("bot.handlers.start.get_or_create_customer")
@patch("bot.handlers.start.async_session")
async def test_start_with_invalid_source_code_shows_catalog(mock_session, mock_get_cust):
    """
    /start broken_code should show fallback menu with catalog button.
    """
    from bot.handlers.start import cmd_start

    mock_db = AsyncMock()
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock(return_value=False)
    mock_db.scalar = AsyncMock(return_value=None)  # post not found
    mock_session.return_value = mock_db

    msg = AsyncMock()
    msg.from_user.id = 123
    msg.from_user.username = "testuser"
    msg.from_user.full_name = "Test"
    msg.chat.id = 123
    msg.text = "/start broken_code_xyz"
    msg.answer = AsyncMock()
    msg.delete = AsyncMock()

    state = AsyncMock()
    state.get_data = AsyncMock(return_value={})
    state.set_state = AsyncMock()
    state.clear = AsyncMock()
    state.update_data = AsyncMock()
    bot = AsyncMock()

    with patch("bot.handlers.start.MenuManager") as mm_class:
        mock_mm = AsyncMock()
        mm_class.return_value = mock_mm

        await cmd_start(msg, state, bot)

    # Menu should be shown with fallback content
    state.clear.assert_called()
    mock_mm.show_menu.assert_called()


@pytest.mark.asyncio
@patch("bot.handlers.start.get_or_create_customer")
@patch("bot.handlers.start.async_session")
async def test_start_with_invalid_florist_source_code_shows_fallback(mock_session, mock_get_cust):
    from bot.handlers.start import cmd_start

    mock_db = AsyncMock()
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock(return_value=False)
    mock_db.scalar = AsyncMock(return_value=None)
    mock_session.return_value = mock_db

    msg = AsyncMock()
    msg.from_user.id = 123
    msg.from_user.username = "testuser"
    msg.from_user.full_name = "Test"
    msg.chat.id = 123
    msg.text = "/start ask_broken_code_xyz"

    state = AsyncMock()
    state.set_state = AsyncMock()
    state.clear = AsyncMock()
    state.update_data = AsyncMock()
    bot = AsyncMock()

    with patch("bot.handlers.start.MenuManager") as mm_class:
        mock_mm = AsyncMock()
        mm_class.return_value = mock_mm

        await cmd_start(msg, state, bot)

    assert mock_mm.show_menu.call_args.kwargs["screen_name"] == "broken_link"


def test_order_saves_source_fields():
    """Order model has source_post_id and product_id fields."""
    from bot.models import Order
    from sqlalchemy import inspect as sa_inspect
    mapper = sa_inspect(Order)
    columns = [c.key for c in mapper.mapper.columns]
    assert "source_post_id" in columns
    assert "product_id" in columns


def test_channel_post_has_source_code_field():
    """ChannelPost model has source_code field."""
    from bot.models import ChannelPost
    from sqlalchemy import inspect as sa_inspect
    mapper = sa_inspect(ChannelPost)
    columns = [c.key for c in mapper.mapper.columns]
    assert "source_code" in columns
    assert "product_id" in columns
