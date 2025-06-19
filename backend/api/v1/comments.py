# backend/api/v1/comments.py
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_db
from backend.crud import comment_crud, graph_crud
from backend.schemas import comment_schema
from backend.models.user_model import User
from backend.core.security import get_current_user

router = APIRouter()

@router.post(
    "/graphs/{graph_id}/comments",
    response_model=comment_schema.CommentOut,
    status_code=status.HTTP_201_CREATED,
    tags=["comments"] # Помечаем тегом для группировки в /docs
)
async def create_comment(
    graph_id: uuid.UUID,
    comment_in: comment_schema.CommentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Добавляет комментарий к графу. Требуется аутентификация.
    """
    # Проверяем, существует ли граф
    db_graph = await graph_crud.get_graph_by_id(db, graph_id=graph_id)
    if db_graph is None:
        raise HTTPException(status_code=404, detail="Graph not found")
        
    return await comment_crud.create_comment_for_graph(
        db, comment=comment_in, graph_id=graph_id, owner_id=current_user.id # type: ignore
    )

@router.get(
    "/graphs/{graph_id}/comments",
    response_model=List[comment_schema.CommentOut],
    tags=["comments"]
)
async def read_comments(
    graph_id: uuid.UUID,
    skip: int = 0,
    limit: int = 10,
    db: AsyncSession = Depends(get_db)
):
    """
    Получает комментарии для графа с пагинацией.
    """
    # Проверку существования графа можно опустить, вернется просто пустой список
    comments = await comment_crud.get_comments_for_graph(db, graph_id=graph_id, skip=skip, limit=limit)
    return comments