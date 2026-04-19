from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app import models
from app.routers import admin, auth, commerce, contact, courses, instructor, interview, student
from app.services.bootstrap import seed_if_empty
from app.utils.config import get_settings
from app.utils.database import Base, SessionLocal, engine

settings = get_settings()

limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_if_empty(db)
    finally:
        db.close()
    yield


app = FastAPI(title=settings.app_name, version="2.0.0", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

_allowed_origins = [o.strip() for o in settings.allowed_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

app.include_router(auth.router)
app.include_router(courses.router)
app.include_router(contact.router)
app.include_router(interview.router)
app.include_router(commerce.router)
app.include_router(admin.router)
app.include_router(student.router)
app.include_router(instructor.router)


@app.get("/")
def root():
    return {"message": "Skillfort LMS API running", "db": settings.database_url}


@app.get("/api/health")
def health():
    return {"status": "ok"}
