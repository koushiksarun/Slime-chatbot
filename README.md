# AI Chatbot — Production-Grade Generative AI Application

A full-stack, production-ready AI chatbot with RAG, memory, agent tools, and a human-in-the-loop RLHF pipeline. Built with Next.js, FastAPI, LangChain, LlamaIndex, and PostgreSQL.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Browser / Mobile                                               │
│  Next.js 15 · TypeScript · Tailwind CSS · Zustand              │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTPS / SSE streaming
┌──────────────────────────▼──────────────────────────────────────┐
│  Nginx (reverse proxy + SSL + rate limiting)                    │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│  FastAPI Backend (Python 3.12)                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────────────┐ │
│  │Auth/JWT  │ │Rate Limit│ │Input San.│ │Prompt Injection Det│ │
│  └──────────┘ └──────────┘ └──────────┘ └────────────────────┘ │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │          LangChain Orchestrator                             │ │
│  │  ┌────────────────┐  ┌──────────────┐  ┌────────────────┐  │ │
│  │  │  Memory Service│  │  LLM Service │  │  Agent Service │  │ │
│  │  │  Short + Long  │  │ OpenAI/Gemini│  │  ReAct + Tools │  │ │
│  │  └────────────────┘  └──────────────┘  └────────────────┘  │ │
│  └─────────────────────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │          LlamaIndex RAG Pipeline                            │ │
│  │  Upload → Extract → Chunk → Embed → Store → Retrieve       │ │
│  └─────────────────────────────────────────────────────────────┘ │
└──────────┬─────────────────────────┬────────────────────────────┘
           │                         │
┌──────────▼───────┐     ┌───────────▼──────────┐     ┌──────────┐
│   PostgreSQL 16  │     │  ChromaDB / Pinecone  │     │  Redis 7 │
│  Users · Chats   │     │  Vector Embeddings    │     │  Cache   │
│  Docs · Feedback │     │  Semantic Search      │     │  Rate Lim│
└──────────────────┘     └──────────────────────┘     └──────────┘
```

---

## Project Structure

```
ai-chatbot/
├── backend/                        # FastAPI application
│   ├── app/
│   │   ├── api/v1/
│   │   │   ├── auth.py             # Register, login, refresh, /me
│   │   │   ├── chat.py             # Chat (streaming SSE + batch)
│   │   │   ├── documents.py        # File upload + management
│   │   │   ├── feedback.py         # Thumbs up/down + admin review
│   │   │   └── admin.py            # Dashboard metrics + user mgmt
│   │   ├── core/
│   │   │   ├── config.py           # All settings via pydantic-settings
│   │   │   ├── database.py         # Async SQLAlchemy engine
│   │   │   ├── security.py         # JWT, password hashing, injection detect
│   │   │   └── redis_client.py     # Redis connection
│   │   ├── models/                 # SQLAlchemy ORM models
│   │   │   ├── user.py             # User + roles (user/admin/moderator)
│   │   │   ├── conversation.py     # Conversation + Message
│   │   │   ├── document.py         # Uploaded documents metadata
│   │   │   └── feedback.py         # User ratings + RLHF workflow
│   │   ├── schemas/                # Pydantic request/response schemas
│   │   ├── services/
│   │   │   ├── ai/llm_service.py   # OpenAI + Gemini wrapper w/ streaming
│   │   │   ├── memory/             # Short-term + long-term memory
│   │   │   ├── rag/                # Document processor + vector store
│   │   │   └── agents/             # LangChain ReAct agent + tools
│   │   ├── middleware/
│   │   │   ├── auth.py             # JWT dependency injection
│   │   │   └── rate_limiter.py     # Redis sliding window rate limit
│   │   └── main.py                 # FastAPI app + lifespan
│   ├── alembic/                    # Database migrations
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/                       # Next.js 15 application
│   └── src/
│       ├── app/
│       │   ├── page.tsx            # Root redirect
│       │   ├── auth/login/         # Login page
│       │   ├── auth/register/      # Registration page
│       │   ├── chat/               # Main chat interface
│       │   ├── admin/              # Admin dashboard
│       │   └── api/auth/           # NextAuth route handler
│       ├── components/
│       │   ├── chat/
│       │   │   ├── MessageBubble.tsx   # Markdown + code highlight + citations
│       │   │   ├── ChatInput.tsx       # Textarea + RAG/Agent toggles
│       │   │   └── ChatSidebar.tsx     # Conversation history sidebar
│       │   └── upload/
│       │       └── DocumentUpload.tsx  # Drag-and-drop file uploader
│       ├── hooks/useChat.ts         # Streaming chat hook (SSE)
│       ├── lib/api.ts               # Axios client + streaming fetch
│       ├── store/auth.ts            # Zustand auth store w/ persistence
│       └── types/index.ts           # TypeScript type definitions
│
├── ml/                             # RLHF + Fine-tuning pipeline
│   ├── feedback/
│   │   └── export_dataset.py       # DB → JSONL (SFT + DPO formats)
│   ├── fine_tuning/
│   │   └── fine_tune_openai.py     # Upload + start OpenAI fine-tune job
│   └── evaluation/
│       └── evaluate_model.py       # BLEU + ROUGE-L + LLM-as-Judge
│
├── infrastructure/
│   ├── nginx/
│   │   ├── nginx.dev.conf          # Dev: SSE proxy + API routing
│   │   └── nginx.prod.conf         # Prod: SSL, rate limit, security headers
│   └── .github/workflows/
│       └── ci.yml                  # GitHub Actions CI/CD pipeline
│
├── docker-compose.yml              # Development stack
├── docker-compose.prod.yml         # Production stack
├── .env.example                    # Environment variable template
└── README.md
```

---

## Database Schema

```sql
-- Users
users (id UUID PK, email UNIQUE, username UNIQUE, hashed_password,
       role ENUM(user/admin/moderator), is_active, is_verified,
       profile_memory TEXT, created_at, updated_at, last_login)

