from decimal import Decimal

from sqlalchemy.orm import Session

from app import repository
from app.models import Einkaufsartikel, Einkaufsliste
from app.schemas import ArtikelErstellen, Fortschritt, ListeAusgabe


class UngueltigeDaten(ValueError):
    pass


class NichtGefunden(Exception):
    pass


def name_validieren(name: str) -> str:
    name = name.strip()
    if not name:
        raise UngueltigeDaten("Der Name darf nicht leer sein.")
    return name


def menge_validieren(menge: Decimal | None) -> Decimal | None:
    if menge is not None and (not menge.is_finite() or menge <= 0):
        raise UngueltigeDaten("Die Menge muss eine endliche Zahl grösser als null sein.")
    if menge is not None:
        # Nachgestellte Nullen ändern den Wert nicht (z. B. 1.500000).
        _, ziffern, exponent = menge.as_tuple()
        while ziffern and ziffern[-1] == 0:
            ziffern = ziffern[:-1]
            exponent += 1
        if exponent < -3:
            raise UngueltigeDaten("Die Menge darf maximal drei Nachkommastellen haben.")
    return menge


def fortschritt_berechnen(artikel: list[Einkaufsartikel]) -> Fortschritt:
    gesamt = len(artikel)
    gekauft = sum(1 for eintrag in artikel if eintrag.gekauft)
    prozent = round(gekauft / gesamt * 100, 1) if gesamt else 0
    return Fortschritt(gekauft=gekauft, gesamt=gesamt, prozent=prozent)


def liste_ausgeben(liste: Einkaufsliste) -> ListeAusgabe:
    return ListeAusgabe(
        id=liste.id, name=liste.name, artikel=liste.artikel,
        fortschritt=fortschritt_berechnen(liste.artikel),
    )


def alle_listen(session: Session) -> list[ListeAusgabe]:
    return [liste_ausgeben(liste) for liste in repository.alle_listen(session)]


def liste_finden(session: Session, liste_id: int) -> Einkaufsliste:
    liste = repository.liste_finden(session, liste_id)
    if liste is None:
        raise NichtGefunden("Die Einkaufsliste wurde nicht gefunden.")
    return liste


def liste_anzeigen(session: Session, liste_id: int) -> ListeAusgabe:
    return liste_ausgeben(liste_finden(session, liste_id))


def liste_erstellen(session: Session, name: str) -> ListeAusgabe:
    return liste_ausgeben(repository.liste_erstellen(session, name_validieren(name)))


def liste_bearbeiten(session: Session, liste_id: int, name: str) -> ListeAusgabe:
    liste = liste_finden(session, liste_id)
    return liste_ausgeben(repository.liste_bearbeiten(session, liste, name_validieren(name)))


def liste_loeschen(session: Session, liste_id: int) -> None:
    liste = liste_finden(session, liste_id)
    # Die Modellbeziehung entfernt beim Löschen auch alle zugehörigen Artikel.
    repository.liste_loeschen(session, liste)


def artikel_hinzufuegen(session: Session, liste_id: int, daten: ArtikelErstellen) -> Einkaufsartikel:
    liste = liste_finden(session, liste_id)
    name = name_validieren(daten.name)
    menge = menge_validieren(daten.menge)
    einheit = (daten.einheit.strip() or None) if daten.einheit is not None else None
    return repository.artikel_erstellen(session, liste, name, menge, einheit)


def artikel_status_setzen(session: Session, artikel_id: int, gekauft: bool) -> Einkaufsartikel:
    artikel = artikel_finden(session, artikel_id)
    return repository.status_setzen(session, artikel, gekauft)


def artikel_finden(session: Session, artikel_id: int) -> Einkaufsartikel:
    artikel = repository.artikel_finden(session, artikel_id)
    if artikel is None:
        raise NichtGefunden("Der Einkaufsartikel wurde nicht gefunden.")
    return artikel


def artikel_bearbeiten(session: Session, artikel_id: int, daten: ArtikelErstellen) -> Einkaufsartikel:
    artikel = artikel_finden(session, artikel_id)
    name = name_validieren(daten.name)
    menge = menge_validieren(daten.menge)
    einheit = (daten.einheit.strip() or None) if daten.einheit is not None else None
    return repository.artikel_bearbeiten(session, artikel, name, menge, einheit)


def artikel_loeschen(session: Session, artikel_id: int) -> None:
    artikel = artikel_finden(session, artikel_id)
    repository.artikel_loeschen(session, artikel)
