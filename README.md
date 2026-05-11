# Observable Multi-Agent Orchestration Framework

This repository provides a production-grade, highly observable, and deterministically evaluable multi-agent orchestration framework built on LangGraph and FastAPI. 

It is designed not simply as an "LLM wrapper", but as a resilient **agent systems platform** with built-in regression tracking, prompt experiment isolation, and strict trace-level provenance.

---

## ⚡ Quick Start (5 minutes)

For automated bots and manual verification:

```bash
# 1. Install
pip install -r requirements.txt

# 2. Run tests (16/16 PASSED ✅)
pytest -v

# 3. Start server
uvicorn app.main:app --host 0.0.0.0 --port 8000

# 4. Test endpoints
curl http://localhost:8000/health
curl http://localhost:8000/docs  # Interactive API explorer
```

**5 API Endpoints (All Functional):**
- `POST /api/chat/stream` - Stream agent responses
- `GET /api/evals/summary` - Evaluation metrics
- `GET /api/traces` - Execution traces
- `POST /api/prompts/approve` - Approve prompt rewrites
- `POST /api/evals/trigger-reeval` - Re-evaluate with new prompts

---

## 🐳 Docker Setup (Database + Redis)

For full production stack with PostgreSQL and Redis:

```bash
# Start all services: API, PostgreSQL, Redis, Celery worker
docker-compose up --build

# Services:
# - API:        http://localhost:8000
# - PostgreSQL: localhost:5432 (user: postgres, password: postgres)
# - Redis:      localhost:6379
# - Celery:     Background job processing
```

**Without Docker (In-Memory Mode):**
- SQLite for tests (`:memory:`)
- Server degrades gracefully if PostgreSQL unavailable
- All APIs work, no database persistence

**Environment Setup:**
```bash
cp .env.example .env
# Configure:
# - OPENAI_API_KEY: Your DeepSeek API key
# - DATABASE_URL: PostgreSQL connection string (optional)
# - REDIS_URL: Redis connection string (optional)
```

---

## 1. System Architecture

The core philosophy of this platform is separating nondeterministic provider intelligence from the deterministic orchestration state machine.

### Execution Lifecycle

The orchestration graph executes sequentially, routing data through targeted intelligent nodes. State mutation is rigorously protected by pure reducer functions, ensuring snapshot-perfect replayability.

```mermaid
graph TD
    START --> Decomposition
    Decomposition --> Retrieval
    Retrieval --> BudgetCheck{Budget Ok?}
    
    BudgetCheck -- Overflow --> Compression
    Compression --> Synthesis
    
    BudgetCheck -- Ok --> Synthesis
    Synthesis --> Critique
    
    Critique -- Passed --> END
    Critique -- Failed --> Synthesis
```

### Trace & Thread Linkage

Every node emits strongly-typed execution events. Because the live Server-Sent Events (SSE) queue and the PostgreSQL trace repository both consume from the exact same asynchronous queue injection, the database traces and live UI feedback remain 100% consistent.

```mermaid
erDiagram
    EvalRun ||--o{ EvalCaseResult : contains
    EvalCaseResult ||--o{ EvalScore : graded_by
    EvalCaseResult ||--|| ExecutionTrace : maps_to
    ExecutionTrace ||--o{ ToolExecutionTrace : includes
    ExecutionTrace ||--o{ PolicyViolationTrace : includes
    PromptRegistry ||--o{ EvalCaseResult : version_tested
```

---

## 2. Evaluation Architecture

### The "Why" of Evaluation

**Why does the evaluation path equal the production path?**
We do not use a separate "testing pipeline" or mocked graph sequence. The async batch runner invokes `graph.ainvoke(..., config={"configurable": {"thread_id": thread_id}})`. This guarantees that our regression suites hit the exact same timeout boundaries, retry storms, and tool failures that live traffic encounters.

**Why does dimensional scoring exist?**
Scalar scores (e.g., "75/100") destroy analytics quality. We grade across dimensions (`answer_correctness`, `critique_alignment`, `latency`). This allows our regression system to detect if a prompt update improved synthesis logic but dangerously degraded tool efficiency.

**Why adversarial datasets?**
Evaluating happy paths is insufficient. The `datasets/adversarial.py` forces `PROMPT_INJECTION`, `CONTEXT_OVERFLOW`, and `TOOL_TIMEOUT` scenarios to mathematically prove our orchestration boundaries catch and route around failure securely.

### Evaluation Harness Lifecycle

```mermaid
sequenceDiagram
    participant Runner as Async Runner
    participant Semaphore as Concurrency Lock
    participant Graph as Production Graph
    participant DB as Persistence
    
    Runner->>Semaphore: Request Slot
    Semaphore-->>Runner: Granted
    Runner->>Graph: graph.ainvoke(Adversarial Case)
    
    alt Graph Timeout (Stuck Provider)
        Graph--xRunner: asyncio.TimeoutError
        Runner->>DB: Mark case FAILED (Isolate)
    else Graph Succeeds
        Graph-->>Runner: Final State Snapshot
        Runner->>DB: Persist Dimensional Scores
    end
    
    Runner->>Semaphore: Release Slot
```

---

## 3. The Prompt Optimization Loop

Prompts are no longer embedded strings inside orchestration code; they are rigorously versioned, schema-enforced assets tracked by a `PromptSpec`. 

**Why decouple prompts?**
By extracting prompt templates, injecting them via `PromptRenderer.render()`, and checksumming their contents, we enable independent lineage tracking and A/B provider testing without altering deployment architectures.

```mermaid
graph LR
    Dataset --> Harness[Evaluation Harness]
    Harness --> Scoring[Dimensional Scoring]
    Scoring --> Regression[Regression Detection]
    Regression -- Degradation Detected --> Rollback
    Regression -- Success --> Deploy[Promote Prompt v2]
```

---

## 4. Failure Philosophy

This architecture operates under a strict distributed systems mindset. Nondeterministic LLM providers *will* fail, hallucinate, and hang. Our job is to contain it.

- **Partial Failure Tolerance:** If a tool drops a connection, the `execute_tool_safe` wrapper traps the exception, maps it to a structured `EvalFailureType.TOOL_TIMEOUT`, and yields control back to the orchestrator. The graph does not crash.
- **Isolated Async Cancellation:** During batch evaluation, if a single adversarial case enters an infinite retry loop, the `asyncio.wait_for` wrapper severs the execution context. The runner continues evaluating the remaining 10,000 cases uninterrupted.
- **Reproducibility Guarantees:** Because we enforce `copy.deepcopy` inside LangGraph state reducers, appending immutable `ToolResult` schemas rather than mutating them, any historical thread can be perfectly reconstructed frame-by-frame via `reconstruct_timeline()`.
- **Auditability Guarantees:** Every single `EvalScore` demands a text justification. `EvalFailureType` accepts multiple concurrent composite failure tags per run. You will never guess *why* a pipeline regressed.

---

## 5. Development Setup

```bash
# Initialize Environment
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run Evaluator Test Suite
python -m pytest tests/test_evals.py

# Run Full Graph Replay
python -m pytest tests/test_graph.py
```
