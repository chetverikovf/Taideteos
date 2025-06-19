# backend/crud/user_crud.py
import uuid
from typing import Optional, List
from sqlalchemy import func, distinct  # noqa: F401
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

# 2. Импортируем модель User для использования в аннотации
from backend.models.user_model import User 
from backend.schemas.user_schema import UserCreate
from backend.core.security import get_password_hash
from backend.models.graph_model import Graph, Node, UserProgress, GraphRating

# 3. Обновляем сигнатуру функции, явно указывая тип возвращаемого значения
async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    """
    Получает пользователя из базы данных по его имени.
    Возвращает объект User или None, если пользователь не найден.
    """
    result = await db.execute(select(User).filter(User.username == username))
    return result.scalar_one_or_none()

async def create_user(db: AsyncSession, user: UserCreate) -> User:
    """
    Создает нового пользователя в базе данных.
    """
    hashed_password = get_password_hash(user.password)
    db_user = User(username=user.username, password_hash=hashed_password)
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

async def get_owned_graphs(db: AsyncSession, user_id: uuid.UUID) -> List[Graph]:
    """Получает все графы, созданные пользователем."""
    result = await db.execute(
        select(Graph)
        .options(selectinload(Graph.owner))
        .filter(Graph.owner_id == user_id)
        .order_by(Graph.created_at.desc())
    )
    return result.scalars().all() # type: ignore

async def get_learning_graphs(db: AsyncSession, user_id: uuid.UUID) -> List[Graph]:
    """Получает графы, в которых пользователь изучил хотя бы один узел."""
    # Находим уникальные graph_id из прогресса пользователя
    subquery = (
        select(distinct(Node.graph_id))
        .join(UserProgress, Node.id == UserProgress.node_id)
        .filter(UserProgress.user_id == user_id)
    ).scalar_subquery()

    # Загружаем эти графы
    result = await db.execute(
        select(Graph)
        .options(selectinload(Graph.owner))
        .filter(Graph.id.in_(subquery))
        .order_by(Graph.created_at.desc())
    )
    return result.scalars().all() # type: ignore

async def get_user_total_ratings(db: AsyncSession, user_id: uuid.UUID):
    """Подсчитывает суммарные лайки и дизлайки для всех графов пользователя."""
    
    # Подзапрос для нахождения всех графов пользователя
    owned_graphs_subquery = select(Graph.id).where(Graph.owner_id == user_id).scalar_subquery()
    
    # Считаем лайки
    likes_query = select(func.count()).select_from(GraphRating).where(
        GraphRating.graph_id.in_(owned_graphs_subquery),
        GraphRating.value == 1
    )
    total_likes = (await db.execute(likes_query)).scalar_one()

    # Считаем дизлайки
    dislikes_query = select(func.count()).select_from(GraphRating).where(
        GraphRating.graph_id.in_(owned_graphs_subquery),
        GraphRating.value == -1
    )
    total_dislikes = (await db.execute(dislikes_query)).scalar_one()

    return {"total_likes": total_likes, "total_dislikes": total_dislikes}