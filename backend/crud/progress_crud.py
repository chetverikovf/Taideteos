# backend/crud/progress_crud.py
import uuid
import logging
from typing import List, Set
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from backend.models.graph_model import UserProgress, Node

# Настраиваем логгер для этого модуля
logger = logging.getLogger(__name__)

async def mark_node_as_learned(db: AsyncSession, user_id: uuid.UUID, node_id: uuid.UUID):
    """Отмечает узел как изученный для пользователя."""
    existing_progress = await db.get(UserProgress, (user_id, node_id))
    if existing_progress:
        return existing_progress

    new_progress = UserProgress(user_id=user_id, node_id=node_id)
    db.add(new_progress)
    await db.commit()
    return new_progress

async def unmark_node_as_learned(db: AsyncSession, user_id: uuid.UUID, node_id: uuid.UUID):
    """Убирает отметку об изучении узла."""
    progress_to_delete = await db.get(UserProgress, (user_id, node_id))
    if progress_to_delete:
        await db.delete(progress_to_delete)
        await db.commit()
    return

async def get_learned_nodes_for_graph(db: AsyncSession, user_id: uuid.UUID, graph_id: uuid.UUID) -> List[uuid.UUID]:
    """Возвращает список ID изученных узлов для конкретного графа и пользователя."""
    logger.info("--- [CRUD] Запущена get_learned_nodes_for_graph ---")
    logger.info(f"[CRUD] user_id: {user_id}")
    logger.info(f"[CRUD] graph_id: {graph_id}")

    # 1. Получаем ВСЕ узлы, которые изучил данный пользователь
    learned_nodes_result = await db.execute(
        select(UserProgress.node_id).where(UserProgress.user_id == user_id)
    )
    all_learned_node_ids: Set[uuid.UUID] = set(learned_nodes_result.scalars().all())
    logger.info(f"[CRUD] Все изученные узлы для юзера {user_id}: {all_learned_node_ids}")

    if not all_learned_node_ids:
        logger.info("[CRUD] Пользователь ничего не изучал. Возвращаем пустой список.")
        return []

    # 2. Получаем ВСЕ узлы, которые принадлежат данному графу
    graph_nodes_result = await db.execute(
        select(Node.id).where(Node.graph_id == graph_id)
    )
    graph_node_ids: Set[uuid.UUID] = set(graph_nodes_result.scalars().all())
    logger.info(f"[CRUD] Все узлы в графе {graph_id}: {graph_node_ids}")

    # 3. Находим пересечение
    learned_nodes_in_graph = all_learned_node_ids.intersection(graph_node_ids)
    logger.info(f"[CRUD] Пересечение (результат): {learned_nodes_in_graph}")
    
    return list(learned_nodes_in_graph)