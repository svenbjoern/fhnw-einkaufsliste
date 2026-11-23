from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_serializer

from app.business import Einkaufsstatus


class ListeErstellen(BaseModel):
    name: str


class ArtikelErstellen(BaseModel):
    name: str
    menge: Decimal | None = None
    einheit: str | None = None


class ArtikelStatus(BaseModel):
    gekauft: bool


class TeileinkaufErfassen(BaseModel):
    zusaetzliche_menge: Decimal


class GekaufteMengeKorrigieren(BaseModel):
    gekaufte_menge: Decimal


class ArtikelAusgabe(BaseModel):
    id: int
    einkaufsliste_id: int
    name: str
    menge: Decimal | None
    einheit: str | None
    gekauft: bool
    gekaufte_menge: Decimal | None
    restmenge: Decimal | None
    status: Einkaufsstatus

    @field_serializer("menge", "gekaufte_menge", "restmenge", when_used="json")
    def menge_als_text(self, wert: Decimal | None) -> str | None:
        return format(wert, "f") if wert is not None else None


class Fortschritt(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    gekauft: int
    gesamt: int
    prozent: float


class ListeAusgabe(BaseModel):
    id: int
    name: str
    artikel: list[ArtikelAusgabe]
    fortschritt: Fortschritt
