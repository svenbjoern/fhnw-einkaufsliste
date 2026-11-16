from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


DATABASE_PATH = Path(__file__).resolve().parent.parent / "einkaufsliste.sqlite3"
engine = create_engine(
    f"sqlite:///{DATABASE_PATH.as_posix()}",
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(bind=engine)


@event.listens_for(engine, "connect")
def enable_foreign_keys(connection, connection_record):
    # SQLite prüft Fremdschlüssel nur, wenn sie pro Verbindung aktiviert werden.
    connection.execute("PRAGMA foreign_keys=ON")


def get_session():
    with SessionLocal() as session:
        yield session
