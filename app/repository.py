from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Einkaufsartikel, Einkaufsliste


def alle_listen(session: Session) -> list[Einkaufsliste]:
    query = select(Einkaufsliste).options(selectinload(Einkaufsliste.artikel))
    return list(session.scalars(query.order_by(Einkaufsliste.id)))


def liste_finden(session: Session, liste_id: int) -> Einkaufsliste | None:
    return session.get(Einkaufsliste, liste_id, options=[selectinload(Einkaufsliste.artikel)])


def liste_erstellen(session: Session, name: str) -> Einkaufsliste:
    liste = Einkaufsliste(name=name, artikel=[])
    session.add(liste)
    return liste


def liste_bearbeiten(liste: Einkaufsliste, name: str) -> None:
    liste.name = name


def liste_loeschen(session: Session, liste: Einkaufsliste) -> None:
    session.delete(liste)


def artikel_erstellen(
    session: Session, liste: Einkaufsliste, name: str,
    menge: float | None, einheit: str | None,
) -> Einkaufsartikel:
    artikel = Einkaufsartikel(
        einkaufsliste=liste, name=name, menge=menge, einheit=einheit,
    )
    session.add(artikel)
    return artikel


def artikel_finden(session: Session, artikel_id: int) -> Einkaufsartikel | None:
    return session.get(Einkaufsartikel, artikel_id)


def artikel_bearbeiten(
    artikel: Einkaufsartikel, name: str, menge: float | None, einheit: str | None,
) -> None:
    artikel.name = name
    artikel.menge = menge
    artikel.einheit = einheit


def artikel_loeschen(session: Session, artikel: Einkaufsartikel) -> None:
    session.delete(artikel)
