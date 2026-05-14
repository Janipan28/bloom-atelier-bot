import secrets
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from bot.models import ChannelPost


def generate_source_code() -> str:
    return f"src_{secrets.token_urlsafe(8)}"


async def create_or_get_channel_post(session: AsyncSession, chat_id: int, message_id: int, caption: str | None = None) -> ChannelPost:
    existing = await session.scalar(
        select(ChannelPost).where(ChannelPost.chat_id == chat_id, ChannelPost.message_id == message_id)
    )
    if existing:
        return existing

    for _ in range(5):
        post = ChannelPost(
            chat_id=chat_id,
            message_id=message_id,
            caption=caption,
            source_code=generate_source_code(),
        )
        session.add(post)
        try:
            await session.commit()
            await session.refresh(post)
            return post
        except Exception:
            await session.rollback()

    raise RuntimeError("Cannot generate unique source_code")


async def get_channel_post_by_source_code(session: AsyncSession, source_code: str) -> ChannelPost | None:
    return await session.scalar(select(ChannelPost).where(ChannelPost.source_code == source_code))
