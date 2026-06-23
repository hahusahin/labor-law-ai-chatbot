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

- [x] **4.1** `backend/services/embedding_service.py` — Gemini embeddings
- [x] **4.2** `backend/services/llm_service.py` — Gemini 2.5 Flash + retry/backoff (tenacity)

### Block 5 — Ingest Script

- [x] **5.1** Pinecone account + index + API key (developer sets up, we guide)
- [x] **5.2** Gemini API key (Google AI Studio, no credit card)
- [x] **5.3** `backend/scripts/ingest.py` — article-aware chunking → embed → write to Pinecone
- [x] **5.4** Run first ingest + verify vectors in Pinecone console

> Verification: vectors visible in Pinecone dashboard

### Block 6 — Query Endpoint

- [x] **6.1** `backend/routes/query.py` — `/query` POST endpoint (embed → retrieve → LLM → response)
- [x] **6.2** Manual test via Postman / curl → real answer comes back

> Verification: `POST /query {"question":"How many days annual leave?"}` → answer with sources

### Block 7 — Frontend

- [x] **7.1** `npx create-next-app@latest frontend` (TypeScript + Tailwind + App Router)
- [x] **7.2** `frontend/src/app/api/chat/route.ts` — thin gateway (Next.js → FastAPI proxy)
- [x] **7.3** `frontend/src/app/page.tsx` — full-page chat UI (empty state + example questions + loading)
- [x] **7.4** Source article chip — each answer shows "Labour Law Article 53" → click reveals article text

### Block 8 — Security + Docker Compose

- [x] **8.1** Shared API key middleware — FastAPI rejects requests without `X-API-Key`; Next.js gateway sends it
- [x] **8.2** `docker-compose.yml` — frontend (3000) + backend (8000) on internal network
- [x] **8.3** End-to-end test with `docker compose up`

> Verification: `http://localhost:3000` opens, question is typed, sourced answer comes back ✓

---

## Phase 1.5 — Evaluation

- [x] **9.1** 15–20 `(question → expected article)` test pairs as a JSON file
- [x] **9.2** `backend/eval/evaluate_retrieval.py` — retrieval hit rate measurement (recall@k + off-topic score distribution)
- [x] **9.3** `backend/eval/evaluate_answers.py` — LLM-as-judge answer correctness + citation + off-topic abstention
- [x] **9.4** Relevance threshold (abstention) — gate retrieval by similarity `min_score`; off-topic
      questions return the "not enough info" answer with **zero** sources (today top-k always returns
      5 chunks, so irrelevant questions still show 5 misleading source chips). Inspect real score
      distributions (relevant vs off-topic) and tune the cutoff from eval data — do NOT hardcode a
      magic number. Fixes both backend (no junk context to LLM) and UI (no junk chips) in one change.

---

## Phase 2 — SSE Streaming

### Block 10 — SSE Streaming

- [x] **10.1** Design the SSE event protocol (sources event → token events → done event); document
      the shape in this file. Keep the existing non-streaming `/query` for eval + as a fallback.

  **Protocol** — each SSE frame is one line `data: <json>\n\n`. Order: one `sources` → many
  `token` → one `done`. On failure mid-stream: an `error` frame. Off-topic = `sources` with `[]`
  then the abstention text as tokens (frontend needs no special-case).
  ```
  data: {"type":"sources","sources":[{"law":"İş Kanunu","article_number":53,"text":"..."}]}
  data: {"type":"token","text":"Yıllık "}
  data: {"type":"done"}
  data: {"type":"error","message":"..."}
  ```
- [x] **10.2** Backend `LLMService.generate_stream()` — Gemini streaming
      (`generate_content_stream`). Keep `generate()` untouched so eval stays honest.
- [ ] **10.3** Refactor `routes/query.py` — extract shared retrieval + abstention logic so both the
      streaming and non-streaming paths reuse it (no duplicated retrieval/threshold code).
- [ ] **10.4** Backend `/query/stream` route — `StreamingResponse` (`text/event-stream`):
      retrieve → emit sources event → stream answer tokens → emit done. Abstention → stream the
      "not in scope" answer with zero sources.
- [ ] **10.5** Gateway `/api/chat` — pass the upstream stream straight through (no buffering),
      forward `text/event-stream`.
- [ ] **10.6** Frontend — consume the stream (`response.body.getReader()`), render tokens
      incrementally, show the source chip first, keep the ~30s timeout + error handling.
- [ ] **10.7** Manual end-to-end test + README note (streaming UX).

### Deferred (documented, not built) — revisit only if the corpus/eval changes

- [ ] Hybrid search (dense + sparse BM25) — deferred: retrieval already near-ceiling
- [ ] Reranking — deferred: would target the 4 rank-2 hits, but too few to measure honestly
- [ ] Query rewriting — deferred: would target the 1 reasoning miss (id 5), not worth the metric noise
- [ ] (Optional Phase 1.5 refinement) Per-article *coverage* recall for multi-part questions

---

## Deploy

- [x] Deploy backend to Render (`backend/` root dir, env vars)
- [x] Deploy frontend to Vercel (`frontend/` root dir, `AI_SERVICE_URL=<render-url>`) — live at
      labor-law-ai-chatbot.vercel.app

---

## Working Rules

- Every terminal command is **run by the developer**, guided step by step
- Each task teaches the relevant Python / FastAPI / design-pattern concept
- Working and ugly > perfect but broken
- **A task is marked done only after the developer explicitly approves it**
