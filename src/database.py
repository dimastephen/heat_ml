from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase
from sqlalchemy.exc import IntegrityError
from src.core.errors import ConflictError, NotFoundError
from abc import ABC,abstractmethod
from typing import Generator, Generic, TypeVar, Type, Optional, Any

from src.config import settings

pg_engine = create_engine(settings.POSTGRES_URL, echo=settings.APP_DEBUG, future=True)
PgSessionLocal = sessionmaker(bind=pg_engine,autoflush=False,autocommit=False, expire_on_commit=False)

TsSessionLocal = None
if settings.TIMESCALEDB_URL:
    ts_engine = create_engine(settings.TIMESCALEDB_URL, echo=settings.APP_DEBUG, future=True)
    TsSessionLocal = sessionmaker(bind=ts_engine, autoflush=False, autocommit=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_pg_db() -> Generator[Session,None,None]:
    db = PgSessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_ts_db() -> Generator[Session, None, None]:
    if TsSessionLocal is None:
        yield from get_pg_db()
        return
    db = TsSessionLocal()
    try:
        yield db
    finally:
        db.close()

T = TypeVar("T", bound=Base)


class BaseRepository(ABC, Generic[T]):
    def __init__(self,db: Session, model: Type[T]):
        self.db = db
        self.model = model

    @abstractmethod
    def get(self, id:Any) -> Optional[T]: ...

    @abstractmethod
    def create(self,obj: Any)-> T:...

    @abstractmethod
    def update(self,db_obj:T, obj:Any) -> T:...

    @abstractmethod
    def delete(self,id:Any) -> None:...


class SQLAlchemyRepository(BaseRepository[T]):
    def get(self, id: Any) -> Optional[T]:
        return self.db.get(self.model, id)

    def create(self, obj_in: dict) -> T:
        obj = self.model(**obj_in)
        self.db.add(obj)
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise ConflictError("Unique constraint violated", code="unique_violation")
        self.db.refresh(obj)
        return obj

    def update(self, db_obj: T, obj_in: dict) -> T:
        for key, value in obj_in.items():
            setattr(db_obj, key, value)
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise ConflictError("Unique constraint violated", code="unique_violation")
        self.db.refresh(db_obj)
        return db_obj

    def delete(self, id: Any) -> None:
        obj = self.db.get(self.model, id)
        if not obj:
            raise NotFoundError(f"{self.model.__name__} with id {id} not found")
        self.db.delete(obj)
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise ConflictError("Delete failed", code="delete_conflict")
