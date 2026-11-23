from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from app.business import Einkaufsstatus


class ListeErstellen(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1)


class ArtikelErstellen(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1)
    menge: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    einheit: str | None = None

    @field_validator("menge")
    @classmethod
    def nachkommastellen_pruefen(cls, menge: float | None) -> float | None:
        if menge is not None and menge != round(menge, 3):
            raise ValueError("Die Menge darf maximal drei Nachkommastellen haben.")
        return menge


class ArtikelStatus(BaseModel):
    gekauft: bool


class TeileinkaufErfassen(BaseModel):
    zusaetzliche_menge: float = Field(gt=0, allow_inf_nan=False)

    @field_validator("zusaetzliche_menge")
    @classmethod
    def nachkommastellen_pruefen(cls, menge: float) -> float:
        if menge != round(menge, 3):
            raise ValueError("Die Menge darf maximal drei Nachkommastellen haben.")
        return menge


class ArtikelAusgabe(BaseModel):
    id: int
    einkaufsliste_id: int
    name: str
    menge: float | None
    einheit: str | None
    gekauft: bool
    gekaufte_menge: float | None
    restmenge: float | None
    status: Einkaufsstatus

    @field_serializer("menge", "gekaufte_menge", "restmenge", when_used="json")
    def menge_als_text(self, wert: float | None) -> str | None:
        return str(wert) if wert is not None else None


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
