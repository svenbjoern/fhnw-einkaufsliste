from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Einkaufsliste(Base):
    __tablename__ = "einkaufslisten"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    artikel: Mapped[list["Einkaufsartikel"]] = relationship(
        back_populates="einkaufsliste", cascade="all, delete-orphan",
        passive_deletes=True, order_by="Einkaufsartikel.id",
    )


class Einkaufsartikel(Base):
    __tablename__ = "einkaufsartikel"

    id: Mapped[int] = mapped_column(primary_key=True)
    einkaufsliste_id: Mapped[int] = mapped_column(ForeignKey("einkaufslisten.id", ondelete="CASCADE"))
    name: Mapped[str]
    menge: Mapped[float | None]
    einheit: Mapped[str | None]
    gekaufte_menge: Mapped[float] = mapped_column(default=0)
    gekauft: Mapped[bool] = mapped_column(default=False)
    einkaufsliste: Mapped[Einkaufsliste] = relationship(back_populates="artikel")
