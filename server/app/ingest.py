import io, os, json
from typing import Iterable, Tuple, Optional
import numpy as np
from pypdf import PdfReader
import docx
from sentence_transformers import SentenceTransformer
import pytesseract
from PIL import Image, ImageOps, ImageFilter

TESSERACT_CMD_DEFAULT = "/opt/homebrew/bin/tesseract"
if os.path.exists(TESSERACT_CMD_DEFAULT):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD_DEFAULT


def _preprocess_image(img: Image.Image) -> Image.Image:
    g = ImageOps.grayscale(img)
    g = ImageOps.autocontrast(g)
    g = g.filter(ImageFilter.SHARPEN)
    # Upscale a bit to help digits
    w, h = g.size
    if w < 1400:
        g = g.resize((int(w * 1.5), int(h * 1.5)))
    return g


def extract_text_image(path: str) -> str:
    try:
        img = Image.open(path)
    except Exception:
        return ""
    img = _preprocess_image(img)
    # LSTM engine, assume uniform block of text/table, preserve spaces
    cfg = "--oem 3 --psm 6 -c preserve_interword_spaces=1"
    return pytesseract.image_to_string(img, config=cfg) or ""


EMB_MODEL_NAME = os.getenv("EMB_MODEL", "all-MiniLM-L6-v2")
_embedder = None


def get_embedder():
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer(EMB_MODEL_NAME)
    return _embedder


# -------- extractors --------

def extract_text_pdf(path: str) -> Tuple[str, list]:
    pages = []
    with open(path, "rb") as f:
        reader = PdfReader(f)
        for i, p in enumerate(reader.pages):
            pages.append((i + 1, p.extract_text() or ""))
    full = "\n\n".join(t for _, t in pages)
    return full, pages


def extract_text_docx(path: str) -> str:
    d = docx.Document(path)
    return "\n".join([p.text for p in d.paragraphs])


def extract_text_plain(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def _preprocess_image(img: Image.Image) -> Image.Image:
    # basic, fast pre-processing for better OCR
    g = ImageOps.grayscale(img)
    g = ImageOps.autocontrast(g)
    g = g.filter(ImageFilter.SHARPEN)
    return g


def extract_text_image(path: str) -> str:
    try:
        img = Image.open(path)
    except Exception:
        return ""
    img = _preprocess_image(img)
    # You can pass lang="eng" explicitly if you have other languages
    text = pytesseract.image_to_string(img)  # , lang="eng"
    return text or ""


# -------- chunking --------

def chunk_text(text: str, max_tokens: int = 900, overlap: int = 120) -> Iterable[str]:
    # token-agnostic: ~4 chars per token
    size = max_tokens * 4
    step = size - (overlap * 4)
    i = 0
    n = len(text)
    while i < n:
        yield text[i: i + size]
        i += max(step, 1)


# -------- embeddings --------

def embed_texts(texts: Iterable[str]) -> np.ndarray:
    model = get_embedder()
    embs = model.encode(list(texts), normalize_embeddings=True)  # cosine-ready
    return np.array(embs, dtype=np.float32)


# -------- controller --------

IMAGE_EXTS = {"png", "jpg", "jpeg", "webp", "bmp", "tif", "tiff"}


def extract_and_chunk(path: str, filename: str):
    ext = filename.lower().rsplit(".", 1)[-1]
    pages_meta = None

    if ext == "pdf":
        full, pages = extract_text_pdf(path)
        pages_meta = pages
        text = full
    elif ext in ("docx",):
        text = extract_text_docx(path)
    elif ext in IMAGE_EXTS:
        text = extract_text_image(path)
    else:
        text = extract_text_plain(path)

    # Guard against empty OCR/plain results to avoid empty chunk embeddings
    if not text.strip():
        text = "(No extractable text found)"

    chunks = list(chunk_text(text))
    embeddings = embed_texts(chunks)

    # crude page mapping (PDF only); images/docs return None
    page_map = []
    if pages_meta:
        offsets = []
        total = 0
        for (pg, t) in pages_meta:
            offsets.append((pg, total, total + len(t)))
            total += len(t) + 2  # \n\n between pages
        size = 900 * 4
        step = size - (120 * 4)
        for i, ch in enumerate(chunks):
            idx = i * step
            pg = next((pg for (pg, s, e) in offsets if s <= idx < e), None)
            page_map.append(pg)
    else:
        page_map = [None] * len(chunks)

    return chunks, embeddings, page_map
