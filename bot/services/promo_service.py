from datetime import datetime
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from bot.models import PromoCode


async def get_active_promo(session: AsyncSession, code: str) -> PromoCode | None:
    normalized = code.strip().upper()
    promo = await session.scalar(select(PromoCode).where(PromoCode.code == normalized))

    if not promo or not promo.is_active:
        return None

    if promo.valid_until and promo.valid_until < datetime.utcnow():
        return None

    if promo.usage_limit is not None and promo.used_count >= promo.usage_limit:
        return None

    return promo


def apply_promo_to_amount(amount: int, promo: PromoCode) -> int:
    result = amount
    if promo.discount_percent:
        result -= int(result * promo.discount_percent / 100)
    if promo.discount_amount:
        result -= promo.discount_amount
    return max(result, 0)


async def increment_promo_usage(session: AsyncSession, promo: PromoCode) -> bool:
    """Atomically increment promo usage. Returns False if limit already reached."""
    if promo.usage_limit is not None:
        stmt = (
            update(PromoCode)
            .where(
                PromoCode.id == promo.id,
                PromoCode.used_count < PromoCode.usage_limit,
            )
            .values(used_count=PromoCode.used_count + 1)
        )
        result = await session.execute(stmt)
        await session.commit()
        return result.rowcount > 0
    else:
        promo.used_count += 1
        await session.commit()
        return True


async def list_promos(session: AsyncSession) -> list[PromoCode]:
    result = await session.execute(select(PromoCode).order_by(PromoCode.id.desc()))
    return list(result.scalars().all())


async def create_promo(
    session: AsyncSession,
    code: str,
    discount_type: str,
    discount_value: int,
    usage_limit: int | None = None,
    valid_until: datetime | None = None,
) -> PromoCode:
    normalized = code.strip().upper()
    promo = PromoCode(
        code=normalized,
        discount_percent=discount_value if discount_type == "percent" else None,
        discount_amount=discount_value if discount_type == "fixed" else None,
        usage_limit=usage_limit,
        valid_until=valid_until,
        is_active=True,
    )
    session.add(promo)
    await session.commit()
    await session.refresh(promo)
    return promo


async def update_promo_discount(session: AsyncSession, promo: PromoCode, discount_type: str, discount_value: int) -> PromoCode:
    promo.discount_percent = discount_value if discount_type == "percent" else None
    promo.discount_amount = discount_value if discount_type == "fixed" else None
    await session.commit()
    await session.refresh(promo)
    return promo


async def update_promo_limit(session: AsyncSession, promo: PromoCode, usage_limit: int | None) -> PromoCode:
    promo.usage_limit = usage_limit
    await session.commit()
    await session.refresh(promo)
    return promo


async def update_promo_valid_until(session: AsyncSession, promo: PromoCode, valid_until: datetime | None) -> PromoCode:
    promo.valid_until = valid_until
    await session.commit()
    await session.refresh(promo)
    return promo


async def deactivate_or_delete_promo(session: AsyncSession, promo: PromoCode) -> None:
    if promo.used_count > 0:
        promo.is_active = False
    else:
        await session.delete(promo)
    await session.commit()
