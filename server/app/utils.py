import hashlib
from passlib.context import CryptContext
import re, calendar
from datetime import date, timedelta
from typing import List, Tuple, Dict, Optional
from .models import Chunk, Document

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

_ROW = re.compile(
    r"(?P<date>20\d{2}-\d{2}-\d{2}).{0,80}?\$?(?P<rev>\d{1,3}(?:,\d{3})*(?:\.\d{2}))",
    flags=re.MULTILINE
)
_MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12
}


def extract_revenue_records(text: str) -> List[Tuple[date, float]]:
    out: List[Tuple[date, float]] = []
    for m in _ROW.finditer(text):
        y, mth, d = (int(m.group("date")[0:4]),
                     int(m.group("date")[5:7]),
                     int(m.group("date")[8:10]))
        val = float(m.group("rev").replace(",", ""))
        out.append((date(y, mth, d), val))
    return out


def _guess_year_month_from_records(records: List[Tuple[date, float]], month: int | None) -> Tuple[int, int]:
    if month is not None:
        # pick the most frequent year for that month
        by_year: Dict[int, int] = {}
        for dt, _ in records:
            if dt.month == month:
                by_year[dt.year] = by_year.get(dt.year, 0) + 1
        if by_year:
            year = max(by_year.items(), key=lambda x: x[1])[0]
            return year, month
    # fallback: pick latest month in data
    if records:
        latest = max(dt for dt, _ in records)
        return latest.year, latest.month
    # final fallback
    today = date.today()
    return today.year, today.month


def resolve_week_range(question: str, records: List[Tuple[date, float]]) -> Optional[Tuple[date, date]]:
    q = question.lower()

    # month in question?
    month = None
    for name, num in _MONTHS.items():
        if name in q:
            month = num
            break

    year, month = _guess_year_month_from_records(records, month)

    # first/last/ordinal week
    which = "first" if "first week" in q or "1st week" in q else \
        "last" if "last week" in q else None
    if which is None and "week of" in q and "april" in q:
        # heuristic: if they say "week of <date>", parse it; omitted for brevity
        pass

    if month is None:
        return None

    _, last_day = calendar.monthrange(year, month)

    if which == "first":
        start, end = date(year, month, 1), date(year, month, 7)
    elif which == "last":
        start, end = date(year, month, last_day - 6), date(year, month, last_day)
    else:
        # if they asked just “week of <YYYY-MM-DD>” you could resolve here
        return None

    return start, end


def aggregate_week(records: List[Tuple[date, float]], start: date, end: date) -> Dict:
    days = [(dt, val) for dt, val in records if start <= dt <= end]
    total = round(sum(val for _, val in days), 2)
    avg = round(total / len(days), 2) if days else 0.0
    return {"total": total, "avg": avg, "days": days}


def hash_password(p: str) -> str:
    return pwd_ctx.hash(p)


def verify_password(p: str, h: str) -> bool:
    return pwd_ctx.verify(p, h)


def file_sha256(fp) -> str:
    sha = hashlib.sha256()
    for chunk in iter(lambda: fp.read(8192), b""):
        sha.update(chunk)
    fp.seek(0)
    return sha.hexdigest()


def mmr_select(candidates, embeddings, k=4, lambda_mult=0.7):
    selected, selected_idx = [], []
    if not candidates: return []
    selected_idx.append(0);
    selected.append(candidates[0])
    import numpy as np
    emb = np.stack(embeddings)
    for _ in range(1, min(k, len(candidates))):
        best, best_i, best_score = None, None, -1
        for i in range(len(candidates)):
            if i in selected_idx: continue
            sim_to_query = float(np.dot(emb[0], emb[i]))
            sim_to_selected = max(float(np.dot(emb[i], emb[j])) for j in selected_idx)
            score = lambda_mult * sim_to_query - (1 - lambda_mult) * sim_to_selected
            if score > best_score: best, best_i, best_score = candidates[i], i, score
        selected_idx.append(best_i);
        selected.append(best)
    return selected


def find_month_sources(db, user_id: int, year: int, month: int, limit: int = 80):
    pattern = f"{year}-{month:02d}-"
    rows = (db.query(Chunk, Document)
            .join(Document, Document.id == Chunk.document_id)
            .filter(Document.user_id == user_id,
                    Chunk.text.contains(pattern))
            .limit(limit)
            .all())
    sources = []
    for ch, doc in rows:
        sources.append({
            "document_id": doc.id,
            "filename": doc.filename,
            "page": ch.page,
            "text": ch.text or ""
        })
    return sources
