from datetime import datetime

from pydantic import BaseModel


class RegisterRequest(BaseModel):
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class DocumentCreate(BaseModel):
    title: str
    text: str


class DocumentSummary(BaseModel):
    id: int
    title: str
    created_at: datetime
    status: str
    audio_url: str | None = None


class DocumentDetail(BaseModel):
    id: int
    owner_id: int
    title: str
    text: str
    created_at: datetime


class ConversionResponse(BaseModel):
    id: int
    document_id: int
    status: str
    audio_url: str | None = None


class JobProgressResponse(BaseModel):
    job_id: str
    progress: int
