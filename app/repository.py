from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Einkaufsartikel, Einkaufsliste


def alle_listen(session: Session) -> list[Einkaufsliste]:
    query = select(Einkaufsliste).options(selectinload(Einkaufsliste.artikel))
    return list(session.scalars(query.order_by(Einkaufsliste.id)))


def liste_finden(session: Session, liste_id: int) -> Einkaufsliste | None:
    return session.get(Einkaufsliste, liste_id)


def liste_erstellen(session: Session, name: str) -> Einkaufsliste:
    liste = Einkaufsliste(name=name)
    session.add(liste)
    session.commit()
    session.refresh(liste)
    return liste


def liste_bearbeiten(session: Session, liste: Einkaufsliste, name: str) -> Einkaufsliste:
    liste.name = name
    session.commit()
    session.refresh(liste)
    return liste


def liste_loeschen(session: Session, liste: Einkaufsliste) -> None:
    session.delete(liste)
    session.commit()


def artikel_erstellen(
    session: Session, liste: Einkaufsliste, name: str,
    menge: Decimal | None, einheit: str | None,
) -> Einkaufsartikel:
    artikel = Einkaufsartikel(
        einkaufsliste=liste, name=name, menge=menge, einheit=einheit, gekauft=False,
    )
    session.add(artikel)
    session.commit()
    session.refresh(artikel)
    return artikel


def artikel_finden(session: Session, artikel_id: int) -> Einkaufsartikel | None:
    return session.get(Einkaufsartikel, artikel_id)


def status_setzen(session: Session, artikel: Einkaufsartikel, gekauft: bool) -> Einkaufsartikel:
    artikel.gekauft = gekauft
    session.commit()
    session.refresh(artikel)
    return artikel


def artikel_bearbeiten(
    session: Session, artikel: Einkaufsartikel, name: str,
    menge: Decimal | None, einheit: str | None,
) -> Einkaufsartikel:
    artikel.name = name
    artikel.menge = menge
    artikel.einheit = einheit
    session.commit()
    session.refresh(artikel)
    return artikel


def artikel_loeschen(session: Session, artikel: Einkaufsartikel) -> None:
    session.delete(artikel)
    session.commit()
