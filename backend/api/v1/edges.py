# backend/api/v1/edges.py
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_db
from backend.crud import edge_crud
from backend.models.user_model import User
from backend.core.security import get_current_user

router = APIRouter()

@router.delete("/{edge_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_edge(
    edge_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Удаляет ребро. Доступно только владельцу графа."""
    db_edge = await edge_crud.get_edge_by_id(db, edge_id=edge_id)
    if not db_edge:
        return

    if db_edge.graph.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
        
    await edge_crud.delete_edge(db=db, db_edge=db_edge)
    return