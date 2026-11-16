from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app import business
from app.database import get_session
from app.schemas import ArtikelAusgabe, ArtikelErstellen, ArtikelStatus, ListeAusgabe, ListeErstellen

router = APIRouter(prefix="/api", tags=["Einkaufslisten"])


@router.get("/listen", response_model=list[ListeAusgabe])
def alle_listen(session: Session = Depends(get_session)):
    return business.alle_listen(session)


@router.post("/listen", response_model=ListeAusgabe, status_code=201)
def liste_erstellen(daten: ListeErstellen, session: Session = Depends(get_session)):
    return business.liste_erstellen(session, daten.name)


@router.get("/listen/{liste_id}", response_model=ListeAusgabe)
def liste_anzeigen(liste_id: int, session: Session = Depends(get_session)):
    return business.liste_anzeigen(session, liste_id)


@router.put("/listen/{liste_id}", response_model=ListeAusgabe)
def liste_bearbeiten(liste_id: int, daten: ListeErstellen, session: Session = Depends(get_session)):
    return business.liste_bearbeiten(session, liste_id, daten.name)


@router.delete("/listen/{liste_id}", status_code=204, response_class=Response)
def liste_loeschen(liste_id: int, session: Session = Depends(get_session)):
    business.liste_loeschen(session, liste_id)
    return Response(status_code=204)


@router.post("/listen/{liste_id}/artikel", response_model=ArtikelAusgabe, status_code=201)
def artikel_hinzufuegen(liste_id: int, daten: ArtikelErstellen, session: Session = Depends(get_session)):
    return business.artikel_hinzufuegen(session, liste_id, daten)


@router.patch("/artikel/{artikel_id}/status", response_model=ArtikelAusgabe)
def artikel_status_setzen(artikel_id: int, daten: ArtikelStatus, session: Session = Depends(get_session)):
    return business.artikel_status_setzen(session, artikel_id, daten.gekauft)


@router.put("/artikel/{artikel_id}", response_model=ArtikelAusgabe)
def artikel_bearbeiten(artikel_id: int, daten: ArtikelErstellen, session: Session = Depends(get_session)):
    # Dasselbe Eingabeschema wie beim Hinzufügen: Name, Menge und Einheit, ohne Status.
    return business.artikel_bearbeiten(session, artikel_id, daten)


@router.delete("/artikel/{artikel_id}", status_code=204, response_class=Response)
def artikel_loeschen(artikel_id: int, session: Session = Depends(get_session)):
    business.artikel_loeschen(session, artikel_id)
    return Response(status_code=204)
