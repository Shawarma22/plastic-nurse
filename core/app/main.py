from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select
from app.config import settings
from app.logger import logger
from app.db.session import init_db, engine
from app.db.models import User
from app.auth.security import get_password_hash
from app.services.camera_service import camera_service
from app.services.job_queue import job_queue_service
from app.routers import auth, motors, door, camera, vitals, jobs, ws

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    with Session(engine) as session:
        admin_user = session.exec(select(User).where(User.username == "admin")).first()
        if not admin_user:
            default_admin = User(
                username="admin",
                hashed_password=get_password_hash("admin123"),
                role="admin",
                is_active=True
            )
            session.add(default_admin)
            session.commit()
            logger.info("Created default administrator user")

    camera_service.start()
    job_queue_service.start()
    logger.info(f"Medical Droid Core started in {settings.DROID_HAL} mode on port {settings.API_PORT}")
    yield
    camera_service.stop()
    await job_queue_service.stop()
    logger.info("Medical Droid Core shutdown complete")

app = FastAPI(
    title="Medical Droid Core API",
    version="1.0.0",
    description="Offline Edge AI and Hardware Control API for Medical Assistive Droid",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(motors.router)
app.include_router(door.router)
app.include_router(camera.router)
app.include_router(vitals.router)
app.include_router(jobs.router)
app.include_router(ws.router)

@app.get("/health", tags=["system"])
def health_check():
    return {
        "status": "healthy",
        "hal_mode": settings.DROID_HAL,
        "environment": settings.DROID_ENV
    }
