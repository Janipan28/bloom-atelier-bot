"""Скрипт для добавления тегов к существующим товарам."""
import asyncio
import sys
from pathlib import Path

# Добавляем корень проекта в PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from bot.db import async_session
from bot.models import Product
from sqlalchemy import select


async def add_tags_to_products():
    """Добавить теги к существующим товарам."""
    async with async_session() as session:
        result = await session.execute(select(Product))
        products = list(result.scalars().all())
        
        print(f"Найдено товаров: {len(products)}")
        
        for product in products:
            # Если теги уже есть, пропускаем
            if product.tags:
                print(f"✓ {product.title} — теги уже есть: {product.tags}")
                continue
            
            # Добавляем теги по умолчанию (можно настроить вручную)
            # Для демо добавим все поводы
            product.tags = "birthday,date,apology,just_because"
            print(f"+ {product.title} — добавлены теги: {product.tags}")
        
        await session.commit()
        print("\n✅ Теги добавлены!")


if __name__ == "__main__":
    asyncio.run(add_tags_to_products())
