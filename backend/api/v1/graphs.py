# backend/api/v1/graphs.py
import uuid
import logging
from typing import List, Optional  # noqa: F401

from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_db
from backend.crud import graph_crud, progress_crud, rating_crud
from backend.schemas import graph_schema
from backend.models.user_model import User
from backend.core.security import get_current_user

# Настраиваем логгер для этого модуля
logger = logging.getLogger(__name__)
router = APIRouter()

# --- ЗАВИСИМОСТЬ для опционального пользователя ---
async def get_optional_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> Optional[User]:
    """
    Пытается получить пользователя из заголовка Authorization.
    Если заголовка нет или токен невалиден, возвращает None.
    Не вызывает ошибку 401.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    
    token = auth_header.split(" ")[1]
    try:
        user = await get_current_user(token=token, db=db)
        return user
    except HTTPException:
        return None

# --- Эндпоинты ---


@router.get("/", response_model=graph_schema.PaginatedGraphs)
async def read_graphs(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 10,
    sort_by: str = Query("date_desc", enum=["date_desc", "rating_desc"]),
    search: Optional[str] = Query(None, min_length=3, max_length=50)
):
    """
    Получает список графов с пагинацией, сортировкой и поиском.
    - sort_by: 'date_desc' (по умолчанию), 'rating_desc'
    """
    paginated_data = await graph_crud.get_graphs(
        db, skip=skip, limit=limit, sort_by=sort_by, search_query=search
    )
    return paginated_data

@router.post("/", response_model=graph_schema.GraphInList, status_code=status.HTTP_201_CREATED)
async def create_graph(
    graph_in: graph_schema.GraphCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await graph_crud.create_graph(db=db, graph=graph_in, owner_id=current_user.id) # type: ignore

@router.get("/{graph_id}", response_model=graph_schema.GraphDetail)
async def read_graph(
    graph_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user) # <-- Теперь эта зависимость работает правильно
):
    logger.info(f"\n--- [API] Запрос на read_graph для ID: {graph_id} ---")
    
    # ... (вся остальная логика функции остается такой же, как в моем предыдущем полном ответе)
    db_graph = await graph_crud.get_graph_by_id(db, graph_id=graph_id)
    if db_graph is None:
        raise HTTPException(status_code=404, detail="Graph not found")

    elements = []
    for node in db_graph.nodes:
        elements.append({"group": "nodes", "data": {"id": str(node.id), "label": node.name}, "position": {"x": node.position_x, "y": node.position_y}})
    for edge in db_graph.edges:
        elements.append({"group": "edges", "data": {"id": str(edge.id), "source": str(edge.source_node_id), "target": str(edge.target_node_id)}})
    
    learned_ids = []
    ratings = await rating_crud.get_graph_ratings(db, graph_id=graph_id)
    my_vote = 0
    
    if current_user:
        logger.info(f"[API] Пользователь аутентифицирован: {current_user.username} (ID: {current_user.id})")
        learned_ids = await progress_crud.get_learned_nodes_for_graph(db, user_id=current_user.id, graph_id=graph_id) # type: ignore
        vote = await rating_crud.get_user_vote_for_graph(db, user_id=current_user.id, graph_id=graph_id) # type: ignore
        my_vote = vote if vote is not None else 0
    else:
        logger.info("[API] Пользователь НЕ аутентифицирован (гость).")
    
    response_data = {
        "id": db_graph.id, "name": db_graph.name, "description": db_graph.description,
        "created_at": db_graph.created_at, "owner": db_graph.owner,
        "elements": elements, "learned_node_ids": learned_ids,
        "likes": ratings["likes"], "dislikes": ratings["dislikes"], "my_vote": my_vote
    }
    logger.info(f"[API] Финальный ответ: {response_data}")
    return response_data

@router.post("/{graph_id}/nodes", response_model=graph_schema.NodeOut, status_code=status.HTTP_201_CREATED)
async def create_node(
    graph_id: uuid.UUID,
    node_in: graph_schema.NodeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_graph = await graph_crud.get_graph_by_id(db, graph_id=graph_id)
    if db_graph is None:
        raise HTTPException(status_code=404, detail="Graph not found")
    if db_graph.owner_id != current_user.id: # type: ignore
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return await graph_crud.create_node_for_graph(db=db, node=node_in, graph_id=graph_id)

@router.post("/{graph_id}/edges", response_model=graph_schema.EdgeOut, status_code=status.HTTP_201_CREATED)
async def create_edge(
    graph_id: uuid.UUID,
    edge_in: graph_schema.EdgeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_graph = await graph_crud.get_graph_by_id(db, graph_id=graph_id)
    if db_graph is None:
        raise HTTPException(status_code=404, detail="Graph not found")
    if db_graph.owner_id != current_user.id: # type: ignore
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return await graph_crud.create_edge_for_graph(db=db, edge=edge_in, graph_id=graph_id)

# --- НОВЫЙ ЭНДПОИНТ ДЛЯ ГОЛОСОВАНИЯ ---
@router.post("/{graph_id}/rate", status_code=status.HTTP_204_NO_CONTENT)
async def rate_graph(
    graph_id: uuid.UUID,
    rating_in: graph_schema.RatingIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Позволяет аутентифицированному пользователю поставить/изменить/убрать оценку графа.
    value: 1 для лайка, -1 для дизлайка.
    Повторная отправка того же значения убирает голос.
    """
    # Проверяем, что граф существует (опционально, но хорошая практика)
    db_graph = await graph_crud.get_graph_by_id(db, graph_id=graph_id)
    if db_graph is None:
        raise HTTPException(status_code=404, detail="Graph not found")
    
    # Нельзя голосовать за свой собственный граф
    if db_graph.owner_id == current_user.id: # type: ignore
        raise HTTPException(status_code=403, detail="Cannot rate your own graph")
    
    await rating_crud.set_graph_rating(
        db, user_id=current_user.id, graph_id=graph_id, value=rating_in.value # type: ignore
    )
    return