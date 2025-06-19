# backend/schemas/comment_schema.py
import uuid
from datetime import datetime
from pydantic import BaseModel
from .user_schema import UserOut # Нам понадобится информация об авторе

class CommentBase(BaseModel):
    content: str

class CommentCreate(CommentBase):
    pass

class CommentOut(CommentBase):
    id: uuid.UUID
    created_at: datetime
    owner: UserOut # Включаем информацию об авторе в ответ

    class Config:
        from_attributes = True