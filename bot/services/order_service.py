from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from bot.models import Customer, Order, OrderStatus


async def get_or_create_customer(session: AsyncSession, telegram_user_id: int, username: str | None, full_name: str | None, phone: str | None = None) -> Customer:
    customer = await session.scalar(select(Customer).where(Customer.telegram_user_id == telegram_user_id))
    if customer:
        customer.username = username
        customer.full_name = full_name
        if phone:
            customer.phone = phone
        # SQLAlchemy tracked change, will commit later
    else:
        customer = Customer(
            telegram_user_id=telegram_user_id,
            username=username,
            full_name=full_name,
            phone=phone,
        )
        session.add(customer)
    
    await session.commit()
    await session.refresh(customer)
    return customer


async def create_order_from_fsm(session: AsyncSession, user_id: int, username: str | None, full_name: str | None, data: dict) -> Order:
    customer = await get_or_create_customer(
        session=session,
        telegram_user_id=user_id,
        username=username,
        full_name=full_name,
        phone=data.get("phone"),
    )

    order = Order(
        customer_id=customer.id,
        source_post_id=data.get("source_post_id"),
        branch_id=data.get("branch_id"),
        product_id=data.get("product_id"),
        delivery_type=data.get("delivery_type"),
        delivery_address=data.get("delivery_address"),
        date_text=data.get("date_text"),
        time_text=data.get("time_text"),
        phone=data.get("phone"),
        card_text=data.get("card_text"),
        additional_services=data.get("additional_services"),
        comment=data.get("comment"),
        promo_code=data.get("promo_code"),
        points_spent=data.get("points_spent", 0),
        total_amount=data.get("total_amount"),
        payment_status=data.get("payment_status"),
        payment_method=data.get("payment_method"),
        status=OrderStatus.NEW.value,
    )
    session.add(order)
    await session.commit()
    await session.refresh(order)
    return order


async def create_florist_lead(
    session: AsyncSession,
    user_id: int,
    username: str | None,
    full_name: str | None,
    source_post_id: int | None = None,
    product_id: int | None = None,
) -> Order:
    customer = await get_or_create_customer(
        session=session,
        telegram_user_id=user_id,
        username=username,
        full_name=full_name,
    )

    lead = Order(
        customer_id=customer.id,
        source_post_id=source_post_id,
        product_id=product_id,
        status=OrderStatus.NEEDS_FLORIST.value,
    )
    session.add(lead)
    await session.commit()
    await session.refresh(lead)
    return lead


async def create_survey_lead(session: AsyncSession, user_id: int, username: str | None, full_name: str | None, survey_data: dict) -> Order:
    customer = await get_or_create_customer(
        session=session,
        telegram_user_id=user_id,
        username=username,
        full_name=full_name,
    )

    comment = (
        f"✨ Заявка на подбор букета\n"
        f"🎈 Повод: {survey_data.get('occasion')}\n"
        f"💸 Бюджет: {survey_data.get('budget')}\n"
        f"🌿 Стиль: {survey_data.get('style')}"
    )

    lead = Order(
        customer_id=customer.id,
        status=OrderStatus.NEEDS_FLORIST.value,
        comment=comment
    )
    session.add(lead)
    await session.commit()
    await session.refresh(lead)
    return lead


async def get_user_orders(session: AsyncSession, user_id: int, limit: int = 5) -> list[Order]:
    customer = await session.scalar(select(Customer).where(Customer.telegram_user_id == user_id))
    if not customer:
        return []
    
    stmt = (
        select(Order)
        .where(
            Order.customer_id == customer.id,
            Order.status.notin_([
                OrderStatus.NEEDS_FLORIST.value,
                "consultation_in_progress",
                "consultation_closed",
            ]),
        )
        .options(selectinload(Order.product))
        .order_by(Order.created_at.desc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())
