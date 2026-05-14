from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from loguru import logger
from routes import active_crop
import time
import sys

from core.config import settings
from core.mongodb import connect_mongodb, close_mongodb
from routes import chat, disease, weather, fertilizer, crop, admin, soil, profile, mandi, farm_health

# Configure Loguru
logger.remove()
logger.add(sys.stderr, format="{time} | {level} | {message}", level="INFO")
logger.add("logs/app.log", rotation="10 MB", retention="30 days", level="DEBUG")

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="KisanSathi — Backend API",
    description="AI-powered Smart Farming Platform for Indian Farmers",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

@app.on_event("startup")
async def startup_event():
    logger.info("Starting KisanSathi backend...")
    await connect_mongodb()

@app.on_event("shutdown")
async def shutdown_event():
    await close_mongodb()

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://kishansathii.netlify.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)





# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(round(process_time * 1000, 2))
    return response

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Please try again later."}
    )

# Include routers
app.include_router(chat.router)
app.include_router(disease.router)
app.include_router(weather.router)
app.include_router(fertilizer.router)
app.include_router(crop.router)
app.include_router(admin.router)
app.include_router(soil.router)
app.include_router(profile.router)
app.include_router(mandi.router)
app.include_router(farm_health.router)
app.include_router(active_crop.router)

@app.get("/")
async def root():
    return {
        "name": "KisanSathi API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/api/docs",
        "environment": settings.ENVIRONMENT
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": time.time()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
