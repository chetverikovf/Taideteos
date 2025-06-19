# backend/crud/comment_crud.py
import uuid
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from ..models.graph_model import Comment
from ..schemas.comment_schema import CommentCreate

async def create_comment_for_graph(
    db: AsyncSession,
    comment: CommentCreate,
    graph_id: uuid.UUID,
    owner_id: uuid.UUID
) -> Comment:
    """Создает комментарий для графа."""
    db_comment = Comment(
        **comment.model_dump(),
        graph_id=graph_id,
        owner_id=owner_id
    )
    db.add(db_comment)
    await db.commit()
    # Обновляем, чтобы загрузить связь с 'owner'
    await db.refresh(db_comment, attribute_names=['owner'])
    return db_comment

async def get_comments_for_graph(
    db: AsyncSession,
    graph_id: uuid.UUID,
    skip: int = 0,
    limit: int = 10
) -> List[Comment]:
    """Получает список комментариев для графа с пагинацией."""
    result = await db.execute(
        select(Comment)
        .options(selectinload(Comment.owner)) # Жадно загружаем автора
        .filter(Comment.graph_id == graph_id)
        .order_by(Comment.created_at.desc()) # Новые комментарии сверху
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all() # type: ignore