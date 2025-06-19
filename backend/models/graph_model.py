# backend/models/graph_model.py
import uuid
from datetime import datetime
from sqlalchemy import Column, String, ForeignKey, DateTime, Text, Float, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from backend.db.session import Base

class Graph(Base):
    __tablename__ = "graphs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    owner = relationship("User")
    
    nodes = relationship("Node", back_populates="graph", cascade="all, delete-orphan")
    edges = relationship("Edge", back_populates="graph", cascade="all, delete-orphan")

class Node(Base):
    __tablename__ = "nodes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    content = Column(Text, default="")
    position_x = Column(Float, default=0.0)
    position_y = Column(Float, default=0.0)
    
    graph_id = Column(UUID(as_uuid=True), ForeignKey("graphs.id"), nullable=False)
    graph = relationship("Graph", back_populates="nodes")

    source_for_edges = relationship("Edge", foreign_keys="Edge.source_node_id", back_populates="source_node", cascade="all, delete-orphan")
    target_for_edges = relationship("Edge", foreign_keys="Edge.target_node_id", back_populates="target_node", cascade="all, delete-orphan")

class Edge(Base):
    __tablename__ = "edges"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    graph_id = Column(UUID(as_uuid=True), ForeignKey("graphs.id"), nullable=False)
    source_node_id = Column(UUID(as_uuid=True), ForeignKey("nodes.id"), nullable=False)
    target_node_id = Column(UUID(as_uuid=True), ForeignKey("nodes.id"), nullable=False)
    
    graph = relationship("Graph", back_populates="edges")
    source_node = relationship("Node", foreign_keys=[source_node_id])
    target_node = relationship("Node", foreign_keys=[target_node_id])
    
    source_node = relationship("Node", foreign_keys=[source_node_id], back_populates="source_for_edges")
    target_node = relationship("Node", foreign_keys=[target_node_id], back_populates="target_for_edges")

class UserProgress(Base):
    __tablename__ = "user_progress"
    
    # Составной первичный ключ
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    node_id = Column(UUID(as_uuid=True), ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    
    # Можно добавить дату, если понадобится в будущем
    # marked_at = Column(DateTime, default=datetime.utcnow)

class GraphRating(Base):
    __tablename__ = "graph_ratings"
    
    # Составной первичный ключ для уникальности голоса
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    graph_id = Column(UUID(as_uuid=True), ForeignKey("graphs.id", ondelete="CASCADE"), primary_key=True)
    
    # Голос: +1 за лайк, -1 за дизлайк
    value = Column(Integer, nullable=False)

class Comment(Base):
    __tablename__ = "comments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    graph_id = Column(UUID(as_uuid=True), ForeignKey("graphs.id", ondelete="CASCADE"), nullable=False)

    # Связи для удобного доступа
    owner = relationship("User")
    # replies = relationship("Reply", back_populates="comment", cascade="all, delete-orphan") # <-- Добавим, когда будем делать ответы