# backend/schemas/user_base_schemas.py (НОВЫЙ ФАЙЛ)
import uuid
from pydantic import BaseModel

class UserOut(BaseModel):
    id: uuid.UUID
    username: str

    class Config:
        from_attributes = True