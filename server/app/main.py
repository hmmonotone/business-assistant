import os
from typing import List, Dict, Optional, Tuple
import numpy as np
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import select, delete
from mimetypes import guess_type

from .db import Base, engine
from .models import User, Document, Chunk
from .schemas import RegisterIn, LoginIn, DocumentOut, AskIn, AskOut, DeleteAccountIn
from .utils import (
    hash_password, verify_password,
    extract_revenue_records, resolve_week_range, aggregate_week
)
from .auth import create_token, get_current_user, get_db
from .ingest import extract_and_chunk, embed_texts
from .llm import answer_with_groq, stream_answer_with_groq

STORAGE_DIR = os.getenv("STORAGE_DIR", "./storage")
os.makedirs(STORAGE_DIR, exist_ok=True)

app = FastAPI(title="Business AI MVP")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

# app.mount("/files", StaticFiles(directory=STORAGE_DIR), name="files")

# create tables
Base.metadata.create_all(bind=engine)


# --------------------------- helpers ---------------------------

def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b))  # embeddings are normalized


def _save_and_ingest(filename: str, contents: bytes, user: User, db: Session) -> Document:
    save_path = os.path.join(STORAGE_DIR, f"{user.id}_{filename}")
    with open(save_path, "wb") as f:
        f.write(contents)
    size = os.path.getsize(save_path)

    doc = Document(user_id=user.id, filename=filename, path=save_path, size=size, meta_json=None)
    db.add(doc)
    db.commit()
    db.refresh(doc)

    chunks, embs, pages = extract_and_chunk(save_path, filename)
    for i, (text, emb) in enumerate(zip(chunks, embs)):
        page = pages[i] if pages else None
        db.add(Chunk(document_id=doc.id, position=i, text=text, embedding=emb.tobytes(), page=page))
    db.commit()
    return doc


# Map month names to numbers for quick parsing from the question
_MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12
}


def _month_from_question(q: str) -> Optional[int]:
    q = q.lower()
    for name, num in _MONTHS.items():
        if name in q:
            return num
    return None


def _normalize_history(history) -> Optional[List[Dict[str, str]]]:
    """Accepts list of dicts or Pydantic ChatMsg models and returns a clean list."""
    if not history:
        return None
    out: List[Dict[str, str]] = []
    for m in history[-8:]:
        if hasattr(m, "model_dump"):
            d = m.model_dump()
        elif hasattr(m, "dict"):
            d = m.dict()
        elif isinstance(m, dict):
            d = m
        else:
            d = {"role": getattr(m, "role", None), "content": getattr(m, "content", "")}
        role = d.get("role")
        content = (d.get("content") or "").strip()
        if role in ("user", "assistant") and content:
            out.append({"role": role, "content": content})
    return out or None


def _find_month_sources(db: Session, user_id: int, month: int, year: Optional[int] = None, limit: int = 300):
    """
    Pull extra chunks that contain the month string so the weekly parser
    sees *all* rows from the revenue table image, not just Top-K.
    If year is None, we match '-MM-' and let the parser pick the year from rows.
    """
    if year:
        pattern = f"{year}-{month:02d}-"
        q = (db.query(Chunk, Document)
             .join(Document, Document.id == Chunk.document_id)
             .filter(Document.user_id == user_id, Chunk.text.contains(pattern))
             .limit(limit))
    else:
        # looser: match '-MM-' to gather all candidate rows across years
        pattern = f"-{month:02d}-"
        q = (db.query(Chunk, Document)
             .join(Document, Document.id == Chunk.document_id)
             .filter(Document.user_id == user_id, Chunk.text.contains(pattern))
             .limit(limit))
    rows = q.all()
    out = []
    for ch, doc in rows:
        out.append({
            "document_id": doc.id,
            "filename": doc.filename,
            "page": ch.page,
            "text": ch.text or ""
        })
    return out


