# backend/crud/graph_crud.py
from sqlalchemy import distinct, func, case, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List, Optional  # noqa: F401
import uuid

from backend.models.graph_model import Graph, Node, Edge, GraphRating
from backend.schemas.graph_schema import GraphCreate, NodeCreate, EdgeCreate

async def create_graph(db: AsyncSession, graph: GraphCreate, owner_id: uuid.UUID) -> Graph:
    """
    Создает новый граф, сохраняет его и возвращает полностью загруженный объект.
    """
    # 1. Создаем объект и добавляем в сессию
    db_graph = Graph(**graph.model_dump(), owner_id=owner_id)
    db.add(db_graph)
    
    # 2. Коммитим, чтобы сохранить объект в БД и получить ID
    await db.commit()
    
    # 3. Обновляем объект из БД, "жадно" загружая связанного владельца.
    # Это ключевой шаг, который делает объект снова "живым" и загружает связи.
    await db.refresh(db_graph, attribute_names=['owner'])
    
    return db_graph

async def get_graph_by_id(db: AsyncSession, graph_id: uuid.UUID) -> Optional[Graph]:
    """
    Получает граф по ID, "жадно" загружая все связанные сущности:
    владельца, узлы и ребра.
    """
    result = await db.execute(
        select(Graph)
        .options(
            selectinload(Graph.owner),
            selectinload(Graph.nodes), # <-- Загружаем узлы
            selectinload(Graph.edges)  # <-- Загружаем ребра
        )
        .filter(Graph.id == graph_id)
    )
    return result.scalar_one_or_none()

async def get_graphs(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 10,
    sort_by: str = "date_desc",
    search_query: Optional[str] = None
):
    """
    Получает графы, включая их рейтинг, с пагинацией, сортировкой и поиском.
    """
    
    # 1. Основной запрос для выборки данных
    # Мы сразу соединяем Graph с GraphRating, чтобы посчитать голоса
    # Используем outerjoin, чтобы графы без оценок тоже попадали в выборку
    base_query = select(
        Graph,
        func.sum(case((GraphRating.value == 1, 1), else_=0)).label("likes"),
        func.sum(case((GraphRating.value == -1, 1), else_=0)).label("dislikes")
    ).outerjoin(GraphRating, Graph.id == GraphRating.graph_id)

    # 2. Применяем фильтр поиска, если он есть
    if search_query:
        search_term = f"%{search_query.lower()}%"
        base_query = base_query.filter(
            or_(
                func.lower(Graph.name).like(search_term),
                func.lower(Graph.description).like(search_term)
            )
        )
    
    # Группировка должна быть после фильтрации, но до сортировки
    query_with_filter = base_query.group_by(Graph.id)
    
    # 3. Применяем сортировку
    if sort_by == "rating_desc":
        # Сортируем по разнице лайков и дизлайков
        rating_expr = func.sum(case((GraphRating.value == 1, 1), (GraphRating.value == -1, -1), else_=0))
        # func.coalesce нужен для графов без оценок (чтобы они считались с рейтингом 0)
        order_expr = func.coalesce(rating_expr, 0).desc()
        query_with_sort = query_with_filter.order_by(order_expr, Graph.created_at.desc())
    else: # По умолчанию (date_desc)
        query_with_sort = query_with_filter.order_by(Graph.created_at.desc())

    # 4. Применяем пагинацию и загрузку связанных данных
    final_query = query_with_sort.options(selectinload(Graph.owner)).offset(skip).limit(limit)
    
    # 5. Выполняем запрос для получения графов
    result = await db.execute(final_query)
    
    # Собираем результат. Теперь result содержит кортежи (Graph, likes, dislikes)
    graphs_with_ratings = []
    for graph, likes, dislikes in result.fetchall():
        graph.likes = likes or 0
        graph.dislikes = dislikes or 0
        graphs_with_ratings.append(graph)

    # 6. Выполняем отдельный запрос для подсчета общего количества элементов
    # Он должен учитывать фильтр поиска, но не пагинацию
    count_query = select(func.count(distinct(Graph.id))) # Считаем уникальные графы
    if search_query:
        search_term = f"%{search_query.lower()}%"
        count_query = count_query.filter(
             or_(
                func.lower(Graph.name).like(search_term),
                func.lower(Graph.description).like(search_term)
            )
        )
    
    total = (await db.execute(count_query)).scalar_one()
    
    return {"total": total, "graphs": graphs_with_ratings}

async def create_node_for_graph(db: AsyncSession, node: NodeCreate, graph_id: uuid.UUID) -> Node:
    """Создает узел для указанного графа."""
    db_node = Node(
        **node.model_dump(),
        graph_id=graph_id
    )
    db.add(db_node)
    await db.commit()
    await db.refresh(db_node)
    return db_node

async def create_edge_for_graph(db: AsyncSession, edge: EdgeCreate, graph_id: uuid.UUID) -> Edge:
    """Создает ребро для указанного графа."""
    # TODO: В будущем здесь нужна валидация, что source и target узлы
    # принадлежат этому же графу. Пока опускаем для простоты.
    db_edge = Edge(
        **edge.model_dump(),
        graph_id=graph_id
    )
    db.add(db_edge)
    await db.commit()
    await db.refresh(db_edge)
    return db_edge