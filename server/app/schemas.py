from pydantic import BaseModel, EmailStr
from typing import List, Optional, Literal


class RegisterIn(BaseModel):
    email: EmailStr
    password: str


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class DocumentOut(BaseModel):
    id: int
    filename: str
    size: int

    class Config:
        from_attributes = True


class AskIn(BaseModel):
    question: str
    top_k: int = 4


class AskOut(BaseModel):
    answer: str
    sources: List[dict]


class ChatMsg(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class AskIn(BaseModel):
    question: str
    top_k: int = 4
    prev_context: Optional[str] = None
    history: Optional[List[ChatMsg]] = None


class DeleteAccountIn(BaseModel):
    password: str
