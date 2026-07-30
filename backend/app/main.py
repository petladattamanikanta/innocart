import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api import cart, styling, deals, payments, admin, websocket, auth, mobile
from app.db.seed_products import seed_database

# Setup Logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s"
)
logger = logging.getLogger("innocart.main")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="InnoCart V2 Production API — Autonomous UHF RFID Cart Session, AI Styling & Rush Deals Engine"
)

# CORS Setup - Support all origins, methods, and headers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Include Routers with /api prefix as well as root
app.include_router(cart.router, prefix="/api")
app.include_router(cart.router)
app.include_router(styling.router, prefix="/api")
app.include_router(styling.router)
app.include_router(deals.router, prefix="/api")
app.include_router(deals.router)
app.include_router(payments.router, prefix="/api")
app.include_router(payments.router)
app.include_router(admin.router, prefix="/api")
app.include_router(admin.router)
app.include_router(websocket.router, prefix="/api")
app.include_router(websocket.router)
app.include_router(auth.router)
app.include_router(mobile.router)

@app.get("/", tags=["Health Probe"])
async def root_probe():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs_url": "/docs",
        "health_check": "/health"
    }

@app.get("/health", tags=["Health Probe"])
async def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION
    }

@app.on_event("startup")
async def startup_event():
    logger.info("Initializing InnoCart V2 FastAPI Backend Service...")
    import asyncio
    def background_seed():
        try:
            seed_database()
            logger.info("✓ Product Database schema & 30+ master items auto-seeded successfully!")
        except Exception as e:
            logger.warning(f"Database startup seeding warning: {e}")

    asyncio.create_task(asyncio.to_thread(background_seed))
