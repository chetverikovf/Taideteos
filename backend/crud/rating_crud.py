# backend/crud/rating_crud.py
import uuid
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..models.graph_model import GraphRating

async def set_graph_rating(db: AsyncSession, user_id: uuid.UUID, graph_id: uuid.UUID, value: int):
    """Устанавливает или обновляет голос пользователя за граф."""
    
    # Пытаемся получить существующий голос
    existing_rating = await db.get(GraphRating, (user_id, graph_id))
    
    if existing_rating:
        # Если пользователь голосует так же еще раз, его голос удаляется (отмена голоса)
        if existing_rating.value == value: # type: ignore
            await db.delete(existing_rating)
        else:
            # Если пользователь меняет голос, обновляем его
            existing_rating.value = value # type: ignore
            db.add(existing_rating)
    else:
        # Если голоса не было, создаем новый
        new_rating = GraphRating(user_id=user_id, graph_id=graph_id, value=value)
        db.add(new_rating)
        
    await db.commit()

async def get_graph_ratings(db: AsyncSession, graph_id: uuid.UUID):
    """Подсчитывает лайки и дизлайки для графа."""
    
    # Считаем лайки (value = 1)
    likes_query = select(func.count()).select_from(GraphRating).where(
        GraphRating.graph_id == graph_id,
        GraphRating.value == 1
    )
    likes_count = (await db.execute(likes_query)).scalar_one()

    # Считаем дизлайки (value = -1)
    dislikes_query = select(func.count()).select_from(GraphRating).where(
        GraphRating.graph_id == graph_id,
        GraphRating.value == -1
    )
    dislikes_count = (await db.execute(dislikes_query)).scalar_one()

    return {"likes": likes_count, "dislikes": dislikes_count}

async def get_user_vote_for_graph(db: AsyncSession, user_id: uuid.UUID, graph_id: uuid.UUID) -> int:
    """Получает голос конкретного пользователя за конкретный граф."""
    query = select(GraphRating.value).where(
        GraphRating.user_id == user_id,
        GraphRating.graph_id == graph_id
    )
    result = (await db.execute(query)).scalar_one_or_none()
    
    return result if result is not None else 0