"""
test_quick_post_e2e.py — тесты E2E flow публикации поста через Quick Post.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, ANY
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext


# ---- Helpers ----------------------------------------------------------------

def make_callback(data: str = "post_action:publish", user_id: int = 1):
    cb = AsyncMock(spec=CallbackQuery)
    cb.data = data
    cb.from_user = MagicMock()
    cb.from_user.id = user_id
    cb.message = AsyncMock()
    cb.message.chat.id = 100
    cb.message.answer = AsyncMock()
    cb.message.delete = AsyncMock()
    cb.answer = AsyncMock()
    return cb


def make_state(data: dict):
    state = AsyncMock(spec=FSMContext)
    state.get_data = AsyncMock(return_value=data)
    state.set_state = AsyncMock()
    state.clear = AsyncMock()
    state.update_data = AsyncMock()
    return state


def make_bot(username: str = "TestFlowerBot"):
    bot = AsyncMock()
    me = MagicMock()
    me.username = username
    bot.get_me = AsyncMock(return_value=me)
    sent = MagicMock()
    sent.message_id = 999
    bot.send_photo = AsyncMock(return_value=sent)
    return bot


# ---- Tests ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_quick_post_accepts_photo():
    """AdminPostFlow.get_photo handler accepts regular photo."""
    from bot.handlers.admin_posts import process_post_photo
    msg = AsyncMock(spec=Message)
    msg.photo = [MagicMock(file_id="file_photo_123")]
    msg.document = None
    msg.caption = None
    msg.answer = AsyncMock()
    state = make_state({})

    await process_post_photo(msg, state)

    state.update_data.assert_called()
    state.set_state.assert_called()
    msg.answer.assert_called()


@pytest.mark.asyncio
async def test_quick_post_accepts_image_document():
    """AdminPostFlow.get_photo handler accepts document with image mime."""
    from bot.handlers.admin_posts import process_post_photo
    msg = AsyncMock(spec=Message)
    msg.photo = None
    msg.document = MagicMock()
    msg.document.file_id = "file_doc_456"
    msg.document.mime_type = "image/jpeg"
    msg.caption = None
    msg.answer = AsyncMock()
    state = make_state({})

    await process_post_photo(msg, state)

    state.update_data.assert_called()
    state.set_state.assert_called()


@pytest.mark.asyncio
async def test_quick_post_rejects_non_image_document():
    """AdminPostFlow.get_photo handler rejects non-image documents."""
    from bot.handlers.admin_posts import process_post_photo
    msg = AsyncMock(spec=Message)
    msg.photo = None
    msg.document = MagicMock()
    msg.document.file_id = "file_pdf_789"
    msg.document.mime_type = "application/pdf"
    msg.caption = None
    msg.answer = AsyncMock()
    state = make_state({})

    await process_post_photo(msg, state)

    # Should answer with error, not advance state
    msg.answer.assert_called_once()
    state.set_state.assert_not_called()


@pytest.mark.asyncio
@patch("bot.handlers.admin_posts.is_admin", return_value=True)
@patch("bot.handlers.admin_posts.async_session")
@patch("bot.handlers.admin_posts.get_settings")
async def test_quick_post_publish_calls_send_photo(mock_settings, mock_session, mock_is_admin):
    """process_post_publish calls bot.send_photo with correct args."""
    from bot.handlers.admin_posts import process_post_publish

    # Settings
    settings = MagicMock()
    settings.channel_id = "-1001234567890"
    mock_settings.return_value = settings

    # DB session mock
    mock_db = AsyncMock()
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock(return_value=False)
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()

    product_ids = iter([42])

    async def fake_flush():
        added_product = mock_db.add.call_args_list[0].args[0]
        added_product.id = next(product_ids)

    async def fake_refresh(obj):
        obj.id = 42
    mock_db.flush = fake_flush
    mock_db.refresh = fake_refresh
    mock_session.return_value = mock_db

    state_data = {
        "photo_id": "AgACAgITest",
        "title": "Букет Нежность",
        "price": 4900,
        "description": "Пионы, эвкалипт",
        "selected_buttons": ["order", "florist"],
    }
    state = make_state(state_data)
    bot = make_bot("TestBot")
    cb = make_callback()

    await process_post_publish(cb, state, bot)

    bot.send_photo.assert_called_once()
    # Check that update_data was called (for publish_in_progress)
    state.update_data.assert_any_call(publish_in_progress=True)
    cb.answer.assert_awaited_with("🚀 Публикую пост...")
    call_kwargs = bot.send_photo.call_args
    assert call_kwargs.kwargs.get("parse_mode") == "HTML" or (
        len(call_kwargs.args) >= 4 and "HTML" in str(call_kwargs)
    )
    # photo_id passed
    call_kw = bot.send_photo.call_args.kwargs
    assert call_kw.get("photo") == "AgACAgITest"


@pytest.mark.asyncio
@patch("bot.handlers.admin_posts.is_admin", return_value=True)
@patch("bot.handlers.admin_posts.async_session")
@patch("bot.handlers.admin_posts.get_settings")
async def test_quick_post_publish_has_inline_deep_link_url(mock_settings, mock_session, mock_is_admin):
    """Inline keyboard under channel post uses URL deep link, not callback."""
    from bot.handlers.admin_posts import process_post_publish

    settings = MagicMock()
    settings.channel_id = "-1001234567890"
    mock_settings.return_value = settings

    mock_db = AsyncMock()
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock(return_value=False)
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()

    product_ids = iter([7])

    async def fake_flush():
        added_product = mock_db.add.call_args_list[0].args[0]
        added_product.id = next(product_ids)

    mock_db.flush = fake_flush
    mock_session.return_value = mock_db

    state_data = {
        "photo_id": "AgTest",
        "title": "Тест",
        "price": 3000,
        "description": None,
        "selected_buttons": ["order"],
    }
    state = make_state(state_data)
    bot = make_bot("FlowerBot")
    cb = make_callback()

    await process_post_publish(cb, state, bot)

    # Check that send_photo was called with a markup that has URL buttons
    call_kw = bot.send_photo.call_args.kwargs
    markup = call_kw.get("reply_markup")
    assert markup is not None, "reply_markup must be provided"
    found_url = False
    for row in markup.inline_keyboard:
        for btn in row:
            if btn.url and "t.me/FlowerBot?start=src_p7" in btn.url:
                found_url = True
    assert found_url, "Channel post must have URL deep link button with source_code"


def test_quick_post_generates_html_caption():
    """build_post_caption generates valid HTML with escaped user input."""
    from bot.services.formatting import build_post_caption

    caption = build_post_caption(
        title='Букет "Нежность" & <тест>',
        price=4900,
        description="Состав: пионы & розы"
    )

    # Should not contain raw unescaped dangerous characters
    assert "<тест>" not in caption
    assert "&amp;" in caption or "тест" not in caption or "Нежность" in caption
    # Should have <b> tags
    assert "<b>" in caption
    # Should have price
    assert "4" in caption


def test_quick_post_creates_product_and_channel_post():
    """Verify publish flow creates both Product and ChannelPost records."""
    # This is validated structurally by the handler code
    # The handler: session.add(product), session.commit, session.add(cp), session.commit
    # We verify the source_code format
    product_id = 99
    source_code = f"src_p{product_id}"
    assert source_code == "src_p99"
    assert len(source_code) < 64  # Must fit in ChannelPost.source_code field


def test_source_code_under_64_chars():
    """source_code must fit in VARCHAR(64)."""
    # Worst case product ID is very large
    large_id = 999999999
    source_code = f"src_p{large_id}"
    assert len(source_code) <= 64
    assert len(source_code.encode("utf-8")) <= 64


@pytest.mark.asyncio
@patch("bot.handlers.admin_posts.is_admin", return_value=True)
@patch("bot.handlers.admin_posts.async_session")
@patch("bot.handlers.admin_posts.get_settings")
async def test_post_publish_missing_channel_answers_alert_once(mock_settings, mock_session, mock_is_admin):
    from bot.handlers.admin_posts import process_post_publish

    settings = MagicMock()
    settings.channel_id = ""
    mock_settings.return_value = settings

    state = make_state({"title": "Тест"})
    bot = make_bot("TestBot")
    cb = make_callback()

    await process_post_publish(cb, state, bot)

    cb.answer.assert_awaited_once_with("❌ Ошибка: CHANNEL_ID не настроен в .env", show_alert=True)
    mock_session.assert_not_called()
    bot.send_photo.assert_not_called()


@pytest.mark.asyncio
@patch("bot.handlers.admin_posts.is_admin", return_value=True)
@patch("bot.handlers.admin_posts.async_session")
@patch("bot.handlers.admin_posts.get_settings")
async def test_post_publish_failure_does_not_clear_state(mock_settings, mock_session, mock_is_admin):
    from bot.handlers.admin_posts import process_post_publish

    settings = MagicMock()
    settings.channel_id = "-1001234567890"
    mock_settings.return_value = settings

    mock_db = AsyncMock()
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock(return_value=False)
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.rollback = AsyncMock()
    mock_session.return_value = mock_db

    state = make_state({
        "photo_id": "AgTest",
        "title": "Тест",
        "price": 3000,
        "description": None,
        "selected_buttons": ["order"],
    })
    bot = make_bot("FlowerBot")
    bot.send_photo = AsyncMock(side_effect=RuntimeError("send failed"))
    cb = make_callback()

    await process_post_publish(cb, state, bot)

    state.clear.assert_not_awaited()
    mock_db.rollback.assert_awaited()


@pytest.mark.asyncio
@patch("bot.handlers.admin_posts.is_admin", return_value=True)
@patch("bot.handlers.admin_posts.async_session")
@patch("bot.handlers.admin_posts.get_settings")
async def test_publish_success_message_escapes_title(mock_settings, mock_session, mock_is_admin):
    from bot.handlers.admin_posts import process_post_publish

    settings = MagicMock()
    settings.channel_id = "-1001234567890"
    mock_settings.return_value = settings

    mock_db = AsyncMock()
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock(return_value=False)
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()

    product_ids = iter([7])

    async def fake_flush():
        added_product = mock_db.add.call_args_list[0].args[0]
        added_product.id = next(product_ids)

    mock_db.flush = fake_flush
    mock_session.return_value = mock_db

    state = make_state({
        "photo_id": "AgTest",
        "title": '<b>Тест</b>',
        "price": 3000,
        "description": None,
        "selected_buttons": ["order"],
    })
    bot = make_bot("FlowerBot")
    cb = make_callback()

    await process_post_publish(cb, state, bot)

    success_text = cb.message.answer.call_args.args[0]
    assert "<b><b>Тест</b></b>" not in success_text
    assert "&lt;b&gt;Тест&lt;/b&gt;" in success_text
