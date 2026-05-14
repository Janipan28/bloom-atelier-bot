from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from bot.models import Branch


async def list_active_branches(session: AsyncSession) -> list[Branch]:
    result = await session.execute(
        select(Branch).where(Branch.is_active.is_(True)).order_by(Branch.id)
    )
    return list(result.scalars().all())


async def create_branch(session: AsyncSession, title: str, address: str, yandex_maps_url: str | None = None, work_hours: str | None = None, phone: str | None = None) -> Branch:
    branch = Branch(
        title=title,
        address=address,
        yandex_maps_url=yandex_maps_url,
        work_hours=work_hours,
        phone=phone,
    )
    session.add(branch)
    await session.commit()
    await session.refresh(branch)
    return branch
