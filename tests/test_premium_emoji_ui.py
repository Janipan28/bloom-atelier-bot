from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from aiogram.types import MessageEntity


def _load_admin_emoji_module():
    import importlib.util

    module_path = Path(__file__).resolve().parents[1] / "bot" / "handlers" / "admin_emoji.py"
    spec = importlib.util.spec_from_file_location("admin_emoji_direct", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _iter_inline_buttons(markup):
    for row in markup.inline_keyboard:
        for button in row:
            yield button


def test_all_callback_data_under_64_bytes():
    from bot.keyboards import admin as admin_kb
    from bot.keyboards import user as user_kb

    markups = [
        user_kb.main_menu_kb(),
        user_kb.entry_choice_kb(),
        user_kb.delivery_type_kb(),
        user_kb.services_kb(["packaging"]),
        user_kb.time_slots_kb(),
        user_kb.time_ambiguous_kb("12:00–14:00"),
        user_kb.date_kb(),
        user_kb.skip_kb("skip:test", "back:test"),
        user_kb.branches_kb([type("Branch", (), {"id": 1, "address": "Тест"})()]),
        user_kb.branch_detail_kb(1, "https://maps.example", has_product=True),
        user_kb.catalog_card_kb(1, 0, 2),
        user_kb.product_detail_kb(1),
        user_kb.florist_menu_kb(),
        user_kb.survey_recommendations_kb(1, 0, 2),
        user_kb.survey_no_results_kb(),
        user_kb.florist_lead_after_kb(),
        user_kb.survey_occasion_kb(),
        user_kb.survey_budget_kb(),
        user_kb.confirm_order_kb(),
        user_kb.edit_order_kb({}),
        admin_kb.admin_menu_kb({"new_orders": 1, "florist_requests": 2}),
        admin_kb.order_status_kb(1),
        admin_kb.florist_lead_kb(1, 42),
        admin_kb.admin_products_menu_kb(),
        admin_kb.admin_product_detail_kb(1, True),
        admin_kb.admin_product_delete_confirm_kb(1),
        admin_kb.admin_posts_menu_kb(),
        admin_kb.post_buttons_kb(["order"]),
        admin_kb.post_preview_kb(),
        admin_kb.admin_promo_detail_kb(1, True),
        admin_kb.admin_branch_detail_kb(1, True, "https://maps.example"),
    ]

    for markup in markups:
        for button in _iter_inline_buttons(markup):
            if button.callback_data:
                assert len(button.callback_data.encode("utf-8")) <= 64, button.callback_data


@pytest.mark.asyncio
async def test_emoji_probe_extracts_custom_emoji_ids():
    admin_emoji = _load_admin_emoji_module()

    message = AsyncMock()
    message.from_user.id = 1
    message.text = "🌹🌷"
    message.caption = None
    message.entities = [
        MessageEntity(type="custom_emoji", offset=0, length=2, custom_emoji_id="111"),
        MessageEntity(type="custom_emoji", offset=2, length=2, custom_emoji_id="222"),
    ]
    message.caption_entities = None
    message.answer = AsyncMock()

    state = AsyncMock()
    state.clear = AsyncMock()
    bot = AsyncMock()
    sticker_a = type("Sticker", (), {"custom_emoji_id": "111", "emoji": "🌹", "set_name": "Flowers_emoji_gray"})()
    sticker_b = type("Sticker", (), {"custom_emoji_id": "222", "emoji": "💐", "set_name": "Flowers_emoji_gray"})()
    bot.get_custom_emoji_stickers = AsyncMock(return_value=[sticker_a, sticker_b])

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(admin_emoji, "is_admin", lambda user_id: True)
        await admin_emoji.collect_custom_emoji_ids(message, state, bot)

    state.clear.assert_awaited_once()
    sent_text = message.answer.await_args.args[0]
    assert "Flowers_emoji_gray" in sent_text
    assert "🌹" in sent_text
    assert "💐" in sent_text
    assert "111" in sent_text
    assert "222" in sent_text


@pytest.mark.asyncio
async def test_non_admin_cannot_use_emoji_probe():
    admin_emoji = _load_admin_emoji_module()

    message = AsyncMock()
    message.from_user.id = 999
    message.answer = AsyncMock()
    state = AsyncMock()

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(admin_emoji, "is_admin", lambda user_id: False)
        await admin_emoji.emoji_probe(message, state)

    state.set_state.assert_not_called()
    message.answer.assert_not_called()