-- Conversations
conversations (id UUID PK, user_id FK, title, summary,
               memory_context JSONB, model_used, total_tokens,
               total_cost_usd, is_archived, created_at, updated_at)

-- Messages
messages (id UUID PK, conversation_id FK, role ENUM(user/assistant/system/tool),
          content TEXT, citations JSONB, tool_calls JSONB,
          prompt_tokens, completion_tokens, cost_usd, model_used,
          latency_ms, created_at)

-- Documents
documents (id UUID PK, user_id FK, filename, original_filename,
           file_type, file_size_bytes, file_path, status ENUM,
           vector_collection, chunk_count, doc_metadata JSONB,
           error_message, is_public, created_at, processed_at)

-- Feedback
feedback (id UUID PK, user_id FK, message_id FK UNIQUE,
          rating ENUM(thumbs_up/thumbs_down), comment,
          prompt_snapshot TEXT, response_snapshot TEXT,
          status ENUM(pending/approved/rejected/in_dataset),
          reviewed_by, reviewed_at, review_notes, created_at)
```

---

## Quick Start (Local Development)

### Prerequisites
- Docker Desktop 4.x+
- Node.js 22+
- Python 3.12+
- An OpenAI API key (get at platform.openai.com)

### 1. Clone and configure

```bash
# Copy environment template
cp .env.example .env

# Edit .env — minimum required:
# OPENAI_API_KEY=sk-your-key
# SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
# NEXTAUTH_SECRET=$(openssl rand -base64 32)
```

### 2. Start all services with Docker Compose

```bash
docker compose up -d

# Watch logs
docker compose logs -f backend
```

Services started:
| Service    | URL                        |
|------------|----------------------------|
| Frontend   | http://localhost:3000       |
| Backend    | http://localhost:8000       |
| API Docs   | http://localhost:8000/docs  |
| ChromaDB   | http://localhost:8001       |
| PostgreSQL | localhost:5432              |
| Redis      | localhost:6379              |

### 3. Run database migrations

```bash
docker compose exec backend alembic upgrade head
```

### 4. Create an admin user

```bash
# Using the API
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "username": "admin",
    "password": "Admin123!",
    "full_name": "Admin User"
  }'

# Then promote to admin via psql
docker compose exec postgres psql -U chatbot chatbot_db \
  -c "UPDATE users SET role='admin' WHERE email='admin@example.com';"
