# backend/schemas/progress_schema.py
import uuid
from pydantic import BaseModel

class UserProgress(BaseModel):
    user_id: uuid.UUID
    node_id: uuid.UUID
    
    class Config:
        from_attributes = True