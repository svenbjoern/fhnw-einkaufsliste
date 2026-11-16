from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class ListeErstellen(BaseModel):
    name: str


class ArtikelErstellen(BaseModel):
    name: str
    menge: Decimal | None = None
    einheit: str | None = None


class ArtikelStatus(BaseModel):
    gekauft: bool


class ArtikelAusgabe(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    einkaufsliste_id: int
    name: str
    menge: Decimal | None
    einheit: str | None
    gekauft: bool


class Fortschritt(BaseModel):
    gekauft: int
    gesamt: int
    prozent: float


class ListeAusgabe(BaseModel):
    id: int
    name: str
    artikel: list[ArtikelAusgabe]
    fortschritt: Fortschritt
