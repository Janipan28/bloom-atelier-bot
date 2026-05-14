from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from bot.models import Order, Branch, PromoCode, Customer, ScheduledPost, OrderStatus, Product, ChannelPost

async def get_basic_stats(session: AsyncSession) -> dict:
    # count orders by status (excluding consultations)
    status_counts_res = await session.execute(
        select(Order.status, func.count(Order.id)).where(
            Order.status.notin_([OrderStatus.NEEDS_FLORIST.value, "consultation_in_progress", "consultation_closed"])
        ).group_by(Order.status)
    )
    order_status_dict = {status: count for status, count in status_counts_res.all()}

    # count consultations by status
    cons_status_counts_res = await session.execute(
        select(Order.status, func.count(Order.id)).where(
            Order.status.in_([OrderStatus.NEEDS_FLORIST.value, "consultation_in_progress", "consultation_closed"])
        ).group_by(Order.status)
    )
    cons_status_dict = {status: count for status, count in cons_status_counts_res.all()}

    # total counts
    total_customers = await session.scalar(select(func.count(Customer.id)))
    total_orders = await session.scalar(select(func.count(Order.id)).where(
        Order.status.notin_([OrderStatus.NEEDS_FLORIST.value, "consultation_in_progress", "consultation_closed"])
    ))
    total_consultations = await session.scalar(select(func.count(Order.id)).where(
        Order.status.in_([OrderStatus.NEEDS_FLORIST.value, "consultation_in_progress", "consultation_closed"])
    ))
    total_branches = await session.scalar(select(func.count(Branch.id)))
    total_promos = await session.scalar(select(func.count(PromoCode.id)))
    total_products = await session.scalar(select(func.count(Product.id)))
    total_posts = await session.scalar(select(func.count(ChannelPost.id)))

    # count by sources
    from_posts = await session.scalar(select(func.count(Order.id)).where(Order.source_post_id != None))
    # Catalog: has product, but NO source post
    from_catalog = await session.scalar(select(func.count(Order.id)).where(Order.product_id != None, Order.source_post_id == None))
    # Survey: comment contains emoji or tag
    from_survey = await session.scalar(select(func.count(Order.id)).where(Order.comment.like("%✨%"), Order.product_id == None))
    # Florist: needs_florist status, but NO product, NO source post, NO survey tag
    from_florist_btn = await session.scalar(select(func.count(Order.id)).where(
        Order.status == OrderStatus.NEEDS_FLORIST.value,
        Order.product_id == None,
        Order.source_post_id == None,
        or_(Order.comment == None, Order.comment.not_like("%✨%"))
    ))

    return {
        "new_orders": order_status_dict.get(OrderStatus.NEW.value, 0),
        "florist_requests": cons_status_dict.get(OrderStatus.NEEDS_FLORIST.value, 0) + cons_status_dict.get("consultation_in_progress", 0),
        "total_customers": total_customers or 0,
        "total_orders": total_orders or 0,
        "total_consultations": total_consultations or 0,
        "total_branches": total_branches or 0,
        "total_promos": total_promos or 0,
        "total_products": total_products or 0,
        "total_posts": total_posts or 0,
        "order_status_counts": order_status_dict,
        "cons_status_counts": cons_status_dict,
        "sources": {
            "posts": from_posts or 0,
            "catalog": from_catalog or 0,
            "survey": from_survey or 0,
            "florist": from_florist_btn or 0
        }
    }

async def get_recent_orders(session: AsyncSession, limit: int = 10) -> list[Order]:
    # Exclude consultations from orders list
    result = await session.execute(
        select(Order).where(
            Order.status.notin_([OrderStatus.NEEDS_FLORIST.value, "consultation_in_progress", "consultation_closed"])
        ).options(selectinload(Order.customer)).order_by(Order.id.desc()).limit(limit)
    )
    return list(result.scalars().all())

async def get_recent_consultations(session: AsyncSession, limit: int = 10) -> list[Order]:
    result = await session.execute(
        select(Order).where(
            Order.status.in_([OrderStatus.NEEDS_FLORIST.value, "consultation_in_progress", "consultation_closed"])
        ).options(selectinload(Order.customer), selectinload(Order.product)).order_by(Order.id.desc()).limit(limit)
    )
    return list(result.scalars().all())

async def get_all_promos(session: AsyncSession) -> list[PromoCode]:
    result = await session.execute(
        select(PromoCode).order_by(PromoCode.id.desc())
    )
    return list(result.scalars().all())

async def get_all_branches(session: AsyncSession) -> list[Branch]:
    result = await session.execute(
        select(Branch).order_by(Branch.id.desc())
    )
    return list(result.scalars().all())

async def get_all_products(session: AsyncSession, only_active: bool = False) -> list[Product]:
    stmt = select(Product)
    if only_active:
        stmt = stmt.where(Product.is_active == True)
    result = await session.execute(stmt.order_by(Product.id.desc()))
    return list(result.scalars().all())

async def get_all_posts(session: AsyncSession, limit: int = 20) -> list[ChannelPost]:
    result = await session.execute(
        select(ChannelPost).order_by(ChannelPost.id.desc()).limit(limit)
    )
    return list(result.scalars().all())

async def get_scheduled_posts(session: AsyncSession) -> list[ScheduledPost]:
    result = await session.execute(
        select(ScheduledPost).order_by(ScheduledPost.publish_at.asc())
    )
    return list(result.scalars().all())
