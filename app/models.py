from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


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
    menge: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    einheit: Mapped[str | None] = mapped_column(String, nullable=True)
    gekauft: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    einkaufsliste: Mapped[Einkaufsliste] = relationship(back_populates="artikel")
