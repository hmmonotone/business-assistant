# Business AI — MVP (RAG)

A minimal but polished **Business Knowledge Assistant** you can run locally.
Upload PDFs/DOCX/TXT/images, ask questions, and get grounded answers with **citations**. Includes onboarding, auth, multi-file upload, protected downloads, chat with short history, and a deterministic weekly-revenue parser for table screenshots.

---

## ✨ Features

* Friendly onboarding + email/password **auth** (JWT).
* **Multi-file upload** (PDF, DOCX, TXT/MD, PNG/JPG/…).
* Image **OCR** (for tables & receipts) and text extraction.
* Chunking + **embeddings** stored in SQLite via SQLAlchemy.
* RAG answers with **Groq** LLM (`GROQ_MODEL`), bracket citations **\[1]**.
* **Source chips** in UI (click to download original, protected).
* Streaming answer endpoint.
* **Deterministic “weekly revenue”** calculator from OCR’d month tables (e.g., “3rd week of April?”).
* Document list with delete; **Delete Account** (hard-deletes user + files).
* Clean React + Tailwind UI (cards, glass header, icons).

---

## 🧱 Stack

* **Server:** FastAPI, SQLAlchemy + SQLite, JWT, Pydantic, (optional) Tesseract OCR
* **LLM:** Groq API (e.g., `llama3-70b-8192`)
* **Frontend:** React + TypeScript + Vite, TailwindCSS (+ Typography/Forms), lucide-react icons, react-markdown

---

## 📁 Project Structure

```
business-ai-mvp/
├─ server/
│  ├─ app/
│  │  ├─ main.py          # routes, auth, ask() RAG, streaming, protected download
│  │  ├─ auth.py          # JWT utilities
│  │  ├─ db.py            # SQLAlchemy engine/session
│  │  ├─ models.py        # User, Document, Chunk
│  │  ├─ schemas.py       # Pydantic request/response models
│  │  ├─ ingest.py        # extract & chunk; embed_texts; OCR for images
│  │  ├─ llm.py           # Groq client, prompts, streaming
│  │  └─ utils.py         # hashing, revenue-table parser (extract/resolve/aggregate)
│  ├─ requirements.txt
│  └─ .env.example
└─ web/
   ├─ index.html
   ├─ package.json
   ├─ postcss.config.js
   ├─ tailwind.config.js
   └─ src/
      ├─ main.tsx         # mounts app & imports styles.css
      ├─ App.tsx          # shell, header, routing (Dashboard/Chat)
      ├─ styles.css       # Tailwind + custom utility classes
      ├─ lib/api.ts       # api(), apiDownload(), upload(), API_BASE
      ├─ store/auth.ts
      ├─ components/
      │  ├─ Onboarding.tsx
      │  ├─ AuthCard.tsx
      │  ├─ FileUploader.tsx
      │  ├─ FileList.tsx
      │  └─ ChatPanel.tsx
      └─ pages/
         ├─ Dashboard.tsx
         └─ Chat.tsx
```

---

## ⚙️ Prerequisites

* **Python 3.11 or 3.12** (avoid 3.13 due to build issues with `pydantic-core`).
* Node 18+ / PNPM or NPM.
* (Optional) **Tesseract** for OCR (macOS `brew install tesseract`).

---

## 🚀 Quickstart

### 1) Backend

```bash
cd server
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env`:

```ini
# server/.env
JWT_SECRET=replace_me_with_random_32_chars
GROQ_API_KEY=sk-your-key
GROQ_MODEL=llama3-70b-8192
STORAGE_DIR=./storage
CORS_ORIGINS=http://localhost:5173
```

Run the API:

```bash
uvicorn app.main:app --reload --port 8000
```

Open API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

### 2) Frontend

```bash
cd web
npm i
# optional but recommended
echo "VITE_API_BASE=http://localhost:8000" > .env
npm run dev
```

