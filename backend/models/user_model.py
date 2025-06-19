# backend/models/user_model.py
import uuid
from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import UUID # Работает и для SQLite
from backend.db.session import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
