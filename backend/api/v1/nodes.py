# backend/api/v1/nodes.py
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_db
from backend.crud import node_crud, progress_crud
from backend.schemas.graph_schema import NodeOut, NodeUpdate
from backend.models.user_model import User
from backend.core.security import get_current_user

router = APIRouter()

@router.get("/{node_id}", response_model=NodeOut)
async def read_node(
    node_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
    # Защита не нужна, так как просмотр контента может быть публичным.
    # Если нужна защита, нужно добавить current_user и проверку.
):
    """Получает данные одного узла по его ID."""
    db_node = await node_crud.get_node_by_id(db, node_id=node_id)
    if not db_node:
        raise HTTPException(status_code=404, detail="Node not found")
    return db_node

@router.patch("/{node_id}", response_model=NodeOut)
async def update_node(
    node_id: uuid.UUID,
    node_in: NodeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Обновляет узел. Доступно только владельцу графа."""
    db_node = await node_crud.get_node_by_id(db, node_id=node_id)
    if not db_node:
        raise HTTPException(status_code=404, detail="Node not found")
    
    # db_node.graph был загружен в get_node_by_id
    if db_node.graph.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
        
    return await node_crud.update_node(db=db, db_node=db_node, node_in=node_in)

@router.delete("/{node_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_node(
    node_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Удаляет узел. Доступно только владельцу графа."""
    db_node = await node_crud.get_node_by_id(db, node_id=node_id)
    if not db_node:
        # Если узел не найден, можно вернуть 204, чтобы избежать утечки информации
        return
    
    if db_node.graph.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
        
    await node_crud.delete_node(db=db, db_node=db_node)
    return

# --- ЭНДПОИНТЫ ДЛЯ ПРОГРЕССА ---

@router.post("/{node_id}/progress", status_code=status.HTTP_204_NO_CONTENT)
async def mark_progress(
    node_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Отмечает узел как изученный для текущего пользователя."""
    # Проверяем, существует ли узел (опционально, но хорошая практика)
    db_node = await node_crud.get_node_by_id(db, node_id=node_id)
    if not db_node:
        raise HTTPException(status_code=404, detail="Node not found")
    
    await progress_crud.mark_node_as_learned(db, user_id= uuid.UUID(str(current_user.id)), node_id=node_id)
    return

@router.delete("/{node_id}/progress", status_code=status.HTTP_204_NO_CONTENT)
async def unmark_progress(
    node_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Убирает отметку об изучении узла для текущего пользователя."""
    await progress_crud.unmark_node_as_learned(db, user_id= uuid.UUID(str(current_user.id)), node_id=node_id)
    return