```

---

## API Reference

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | Create account |
| POST | `/api/v1/auth/login` | Login → JWT tokens |
| POST | `/api/v1/auth/refresh` | Refresh access token |
| GET | `/api/v1/auth/me` | Get current user |
| PATCH | `/api/v1/auth/me` | Update profile |

### Chat
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/chat/` | Send message (stream or batch) |
| GET | `/api/v1/chat/conversations` | List conversations |
| GET | `/api/v1/chat/conversations/{id}` | Get conversation + messages |
| DELETE | `/api/v1/chat/conversations/{id}` | Delete conversation |

### Documents (RAG)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/documents/upload` | Upload PDF/DOCX/TXT |
| GET | `/api/v1/documents/` | List user's documents |
| DELETE | `/api/v1/documents/{id}` | Delete document + vectors |

### Feedback (RLHF)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/feedback/` | Submit thumbs up/down |
| GET | `/api/v1/feedback/pending` | List pending reviews (admin) |
| PATCH | `/api/v1/feedback/{id}/review` | Approve/reject (admin) |
| GET | `/api/v1/feedback/stats` | Feedback analytics (admin) |

### Admin
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/admin/metrics` | Dashboard KPIs |
| GET | `/api/v1/admin/users` | List all users |
| PATCH | `/api/v1/admin/users/{id}/role` | Change user role |
| GET | `/api/v1/admin/model-performance` | Latency + cost by model |

---

## Memory Architecture

```
Per Request:
  1. Load last 20 messages from DB (short-term window)
  2. Prepend LLM summary if conversation > 40 turns (long-term)
  3. Inject user profile facts extracted from past messages

LLM Context = [System Prompt] + [Profile] + [Summary?] + [RAG Context?] + [History] + [User Message]

Storage:
  - Short-term: PostgreSQL messages table (live)
  - Long-term:  conversations.summary (compressed by GPT-4o-mini)
  - Profile:    users.profile_memory (JSON fact store)
```

---

## RAG Pipeline

```
Upload Flow:
  File → Validate (type/size) → Save to disk → DB record (PENDING)
       → Background task → Extract text (PyPDF/docx)
       → Chunk (LlamaIndex SentenceSplitter, 512 tokens, 64 overlap)
       → Embed (OpenAI text-embedding-3-small or sentence-transformers)
       → Store in ChromaDB/Pinecone (user-scoped collection)
       → Update DB record (READY, chunk_count=N)

Query Flow:
  Message → Embed query → Cosine similarity search (top-6)
          → Filter by similarity threshold (0.7)
          → Format as context: "[Source N: filename]\n{chunk_text}"
          → Append to LLM prompt
          → Generate response with citations
```

---

## RLHF Pipeline (Human-in-Loop)

```
Step 1: Collection
  User clicks 👍/👎 on any assistant message → stored in feedback table

Step 2: Human Review (Admin Dashboard)
  Admin views pending feedback → Approve or Reject
  Only APPROVED examples flow into training data

Step 3: Dataset Export
  python ml/feedback/export_dataset.py \
    --format openai \
    --output ml/data/dataset.jsonl

Step 4: Fine-Tuning
  python ml/fine_tuning/fine_tune_openai.py \
    --dataset ml/data/dataset.jsonl \
    --base-model gpt-4o-mini-2024-07-18

Step 5: Evaluation
  python ml/evaluation/evaluate_model.py \
    --model ft:gpt-4o-mini-...:chatbot-v1 \
    --test-set ml/data/test_set.jsonl \
    --baseline gpt-4o-mini

Step 6: Deploy
  Update OPENAI_MODEL in .env → restart backend
