import pytest
from aiogram.types import Message, Document, PhotoSize
from aiogram.fsm.context import FSMContext
from bot.handlers.admin_posts import process_post_photo
from bot.handlers.admin_products import process_prod_photo
from bot.states.admin_states import AdminPostFlow, AdminProductFlow
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_quick_post_accepts_photo():
    message = AsyncMock(spec=Message)
    message.photo = [MagicMock(spec=PhotoSize, file_id="photo123")]
    message.document = None
    message.caption = None
    message.answer = AsyncMock()
    state = AsyncMock(spec=FSMContext)
    
    await process_post_photo(message, state)
    
    state.update_data.assert_any_call(photo_id="photo123")
    state.set_state.assert_called_with(AdminPostFlow.get_title)

@pytest.mark.asyncio
async def test_quick_post_accepts_image_document():
    message = AsyncMock(spec=Message)
    message.photo = None
    message.document = MagicMock(spec=Document, file_id="doc123", mime_type="image/jpeg")
    message.caption = "Test Caption"
    message.answer = AsyncMock()
    state = AsyncMock(spec=FSMContext)
    
    await process_post_photo(message, state)
    
    state.update_data.assert_any_call(photo_id="doc123")
    state.update_data.assert_any_call(title_candidate="Test Caption")
    state.set_state.assert_called_with(AdminPostFlow.get_title)

@pytest.mark.asyncio
async def test_quick_post_rejects_non_image_document():
    message = AsyncMock(spec=Message)
    message.photo = None
    message.document = MagicMock(spec=Document, file_id="doc123", mime_type="application/pdf")
    message.answer = AsyncMock()
    state = AsyncMock(spec=FSMContext)
    
    await process_post_photo(message, state)
    
    message.answer.assert_called()
    assert "Сейчас нужно отправить фото букета" in message.answer.call_args[0][0]
    state.update_data.assert_not_called()

@pytest.mark.asyncio
async def test_bouquet_create_accepts_photo():
    message = AsyncMock(spec=Message)
    message.photo = [MagicMock(spec=PhotoSize, file_id="photo456")]
    message.document = None
    message.answer = AsyncMock()
    state = AsyncMock(spec=FSMContext)
    
    await process_prod_photo(message, state)
    
    state.update_data.assert_called_with(photo_id="photo456")
    state.set_state.assert_called_with(AdminProductFlow.get_title)

@pytest.mark.asyncio
async def test_global_non_text_does_not_override_admin_photo_states():
    from bot.handlers.user_order import handle_non_text
    message = AsyncMock(spec=Message)
    state = AsyncMock(spec=FSMContext)
    state.get_state.return_value = "AdminPostFlow:get_photo"
    bot = MagicMock()
    
    await handle_non_text(message, state, bot)
    
    # Should return early without answering or deleting
    message.answer.assert_not_called()
