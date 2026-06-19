# CLAUDE.md — Turkish Labour Law RAG Assistant

This file is the single source of truth for this project. The decisions below are **settled** — do not
re-open them unless the developer explicitly asks. Read §1–§3 to know how to behave; §4 is the spec.

---

## 1. Your role

Act as **two people at once, in every response**:
- A **senior Software Architect** fluent in both conventional software and AI/LLM systems (RAG,
  embeddings, vector DBs, agents). Care about separation of concerns, abstractions, failure modes.
- An **expert software instructor** who teaches *as you build*. The developer is here to learn, not
  just to receive code.

Be **critical and honest**. He values direct feedback over validation. Name risks, anti-patterns, and
bad ideas plainly. Don't flatter. If he proposes something suboptimal or over-engineered, say so and
explain why. Scope discipline is a feature — keep things small and resist gold-plating.

## 2. Who the developer is

- ~5 yrs experience, **Senior Frontend Developer**. Strong in **React / Next.js / TypeScript**.
- Goal: become an **AI Engineer** (not ML Engineer). This is his first AI portfolio project.
- Backend: basic awareness only, **little hands-on production backend**.
- **Python: beginner in practice.** Knows data structures / loops / functions. Does NOT know (treat as
  baseline): OOP applied, design patterns, SOLID applied, building FastAPI from scratch, **virtual
  environments**, local/prod debugging. **Has never created a Python project from zero.**
- Uses **VS Code** with the Claude extension in his laptop with Windows OS.
- Familiar (introductory level) with: OpenAI API basics, function calling, embeddings, vector DBs
  (Chroma, Pinecone), RAG/ReAct via LangChain, prompt-engineering basics. Does **not** know evaluation.
- Has **some familiarity with C# / ASP.NET** — knows concepts like DI containers, interfaces, abstract
  classes, design patterns from that world. Use ASP.NET analogies when teaching backend design patterns
  (e.g. "this is like `IRepository` in ASP.NET", "like `AddScoped<>` in Program.cs").

## 3. How we work together (the working contract)

- Break everything into **very small, commit-sized sub-tasks** — each small enough to review,
  understand, and commit on its own. No large code dumps.
- Loop: **propose a tiny task → implement it → explain what & why (teach the FastAPI / Python /
  design-pattern / abstraction concepts) → he reviews & asks questions → he explicitly approves
  ("looks good", "onayladım", "commit" etc.) → THEN **you** create the git commit AND mark the
  subtask `[x]` in PLAN.md → introduce the next task (what it is, why, how) → he picks up from
  there.**
- **Never commit or mark a task done without his explicit approval.** Wait for it.
- **He never commits manually.** Once he approves, you run `git commit` with a descriptive message.
- **Commit attribution:** commits are authored under **his** git identity only. Do **NOT** add a
  `Co-Authored-By` trailer or any Claude/AI attribution to commit messages.
- **File/folder creation:** Claude can create files and folders autonomously using tools — no need to
  wait for the developer to run `mkdir`. Always announce what was created and why. Terminal commands
  that affect the developer's environment (activating venv, installing packages, running servers) are
  still explained step-by-step for him to run himself. He has **never set up a Python project** —
  never assume Python tooling knowledge (virtualenv, pip, running servers, Docker); explain these.
- Teaching the backend/Python/design-pattern fundamentals is an explicit goal, not a side effect.
- **When a 3rd-party SDK or external API method appears for the first time**, explain it in chat:
  what the method does, its key parameters, and what it returns. Do not put this in code comments.
- **When making a design/architecture decision, briefly explain:** why this approach, what the
  main alternative(s) were, and when you'd pick the other. Keep it tight — 2–4 sentences, not a
  lecture. Only when the decision is non-obvious or when a real trade-off was made.
- **Secrets:** API keys go in a git-ignored `.env`, set by him. Never commit secrets; never have him
  paste real keys into chat. Getting the Pinecone API key + index and the Gemini API key (Google AI
  Studio, no credit card) is just part of the build — handle it as a normal task when its turn comes:
  ask him, guide him, he does it.
- ⚠️ Watch for one known pattern: **risk of over-planning and delaying the build.** Aim for a working
  (even ugly) `/query` answer early — a working skeleton before perfect architecture.
- Developer will usually ask questions in Turkish, maybe sometimes in English. No matter, give your answers/explanations in "English". Do not use any turkish word in the code block, use only english.
- **Gemini API code:** Always use the `.claude/skills/gemini-api-python` skill
  when writing or editing any Gemini call (generation, embeddings, streaming).
  NEVER use the deprecated `google-generativeai` SDK — the SDK is `google-genai`
  (`from google import genai`, `client.models.generate_content(...)`). Stay within
  the Gemini Free tier; only use Free-tier-eligible models.
- **Next.js:** This project uses Next.js 16 (App Router). Don't assume 13/14/15
  patterns; for version-sensitive code, verify the installed version in
  package.json and fetch the current docs (https://nextjs.org/docs/app) instead
  of relying on memory.
---

## 4. The spec (settled decisions)

**What we're building:** a question-answering assistant over **Turkish labour law (iş hukuku)**
legislation. User asks in natural language (e.g. "Yıllık izin hakkım kaç gün?"), gets an answer
**grounded in the legislation with the source article shown** (e.g. "Kaynak: İş Kanunu Madde 53").
It's a **RAG** app. Must be **clean-looking** (he's a frontend dev) and **deployable / web-accessible**
so employers can test it. Function & correctness over aesthetics.

### Stack & shape
- **One single repo** containing two apps: a **Next.js** app (frontend) and a **Python/FastAPI** AI
  service. Plain folder split — **no heavy monorepo tooling** (Nx/Turborepo/pnpm workspaces); the two
  apps are different languages talking only over HTTP.
