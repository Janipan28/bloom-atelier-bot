"""
test_ui_tokens.py — тесты emoji словаря и HTML-форматирования.
"""
import pytest


def test_ui_tokens_all_required_keys_present():
    """E dict must contain all required emoji token keys."""
    from bot.ui_tokens import E

    required = [
        "popular", "bouquet", "choose", "shop", "cart", "orders", "help",
        "back", "admin", "post", "promo", "branch", "stats", "florist",
        "success", "danger", "pay", "delivery", "pickup", "date", "time",
        "package", "postcard", "next", "prev", "publish",
    ]
    for key in required:
        assert key in E, f"Missing emoji token: '{key}'"


def test_ui_tokens_are_non_empty_strings():
    """All emoji tokens must be non-empty strings."""
    from bot.ui_tokens import E
    for key, val in E.items():
        assert isinstance(val, str), f"Token '{key}' is not a string"
        assert len(val) > 0, f"Token '{key}' is empty"


def test_ui_tokens_has_custom_emoji_layer():
    from bot.ui_tokens import CE, E, STYLE

    assert isinstance(E, dict)
    assert isinstance(CE, dict)
    assert isinstance(STYLE, dict)
    assert STYLE["primary"] == "primary"
    assert STYLE["success"] == "success"
    assert STYLE["danger"] == "danger"


def test_html_escape_user_input():
    """h() must escape <, >, & characters."""
    from bot.services.formatting import h
    assert h("<script>") == "&lt;script&gt;"
    assert h("A & B") == "A &amp; B"
    assert h('"quoted"') == '"quoted"'  # quote=False, so quotes not escaped


def test_html_b_wraps_escaped():
    """b() must wrap escaped text in <b> tags."""
    from bot.services.formatting import b
    result = b("Hello <World>")
    assert result == "<b>Hello &lt;World&gt;</b>"


def test_html_i_wraps_escaped():
    """i() must wrap escaped text in <i> tags."""
    from bot.services.formatting import i
    result = i("test & more")
    assert result == "<i>test &amp; more</i>"


def test_html_code_wraps_escaped():
    """code() must wrap escaped text in <code> tags."""
    from bot.services.formatting import code
    result = code("src_p<42>")
    assert result == "<code>src_p&lt;42&gt;</code>"


def test_html_quote_wraps_escaped():
    """quote() must wrap escaped text in <blockquote> tags."""
    from bot.services.formatting import quote
    result = quote("Пионы & розы")
    assert "<blockquote>" in result
    assert "&amp;" in result


def test_tg_emoji_returns_unicode_when_missing():
    from bot.services.formatting import tg_emoji
    from bot.ui_tokens import CE

    CE.pop("bouquet", None)
    assert tg_emoji("bouquet") == "💐"


def test_tg_emoji_returns_html_tag_when_custom_id_present(monkeypatch):
    from bot.services.formatting import tg_emoji

    monkeypatch.setitem(__import__("bot.ui_tokens", fromlist=["CE"]).CE, "bouquet", "1234567890")
    assert tg_emoji("bouquet") == '<tg-emoji emoji-id="1234567890">💐</tg-emoji>'


def test_build_post_caption_is_safe_html():
    """build_post_caption must escape dangerous user-supplied data."""
    from bot.services.formatting import build_post_caption

    caption = build_post_caption(
        title='<script>alert("xss")</script>',
        price=1000,
        description='Состав: <b>опасно</b> & "кавычки"'
    )
    # Raw HTML tags from user input must be escaped
    assert "<script>" not in caption
    assert "alert" in caption  # text survives but escaped
    # Price should appear
    assert "1" in caption
    # Should have valid HTML structure
    assert "<b>" in caption


def test_build_post_caption_with_none_description():
    """build_post_caption handles None description gracefully."""
    from bot.services.formatting import build_post_caption
    caption = build_post_caption(title="Букет", price=None, description=None)
    assert "Букет" in caption
    assert "по запросу" in caption


def test_build_post_caption_with_price():
    """build_post_caption shows formatted price."""
    from bot.services.formatting import build_post_caption
    caption = build_post_caption(title="Нежность", price=4900, description=None)
    assert "4" in caption
    assert "900" in caption


def test_build_post_caption_under_1024_chars():
    """build_post_caption trims very long captions to Telegram-safe size."""
    from bot.services.formatting import build_post_caption, MAX_TELEGRAM_PHOTO_CAPTION

    caption = build_post_caption(
        title="Нежность",
        price=4900,
        description="очень длинное описание " * 200,
    )

    assert len(caption) <= MAX_TELEGRAM_PHOTO_CAPTION
    assert "…" in caption


def test_ibtn_uses_custom_emoji_id_when_present(monkeypatch):
    from bot.ui.buttons import ibtn
    from bot.ui_tokens import CE

    monkeypatch.setitem(CE, "popular", "999")
    button = ibtn("popular", "Популярные букеты", callback_data="user:catalog")
    assert button.icon_custom_emoji_id == "999"
    assert button.text == "Популярные букеты"


def test_ibtn_falls_back_to_unicode_when_missing():
    from bot.ui.buttons import ibtn
    from bot.ui_tokens import CE

    CE.pop("popular", None)
    button = ibtn("popular", "Популярные букеты", callback_data="user:catalog")
    assert button.icon_custom_emoji_id is None
    assert button.text.startswith("🌸 ")


def test_rbtn_uses_custom_emoji_id_when_present(monkeypatch):
    from bot.ui.buttons import rbtn
    from bot.ui_tokens import CE

    monkeypatch.setitem(CE, "phone", "123")
    button = rbtn("phone", "Отправить контакт", request_contact=True)
    assert button.icon_custom_emoji_id == "123"
    assert button.text == "Отправить контакт"
