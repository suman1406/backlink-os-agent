from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.db.database import db
import logging

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI App
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_db_client():
    await db.connect_db()
    logger.info("✓ MongoDB startup complete.")


@app.on_event("shutdown")
async def shutdown_db_client():
    await db.close_db()


@app.get("/health")
def health_check():
    return {"status": "ok", "project": settings.PROJECT_NAME}


# Temporary diagnostics endpoint — remove after verification
@app.get("/debug/database")
async def debug_database():
    """Returns MongoDB connectivity diagnostics. REMOVE BEFORE PRODUCTION."""
    info = await db.ping()
    return JSONResponse(content=info)


from app.api.routes import router as api_router
app.include_router(api_router, prefix=settings.API_V1_STR)
