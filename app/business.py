from dataclasses import dataclass
from math import isfinite
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


def name_validieren(name: str) -> str:
    name = name.strip()
    if not name:
        raise UngueltigeDaten("Der Name darf nicht leer sein.")
    return name


def menge_validieren(menge: float | None, *, null_zulaessig: bool = False) -> float | None:
    if menge is None:
        return None
    if not isfinite(menge) or menge < 0 or (menge == 0 and not null_zulaessig):
        grenze = "mindestens null" if null_zulaessig else "grösser als null"
        raise UngueltigeDaten(f"Die Menge muss eine endliche Zahl {grenze} sein.")
    # Nachgestellte Nullen ändern den Wert nicht (z. B. 1.500000).
    if not hat_gueltige_praezision(menge):
        raise UngueltigeDaten("Die Menge darf maximal drei Nachkommastellen haben.")
    return menge


def hat_gueltige_praezision(menge: float) -> bool:
    return round(menge, 3) == menge


def positive_menge(menge: float | None) -> bool:
    return menge is not None and isfinite(menge) and menge > 0


def restmenge_berechnen(artikel: Einkaufsartikel) -> float | None:
    if not positive_menge(artikel.menge):
        return None
    return round(artikel.menge - artikel.gekaufte_menge, 3)


def status_berechnen(artikel: Einkaufsartikel) -> Einkaufsstatus:
    if not positive_menge(artikel.menge):
        return "gekauft" if artikel.gekauft_ohne_menge else "offen"
    gekauft = artikel.gekaufte_menge
    if gekauft == artikel.menge:
        return "gekauft"
    return "teilweise_gekauft" if gekauft > 0 else "offen"


def fortschritt_berechnen(artikel: list[Einkaufsartikel]) -> Fortschritt:
    gesamt = len(artikel)
    gekauft = sum(1 for eintrag in artikel if status_berechnen(eintrag) == "gekauft")
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
        liste = repository.liste_erstellen(session, name_validieren(name))
    return liste


def liste_bearbeiten(session: Session, liste_id: int, name: str) -> Einkaufsliste:
    with session.begin():
        liste = liste_finden(session, liste_id)
        repository.liste_bearbeiten(session, liste, name_validieren(name))
    return liste


def liste_loeschen(session: Session, liste_id: int) -> None:
    with session.begin():
        repository.liste_loeschen(session, liste_finden(session, liste_id))


def artikel_hinzufuegen(
    session: Session, liste_id: int, name: str, menge: float | None, einheit: str | None,
) -> Einkaufsartikel:
    with session.begin():
        liste = liste_finden(session, liste_id)
        name = name_validieren(name)
        menge = menge_validieren(menge)
        artikel = repository.artikel_erstellen(session, liste, name, menge, (einheit or "").strip() or None)
    return artikel


def artikel_status_setzen(session: Session, artikel_id: int, gekauft: bool) -> Einkaufsartikel:
    with session.begin():
        artikel = artikel_finden(session, artikel_id)
        menge_vorhanden = positive_menge(artikel.menge)
        artikel.gekaufte_menge = artikel.menge if gekauft and menge_vorhanden else 0
        artikel.gekauft_ohne_menge = gekauft and not menge_vorhanden
    return artikel


def teileinkauf_erfassen(session: Session, artikel_id: int, zusaetzliche_menge: float) -> Einkaufsartikel:
    with session.begin():
        artikel = artikel_finden(session, artikel_id)
        if not positive_menge(artikel.menge) or not hat_gueltige_praezision(artikel.menge):
            raise UngueltigeDaten("Teileinkäufe benötigen eine positive geplante Menge mit maximal drei Nachkommastellen.")
        if status_berechnen(artikel) == "gekauft":
            raise UngueltigeDaten("Der Artikel ist bereits vollständig gekauft.")
        menge_validieren(zusaetzliche_menge)
        if zusaetzliche_menge > restmenge_berechnen(artikel):
            raise UngueltigeDaten("Die zusätzlich gekaufte Menge darf die offene Restmenge nicht überschreiten.")
        artikel.gekaufte_menge = round(artikel.gekaufte_menge + zusaetzliche_menge, 3)
    return artikel


def gekaufte_menge_korrigieren(session: Session, artikel_id: int, menge: float) -> Einkaufsartikel:
    with session.begin():
        artikel = artikel_finden(session, artikel_id)
        if not positive_menge(artikel.menge) or not hat_gueltige_praezision(artikel.menge):
            raise UngueltigeDaten("Die Korrektur benötigt eine positive geplante Menge mit maximal drei Nachkommastellen.")
        menge_validieren(menge, null_zulaessig=True)
        if menge > artikel.menge:
            raise UngueltigeDaten("Die gekaufte Menge darf die geplante Menge nicht überschreiten.")
        artikel.gekaufte_menge = menge
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
        name = name_validieren(name)
        if menge != artikel.menge:
            menge_validieren(menge)
        einheit = (einheit or "").strip() or None
        status = status_berechnen(artikel)
        hat_einkaufsmenge = artikel.gekaufte_menge > 0
        if hat_einkaufsmenge and (menge is not None or status == "teilweise_gekauft"):
            if menge is None or menge < artikel.gekaufte_menge:
                raise UngueltigeDaten("Die geplante Menge muss mindestens der bereits gekauften Menge entsprechen.")
            if einheit != artikel.einheit:
                raise UngueltigeDaten("Bei einer bereits gekauften Menge kann die Einheit nicht geändert werden.")
        elif status == "gekauft":
            # Beim Wechsel zwischen Mengenartikel und Checkbox ohne Menge
            # bleibt ein vollständig abgehakter Artikel vollständig gekauft.
            menge_vorhanden = positive_menge(menge)
            artikel.gekaufte_menge = menge if menge_vorhanden else 0
            artikel.gekauft_ohne_menge = not menge_vorhanden
        repository.artikel_bearbeiten(artikel, name, menge, einheit)
    return artikel


def artikel_loeschen(session: Session, artikel_id: int) -> None:
    with session.begin():
        repository.artikel_loeschen(session, artikel_finden(session, artikel_id))
