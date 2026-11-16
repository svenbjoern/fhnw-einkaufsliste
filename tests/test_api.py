from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session

from app import main
from app.database import Base, get_session
from app.models import Einkaufsartikel, Einkaufsliste


@pytest.fixture
def client(tmp_path, monkeypatch):
    # Jede Prüfung erhält eine eigene Datenbank; die lokale Anwendung bleibt unberührt.
    engine = create_engine(f"sqlite:///{(tmp_path / 'test.sqlite3').as_posix()}",
                           connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def foreign_keys(connection, record):
        connection.execute("PRAGMA foreign_keys=ON")

    def test_session():
        with Session(engine) as session:
            yield session

    monkeypatch.setattr(main, "engine", engine)
    main.app.dependency_overrides[get_session] = test_session
    try:
        with TestClient(main.app) as test_client:
            yield test_client, engine
    finally:
        main.app.dependency_overrides.clear()
        engine.dispose()


def test_end_to_end(client):
    api, engine = client
    assert api.get("/").status_code == 200
    assert api.get("/static/app.js").status_code == 200
    assert api.get("/docs").status_code == 200
    assert api.get("/api/listen").json() == []
    response = api.post("/api/listen", json={"name": "  Migros "})
    assert response.status_code == 201
    liste = response.json()
    assert liste["name"] == "Migros"
    assert liste["fortschritt"] == {"gekauft": 0, "gesamt": 0, "prozent": 0}
    pfad = f"/api/listen/{liste['id']}"
    response = api.post(f"{pfad}/artikel", json={"name": " Milch ", "menge": "1.5", "einheit": " Liter "})
    assert response.status_code == 201
    artikel = response.json()
    assert artikel["name"] == "Milch"
    assert artikel["einheit"] == "Liter"
    assert float(artikel["menge"]) == 1.5
    assert artikel["gekauft"] is False
    status_pfad = f"/api/artikel/{artikel['id']}/status"
    assert api.patch(status_pfad, json={"gekauft": True}).status_code == 200
    assert api.get(pfad).json()["fortschritt"] == {"gekauft": 1, "gesamt": 1, "prozent": 100}
    assert api.get("/api/listen").json()[0]["fortschritt"]["gekauft"] == 1
    assert api.patch(status_pfad, json={"gekauft": False}).json()["gekauft"] is False
    assert api.get(pfad).json()["fortschritt"]["prozent"] == 0
    optional = api.post(f"{pfad}/artikel", json={"name": "Brot"}).json()
    assert optional["menge"] is None and optional["einheit"] is None
    # Auch beim direkten ORM-Löschen muss die Modellbeziehung kaskadieren.
    with Session(engine) as session:
        session.delete(session.get(Einkaufsliste, liste["id"]))
        session.commit()
        assert list(session.scalars(select(Einkaufsartikel))) == []


def test_fehler(client):
    api, _ = client
    assert api.get("/api/listen/999").status_code == 404
    assert api.patch("/api/artikel/999/status", json={"gekauft": True}).status_code == 404
    assert api.post("/api/listen/999/artikel", json={"name": "Milch"}).status_code == 404
    assert api.post("/api/listen", json={"name": " "}).status_code == 422
    assert api.post("/api/listen", json={}).status_code == 422
    liste = api.post("/api/listen", json={"name": "Test"}).json()
    for daten in [{"name": " "}, {"name": "Milch", "menge": "-1"}, {"name": "Milch", "menge": "abc"}]:
        response = api.post(f"/api/listen/{liste['id']}/artikel", json=daten)
        assert response.status_code == 422
        assert isinstance(response.json()["detail"], str)


@pytest.mark.parametrize("gekauft", [False, True])
def test_artikel_bearbeiten(client, gekauft):
    api, engine = client
    liste = api.post("/api/listen", json={"name": "Migros"}).json()
    listen_pfad = f"/api/listen/{liste['id']}"
    artikel = api.post(f"{listen_pfad}/artikel", json={"name": "Milch"}).json()
    pfad = f"/api/artikel/{artikel['id']}"
    api.patch(f"{pfad}/status", json={"gekauft": gekauft})

    response = api.put(pfad, json={"name": " Hafermilch ", "menge": "2.5", "einheit": " Liter "})
    assert response.status_code == 200
    assert response.json()["name"] == "Hafermilch"
    assert response.json()["einheit"] == "Liter"
    assert response.json()["gekauft"] is gekauft
    with Session(engine) as session:
        gespeichert = session.get(Einkaufsartikel, artikel["id"])
        assert gespeichert.name == "Hafermilch"
        assert float(gespeichert.menge) == 2.5
        assert gespeichert.einheit == "Liter"
        assert gespeichert.gekauft is gekauft
        assert gespeichert.einkaufsliste_id == liste["id"]

    response = api.put(pfad, json={"name": "Brot", "menge": None, "einheit": "  "})
    assert response.status_code == 200
    assert response.json()["menge"] is None
    assert response.json()["einheit"] is None
    assert response.json()["gekauft"] is gekauft
    daten = api.get(listen_pfad).json()
    assert daten["artikel"][0]["name"] == "Brot"
    assert daten["fortschritt"]["gekauft"] == int(gekauft)


@pytest.mark.parametrize("daten", [
    {"name": " "},
    {"name": "Neu", "menge": "0"},
    {"name": "Neu", "menge": "-1"},
    {"name": "Neu", "menge": "abc"},
    {},
])
def test_bearbeiten_mit_ungueltigen_daten_aendert_nichts(client, daten):
    api, _ = client
    liste = api.post("/api/listen", json={"name": "Migros"}).json()
    listen_pfad = f"/api/listen/{liste['id']}"
    artikel = api.post(f"{listen_pfad}/artikel", json={"name": "Milch", "menge": "2", "einheit": "Liter"}).json()
    response = api.put(f"/api/artikel/{artikel['id']}", json=daten)
    assert response.status_code == 422
    assert isinstance(response.json()["detail"], str)
    assert api.get(listen_pfad).json()["artikel"] == [artikel]


@pytest.mark.parametrize("gekauft", [False, True])
def test_artikel_loeschen_aktualisiert_fortschritt(client, gekauft):
    api, engine = client
    liste = api.post("/api/listen", json={"name": "Migros"}).json()
    listen_pfad = f"/api/listen/{liste['id']}"
    offen = api.post(f"{listen_pfad}/artikel", json={"name": "Brot"}).json()
    gekauft_artikel = api.post(f"{listen_pfad}/artikel", json={"name": "Milch"}).json()
    api.patch(f"/api/artikel/{gekauft_artikel['id']}/status", json={"gekauft": True})
    assert api.get(listen_pfad).json()["fortschritt"]["prozent"] == 50

    entfernt = gekauft_artikel if gekauft else offen
    verbleibend = offen if gekauft else gekauft_artikel
    pfad = f"/api/artikel/{entfernt['id']}"
    response = api.delete(pfad)
    assert response.status_code == 204
    assert response.content == b""
    with Session(engine) as session:
        assert session.get(Einkaufsartikel, entfernt["id"]) is None
        assert session.get(Einkaufsliste, liste["id"]) is not None
    daten = api.get(listen_pfad).json()
    assert [a["id"] for a in daten["artikel"]] == [verbleibend["id"]]
    assert daten["fortschritt"] == {"gekauft": int(not gekauft), "gesamt": 1, "prozent": 0 if gekauft else 100}
    assert api.get("/api/listen").json()[0]["fortschritt"] == daten["fortschritt"]
    assert api.delete(pfad).status_code == 404

    assert api.delete(f"/api/artikel/{verbleibend['id']}").status_code == 204
    assert api.get(listen_pfad).json()["fortschritt"] == {"gekauft": 0, "gesamt": 0, "prozent": 0}


def test_bearbeiten_und_loeschen_nicht_vorhandener_artikel(client):
    api, _ = client
    for response in [
        api.put("/api/artikel/999", json={"name": "Milch"}),
        api.delete("/api/artikel/999"),
    ]:
        assert response.status_code == 404
        assert response.json()["detail"] == "Der Einkaufsartikel wurde nicht gefunden."


def test_liste_umbenennen_nach_id_behaelt_artikel(client):
    api, engine = client
    erste = api.post("/api/listen", json={"name": "Aldi"}).json()
    zweite = api.post("/api/listen", json={"name": "Aldi"}).json()
    pfad = f"/api/listen/{erste['id']}"
    artikel = api.post(f"{pfad}/artikel", json={"name": "Milch", "menge": "1.125", "einheit": "Liter"}).json()
    api.patch(f"/api/artikel/{artikel['id']}/status", json={"gekauft": True})
    vorher = api.get(pfad).json()
    response = api.put(pfad, json={"name": " Migros "})
    assert response.status_code == 200
    assert response.json()["name"] == "Migros"
    assert response.json()["artikel"] == vorher["artikel"]
    assert response.json()["fortschritt"] == vorher["fortschritt"]
    assert api.get(f"/api/listen/{zweite['id']}").json()["name"] == "Aldi"
    with Session(engine) as session:
        assert session.get(Einkaufsliste, erste["id"]).name == "Migros"
        assert session.get(Einkaufsartikel, artikel["id"]).einkaufsliste_id == erste["id"]
    # Auch Umbenennen auf einen bereits vorhandenen Namen bleibt erlaubt.
    assert api.put(pfad, json={"name": "Aldi"}).status_code == 200
    assert [liste["name"] for liste in api.get("/api/listen").json()] == ["Aldi", "Aldi"]
    for daten in [{"name": " "}, {}]:
        assert api.put(pfad, json=daten).status_code == 422
        assert api.get(pfad).json()["name"] == "Aldi"


@pytest.mark.parametrize("mit_artikeln", [False, True])
def test_liste_loeschen_kaskadiert_nur_zugehoerige_artikel(client, mit_artikeln):
    api, engine = client
    erste = api.post("/api/listen", json={"name": "Aldi"}).json()
    zweite = api.post("/api/listen", json={"name": "Aldi"}).json()
    pfad = f"/api/listen/{erste['id']}"
    if mit_artikeln:
        api.post(f"{pfad}/artikel", json={"name": "Brot"})
        gekauft = api.post(f"{pfad}/artikel", json={"name": "Milch"}).json()
        api.patch(f"/api/artikel/{gekauft['id']}/status", json={"gekauft": True})
    behalten = api.post(f"/api/listen/{zweite['id']}/artikel", json={"name": "Eier"}).json()
    response = api.delete(pfad)
    assert response.status_code == 204 and response.content == b""
    assert api.get(pfad).status_code == 404
    assert [liste["id"] for liste in api.get("/api/listen").json()] == [zweite["id"]]
    with Session(engine) as session:
        assert session.get(Einkaufsliste, erste["id"]) is None
        assert [artikel.id for artikel in session.scalars(select(Einkaufsartikel))] == [behalten["id"]]
    assert api.delete(f"/api/listen/{zweite['id']}").status_code == 204
    assert api.get("/api/listen").json() == []


def test_listenaktionen_nicht_vorhandener_id(client):
    api, _ = client
    for response in [api.put("/api/listen/999", json={"name": "Aldi"}), api.delete("/api/listen/999")]:
        assert response.status_code == 404
        assert response.json()["detail"] == "Die Einkaufsliste wurde nicht gefunden."


def test_mengenpraezision_beim_hinzufuegen_und_bearbeiten(client):
    api, _ = client
    liste = api.post("/api/listen", json={"name": "Test"}).json()
    pfad = f"/api/listen/{liste['id']}"
    artikel = api.post(f"{pfad}/artikel", json={"name": "Milch", "menge": "1.125"}).json()
    assert Decimal(artikel["menge"]) == Decimal("1.125")
    for menge in ["1.1251", "0.0001"]:
        daten = {"name": "Milch", "menge": menge}
        for response in [api.post(f"{pfad}/artikel", json=daten), api.put(f"/api/artikel/{artikel['id']}", json=daten)]:
            assert response.status_code == 422
            assert "maximal drei Nachkommastellen" in response.json()["detail"]
        assert api.get(pfad).json()["artikel"] == [artikel]


def test_bestehende_mengen_bleiben_lesbar_und_unveraendert(client):
    api, engine = client
    liste = api.post("/api/listen", json={"name": "Altbestand"}).json()
    with Session(engine) as session:
        alt = Einkaufsartikel(einkaufsliste_id=liste["id"], name="Reis", menge=Decimal("1.23456"))
        session.add(alt)
        session.commit()
        artikel_id = alt.id
    pfad = f"/api/listen/{liste['id']}"
    assert Decimal(api.get(pfad).json()["artikel"][0]["menge"]) == Decimal("1.23456")
    assert api.put(pfad, json={"name": "Vorrat"}).status_code == 200
    assert api.patch(f"/api/artikel/{artikel_id}/status", json={"gekauft": True}).status_code == 200
    with Session(engine) as session:
        assert session.get(Einkaufsartikel, artikel_id).menge == Decimal("1.23456")
