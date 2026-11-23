from dataclasses import dataclass
from decimal import Decimal, localcontext
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


def menge_validieren(menge: Decimal | None, *, null_zulaessig: bool = False) -> Decimal | None:
    if menge is None:
        return None
    if not menge.is_finite() or menge < 0 or (menge == 0 and not null_zulaessig):
        grenze = "mindestens null" if null_zulaessig else "grösser als null"
        raise UngueltigeDaten(f"Die Menge muss eine endliche Zahl {grenze} sein.")
    # Nachgestellte Nullen ändern den Wert nicht (z. B. 1.500000).
    if not hat_gueltige_praezision(menge):
        raise UngueltigeDaten("Die Menge darf maximal drei Nachkommastellen haben.")
    return menge


def hat_gueltige_praezision(menge: Decimal) -> bool:
    _, ziffern, exponent = menge.as_tuple()
    ueberzaehlige_stellen = max(0, -exponent - 3)
    return not ueberzaehlige_stellen or not any(ziffern[-ueberzaehlige_stellen:])


def geplante_menge_validieren(menge: Decimal | None) -> Decimal | None:
    menge_validieren(menge)
    if menge is not None:
        numerisch = float(menge)
        # SQLite legt ganzzahlige NUMERIC-Werte bis 2**63 als INTEGER ab.
        gespeichert = int(numerisch) if numerisch < 2**63 and numerisch.is_integer() else numerisch
        if Decimal(str(gespeichert)) != menge:
            raise UngueltigeDaten("Die geplante Menge ist für die Datenbank zu gross oder zu genau.")
    return menge


def positive_menge(menge: Decimal | None) -> bool:
    return menge is not None and menge.is_finite() and menge > 0


def restmenge_berechnen(artikel: Einkaufsartikel) -> Decimal | None:
    if not positive_menge(artikel.menge):
        return None
    with localcontext() as kontext:
        # Auch grosse SQLite-Altwerte mit einem Einkauf von 0.001 bleiben exakt.
        kontext.prec = max(28, artikel.menge.adjusted() + 4)
        return artikel.menge - Decimal(artikel.gekaufte_menge)


def status_berechnen(artikel: Einkaufsartikel) -> Einkaufsstatus:
    if not positive_menge(artikel.menge):
        return "gekauft" if artikel.gekauft_ohne_menge else "offen"
    gekauft = Decimal(artikel.gekaufte_menge)
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
        repository.schreibzugriff_sichern(session)
        liste = liste_finden(session, liste_id)
        repository.liste_bearbeiten(session, liste, name_validieren(name))
    return liste


def liste_loeschen(session: Session, liste_id: int) -> None:
    with session.begin():
        repository.schreibzugriff_sichern(session)
        repository.liste_loeschen(session, liste_finden(session, liste_id))


def artikel_hinzufuegen(
    session: Session, liste_id: int, name: str, menge: Decimal | None, einheit: str | None,
) -> Einkaufsartikel:
    with session.begin():
        repository.schreibzugriff_sichern(session)
        liste = liste_finden(session, liste_id)
        name = name_validieren(name)
        menge = geplante_menge_validieren(menge)
        artikel = repository.artikel_erstellen(session, liste, name, menge, (einheit or "").strip() or None)
    return artikel


def artikel_status_setzen(session: Session, artikel_id: int, gekauft: bool) -> Einkaufsartikel:
    with session.begin():
        repository.schreibzugriff_sichern(session)
        artikel = artikel_finden(session, artikel_id)
        menge_vorhanden = positive_menge(artikel.menge)
        artikel.gekaufte_menge = str(artikel.menge) if gekauft and menge_vorhanden else "0"
        artikel.gekauft_ohne_menge = gekauft and not menge_vorhanden
    return artikel


def teileinkauf_erfassen(session: Session, artikel_id: int, zusaetzliche_menge: Decimal) -> Einkaufsartikel:
    with session.begin():
        repository.schreibzugriff_sichern(session)
        artikel = artikel_finden(session, artikel_id)
        if not positive_menge(artikel.menge) or not hat_gueltige_praezision(artikel.menge):
            raise UngueltigeDaten("Teileinkäufe benötigen eine positive geplante Menge mit maximal drei Nachkommastellen.")
        if status_berechnen(artikel) == "gekauft":
            raise UngueltigeDaten("Der Artikel ist bereits vollständig gekauft.")
        menge_validieren(zusaetzliche_menge)
        if zusaetzliche_menge > restmenge_berechnen(artikel):
            raise UngueltigeDaten("Die zusätzlich gekaufte Menge darf die offene Restmenge nicht überschreiten.")
        with localcontext() as kontext:
            kontext.prec = max(28, artikel.menge.adjusted() + 4)
            artikel.gekaufte_menge = str(Decimal(artikel.gekaufte_menge) + zusaetzliche_menge)
    return artikel


def gekaufte_menge_korrigieren(session: Session, artikel_id: int, menge: Decimal) -> Einkaufsartikel:
    with session.begin():
        repository.schreibzugriff_sichern(session)
        artikel = artikel_finden(session, artikel_id)
        if not positive_menge(artikel.menge) or not hat_gueltige_praezision(artikel.menge):
            raise UngueltigeDaten("Die Korrektur benötigt eine positive geplante Menge mit maximal drei Nachkommastellen.")
        menge_validieren(menge, null_zulaessig=True)
        if menge > artikel.menge:
            raise UngueltigeDaten("Die gekaufte Menge darf die geplante Menge nicht überschreiten.")
        artikel.gekaufte_menge = str(menge) if menge else "0"
    return artikel


def artikel_finden(session: Session, artikel_id: int) -> Einkaufsartikel:
    artikel = repository.artikel_finden(session, artikel_id)
    if artikel is None:
        raise NichtGefunden("Der Einkaufsartikel wurde nicht gefunden.")
    return artikel


def artikel_bearbeiten(
    session: Session, artikel_id: int, name: str, menge: Decimal | None, einheit: str | None,
) -> Einkaufsartikel:
    with session.begin():
        repository.schreibzugriff_sichern(session)
        artikel = artikel_finden(session, artikel_id)
        name = name_validieren(name)
        if menge != artikel.menge:
            geplante_menge_validieren(menge)
        einheit = (einheit or "").strip() or None
        status = status_berechnen(artikel)
        hat_einkaufsmenge = Decimal(artikel.gekaufte_menge) > 0
        if hat_einkaufsmenge and (menge is not None or status == "teilweise_gekauft"):
            if menge is None or menge < Decimal(artikel.gekaufte_menge):
                raise UngueltigeDaten("Die geplante Menge muss mindestens der bereits gekauften Menge entsprechen.")
            if einheit != artikel.einheit:
                raise UngueltigeDaten("Bei einer bereits gekauften Menge kann die Einheit nicht geändert werden.")
        elif status == "gekauft":
            # Beim Wechsel zwischen Mengenartikel und Checkbox ohne Menge
            # bleibt ein vollständig abgehakter Artikel vollständig gekauft.
            menge_vorhanden = positive_menge(menge)
            artikel.gekaufte_menge = str(menge) if menge_vorhanden else "0"
            artikel.gekauft_ohne_menge = not menge_vorhanden
        repository.artikel_bearbeiten(artikel, name, menge, einheit)
    return artikel


def artikel_loeschen(session: Session, artikel_id: int) -> None:
    with session.begin():
        repository.schreibzugriff_sichern(session)
        repository.artikel_loeschen(session, artikel_finden(session, artikel_id))
