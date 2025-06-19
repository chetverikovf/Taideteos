# backend/schemas/user_schema.py
import uuid
from pydantic import BaseModel, constr
from typing import Annotated, List, TYPE_CHECKING

from .user_base_schemas import UserOut  # noqa: F401
from backend.schemas.graph_base_schemas import GraphInList

if TYPE_CHECKING:
    from .graph_base_schemas import GraphInList

# Схема для создания пользователя (что приходит в запросе)
class UserCreate(BaseModel):
    # 2. Используем Annotated для указания ограничений
    username: Annotated[str, constr(min_length=3, max_length=50)]
    password: Annotated[str, constr(min_length=6)]

class UserProfile(BaseModel):
    id: uuid.UUID
    username: str
    
    total_likes: int
    total_dislikes: int
    
    owned_graphs: List["GraphInList"] 
    learning_graphs: List["GraphInList"]

    class Config:
        from_attributes = True

from .graph_base_schemas import GraphInList  # noqa: E402
UserProfile.model_rebuild(force=True)