# --------------------------- AUTH ---------------------------
@app.post("/api/auth/delete-account")
def delete_account(payload: DeleteAccountIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # 1) verify password
    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(403, "Invalid password")

    # 2) delete all user docs/chunks + files from disk
    docs = db.scalars(select(Document).where(Document.user_id == user.id)).all()
    for doc in docs:
        db.execute(delete(Chunk).where(Chunk.document_id == doc.id))
        db.delete(doc)
        try:
            os.remove(doc.path)
        except Exception:
            pass

    # 3) finally delete the user
    db.delete(user)
    db.commit()

    # Client should forget JWT locally; it’s stateless
    return {"ok": True}


@app.get("/api/documents/{doc_id}/download")
def download_document(doc_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = db.get(Document, doc_id)
    if not doc or doc.user_id != user.id:
        raise HTTPException(404, "Not found")
    media_type, _ = guess_type(doc.filename)
    return FileResponse(
        path=doc.path,
        filename=doc.filename,
        media_type=media_type or "application/octet-stream",
    )

@app.post("/api/auth/register")
def register(payload: RegisterIn, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.email == payload.email)):
        raise HTTPException(400, "Email already registered")
    user = User(email=payload.email, password_hash=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_token(user.id)
    return {"token": token, "user": {"id": user.id, "email": user.email}}


@app.post("/api/auth/login")
def login(payload: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, "Invalid credentials")
    token = create_token(user.id)
    return {"token": token, "user": {"id": user.id, "email": user.email}}


@app.get("/api/auth/profile")
def profile(user: User = Depends(get_current_user)):
    return {"id": user.id, "email": user.email}


# --------------------------- DOCUMENTS ---------------------------

@app.post("/api/documents/upload", response_model=DocumentOut)
async def upload_document(
        file: UploadFile = File(...),
        user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
):
    contents = await file.read()
    doc = _save_and_ingest(file.filename, contents, user, db)
    return doc


@app.post("/api/documents/upload/batch", response_model=List[DocumentOut])
async def upload_documents_batch(
        files: List[UploadFile] = File(...),
        user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
):
    if not files:
        raise HTTPException(400, "No files provided")
    docs: List[Document] = []
    for f in files:
        contents = await f.read()
        docs.append(_save_and_ingest(f.filename, contents, user, db))
    return docs


@app.get("/api/documents", response_model=List[DocumentOut])
def list_documents(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    docs = db.scalars(
        select(Document).where(Document.user_id == user.id).order_by(Document.created_at.desc())
    ).all()
    return docs


@app.delete("/api/documents/{doc_id}")
def delete_document(doc_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = db.get(Document, doc_id)
    if not doc or doc.user_id != user.id:
        raise HTTPException(404, "Not found")
    db.execute(delete(Chunk).where(Chunk.document_id == doc.id))
    db.delete(doc)
    db.commit()
    try:
        os.remove(doc.path)
    except Exception:
        pass
    return {"ok": True}


# --------------------------- ASK ---------------------------

@app.post("/api/knowledge/ask", response_model=AskOut)
def ask(payload: AskIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q_text = payload.question
    q_lower = q_text.lower()
    is_sales_q = ("sales" in q_lower or "revenue" in q_lower) and ("week" in q_lower)
    month_hint = _month_from_question(q_lower)

    # Embed question (bias slightly for sales table lookups)
    if is_sales_q:
        q_text += " monthly revenue record total revenue transactions table"
    q_emb = embed_texts([q_text])[0]

    # Load candidate chunks for this user
    rows = db.scalars(
        select(Chunk).join(Document, Chunk.document_id == Document.id).where(Document.user_id == user.id)
    ).all()
    if not rows:
        raise HTTPException(400, "No documents ingested yet. Upload first.")

    # Rank by cosine
    scored = [(cosine_sim(q_emb, np.frombuffer(r.embedding, dtype=np.float32)), r) for r in rows]
    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[: payload.top_k]

    THRESHOLD = 0.28
    sources = [
        {
            "document_id": r.document_id,
            "filename": r.document.filename,
            "page": r.page,
            "url": f"/api/documents/{r.document_id}/download",  # <-- protected
            "text": (r.text or ""),
        }
        for _, r in top
    ]

    # If relevance is weak and it's a sales week question, don't bail yet—expand sources by month.
    if (not top or top[0][0] < THRESHOLD) and is_sales_q and month_hint:
        sources.extend(_find_month_sources(db, user.id, month_hint, year=None))

    # ---------- Deterministic weekly revenue path ----------
    if is_sales_q:
        context_text = "\n\n".join(s.get("text", "") for s in sources)
        records = extract_revenue_records(context_text)

        # If we didn't capture enough rows, expand from DB by month and retry
        if month_hint and len(records) < 7:
            extra = _find_month_sources(db, user.id, month_hint, year=None)
            # Deduplicate quickly
            seen = {(s["document_id"], s.get("page"), (s.get("text", "")[:64])) for s in sources}
            for e in extra:
                key = (e["document_id"], e.get("page"), (e.get("text", "")[:64]))
                if key not in seen:
                    sources.append(e);
                    seen.add(key)
            context_text = "\n\n".join(s.get("text", "") for s in sources)
            records = extract_revenue_records(context_text)

        rng = resolve_week_range(payload.question, records)
        if rng:
            start, end = rng
            week_rows = [(dt, val) for dt, val in records if start <= dt <= end]
            if week_rows:
                agg = aggregate_week(records, start, end)

                index_by_id_page = {}
                for idx, s in enumerate(sources, 1):
                    index_by_id_page[(s["document_id"], s.get("page"))] = idx

                def cite_for(dt_str: str) -> str:
                    for idx, s in enumerate(sources, 1):
                        if dt_str in (s.get("text") or ""):
                            return f"[{idx}]"
                    return ""

                bullets = [
                    f"- {dt.isoformat()}: ${val:,.2f} {cite_for(dt.isoformat())}"
                    for dt, val in sorted(week_rows, key=lambda x: x[0])
                ]
                answer = (
                        f"Sales in {start.strftime('%B')} {start.day}–{end.day}, {start.year}: "
                        f"**${agg['total']:,.2f}** (avg **${agg['avg']:,.2f}**/day).\n" +
                        "\n".join(bullets)
                )
                return {"answer": answer, "sources": sources}

        # If still nothing concrete, and relevance was truly low, fall through to graceful not-enough-info
        if not top or top[0][0] < THRESHOLD:
            return {"answer": "I don’t have enough information in your documents to answer that.", "sources": []}
        # else we’ll let LLM attempt with whatever sources we have

    # ---------- RAG path (LLM) ----------
    # Prepend previous context if provided
    carry = (payload.prev_context or "").strip()
    if carry:
        carry = carry[-4000:]
        sources = ([{"document_id": 0, "filename": "previous-context", "page": None, "text": carry}] + sources)

    history = _normalize_history(payload.history)
    answer = answer_with_groq(payload.question, sources, history=history)
    return {"answer": answer, "sources": sources}


@app.post("/api/knowledge/ask/stream")
def ask_stream(payload: AskIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q_emb = embed_texts([payload.question])[0]

    rows = db.scalars(
        select(Chunk).join(Document, Chunk.document_id == Document.id).where(Document.user_id == user.id)
    ).all()
    if not rows:
        raise HTTPException(400, "No documents ingested yet. Upload first.")

    scored = [(cosine_sim(q_emb, np.frombuffer(r.embedding, dtype=np.float32)), r) for r in rows]
    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[: payload.top_k]

    sources = [
        {
            "document_id": r.document_id,
            "filename": r.document.filename,
            "page": r.page,
            "url": f"/api/documents/{r.document_id}/download",  # <-- protected
            "text": (r.text or ""),
        }
        for _, r in top
    ]

    carry = (payload.prev_context or "").strip()
    if carry:
        carry = carry[-4000:]
        sources = ([{"document_id": 0, "filename": "previous-context", "page": None, "text": carry}] + sources)

    history = _normalize_history(payload.history)

    def gen():
        for chunk in stream_answer_with_groq(payload.question, sources, history=history):
            yield chunk

    return StreamingResponse(gen(), media_type="text/plain")
