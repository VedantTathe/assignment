from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.api.routes import chat, traces
from app.core.config import settings
from app.db.session import engine
from app.db.models import Base
from app.core.logger import logger

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Auto-initialize database tables on startup (graceful degradation if DB unavailable)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables initialized successfully")
    except Exception as e:
        logger.warning(f"Database initialization failed (may be expected in dev): {e}")
        logger.info("Continuing without database - in-memory operations only")
    yield

app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

app.include_router(chat.router, prefix="/api")
app.include_router(traces.router, prefix="/api")

@app.get("/health")
def health_check():
    return {"status": "ok"}
