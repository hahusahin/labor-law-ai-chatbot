# Turkish Labour Law (İş Kanunu) AI Assistant

A RAG-based question-answering app over Turkish labour law legislation. Ask a question in natural language, get an answer grounded in the actual law — with the source article shown and expandable.

**Live demo:** [labor-law-ai-chatbot.vercel.app](https://labor-law-ai-chatbot.vercel.app)

---

## What it does

Users ask questions like *"Yıllık iznim kaç gün?"* or *"Kıdem tazminatı nasıl hesaplanır?"* and get answers that cite the specific article from the İş Kanunu. The source reference is clickable — you can read the original article text right in the UI. No hallucinated answers without backing.

## How it works (RAG pipeline)

1. Turkish labour law legislation is pre-chunked by article and embedded with **Gemini embeddings** into **Pinecone**
2. When a question comes in, it's embedded the same way and matched against the stored vectors
3. The top matching articles are passed as context to **Gemini API**, which generates the answer
4. The answer and source chunks (with article numbers) are returned to the frontend

## Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 16 (App Router), TypeScript, Tailwind CSS |
| AI service | Python, FastAPI |
| Embeddings | Gemini (`gemini-embedding-001`) |
| LLM | Gemini 3.1 |
| Vector DB | Pinecone |
| Local dev | Docker Compose |
| Deploy | Vercel (frontend) + Render (AI service) |

## Architecture

```
Browser → Vercel (Next.js)
           └─ /api/chat  ──→  Render (FastAPI)
                                ├─ EmbeddingService  → Gemini API
                                ├─ VectorRepository  → Pinecone
                                └─ LLMService        → Gemini API
```

The FastAPI service is layered (routes → services → repositories) with the vector DB abstracted behind an interface — swap Pinecone for another store without touching business logic.

## What's next

- **Phase 1.5 — Evaluation:** build a test set of 15–20 (question → expected article) pairs and measure retrieval hit rate and answer correctness.
- **Phase 2:** hybrid search, reranking, query rewriting, SSE streaming — and show the eval score improving between phases.

## Running locally

```bash
# Copy and fill in env vars
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local

# Start both services
docker compose up
```

Open [localhost:3000](http://localhost:3000).
