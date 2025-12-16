from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Database:
    def __init__(self, db_url: str):
        self._engine = create_engine(db_url, connect_args={"check_same_thread": False})
        self._session_factory = sessionmaker(autocommit=False, autoflush=False, bind=self._engine)

    def init_tables(self):
        Base.metadata.create_all(bind=self._engine)

    @contextmanager
    def session(self):
        session: Session = self._session_factory()
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
