import logging
from fastapi import FastAPI
from src.api.routes import router as engine_router
from src.config.settings import settings

logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

app = FastAPI(
    title=settings.APP_NAME,
    description="Python AI Microservice for processing financial intelligence",
    version="0.1.0"
)

app.include_router(engine_router)

@app.get("/")
async def root():
    return {"status": "ok", "message": "StockSense AI Engine is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": settings.APP_NAME}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)
