import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from bot.models import Order, Customer, OrderStatus
from bot.config import get_settings

logger = logging.getLogger(__name__)

async def credit_loyalty_points(session: AsyncSession, order_id: int):
    """Credits points to customer after order is delivered."""
    order = await session.get(Order, order_id)
    if not order:
        logger.error(f"Order {order_id} not found for loyalty credit")
        return

    if order.status != OrderStatus.DELIVERED.value:
        logger.warning(f"Order {order_id} is not delivered, status: {order.status}")
        return

    if order.is_loyalty_credited:
        logger.info(f"Loyalty already credited for order {order_id}")
        return

    customer = await session.scalar(select(Customer).where(Customer.id == order.customer_id))
    if not customer:
        logger.error(f"Customer {order.customer_id} not found for order {order_id}")
        return

    settings = get_settings()
    cashback_percent = settings.loyalty_cashback_percent
    
    # Amount used for points calculation (usually excluding points used and potentially delivery?)
    # For now, let's take % of the total_amount paid.
    if order.total_amount:
        points_to_add = int(order.total_amount * (cashback_percent / 100))
        customer.loyalty_points += points_to_add
        order.is_loyalty_credited = True
        
        await session.commit()
        logger.info(f"Credited {points_to_add} points to user {customer.telegram_user_id} for order {order_id}")
        return points_to_add
    
    return 0
