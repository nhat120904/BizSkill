from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import structlog
from app.core.config import settings
from app.api.v1.router import api_router
from app.db.session import engine, Base

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    # Startup
    logger.info("Starting BizSkill AI API", debug=settings.debug)
    
    # Note: Database tables are managed by Alembic migrations
    # Run: alembic upgrade head
    logger.info("Application started - ensure migrations have been run")
    
    yield
    
    # Shutdown
    logger.info("Shutting down BizSkill AI API")


app = FastAPI(
    title=settings.app_name,
    description="AI-powered video learning platform for business professionals",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": settings.app_name,
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    from app.db.session import SessionLocal
    
    health = {
        "status": "healthy",
        "database": "unknown",
        "redis": "unknown",
        "qdrant": "unknown",
    }
    
    # Check database
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        health["database"] = "connected"
    except Exception as e:
        health["database"] = f"error: {str(e)}"
        health["status"] = "degraded"
    
    # Check Redis
    try:
        import redis
        r = redis.from_url(settings.redis_url)
        r.ping()
        health["redis"] = "connected"
    except Exception as e:
        health["redis"] = f"error: {str(e)}"
        health["status"] = "degraded"
    
    # Check Qdrant
    try:
        from qdrant_client import QdrantClient
        client = QdrantClient(url=settings.qdrant_url)
        client.get_collections()
        health["qdrant"] = "connected"
    except Exception as e:
        health["qdrant"] = f"error: {str(e)}"
        health["status"] = "degraded"
    
    return health


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )
