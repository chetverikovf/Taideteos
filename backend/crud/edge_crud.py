# backend/crud/edge_crud.py
import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from ..models.graph_model import Edge

async def get_edge_by_id(db: AsyncSession, edge_id: uuid.UUID) -> Optional[Edge]:
    """Получает ребро по ID, жадно загружая его граф для проверки прав."""
    result = await db.execute(
        select(Edge).options(selectinload(Edge.graph)).filter(Edge.id == edge_id)
    )
    return result.scalar_one_or_none()

async def delete_edge(db: AsyncSession, db_edge: Edge) -> None:
    """Удаляет ребро."""
    await db.delete(db_edge)
    await db.commit()
    return