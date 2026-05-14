import asyncio
from bot.db import async_session
from bot.models import Branch, Product, PromoCode
from sqlalchemy import select

async def main():
    async with async_session() as session:
        branches = (await session.execute(select(Branch))).scalars().all()
        products = (await session.execute(select(Product))).scalars().all()
        promos = (await session.execute(select(PromoCode))).scalars().all()
        print(f"Branches: {len(branches)}")
        print(f"Products: {len(products)}")
        print(f"Promos: {len(promos)}")

if __name__ == "__main__":
    asyncio.run(main())
