from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool
from app.utils.config import get_settings

settings = get_settings()

if settings.database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
    if settings.database_url.strip() == "sqlite:///:memory:":
        engine = create_engine(
            settings.database_url,
            echo=False,
            future=True,
            connect_args=connect_args,
            poolclass=StaticPool,
        )
    else:
        engine = create_engine(settings.database_url, echo=False, future=True, connect_args=connect_args)
else:
    engine = create_engine(settings.database_url, echo=False, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
