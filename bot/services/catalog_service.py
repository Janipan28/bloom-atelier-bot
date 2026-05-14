"""Сервис для работы с каталогом товаров."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from bot.models import Product


# Маппинг поводов на теги
OCCASION_TAGS = {
    "birthday": ["birthday", "день рождения"],
    "date": ["date", "свидание", "романтика"],
    "apology": ["apology", "извинение", "прости"],
    "just_because": ["just_because", "без повода", "просто так"],
}


async def get_products_by_occasion(session: AsyncSession, occasion: str) -> list[Product]:
    """Получить товары по поводу (фильтр по тегам)."""
    tags = OCCASION_TAGS.get(occasion, [])
    
    if not tags:
        # Если повод не найден, возвращаем все активные товары
        return await get_all_products(session)
    
    # Фильтруем по тегам (проверяем что хотя бы один тег есть в поле tags)
    result = await session.execute(
        select(Product)
        .where(Product.is_active == True)
        .order_by(Product.created_at.desc())
    )
    all_products = list(result.scalars().all())
    
    # Фильтруем в Python (проще чем сложный SQL)
    filtered = []
    for product in all_products:
        if product.tags:
            product_tags_lower = product.tags.lower()
            for tag in tags:
                if tag.lower() in product_tags_lower:
                    filtered.append(product)
                    break
    
    return filtered


async def get_all_products(session: AsyncSession) -> list[Product]:
    """Получить все активные товары."""
    result = await session.execute(
        select(Product)
        .where(Product.is_active == True)
        .order_by(Product.created_at.desc())
    )
    return list(result.scalars().all())
