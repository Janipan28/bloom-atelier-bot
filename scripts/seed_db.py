import asyncio
from datetime import datetime
from sqlalchemy import select
from bot.db import async_session, init_db
from bot.models import Branch, Product, PromoCode


async def seed_data():
    await init_db()
    
    async with async_session() as session:
        # 1. Точки самовывоза
        stmt = select(Branch)
        existing_branches = await session.execute(stmt)
        if not existing_branches.scalars().all():
            branches = [
                Branch(
                    title="Bloom Atelier · Центр",
                    address="ул. Цветочная, 10",
                    work_hours="10:00–21:00",
                    yandex_maps_url="https://maps.yandex.ru/?text=Цветочная+10",
                ),
                Branch(
                    title="Bloom Atelier · Север",
                    address="ул. Лесная, 5",
                    work_hours="09:00–20:00",
                    yandex_maps_url="https://maps.yandex.ru/?text=Лесная+5",
                )
            ]
            session.add_all(branches)
            print("Added demo branches.")

        # 2. Товары
        stmt = select(Product)
        existing_products = await session.execute(stmt)
        if not existing_products.scalars().all():
            products = [
                Product(
                    title="Букет «Нежность»",
                    price=4900,
                    description="Состав: пионы, эвкалипт, лента.",
                ),
                Product(
                    title="Композиция «Весна»",
                    price=3500,
                    description="В корзинке. Тюльпаны и зелень.",
                )
            ]
            session.add_all(products)
            print("Added demo products.")

        # 3. Промокоды
        stmt = select(PromoCode)
        existing_promos = await session.execute(stmt)
        if not existing_promos.scalars().all():
            promos = [
                PromoCode(
                    code="SPRING2026",
                    title="Весенняя скидка",
                    discount_percent=10,
                    usage_limit=100,
                ),
                PromoCode(
                    code="FIRST500",
                    title="Скидка на первый заказ",
                    discount_amount=500,
                    usage_limit=50,
                )
            ]
            session.add_all(promos)
            print("Added demo promo codes.")

        await session.commit()
    print("Seeding complete.")


if __name__ == "__main__":
    asyncio.run(seed_data())
