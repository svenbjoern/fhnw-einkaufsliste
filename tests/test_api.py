import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session

from app import main
from app.database import get_session, sqlite_fremdschluessel_aktivieren
from app.models import Einkaufsartikel


@pytest.fixture
def anwendung(tmp_path, monkeypatch):
    pfad = tmp_path / "test.sqlite3"
    engine = create_engine(f"sqlite:///{pfad.as_posix()}")
    event.listen(engine, "connect", sqlite_fremdschluessel_aktivieren)

    def test_session():
        with Session(engine, expire_on_commit=False) as session:
            yield session

    monkeypatch.setattr(main, "engine", engine)
    main.app.dependency_overrides[get_session] = test_session
    try:
        with TestClient(main.app) as browser:
            yield browser, engine
    finally:
        main.app.dependency_overrides.clear()
        engine.dispose()


@pytest.fixture
def api(anwendung):
    browser, _ = anwendung
    return browser


def liste_anlegen(api, name="Migros"):
    antwort = api.post("/api/listen", json={"name": name})
    assert antwort.status_code == 201
    return f"/api/listen/{antwort.json()['id']}"


def artikel_anlegen(api, listenpfad, name="Kartoffeln", menge=3):
    antwort = api.post(f"{listenpfad}/artikel", json={"name": name, "menge": menge, "einheit": "kg"})
    assert antwort.status_code == 201
    return f"/api/artikel/{antwort.json()['id']}"


def teileinkauf(api, artikelpfad, menge):
    return api.post(f"{artikelpfad}/teileinkauf", json={"zusaetzliche_menge": menge})


def test_startseite_und_api_dokumentation(api):
    assert "theme-schalter" in api.get("/").text
    assert api.get("/static/app.js").status_code == 200
    assert api.get("/docs").status_code == 200
    assert "/api/artikel/{artikel_id}/gekaufte-menge" not in api.get("/openapi.json").json()["paths"]


def test_liste_erstellen_anzeigen_und_umbenennen(api):
    pfad = liste_anlegen(api, "  Migros  ")
    assert api.get(pfad).json()["name"] == "Migros"

    antwort = api.put(pfad, json={"name": "Aldi"})
    assert antwort.status_code == 200
    assert [liste["name"] for liste in api.get("/api/listen").json()] == ["Aldi"]


def test_liste_loeschen_kaskadiert(anwendung):
    api, engine = anwendung
    migros = liste_anlegen(api)
    aldi = liste_anlegen(api, "Aldi")
    artikel_anlegen(api, migros)
    artikel_anlegen(api, aldi, name="Äpfel")

    assert api.delete(migros).status_code == 204
    assert api.get(migros).status_code == 404
    with Session(engine) as session:
        assert list(session.scalars(select(Einkaufsartikel.name))) == ["Äpfel"]


def test_artikel_erstellen_anzeigen_bearbeiten_und_loeschen(api):
    liste = liste_anlegen(api)
    artikel = artikel_anlegen(api, liste)
    assert api.get(liste).json()["artikel"][0]["name"] == "Kartoffeln"

    antwort = api.put(artikel, json={"name": "  Mehl ", "menge": 1.5, "einheit": " kg "})
    assert antwort.status_code == 200
    daten = antwort.json()
    assert (daten["name"], daten["menge"], daten["einheit"]) == ("Mehl", 1.5, "kg")

    assert api.delete(artikel).status_code == 204
    assert api.get(liste).json()["artikel"] == []


def test_checkbox_mit_menge(api):
    artikel = artikel_anlegen(api, liste_anlegen(api))
    daten = api.patch(f"{artikel}/status", json={"gekauft": True}).json()
    assert daten["status"] == "gekauft"
    assert daten["gekaufte_menge"] == 3
    assert daten["restmenge"] == 0
    assert "gekauft" not in daten

    daten = api.patch(f"{artikel}/status", json={"gekauft": False}).json()
    assert daten["status"] == "offen"
    assert daten["gekaufte_menge"] == 0
    assert daten["restmenge"] == 3


