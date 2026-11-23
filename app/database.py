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
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def datenbank_initialisieren(db_engine):
    Base.metadata.create_all(db_engine)


@event.listens_for(engine, "connect")
def sqlite_fremdschluessel_aktivieren(verbindung, verbindungsinfo):
    # SQLite prüft Fremdschlüssel nur, wenn sie pro Verbindung aktiviert werden.
    verbindung.execute("PRAGMA foreign_keys=ON")


def get_session():
    with SessionLocal() as session:
        yield session