```

**Key principle:** The model NEVER retrains itself automatically. Every training sample passes through human review. This prevents reward hacking and quality degradation.

---

## Agent Tools

| Tool | Description | API Required |
|------|-------------|--------------|
| `web_search` | Live web search via Tavily | `TAVILY_API_KEY` |
| `calculator` | Safe math evaluation (sandboxed) | None |
| `get_weather` | Current weather by city | `OPENWEATHER_API_KEY` |

Enable agents per-request by setting `use_agents: true` in the chat payload.

---

## Security

| Layer | Implementation |
|-------|---------------|
| Authentication | JWT (HS256) with 30-min access + 7-day refresh |
| Password storage | bcrypt (passlib, 12 rounds) |
| Prompt injection | Regex + pattern detection before LLM call |
| Rate limiting | Redis sliding window (60/min, 500/hr per user) |
| Input validation | Pydantic models with field constraints |
| File uploads | Extension allowlist + size limit + random filename |
| RBAC | user / moderator / admin roles enforced at middleware |
| CORS | Explicit origin allowlist |
| Admin endpoints | IP allowlist in nginx.prod.conf |
| TLS | nginx SSL termination with TLS 1.2/1.3 only |

---

## Deployment (Production)

### AWS EC2 / Azure VM

```bash
# On your production server
git clone https://github.com/your-org/ai-chatbot /opt/chatbot
cd /opt/chatbot

# Copy and fill in production env
cp .env.example .env.production
# Edit .env.production with production secrets

# Pull and start
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d

# Run migrations
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

### SSL Certificates (Let's Encrypt)

```bash
# Install certbot
apt install certbot
certbot certonly --standalone -d your-domain.com

# Copy certs to nginx ssl folder
cp /etc/letsencrypt/live/your-domain.com/fullchain.pem infrastructure/nginx/ssl/
cp /etc/letsencrypt/live/your-domain.com/privkey.pem infrastructure/nginx/ssl/

# Auto-renew
echo "0 12 * * * certbot renew --quiet && docker compose -f /opt/chatbot/docker-compose.prod.yml restart nginx" | crontab -
```

### Switch to Pinecone for production

```bash
# In .env.production:
VECTOR_DB_PROVIDER=pinecone
PINECONE_API_KEY=your-key
PINECONE_ENVIRONMENT=us-east-1-aws
PINECONE_INDEX_NAME=chatbot-index

# Create index in Pinecone dashboard:
# Dimensions: 1536 (OpenAI text-embedding-3-small)
# Metric: cosine
```

### GitHub Actions CI/CD

Configure these secrets in GitHub → Settings → Secrets:
- `OPENAI_API_KEY` — for test runs
- `PROD_HOST` — production server IP
- `PROD_USER` — SSH username
- `PROD_SSH_KEY` — private SSH key

Every push to `main` triggers: Test → Security Scan → Build Docker → Deploy.

---

## Development Commands

```bash
# Backend — run without Docker
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# Run migrations
alembic upgrade head
alembic revision --autogenerate -m "add new table"

# Frontend — run without Docker
cd frontend
npm install
npm run dev

# ML pipeline
python ml/feedback/export_dataset.py --output ml/data/dataset.jsonl
python ml/fine_tuning/fine_tune_openai.py --dataset ml/data/dataset.jsonl
python ml/evaluation/evaluate_model.py --model gpt-4o --test-set ml/data/test.jsonl
```

---

## Tech Stack Summary

| Layer | Technology | Purpose |
|-------|------------|---------|
| Frontend | Next.js 15, React 19, TypeScript | UI, SSR, routing |
| Styling | Tailwind CSS, lucide-react | Design system |
| State | Zustand | Auth + global state |
| Backend | FastAPI, Python 3.12 | API server, async |
| ORM | SQLAlchemy 2.0 (async) | Database layer |
| Migrations | Alembic | Schema versioning |
| Auth | JWT (python-jose) + bcrypt | Security |
| AI Orchestration | LangChain | Agents, memory chains |
| RAG | LlamaIndex | Chunking, indexing |
| LLM | OpenAI GPT-4o / Google Gemini | Inference |
| Embeddings | OpenAI ada / Sentence Transformers | Vectorization |
| Vector DB (dev) | ChromaDB | Local vector search |
| Vector DB (prod) | Pinecone | Managed vector search |
| Database | PostgreSQL 16 | Relational data |
| Cache | Redis 7 | Rate limiting, sessions |
| Proxy | Nginx | SSL, routing, rate limit |
| Containers | Docker + Compose | Reproducible deploys |
| CI/CD | GitHub Actions | Automated pipeline |
| Monitoring | Sentry | Error tracking |
| Fine-tuning | OpenAI FT API | RLHF pipeline |
| Evaluation | BLEU, ROUGE-L, LLM Judge | Model quality |

---

## License

MIT License — see LICENSE file.
