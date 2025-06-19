# backend/crud/node_crud.py
import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from backend.models.graph_model import Node
from backend.schemas.graph_schema import NodeUpdate

async def get_node_by_id(db: AsyncSession, node_id: uuid.UUID) -> Optional[Node]:
    """Получает узел по ID, жадно загружая его граф для проверки прав."""
    result = await db.execute(
        select(Node).options(selectinload(Node.graph)).filter(Node.id == node_id)
    )
    return result.scalar_one_or_none()

async def update_node(db: AsyncSession, db_node: Node, node_in: NodeUpdate) -> Node:
    """Обновляет данные узла."""
    update_data = node_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_node, key, value)
    
    db.add(db_node)
    await db.commit()
    await db.refresh(db_node)
    return db_node

async def delete_node(db: AsyncSession, db_node: Node) -> None:
    """Удаляет узел."""
    await db.delete(db_node)
    await db.commit()
    return