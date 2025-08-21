from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, LargeBinary, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .db import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="user")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    documents = relationship("Document", back_populates="owner")


class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename = Column(String, nullable=False)
    path = Column(String, nullable=False)
    size = Column(Integer)
    meta_json = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", back_populates="documents")
    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")


class Chunk(Base):
    __tablename__ = "chunks"
    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    position = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    # Store embedding as raw bytes (float32 array)
    embedding = Column(LargeBinary, nullable=False)
    page = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    document = relationship("Document", back_populates="chunks")


# models.py
class AnswerCache(Base):
    __tablename__="answer_cache"
    id=Column(Integer, primary_key=True)
    user_id=Column(Integer, index=True)
    qhash=Column(String, index=True)  # sha256 of normalized q
    payload=Column(Text)              # JSON of answer+sources
    created_at=Column(DateTime(timezone=True), server_default=func.now())
