import asyncio
from sqlalchemy import select
from bot.db import async_session
from bot.models import ChannelPost

async def check_posts():
    async with async_session() as session:
        posts = await session.scalars(select(ChannelPost))
        for p in posts:
            print(f"ID: {p.id}, Chat ID: {p.chat_id}, Message ID: {p.message_id}")

if __name__ == "__main__":
    asyncio.run(check_posts())