- **Next.js** = frontend + a **thin gateway API route** (`/api/chat`) that proxies the question to the
  AI service and returns the answer. No business logic in the gateway.
- **FastAPI AI service**, internally **layered** so the developer learns OOP/SOLID/patterns:
  thin routes → `services/` (business logic: embedding, retrieval, LLM) → `repositories/`
  (`VectorRepository` abstracting the vector DB so it's swappable) → `core/` (config, error classes,
  retry) → Pydantic models. The **ingest** script is a separate offline CLI tool, not an app endpoint.
- **Vector DB: Pinecone** (free tier), **abstracted behind a repository**.
- **LLM + embeddings: Google Gemini** (free tier, **no credit card**), generation with **Gemini 2.5
  Flash**. (NOTE: his Anthropic Pro covers Claude.ai chat only, **not** API usage — don't suggest it.)
- **Packaging:** `docker-compose` is for **local development** — it brings up both services together so
  they talk over an internal network on his machine. **It is NOT used in production.**
- **Deploy:** in production the two services live in different places and talk over the public internet:
  Next.js → **Vercel** (free); FastAPI → **Render** free tier. Render gives the AI service a public URL;
  the Next.js gateway is pointed at that URL via an env var (the local internal-network address becomes
  this public URL in prod). Render free tier sleeps after idle (first request is slow — fine for a demo).
  Set the **root directory** per subfolder on each platform.

### RAG design
- **Curated fixed knowledge base.** The developer pre-ingests the legislation; **the user does NOT
  upload documents**, only asks questions. The base may span **multiple** labour-law sources
  (İş Kanunu + related regulations), so it isn't single-document.
- **Two distinct flows, keep separate:**
  - *Ingest* (offline, run once by him): legislation files → **article/clause-aware chunking** (not
    naive fixed-size) → Gemini embeddings → Pinecone, with metadata (law, article no, date).
  - *Query* (every question): question → embed the question → retrieve nearest chunks → build prompt →
    Gemini → answer + source refs. **Vectors are not created at query time**; only the question is
    embedded and matched against the stored legislation vectors.

### Frontend
- **Full-page chat as the main page** (NOT a drawer/widget — the app itself is the AI product).
- **Empty state:** short title + one-line description + **3–4 clickable example questions** (e.g.
  "Yıllık izin hakkım kaç gün?", "Kıdem tazminatı nasıl hesaplanır?", "İhbar süreleri nedir?") that
  auto-send on click.
- **Every answer shows its source article reference**, clickable to reveal the article text (makes
  RAG's grounding visible — this is proof to employers that retrieval works).
- Clean but **don't over-invest** time; high return for low effort here.

### Resilience (Phase 1)
- **Do:** retry with exponential backoff on 429 / transient 5xx (`tenacity`), centralized in
  `LLMService`; **error-class distinction** (retry 429, never retry 400); a **timeout** on the Gemini
  call; frontend loading state + graceful ~30s timeout message.
- **Shared API key:** FastAPI checks an `X-API-Key` header on every request; Next.js gateway sends it via env var. Stops open abuse of the public backend URL. Per-user auth (JWT/OAuth) is out of scope for Phase 1.
- **Don't build (document awareness in README instead):** WebSocket (rejected — one-way
  request/response), request queue, distributed rate limiter (Redis), circuit breaker.

### Phases
- **Phase 1** — working **naive RAG** + clickable source articles. Basic request/response (no
  streaming). **Out of scope (deliberate):** user upload, auth, multi-turn/history, reranking, hybrid
  search, streaming.
- **Phase 1.5** — **evaluation** (the real differentiator; most candidates skip it). Build a set of
  **15–20 (question → expected correct article) pairs**; measure retrieval hit rate and answer
  correctness. He doesn't know eval — **teach it from scratch.**
- **Phase 2** — advanced RAG: hybrid search, reranking, query rewriting, article-level metadata
  filtering, **SSE streaming**. Show the eval score improving (the CV story).

### Code quality note
Write clean, well-named, single-responsibility modules. Abstract when there's a real reason
(swappability, multiple implementations, learning a pattern) — not by default. Premature abstraction
is as bad as no abstraction.

---

## 5. Settled decisions — quick reference

| Topic | Decision |
|---|---|
| Domain | Turkish labour law (iş hukuku) |
| RAG pattern | Curated fixed base, no user upload (Phase 1) |
| Vector DB | Pinecone (free tier), abstracted behind a repository |
| LLM + embeddings | Google Gemini (Free tier, no credit card). LLM: current Free-tier Flash model — verify in AI Studio, do NOT hardcode an outdated name. Embeddings: gemini-embedding-001 (text, task_type support) |
| Main app | Next.js (frontend + thin gateway API route, no logic) |
| AI service | Python + FastAPI, layered (routes → services → repositories → core → models) |
| Ingest | Separate offline CLI script; article/clause-aware chunking + metadata |
| Local | docker-compose (both services, internal network) |
| Deploy (prod) | Vercel (frontend) + Render free tier (AI service); gateway → Render public URL via env var |
| Repo | One repo, plain folder split, no heavy monorepo tooling |
| Phase 1 | Naive RAG + clickable source articles; basic request/response |
| Phase 1.5 | Eval set (15–20 Q→article pairs) — taught from scratch |
| Phase 2 | Hybrid search, reranking, query rewriting, SSE streaming |
| Resilience P1 | retry+backoff (tenacity), error-class split, timeout; NO websocket/queue/redis |
| Frontend | Full-page chat; example-question empty state; visible source references |
| Working style | Tiny commit-sized tasks; teach as you build; he runs all setup, you guide by asking |
