from dataclasses import dataclass
from typing import Literal

from sqlalchemy.orm import Session

from app import repository
from app.models import Einkaufsartikel, Einkaufsliste


class UngueltigeDaten(ValueError):
    pass


class NichtGefunden(Exception):
    pass


Einkaufsstatus = Literal["offen", "teilweise_gekauft", "gekauft"]


@dataclass(frozen=True)
class Fortschritt:
    gekauft: int
    gesamt: int
    prozent: float


def restmenge_berechnen(artikel: Einkaufsartikel) -> float | None:
    if artikel.menge is None:
        return None
    return round(artikel.menge - artikel.gekaufte_menge, 3)


def status_berechnen(artikel: Einkaufsartikel) -> Einkaufsstatus:
    if artikel.gekauft:
        return "gekauft"
    if artikel.gekaufte_menge > 0:
        return "teilweise_gekauft"
    return "offen"


def fortschritt_berechnen(artikel: list[Einkaufsartikel]) -> Fortschritt:
    gesamt = len(artikel)
    gekauft = sum(1 for eintrag in artikel if eintrag.gekauft)
    prozent = round(gekauft / gesamt * 100, 1) if gesamt else 0
    return Fortschritt(gekauft=gekauft, gesamt=gesamt, prozent=prozent)


def alle_listen(session: Session) -> list[Einkaufsliste]:
    return repository.alle_listen(session)


def liste_finden(session: Session, liste_id: int) -> Einkaufsliste:
    liste = repository.liste_finden(session, liste_id)
    if liste is None:
        raise NichtGefunden("Die Einkaufsliste wurde nicht gefunden.")
    return liste


def liste_erstellen(session: Session, name: str) -> Einkaufsliste:
    with session.begin():
        liste = repository.liste_erstellen(session, name)
    return liste


def liste_bearbeiten(session: Session, liste_id: int, name: str) -> Einkaufsliste:
    with session.begin():
        liste = liste_finden(session, liste_id)
        repository.liste_bearbeiten(session, liste, name)
    return liste


def liste_loeschen(session: Session, liste_id: int) -> None:
    with session.begin():
        repository.liste_loeschen(session, liste_finden(session, liste_id))


def artikel_hinzufuegen(
    session: Session, liste_id: int, name: str, menge: float | None, einheit: str | None,
) -> Einkaufsartikel:
    with session.begin():
        liste = liste_finden(session, liste_id)
        artikel = repository.artikel_erstellen(session, liste, name, menge, einheit or None)
    return artikel


def artikel_status_setzen(session: Session, artikel_id: int, gekauft: bool) -> Einkaufsartikel:
    with session.begin():
        artikel = artikel_finden(session, artikel_id)
        artikel.gekauft = gekauft
        artikel.gekaufte_menge = (artikel.menge or 0) if gekauft else 0
    return artikel


def teileinkauf_erfassen(session: Session, artikel_id: int, zusaetzliche_menge: float) -> Einkaufsartikel:
    with session.begin():
        artikel = artikel_finden(session, artikel_id)
        restmenge = restmenge_berechnen(artikel)
        if restmenge is None:
            raise UngueltigeDaten("Teileinkäufe benötigen eine geplante Menge.")
        if artikel.gekauft:
            raise UngueltigeDaten("Der Artikel ist bereits vollständig gekauft.")
        if zusaetzliche_menge > restmenge:
            raise UngueltigeDaten("Die zusätzlich gekaufte Menge darf die offene Restmenge nicht überschreiten.")
        artikel.gekaufte_menge = round(artikel.gekaufte_menge + zusaetzliche_menge, 3)
        artikel.gekauft = artikel.gekaufte_menge >= artikel.menge
    return artikel


def artikel_finden(session: Session, artikel_id: int) -> Einkaufsartikel:
    artikel = repository.artikel_finden(session, artikel_id)
    if artikel is None:
        raise NichtGefunden("Der Einkaufsartikel wurde nicht gefunden.")
    return artikel


def artikel_bearbeiten(
    session: Session, artikel_id: int, name: str, menge: float | None, einheit: str | None,
) -> Einkaufsartikel:
    with session.begin():
        artikel = artikel_finden(session, artikel_id)
        einheit = einheit or None
        gekauft = artikel.gekaufte_menge
        if menge is None and gekauft > 0 and not artikel.gekauft:
            raise UngueltigeDaten("Bei einem teilweise gekauften Artikel muss die geplante Menge erhalten bleiben.")
        if menge is not None and menge < gekauft:
            raise UngueltigeDaten("Die geplante Menge muss mindestens der bereits gekauften Menge entsprechen.")
        if menge is not None and gekauft > 0 and einheit != artikel.einheit:
            raise UngueltigeDaten("Bei einer bereits gekauften Menge kann die Einheit nicht geändert werden.")

        # Ein abgehakter Artikel behält sein Häkchen beim Wechsel zu oder von «ohne Menge».
        if menge is None or artikel.menge is None and artikel.gekauft:
            artikel.gekaufte_menge = menge or 0
        if menge is not None:
            artikel.gekauft = artikel.gekaufte_menge >= menge
        repository.artikel_bearbeiten(artikel, name, menge, einheit)
    return artikel


def artikel_loeschen(session: Session, artikel_id: int) -> None:
    with session.begin():
        repository.artikel_loeschen(session, artikel_finden(session, artikel_id))
