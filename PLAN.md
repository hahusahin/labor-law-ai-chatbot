# İş Hukuku Chatbot — Build Planı

Buradaki her görev bitince `- [ ]` → `- [x]` yapıyoruz.

---

## Klasör Yapısı (Hedef)

```
22-is-hukuku-chatbot/
├── frontend/          ← Next.js (TypeScript)
│   ├── src/app/
│   │   ├── page.tsx           (tam ekran chat UI)
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
│   ├── scripts/ingest.py      (offline CLI, bir kez çalışır)
│   ├── requirements.txt
│   └── .env.example
├── docker-compose.yml
├── .gitignore
├── CLAUDE.md
└── PLAN.md  ← bu dosya
```

---

## Phase 1 — Çalışan Naive RAG

### Blok 1 — Repo & Git

- [x] **1.1** `git init` + `frontend/` ve `backend/` klasörleri + `.gitignore`
- [x] **1.2** İlk commit — "chore: init repo structure"

### Blok 2 — Backend Kurulumu

- [x] **2.1** Python sanal ortam (`.venv`) + `requirements.txt` + paket kurulumu
- [ ] **2.2** `backend/main.py` — FastAPI app + `/health` endpoint + CORS
- [ ] **2.3** `backend/core/config.py` — Pydantic Settings, `.env` okuma
- [ ] **2.4** `backend/models/schemas.py` — `QueryRequest`, `QueryResponse`, `SourceChunk`
- [ ] **2.5** `backend/core/errors.py` — `RetryableError`, `NonRetryableError`

> Doğrulama: `GET http://localhost:8000/health` → `{"status": "ok"}`

### Blok 3 — Repository Katmanı

- [ ] **3.1** `backend/repositories/vector_repository.py` — abstract class + `PineconeRepository`

### Blok 4 — Services Katmanı

- [ ] **4.1** `backend/services/embedding_service.py` — Gemini embeddings
- [ ] **4.2** `backend/services/llm_service.py` — Gemini 2.5 Flash + retry/backoff (tenacity)

### Blok 5 — İngest Script

- [ ] **5.1** Pinecone hesabı + index + API key (sen açarsın, biz yönlendiririz)
- [ ] **5.2** Gemini API key (Google AI Studio, kredi kartı yok)
- [ ] **5.3** `backend/scripts/ingest.py` — madde-bazlı chunking → embed → Pinecone'a yaz
- [ ] **5.4** İlk ingest çalıştır + Pinecone konsolunda vektörleri doğrula

> Doğrulama: Pinecone dashboard'da vektörler görünür

### Blok 6 — Query Endpoint

- [ ] **6.1** `backend/routes/query.py` — `/query` POST endpoint (embed → retrieve → LLM → yanıt)
- [ ] **6.2** Manuel test: Postman / curl ile `/query` dene → gerçek yanıt gelir

> Doğrulama: `POST /query {"question":"Yıllık izin kaç gün?"}` → kaynaklı yanıt

### Blok 7 — Frontend

- [ ] **7.1** `npx create-next-app@latest frontend` (TypeScript + Tailwind + App Router)
- [ ] **7.2** `frontend/src/app/api/chat/route.ts` — thin gateway (Next.js → FastAPI proxy)
- [ ] **7.3** `frontend/src/app/page.tsx` — tam ekran chat UI (boş durum + örnek sorular + loading)
- [ ] **7.4** Kaynak madde chip'i — her yanıtta "İş Kanunu Madde 53" → tıklayınca madde metni açılır

### Blok 8 — Docker Compose

- [ ] **8.1** `docker-compose.yml` — frontend (3000) + backend (8000) iç ağda
- [ ] **8.2** `docker compose up` ile uçtan uca test

> Doğrulama: `http://localhost:3000` açılır, soru yazılır, kaynak maddeli yanıt gelir ✓

---

## Phase 1.5 — Evaluation

- [ ] **9.1** 15–20 `(soru → beklenen madde)` test çifti JSON dosyası
- [ ] **9.2** `backend/scripts/evaluate.py` — retrieval hit rate ölçümü
- [ ] **9.3** Yanıt doğruluğu skoru + rapor

---

## Phase 2 — Advanced RAG

- [ ] Hybrid search (dense + sparse BM25)
- [ ] Reranking
- [ ] Query rewriting
- [ ] SSE streaming
- [ ] Eval skoru Phase 1.5 vs Phase 2 karşılaştırması

---

## Deploy (Phase 1 bittikten sonra)

- [ ] Render'a backend deploy (`backend/` root dir, env vars)
- [ ] Vercel'e frontend deploy (`frontend/` root dir, `AI_SERVICE_URL=<render-url>`)

---

## Notlar

- Her terminal komutunu **sen çalıştırırsın**, biz adım adım yönlendiririz
- Her görevde ilgili Python / FastAPI / design-pattern kavramını öğretiyoruz
- Çalışan çirkin > mükemmel ama çalışmayan
