# Quick Start - Automated Verification

For automated bots and manual testing.

## System Requirements
- Python 3.10+
- pip/poetry
- Optional: PostgreSQL, Redis

## Setup (5 minutes)

### 1. Clone & Install
```bash
git clone https://github.com/VedantTathe/assignment.git
cd assignment
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env with your DeepSeek API key (or it will mock)
```

### 3. Run Tests (Verification)
```bash
pytest -v
# Expected: 16 passed, 4 warnings in ~15s
```

### 4. Start Server
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
# Expected: "Application startup complete"
```

### 5. Test Endpoints
```bash
# Health check
curl http://localhost:8000/health

# API docs (interactive)
curl http://localhost:8000/docs

# Chat API (SSE)
curl -X POST http://localhost:8000/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "What is AI?", "thread_id": "test-1"}'

# Eval Summary
curl http://localhost:8000/api/evals/summary
```

---

## Verification Checklist

- [ ] `pytest -v` → 16/16 PASSED
- [ ] `curl http://localhost:8000/health` → `{"status":"ok"}`
- [ ] `curl http://localhost:8000/docs` → Interactive Swagger UI loads
- [ ] `curl -X POST /api/chat/stream` → Streams SSE events
- [ ] `curl http://localhost:8000/api/evals/summary` → Returns eval data

---

## Docker (Alternative)

```bash
docker-compose up --build
# Same endpoints available on localhost:8000
```

---

## Project Structure

```
app/
  ├─ main.py                 # FastAPI app entry
  ├─ api/routes/
  │  ├─ chat.py             # POST /api/chat/stream
  │  └─ traces.py           # GET /api/evals/summary, etc.
  ├─ orchestrator/
  │  ├─ graph.py            # LangGraph pipeline
  │  ├─ agents/             # 5 agents (decomposition, retrieval, etc.)
  │  ├─ tools/              # 4 tools (sandbox, sql, reflection, etc.)
  │  └─ tracing/            # Distributed tracing
  ├─ evals/
  │  ├─ datasets/           # 15 test cases
  │  ├─ scoring/            # 6 scoring dimensions
  │  └─ runners/            # Async evaluation harness
  └─ db/                     # SQLAlchemy models & session

tests/
  ├─ test_graph.py          # Routing tests
  ├─ test_tools.py          # Tool failure modes
  ├─ test_evals.py          # Evaluation harness
  ├─ test_state.py          # State management
  ├─ test_tracing.py        # Tracing system
  ├─ test_sse.py            # SSE streaming
  └─ test_llm_integration.py # LLM client
```

---

## API Endpoints (5 Required)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/chat/stream` | Stream agent responses via SSE |
| GET | `/api/traces` | Get execution traces |
| GET | `/api/evals/summary` | Evaluation summary by category |
| POST | `/api/prompts/approve` | Human approval of prompt rewrites |
| POST | `/api/evals/trigger-reeval` | Re-evaluate with new prompts |

---

## Test Coverage

**16/16 Tests Passing (100%)**

- `test_graph.py` - Dynamic routing ✅
- `test_tools.py` - Tool failure modes ✅
- `test_evals.py` - Eval harness ✅
- `test_state.py` - State immutability ✅
- `test_tracing.py` - Trace reconstruction ✅
- `test_sse.py` - Streaming ✅
- `test_llm_integration.py` - LLM client ✅

---

## Troubleshooting

### PostgreSQL Not Available
✅ Expected - system gracefully degrades to in-memory

### API Returns 404
- Check `/api` prefix is included (e.g., `/api/chat/stream`, not `/chat/stream`)
- Use `http://localhost:8000/docs` to see all endpoints

### Tests Fail
```bash
# Clear cache and re-run
rm -rf .pytest_cache __pycache__
pytest -v
```

### DeepSeek API Key Missing
- Set `OPENAI_API_KEY` in `.env`
- Or use mock provider in tests

---

## Documentation Files

- **README.md** - Architecture & philosophy
- **README_COMPREHENSIVE.md** - Detailed feature guide
- **QUICKSTART.md** (this file) - Run & verify

---

## GitHub Repository

https://github.com/VedantTathe/assignment

---

## Questions?

All code is documented inline. Key entry points:
- `app/main.py` - FastAPI initialization
- `app/orchestrator/graph.py` - Multi-agent pipeline
- `tests/` - Verification examples
