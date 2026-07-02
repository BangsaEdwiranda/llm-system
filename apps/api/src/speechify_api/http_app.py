from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from . import auth
from .db import get_session, init_db
from .models import User
from .schemas import (
    ConversionResponse,
    DocumentCreate,
    DocumentDetail,
    DocumentSummary,
    JobProgressResponse,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
)
from .services import conversion_service, document_service

app = FastAPI(title="Speechify Practice API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


def get_current_user(
    authorization: str = Header(default=""),
    session: Session = Depends(get_session),
) -> User:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.removeprefix("Bearer ")
    try:
        user_id = auth.decode_access_token(token)
    except Exception as exc:  # noqa: BLE001 - any decode failure is unauthorized
        raise HTTPException(status_code=401, detail="Invalid token") from exc
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user


@app.post("/auth/register", response_model=TokenResponse)
def register(payload: RegisterRequest, session: Session = Depends(get_session)) -> TokenResponse:
    existing = session.query(User).filter(User.email == payload.email).first()
    if existing is not None:
        raise HTTPException(status_code=409, detail="Email already registered")
    user = User(email=payload.email, hashed_password=auth.hash_password(payload.password))
    session.add(user)
    session.commit()
    session.refresh(user)
    return TokenResponse(access_token=auth.create_access_token(user.id))


@app.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, session: Session = Depends(get_session)) -> TokenResponse:
    user = session.query(User).filter(User.email == payload.email).first()
    if user is None or not auth.verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return TokenResponse(access_token=auth.create_access_token(user.id))


@app.post("/documents", response_model=DocumentDetail)
def create_document(
    payload: DocumentCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> DocumentDetail:
    document = document_service.create_document(session, current_user.id, payload.title, payload.text)
    return DocumentDetail(
        id=document.id,
        owner_id=document.owner_id,
        title=document.title,
        text=document.text,
        created_at=document.created_at,
    )


@app.get("/documents", response_model=list[DocumentSummary])
def list_documents(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[DocumentSummary]:
    return [DocumentSummary(**row) for row in document_service.list_documents_with_status(session, current_user.id)]


@app.get("/documents/{document_id}", response_model=DocumentDetail)
def read_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> DocumentDetail:
    document = document_service.get_document(session, document_id, current_user.id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentDetail(
        id=document.id,
        owner_id=document.owner_id,
        title=document.title,
        text=document.text,
        created_at=document.created_at,
    )


@app.post("/documents/{document_id}/convert", response_model=ConversionResponse)
def convert_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ConversionResponse:
    document = document_service.get_document(session, document_id, current_user.id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    conversion = conversion_service.create_conversion(session, document.id, document.text)
    return ConversionResponse(
        id=conversion.id,
        document_id=conversion.document_id,
        status=conversion.status,
        audio_url=conversion.audio_url,
    )


@app.get("/documents/{document_id}/audio", response_model=ConversionResponse)
def download_audio(
    document_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ConversionResponse:
    document = document_service.get_document(session, document_id, current_user.id)
    if document is None or not document.conversions:
        raise HTTPException(status_code=404, detail="No conversion available")
    latest = document.conversions[0]
    return ConversionResponse(
        id=latest.id,
        document_id=latest.document_id,
        status=latest.status,
        audio_url=latest.audio_url,
    )


@app.get("/jobs/{job_id}/progress", response_model=JobProgressResponse)
def job_progress(job_id: str, current_user: User = Depends(get_current_user)) -> JobProgressResponse:
    return JobProgressResponse(job_id=job_id, progress=conversion_service.get_job_progress(job_id))