Open UI: [http://localhost:5173](http://localhost:5173)

> First run: Register, then upload a few files. Try an image table for April revenue and a feedback doc.

---

## 🔐 Auth & Security

* JWT is returned on login/register and sent via `Authorization: Bearer <token>`.
* Uploaded files are **not** exposed publicly.
  Downloads go through: `GET /api/documents/{doc_id}/download` (auth-checked).
* “Delete account” requires password and **hard-deletes** user, docs, chunks, and disk files.

---

## 📤 Ingestion & Retrieval

* **Supported:** `pdf`, `docx`, `txt`, `md`, images (`png`, `jpg`, `jpeg`, `webp`, `bmp`, `tif`, …).
* **Images:** OCR via Tesseract (configured in `ingest.py`), preserving table spacing (`--psm 6`).
* **Chunking:** Simple fixed-size text chunks with slight overlap.
* **Embeddings:** Stored per chunk in DB (as `float32` bytes).
* **Retrieval:** Cosine similarity over normalized embeddings (`top_k` configurable).

### Weekly Revenue Smart Path

For queries like “**3rd week of April revenue?**”:

1. Regular Top-K chunks are fetched.
2. If they don’t contain all rows for that week, the server **expands** context by scanning chunks that contain the month string (e.g., `-04-`), ensuring full coverage of the month table.
3. A deterministic parser reads `YYYY-MM-DD` + `$amount` pairs, resolves the requested week, and returns totals + daily bullets with proper citations.

---

## 🧠 LLM & Citations

* Prompt instructs the model to **use only provided context**.
* Context is numbered; answers include bracket citations **\[1]**, **\[2]**.
* UI renders “source chips” (filename + optional page) and a **download** action (auth-guarded).

---

## 🖥️ UI Notes

* **Dashboard:** drag-and-drop multi-file upload, file list with size + delete.
* **Chat:** suggestions, markdown rendering, copy button, source chips with download.
* **Header:** glass effect, segmented tabs, logout & **Delete account**.

---

## 🧪 API Reference (selected)

### Auth

* `POST /api/auth/register` → `{ token, user }`
* `POST /api/auth/login` → `{ token, user }`
* `GET  /api/auth/profile` → `{ id, email }`
* `POST /api/auth/delete-account` → `{ ok: true }` (requires `{ password }`)

### Documents

* `POST /api/documents/upload` (form field: `file`)
* `POST /api/documents/upload/batch` (form field(s): `files`)
* `GET  /api/documents` → list user docs
* `DELETE /api/documents/{id}`
* `GET  /api/documents/{id}/download` (auth-checked)

### Knowledge

* `POST /api/knowledge/ask`

  ```json
  {
    "question": "3rd week of April revenue?",
    "top_k": 6,
    "prev_context": "optional last context text",
    "history": [{"role":"user","content":"..."},{"role":"assistant","content":"..."}]
  }
  ```

  → `{ "answer": "...", "sources": [{ "filename":"...", "page":3, "url":"/api/documents/1/download" }] }`

* `POST /api/knowledge/ask/stream` → `text/plain` chunked stream

---

## 🔧 Configuration

Environment (server):

* `JWT_SECRET` – random string for signing tokens
* `GROQ_API_KEY` – your Groq key
* `GROQ_MODEL` – e.g., `llama3-70b-8192`
* `STORAGE_DIR` – where uploads are stored
* `CORS_ORIGINS` – comma-separated allowed origins

Environment (web):

* `VITE_API_BASE` – e.g., `http://localhost:8000`

---

## 🧩 Sample Questions

* “Summarize April revenue in bullets with citations.”
* “3rd week of April revenue?”
* “Which day in April had the highest sales?”
* “Top 3 customer complaints with quotes and sources.”
* “Extract positive feedback themes with examples.”

---

## 🛟 Troubleshooting

* **`uvicorn: command not found`** → `pip install -r requirements.txt` inside the venv.
* **Pydantic/pyo3 build error on Python 3.13** → use **Python 3.11/3.12**.
* **Source links open on 5173 & 404** → we use **protected download**; front-end calls `/api/documents/{id}/download` with Bearer (already implemented).
* **Vite/Tailwind “prose class does not exist”** → `npm i -D @tailwindcss/typography` and add it to `tailwind.config.js` (or remove the `prose` apply).
* **Citations show `Doc 0:?`** → already replaced by numbered sources + UI chips via `llm.build_context()`.
* **3rd-week revenue returns “unknown”** → fixed via month-expansion fallback in `ask()` (ensures all rows are parsed).

---

## 🗺️ Roadmap (easy wins)

* Dark mode + theme toggle.
* CSV/XLSX ingestion → structured QA.
* Reranking (e.g., cross-encoder) after vector search.
* Conversational memory w/ session titles & export.
* Connectors (Drive/Slack/Notion) with per-space access control.
* Dockerfiles for one-command dev.

---


## 🙌 Credits

Built with FastAPI + React + Tailwind and powered by Groq LLMs.
