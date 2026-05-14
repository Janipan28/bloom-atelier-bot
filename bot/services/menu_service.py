import logging
import os
from typing import Optional, Union
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InputMediaPhoto, Message, FSInputFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from bot.models import UserMenuSession

logger = logging.getLogger(__name__)

class MenuManager:
    def __init__(self, bot: Bot, session: AsyncSession):
        self.bot = bot
        self.session = session

    async def get_session(self, user_id: int) -> UserMenuSession:
        stmt = select(UserMenuSession).where(UserMenuSession.user_id == user_id)
        db_session = await self.session.scalar(stmt)
        if not db_session:
            db_session = UserMenuSession(user_id=user_id)
            self.session.add(db_session)
            await self.session.commit()
            await self.session.refresh(db_session)
        return db_session

    def _get_photo(self, photo_path: Optional[str]) -> Optional[Union[FSInputFile, str]]:
        if not photo_path:
            return None
        if os.path.exists(photo_path) and os.path.getsize(photo_path) > 0:
            return FSInputFile(photo_path)
        # Telegram file_id or URL: aiogram accepts it as a string.
        if not photo_path.startswith("assets/"):
            return photo_path
        # logger.warning(f"Photo path {photo_path} does not exist or is empty. Falling back to text.")
        return None

    async def show_menu(
        self,
        chat_id: int,
        user_id: int,
        text: str,
        reply_markup: Optional[InlineKeyboardMarkup] = None,
        photo_path: Optional[str] = None,
        screen_name: Optional[str] = None
    ) -> Message:
        menu_session = await self.get_session(user_id)
        photo = self._get_photo(photo_path)
        
        # Попытка отредактировать текущее сообщение
        if menu_session.active_menu_message_id:
            try:
                # Если у нас сейчас фото и было фото, или сейчас текст и был текст - редактируем
                # Иначе - удаляем и отправляем заново, так как тип сообщения изменить нельзя
                
                # Примечание: Проверить тип старого сообщения программно сложно без хранения в БД,
                # поэтому пробуем редактировать, если падает - отправляем заново.
                
                if photo:
                    media = InputMediaPhoto(media=photo, caption=text, parse_mode="HTML")
                    msg = await self.bot.edit_message_media(
                        chat_id=chat_id,
                        message_id=menu_session.active_menu_message_id,
                        media=media,
                        reply_markup=reply_markup
                    )
                else:
                    msg = await self.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=menu_session.active_menu_message_id,
                        text=text,
                        reply_markup=reply_markup,
                        parse_mode="HTML"
                    )
                
                menu_session.current_screen = screen_name
                await self.session.commit()
                return msg
            except Exception as e:
                # logger.warning(f"Failed to edit menu for user {user_id}: {e}")
                try:
                    await self.bot.delete_message(chat_id, menu_session.active_menu_message_id)
                except:
                    pass

        # Отправка нового сообщения
        if photo:
            msg = await self.bot.send_photo(
                chat_id=chat_id,
                photo=photo,
                caption=text,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
        else:
            msg = await self.bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )

        menu_session.active_menu_message_id = msg.message_id
        menu_session.current_screen = screen_name
        await self.session.commit()
        return msg

    async def delete_user_message(self, message: Message):
        """Удаляет сообщение пользователя, чтобы не засорять чат."""
        try:
            await message.delete()
        except:
            pass

    async def cleanup_menu(self, user_id: int, chat_id: int):
        menu_session = await self.get_session(user_id)
        if menu_session.active_menu_message_id:
            try:
                await self.bot.delete_message(chat_id, menu_session.active_menu_message_id)
            except:
                pass
            menu_session.active_menu_message_id = None
            await self.session.commit()
