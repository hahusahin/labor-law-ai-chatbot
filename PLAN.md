# Labour Law Chatbot — Build Plan

Mark each task `- [ ]` → `- [x]` only after explicit developer approval.

---

## Target Folder Structure

```
22-is-hukuku-chatbot/
├── frontend/          ← Next.js (TypeScript)
│   ├── src/app/
│   │   ├── page.tsx           (full-page chat UI)
│   │   └── api/chat/route.ts  (thin gateway → FastAPI)
│   ├── package.json
│   └── ...
├── backend/           ← Python FastAPI
│   ├── main.py
│   ├── routes/query.py
│   ├── services/
│   │   ├── embedding_service.py
│   │   └── llm_service.py
│   ├── repositories/vector_repository.py
│   ├── core/
│   │   ├── config.py
│   │   └── errors.py
│   ├── models/schemas.py
│   ├── scripts/ingest.py      (offline CLI, run once)
│   ├── requirements.txt
│   └── .env.example
├── docker-compose.yml
├── .gitignore
├── CLAUDE.md
└── PLAN.md  ← this file
```

---

## Phase 1 — Working Naive RAG

### Block 1 — Repo & Git

- [x] **1.1** `git init` + `frontend/` and `backend/` folders + `.gitignore`
- [x] **1.2** First commit — "chore: init repo structure"

### Block 2 — Backend Setup

- [x] **2.1** Python virtual environment (`.venv`) + `requirements.txt` + package install
- [x] **2.2** `backend/main.py` — FastAPI app + `/health` endpoint + CORS
- [x] **2.3** `backend/core/config.py` — Pydantic Settings, `.env` reading
- [x] **2.4** `backend/models/schemas.py` — `QueryRequest`, `QueryResponse`, `SourceChunk`
- [x] **2.5** `backend/core/errors.py` — `RetryableError`, `NonRetryableError`

> Verification: `GET http://localhost:8000/health` → `{"status": "ok"}`

### Block 3 — Repository Layer

- [x] **3.1** `backend/repositories/vector_repository.py` — abstract class + `PineconeRepository`

### Block 4 — Services Layer

- [ ] **4.1** `backend/services/embedding_service.py` — Gemini embeddings
- [ ] **4.2** `backend/services/llm_service.py` — Gemini 2.5 Flash + retry/backoff (tenacity)

### Block 5 — Ingest Script

- [ ] **5.1** Pinecone account + index + API key (developer sets up, we guide)
- [ ] **5.2** Gemini API key (Google AI Studio, no credit card)
- [ ] **5.3** `backend/scripts/ingest.py` — article-aware chunking → embed → write to Pinecone
- [ ] **5.4** Run first ingest + verify vectors in Pinecone console

> Verification: vectors visible in Pinecone dashboard

### Block 6 — Query Endpoint

- [ ] **6.1** `backend/routes/query.py` — `/query` POST endpoint (embed → retrieve → LLM → response)
- [ ] **6.2** Manual test via Postman / curl → real answer comes back

> Verification: `POST /query {"question":"How many days annual leave?"}` → answer with sources

### Block 7 — Frontend

- [ ] **7.1** `npx create-next-app@latest frontend` (TypeScript + Tailwind + App Router)
- [ ] **7.2** `frontend/src/app/api/chat/route.ts` — thin gateway (Next.js → FastAPI proxy)
- [ ] **7.3** `frontend/src/app/page.tsx` — full-page chat UI (empty state + example questions + loading)
- [ ] **7.4** Source article chip — each answer shows "Labour Law Article 53" → click reveals article text

### Block 8 — Docker Compose

- [ ] **8.1** `docker-compose.yml` — frontend (3000) + backend (8000) on internal network
- [ ] **8.2** End-to-end test with `docker compose up`

> Verification: `http://localhost:3000` opens, question is typed, sourced answer comes back ✓

---

## Phase 1.5 — Evaluation

- [ ] **9.1** 15–20 `(question → expected article)` test pairs as a JSON file
- [ ] **9.2** `backend/scripts/evaluate.py` — retrieval hit rate measurement
- [ ] **9.3** Answer correctness score + report

---

## Phase 2 — Advanced RAG

- [ ] Hybrid search (dense + sparse BM25)
- [ ] Reranking
- [ ] Query rewriting
- [ ] SSE streaming
- [ ] Eval score comparison Phase 1.5 vs Phase 2

---

## Deploy (after Phase 1 is complete)

- [ ] Deploy backend to Render (`backend/` root dir, env vars)
- [ ] Deploy frontend to Vercel (`frontend/` root dir, `AI_SERVICE_URL=<render-url>`)

---

## Working Rules

- Every terminal command is **run by the developer**, guided step by step
- Each task teaches the relevant Python / FastAPI / design-pattern concept
- Working and ugly > perfect but broken
- **A task is marked done only after the developer explicitly approves it**
