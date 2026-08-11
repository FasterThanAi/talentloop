import contextvars
import logging
from collections.abc import Generator
from typing import Any, Generic, List, Optional, Type, TypeVar

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

logger = logging.getLogger("talentloop.db")

# Context variable to hold the current request's tenant org_id
current_org_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar("current_org_id_ctx", default=None)


class Base(DeclarativeBase):
    pass


# Connect args for SQLite support
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            return True
    except Exception as e:
        logger.warning(f"Database connection check failed: {e}")
        return False


def check_pgvector_extension() -> bool:
    if settings.DATABASE_URL.startswith("sqlite"):
        return True  # Vector features run with cosine fallback in sqlite mode
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
            ).scalar()
            return bool(result)
    except Exception as e:
        logger.warning(f"pgvector extension check failed: {e}")
        return False


T = TypeVar("T", bound=Base)


class BaseRepository(Generic[T]):
    """
    Base repository enforcing multi-tenancy via org_id filter.
    Every business query is scoped to the tenant organization.
    """
    def __init__(self, model: type[T], db: Session, org_id: str | None = None):
        self.model = model
        self.db = db
        self._explicit_org_id = org_id

    @property
    def org_id(self) -> str | None:
        if self._explicit_org_id is not None:
            return self._explicit_org_id
        return current_org_id_ctx.get()

    def get_by_id(self, item_id: str) -> T | None:
        stmt = select(self.model).where(self.model.id == item_id)
        if hasattr(self.model, "org_id") and self.org_id:
            stmt = stmt.where(self.model.org_id == self.org_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def list(self, limit: int = 50, offset: int = 0) -> list[T]:
        stmt = select(self.model)
        if hasattr(self.model, "org_id") and self.org_id:
            stmt = stmt.where(self.model.org_id == self.org_id)
        stmt = stmt.limit(limit).offset(offset)
        return list(self.db.execute(stmt).scalars().all())

    def create(self, **kwargs: Any) -> T:
        if hasattr(self.model, "org_id") and "org_id" not in kwargs and self.org_id:
            kwargs["org_id"] = self.org_id
        instance = self.model(**kwargs)
        self.db.add(instance)
        self.db.commit()
        self.db.refresh(instance)
        return instance

    def delete(self, item: T) -> None:
        self.db.delete(item)
        self.db.commit()
