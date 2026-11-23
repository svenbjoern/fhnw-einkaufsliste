from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app import business
from app.database import get_session
from app.models import Einkaufsartikel, Einkaufsliste
from app.schemas import (
    ArtikelAusgabe, ArtikelEingabe, ArtikelStatusEingabe, Fortschritt, ListeAusgabe,
    ListeEingabe, TeileinkaufEingabe,
)

router = APIRouter(prefix="/api", tags=["Einkaufslisten"])


def artikel_ausgeben(artikel: Einkaufsartikel) -> ArtikelAusgabe:
    status = business.status_berechnen(artikel)
    restmenge = business.restmenge_berechnen(artikel)
    return ArtikelAusgabe(
        id=artikel.id, einkaufsliste_id=artikel.einkaufsliste_id, name=artikel.name,
        menge=artikel.menge, einheit=artikel.einheit,
        gekaufte_menge=artikel.gekaufte_menge if restmenge is not None else None,
        restmenge=restmenge, status=status,
    )


def liste_ausgeben(liste: Einkaufsliste) -> ListeAusgabe:
    return ListeAusgabe(
        id=liste.id, name=liste.name, artikel=[artikel_ausgeben(artikel) for artikel in liste.artikel],
        fortschritt=Fortschritt.model_validate(business.fortschritt_berechnen(liste.artikel)),
    )


@router.get("/listen", response_model=list[ListeAusgabe])
def alle_listen(session: Session = Depends(get_session)):
    return [liste_ausgeben(liste) for liste in business.alle_listen(session)]


@router.post("/listen", response_model=ListeAusgabe, status_code=201)
def liste_erstellen(daten: ListeEingabe, session: Session = Depends(get_session)):
    return liste_ausgeben(business.liste_erstellen(session, daten.name))


@router.get("/listen/{liste_id}", response_model=ListeAusgabe)
def liste_anzeigen(liste_id: int, session: Session = Depends(get_session)):
    return liste_ausgeben(business.liste_finden(session, liste_id))


@router.put("/listen/{liste_id}", response_model=ListeAusgabe)
def liste_bearbeiten(liste_id: int, daten: ListeEingabe, session: Session = Depends(get_session)):
    return liste_ausgeben(business.liste_bearbeiten(session, liste_id, daten.name))


@router.delete("/listen/{liste_id}", status_code=204, response_class=Response)
def liste_loeschen(liste_id: int, session: Session = Depends(get_session)):
    business.liste_loeschen(session, liste_id)
    return Response(status_code=204)


@router.post("/listen/{liste_id}/artikel", response_model=ArtikelAusgabe, status_code=201)
def artikel_hinzufuegen(liste_id: int, daten: ArtikelEingabe, session: Session = Depends(get_session)):
    return artikel_ausgeben(business.artikel_hinzufuegen(session, liste_id, daten.name, daten.menge, daten.einheit))


@router.patch("/artikel/{artikel_id}/status", response_model=ArtikelAusgabe)
def artikel_status_setzen(artikel_id: int, daten: ArtikelStatusEingabe, session: Session = Depends(get_session)):
    return artikel_ausgeben(business.artikel_status_setzen(session, artikel_id, daten.gekauft))


@router.post("/artikel/{artikel_id}/teileinkauf", response_model=ArtikelAusgabe)
def teileinkauf_erfassen(artikel_id: int, daten: TeileinkaufEingabe, session: Session = Depends(get_session)):
    return artikel_ausgeben(business.teileinkauf_erfassen(session, artikel_id, daten.zusaetzliche_menge))


@router.put("/artikel/{artikel_id}", response_model=ArtikelAusgabe)
def artikel_bearbeiten(artikel_id: int, daten: ArtikelEingabe, session: Session = Depends(get_session)):
    # Dasselbe Eingabeschema wie beim Hinzufügen: Name, Menge und Einheit, ohne Status.
    return artikel_ausgeben(business.artikel_bearbeiten(session, artikel_id, daten.name, daten.menge, daten.einheit))


@router.delete("/artikel/{artikel_id}", status_code=204, response_class=Response)
def artikel_loeschen(artikel_id: int, session: Session = Depends(get_session)):
    business.artikel_loeschen(session, artikel_id)
    return Response(status_code=204)