def test_checkbox_ohne_menge(api):
    artikel = artikel_anlegen(api, liste_anlegen(api), menge=None)
    daten = api.patch(f"{artikel}/status", json={"gekauft": True}).json()
    assert daten["status"] == "gekauft"
    assert daten["restmenge"] is None
    daten = api.patch(f"{artikel}/status", json={"gekauft": False}).json()
    assert daten["status"] == "offen"


def test_teileinkauf_bis_gekauft(api):
    liste = liste_anlegen(api)
    artikel = artikel_anlegen(api, liste)

    erster = teileinkauf(api, artikel, 2)
    assert erster.status_code == 200
    assert erster.json()["status"] == "teilweise_gekauft"
    assert erster.json()["restmenge"] == 1

    zweiter = teileinkauf(api, artikel, 1)
    assert zweiter.status_code == 200
    daten = zweiter.json()
    assert daten["status"] == "gekauft"
    assert daten["gekaufte_menge"] == 3
    assert daten["restmenge"] == 0
    assert api.get(liste).json()["artikel"] == [daten]
    assert teileinkauf(api, artikel, 1).status_code == 422


def test_teileinkauf_ueber_restmenge(api):
    liste = liste_anlegen(api)
    artikel = artikel_anlegen(api, liste)
    assert teileinkauf(api, artikel, 2).status_code == 200

    antwort = teileinkauf(api, artikel, 2)
    assert antwort.status_code == 422
    assert "Restmenge" in antwort.json()["detail"]
    daten = api.get(liste).json()["artikel"][0]
    assert daten["gekaufte_menge"] == 2


def test_teileinkauf_ohne_geplante_menge(api):
    artikel = artikel_anlegen(api, liste_anlegen(api), menge=None)
    antwort = teileinkauf(api, artikel, 1)
    assert antwort.status_code == 422
    assert "geplante Menge" in antwort.json()["detail"]


def test_fortschritt_zaehlt_nur_vollstaendig_gekaufte_artikel(api):
    liste = liste_anlegen(api)
    assert api.get(liste).json()["fortschritt"] == {"gekauft": 0, "gesamt": 0, "prozent": 0}

    fertig = artikel_anlegen(api, liste, name="Mehl")
    teilweise = artikel_anlegen(api, liste)
    artikel_anlegen(api, liste, name="Brot", menge=None)
    api.patch(f"{fertig}/status", json={"gekauft": True})
    teileinkauf(api, teilweise, 2)

    assert api.get(liste).json()["fortschritt"] == {"gekauft": 1, "gesamt": 3, "prozent": 33.3}


def test_artikelbearbeitung_behaelt_gekaufte_menge(api):
    liste = liste_anlegen(api)
    artikel = artikel_anlegen(api, liste)
    teileinkauf(api, artikel, 2)

    antwort = api.put(artikel, json={"name": "Rote Kartoffeln", "menge": 4, "einheit": "kg"})
    assert antwort.status_code == 200
    assert antwort.json()["gekaufte_menge"] == 2
    assert antwort.json()["restmenge"] == 2

    for menge, einheit in [(1, "kg"), (None, "kg"), (4, "g")]:
        ungueltig = api.put(artikel, json={"name": "Kartoffeln", "menge": menge, "einheit": einheit})
        assert ungueltig.status_code == 422
    assert api.get(liste).json()["artikel"] == [antwort.json()]


def test_nicht_vorhandene_id_gibt_404(api):
    assert api.get("/api/listen/999").json()["detail"] == "Die Einkaufsliste wurde nicht gefunden."
    antwort = api.delete("/api/artikel/999")
    assert antwort.status_code == 404
    assert antwort.json()["detail"] == "Der Einkaufsartikel wurde nicht gefunden."


def test_falsches_format_gibt_verstaendliches_detail(api):
    antwort = api.post("/api/listen", json={"name": "  "})
    assert antwort.status_code == 422
    assert "Namen" in antwort.json()["detail"]

    liste = liste_anlegen(api)
    antwort = api.post(f"{liste}/artikel", json={"name": "Reis", "menge": -1})
    assert antwort.status_code == 422
    assert "Menge" in antwort.json()["detail"]
    artikel = artikel_anlegen(api, liste)
    assert teileinkauf(api, artikel, "viel").status_code == 422
