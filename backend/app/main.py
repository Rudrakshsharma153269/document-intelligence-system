from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
import os
import shutil
from typing import List, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from .database import Base, engine, get_db
from .models import User, Document
from .auth import (
    get_password_hash,
    authenticate_user,
    create_access_token,
    get_current_user,
)
from .rag_pipeline import RAGPipeline

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Document Intelligence System")

# CORS (frontend dev on 3000 or 5173)
origins = os.getenv("BACKEND_CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

rag = RAGPipeline()


# ---------- Pydantic Schemas ----------
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class QuestionRequest(BaseModel):
    question: str
    chat_history: Optional[List[dict]] = None


class SourceChunk(BaseModel):
    text: str
    page: Optional[int] = None
    doc_id: Optional[str] = None


class AnswerResponse(BaseModel):
    answer: str
    sources: List[SourceChunk]


# ---------- Auth Endpoints ----------
@app.post("/auth/register", response_model=TokenResponse)
def register_user(payload: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user and return a JWT."""
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    user = User(email=payload.email, hashed_password=get_password_hash(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": user.email})
    return TokenResponse(access_token=token)


@app.post("/auth/login", response_model=TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    OAuth2-compatible login endpoint.
    Accepts form data: username (email) and password.
    """
    user = authenticate_user(db, email=form_data.username, password=form_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    token = create_access_token({"sub": user.email})
    return TokenResponse(access_token=token)


# ---------- Document Upload ----------
@app.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a PDF, store it on disk, create a DB entry and index into FAISS.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    documents_dir = os.getenv("DOCUMENTS_PATH", "./documents")
    os.makedirs(documents_dir, exist_ok=True)

    # Use user ID + original filename to avoid collisions
    safe_name = f"user_{current_user.id}_{file.filename}"
    file_path = os.path.join(documents_dir, safe_name)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    doc = Document(
        filename=safe_name,
        original_name=file.filename,
        owner_id=current_user.id,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Ingest into RAG pipeline
    rag.ingest_document(user_id=current_user.id, doc_path=file_path, doc_id=str(doc.id))

    return {"message": "Document uploaded and indexed", "document_id": doc.id}


# ---------- Document List ----------
@app.get("/documents/list")
def list_documents(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    docs = db.query(Document).filter(Document.owner_id == current_user.id).all()
    return [{"id": d.id, "name": d.original_name} for d in docs]


# ---------- Question Answering ----------
@app.post("/chat/ask", response_model=AnswerResponse)
def ask_question(
    payload: QuestionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Answer a question using RAG over the current user's documents.
    """
    if not payload.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    chunks = rag.retrieve(user_id=current_user.id, query=payload.question, k=5)
    if not chunks:
        return AnswerResponse(answer="I could not find any relevant information in your documents.", sources=[])

    answer = rag.generate_answer(
        query=payload.question,
        context_chunks=chunks,
        chat_history=payload.chat_history or [],
    )

    sources = [SourceChunk(**c) for c in chunks]
    return AnswerResponse(answer=answer, sources=sources)


@app.get("/health")
def health_check():
    return {"status": "ok"}

