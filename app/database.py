from pathlib import Path

from sqlalchemy import create_engine, event, inspect, text
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
    with db_engine.begin() as verbindung:
        # SQLite soll auch Schemaänderungen in dieselbe Transaktion aufnehmen.
        verbindung.exec_driver_sql("BEGIN IMMEDIATE")
        Base.metadata.create_all(verbindung)
        spalten = inspect(verbindung).get_columns("einkaufsartikel")
        if any(spalte["name"] == "gekaufte_menge" for spalte in spalten):
            return
        verbindung.exec_driver_sql(
            "ALTER TABLE einkaufsartikel ADD COLUMN gekaufte_menge VARCHAR NOT NULL DEFAULT '0'"
        )
        bereits_gekauft = verbindung.execute(text(
            "SELECT id, menge FROM einkaufsartikel WHERE gekauft = 1 AND menge > 0"
        ))
        zeilen = [
            {"id": artikel_id, "menge": str(menge)}
            for artikel_id, menge in bereits_gekauft
            if isinstance(menge, (int, float)) and menge < float("inf")
        ]
        if zeilen:
            verbindung.execute(text(
                "UPDATE einkaufsartikel SET gekaufte_menge = :menge, gekauft = 0 WHERE id = :id"
            ), zeilen)


@event.listens_for(engine, "connect")
def enable_foreign_keys(connection, connection_record):
    # SQLite prüft Fremdschlüssel nur, wenn sie pro Verbindung aktiviert werden.
    connection.execute("PRAGMA foreign_keys=ON")


def get_session():
    with SessionLocal() as session:
        yield session
