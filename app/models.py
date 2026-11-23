from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Numeric, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator

from app.database import Base


class GeplanteMenge(TypeDecorator):
    # SQLite liefert NUMERIC als int oder float. Der kürzeste Dezimaltext
    # vermeidet zusätzliche Nachkommastellen aus der Binärdarstellung.
    impl = Numeric(asdecimal=False)
    cache_ok = True

    def process_result_value(self, value, dialect):
        return Decimal(str(value)) if value is not None else None


class Einkaufsliste(Base):
    __tablename__ = "einkaufslisten"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    artikel: Mapped[list["Einkaufsartikel"]] = relationship(
        back_populates="einkaufsliste", cascade="all, delete-orphan",
        passive_deletes=True, order_by="Einkaufsartikel.id",
    )


class Einkaufsartikel(Base):
    __tablename__ = "einkaufsartikel"

    id: Mapped[int] = mapped_column(primary_key=True)
    einkaufsliste_id: Mapped[int] = mapped_column(
        ForeignKey("einkaufslisten.id", ondelete="CASCADE"), nullable=False,
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    menge: Mapped[Decimal | None] = mapped_column(GeplanteMenge, nullable=True)
    einheit: Mapped[str | None] = mapped_column(String, nullable=True)
    # Der Boolean wird für Artikel ohne positive geplante Menge verwendet.
    gekauft_ohne_menge: Mapped[bool] = mapped_column("gekauft", Boolean, default=False, nullable=False)
    # SQLite speichert den Dezimaltext ohne Umwandlung in eine Gleitkommazahl.
    gekaufte_menge: Mapped[str] = mapped_column(String, server_default=text("'0'"), nullable=False)
    einkaufsliste: Mapped[Einkaufsliste] = relationship(back_populates="artikel")
