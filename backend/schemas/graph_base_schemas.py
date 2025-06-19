# backend/schemas/graph_base_schemas.py
import uuid
from datetime import datetime
from pydantic import BaseModel
from .user_base_schemas import UserOut
from typing import List

class GraphInList(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    created_at: datetime
    owner: UserOut
    
    likes: int = 0
    dislikes: int = 0

    class Config:
        from_attributes = True

# ---СХЕМА-ОБЕРТКА ---
class PaginatedGraphs(BaseModel):
    total: int
    graphs: List[GraphInList]