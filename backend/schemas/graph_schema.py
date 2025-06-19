# backend/schemas/graph_schema.py
import uuid
from datetime import datetime  # noqa: F401
from pydantic import BaseModel, Field  # noqa: F401
from typing import Optional, List, Dict, Union, Literal

from backend.schemas.user_schema import UserOut  # noqa: F401
from .graph_base_schemas import GraphInList, PaginatedGraphs  # noqa: F401

# --- Схемы для элементов Cytoscape ---

class CytoscapeNodeData(BaseModel):
    id: str # Cytoscape требует строковый id
    label: str
    # Дополнительные данные, если понадобятся
    # content: str 

class CytoscapeEdgeData(BaseModel):
    id: str # Cytoscape требует строковый id
    source: str
    target: str

class CytoscapeElement(BaseModel):
    group: str # 'nodes' или 'edges'
    data: Union[CytoscapeNodeData, CytoscapeEdgeData]
    position: Optional[Dict[str, float]] = None # Для узлов { "x": 100, "y": 100 }


# --- Схемы для сущностей из БД ---

class NodeBase(BaseModel):
    name: str
    content: Optional[str] = ""
    position_x: Optional[float] = 0.0
    position_y: Optional[float] = 0.0

class NodeCreate(NodeBase):
    pass # Все поля наследуются от NodeBase

class NodeUpdate(BaseModel):
    name: Optional[str] = None
    content: Optional[str] = None
    position_x: Optional[float] = None
    position_y: Optional[float] = None
    
class NodeOut(NodeBase):
    id: uuid.UUID

    class Config:
        from_attributes = True

class EdgeBase(BaseModel):
    source_node_id: uuid.UUID
    target_node_id: uuid.UUID

class EdgeCreate(EdgeBase):
    pass # Все поля наследуются от EdgeBase

class EdgeOut(EdgeBase):
    id: uuid.UUID

    class Config:
        from_attributes = True

# --- Основные схемы для графа ---

class GraphBase(BaseModel):
    name: str
    description: Optional[str] = None

class GraphCreate(GraphBase):
    pass

class RatingIn(BaseModel):
    # Принимаем только значения 1 или -1
    value: Literal[1, -1]
    
# Схема для детального ответа (с элементами для Cytoscape)
class GraphDetail(GraphInList):
    elements: List[CytoscapeElement]
    learned_node_ids: Optional[List[uuid.UUID]] = None
    
    likes: int = 0
    dislikes: int = 0
    # Голос текущего пользователя: 1, -1 или 0 (если не голосовал)
    my_vote: Optional[Literal[1, -1, 0]] = 0