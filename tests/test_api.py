from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import business, main
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
        with Session(engine, expire_on_commit=False) as session:
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
    startseite = api.get("/")
    assert startseite.status_code == 200
    assert startseite.headers["cache-control"] == "no-cache"
    script = api.get("/static/app.js")
    assert script.status_code == 200
    assert script.headers["cache-control"] == "no-cache"
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
        assert gespeichert.gekauft_ohne_menge is False
        assert Decimal(gespeichert.gekaufte_menge) == (Decimal("2.5") if gekauft else 0)
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


def teileinkauf_anlegen(api, menge=None):
    liste = api.post("/api/listen", json={"name": "Migros"}).json()
    listen_pfad = f"/api/listen/{liste['id']}"
    response = api.post(f"{listen_pfad}/artikel", json={"name": "Kartoffeln", "menge": menge, "einheit": "kg"})
    assert response.status_code == 201
    return listen_pfad, f"/api/artikel/{response.json()['id']}"


def test_teileinkauf_bis_zum_vollstaendigen_einkauf(client):
    api, _ = client
    liste, artikel = teileinkauf_anlegen(api, "3")
    zweite_liste = api.post("/api/listen", json={"name": "Aldi"}).json()
    assert api.get(liste).json()["artikel"][0]["status"] == "offen"

    for zusatz, gekauft, rest, status in [
        ("2", "2", "1", "teilweise_gekauft"),
        ("1", "3", "0", "gekauft"),
    ]:
        response = api.post(f"{artikel}/teileinkauf", json={"zusaetzliche_menge": zusatz})
        assert response.status_code == 200
        daten = response.json()
        assert Decimal(daten["menge"]) == 3 and daten["einheit"] == "kg"
        assert Decimal(daten["gekaufte_menge"]) == Decimal(gekauft)
        assert Decimal(daten["restmenge"]) == Decimal(rest)
        assert daten["status"] == status
        assert daten["gekauft"] is (status == "gekauft")
        gespeichert = api.get(liste).json()
        assert gespeichert["artikel"] == [daten]
        assert gespeichert["fortschritt"]["gekauft"] == int(daten["gekauft"])
        assert api.get(f"/api/listen/{zweite_liste['id']}").json()["artikel"] == []

    assert api.post(f"{artikel}/teileinkauf", json={"zusaetzliche_menge": "1"}).status_code == 422
    assert api.get(liste).json()["artikel"] == [daten]


def test_dezimaler_teileinkauf_und_checkbox(client):
    api, _ = client
    liste, artikel = teileinkauf_anlegen(api, "0.301")
    for menge in ("0.1000", "0.2"):
        assert api.post(f"{artikel}/teileinkauf", json={"zusaetzliche_menge": menge}).status_code == 200
    assert Decimal(api.get(liste).json()["artikel"][0]["restmenge"]) == Decimal("0.001")
    for wert, gekauft, rest in [(True, "0.301", "0"), (False, "0", "0.301")]:
        daten = api.patch(f"{artikel}/status", json={"gekauft": wert}).json()
        assert daten["gekauft"] is wert
        assert Decimal(daten["gekaufte_menge"]) == Decimal(gekauft)
        assert Decimal(daten["restmenge"]) == Decimal(rest)


def test_teileinkauf_behaelt_tausendstel_bei_grosser_geplanter_menge(client):
    api, _ = client
    liste, artikel = teileinkauf_anlegen(api, "1000000000000000000000000000000")
    assert api.post(f"{artikel}/teileinkauf", json={"zusaetzliche_menge": "0.001"}).status_code == 200
    daten = api.get(liste).json()["artikel"][0]
    assert Decimal(daten["gekaufte_menge"]) == Decimal("0.001")
    assert daten["restmenge"] == "999999999999999999999999999999.999"
    assert daten["status"] == "teilweise_gekauft"
    assert api.put(artikel, json={"name": "Kartoffeln", "menge": "1e400", "einheit": "kg"}).status_code == 422
    assert api.get(liste).json()["artikel"] == [daten]


@pytest.mark.parametrize("menge", ["-1", "0", "abc", "0.0001", "1.001", "NaN", None])
def test_ungueltiger_teileinkauf_aendert_nichts(client, menge):
    api, _ = client
    liste, artikel = teileinkauf_anlegen(api, "3")
    assert api.post(f"{artikel}/teileinkauf", json={"zusaetzliche_menge": "2"}).status_code == 200
    vorher = api.get(liste).json()
    response = api.post(f"{artikel}/teileinkauf", json={"zusaetzliche_menge": menge})
    assert response.status_code == 422
    assert isinstance(response.json()["detail"], str)
    assert api.get(liste).json() == vorher


def test_kein_teileinkauf_ohne_menge_und_checkbox_funktioniert(client):
    api, _ = client
    _, artikel = teileinkauf_anlegen(api)
    assert api.post(f"{artikel}/teileinkauf", json={"zusaetzliche_menge": "1"}).status_code == 422
    assert api.post("/api/artikel/999/teileinkauf", json={"zusaetzliche_menge": "1"}).status_code == 404
    for wert, status in [(True, "gekauft"), (False, "offen")]:
        daten = api.patch(f"{artikel}/status", json={"gekauft": wert}).json()
        assert daten["status"] == status
        assert daten["gekaufte_menge"] is None and daten["restmenge"] is None


def test_bearbeiten_behaelt_teileinkauf(client):
    api, _ = client
    liste, artikel = teileinkauf_anlegen(api, "3")
    api.post(f"{artikel}/teileinkauf", json={"zusaetzliche_menge": "2"})

    response = api.put(artikel, json={"name": "Festkochende Kartoffeln", "menge": "4", "einheit": "kg"})
    assert response.status_code == 200
    daten = response.json()
    assert Decimal(daten["gekaufte_menge"]) == Decimal(daten["restmenge"]) == 2
    assert daten["status"] == "teilweise_gekauft"
    for menge, einheit in [("1", "kg"), (None, "kg"), ("4", "g")]:
        assert api.put(artikel, json={"name": "Anderer Name", "menge": menge, "einheit": einheit}).status_code == 422
        assert api.get(liste).json()["artikel"] == [daten]
    response = api.put(artikel, json={"name": daten["name"], "menge": "2", "einheit": "kg"})
    assert response.json()["status"] == "gekauft"
    response = api.put(artikel, json={"name": daten["name"], "menge": "3", "einheit": "kg"})
    assert response.json()["status"] == "teilweise_gekauft"
    assert Decimal(response.json()["gekaufte_menge"]) == 2


def test_gekaufte_menge_korrigieren_ersetzt_statt_zu_addieren(client):
    api, _ = client
    liste, artikel = teileinkauf_anlegen(api, "3")
    assert api.post(f"{artikel}/teileinkauf", json={"zusaetzliche_menge": "2"}).status_code == 200
    korrektur = f"{artikel}/gekaufte-menge"
    vorher = api.get(liste).json()
    for ungueltig in ("-1", "3.001", "1.5001", "abc", None):
        assert api.patch(korrektur, json={"gekaufte_menge": ungueltig}).status_code == 422
        assert api.get(liste).json() == vorher

    for menge, rest, status in [
        ("1.5", "1.5", "teilweise_gekauft"),
        ("1.5", "1.5", "teilweise_gekauft"),
        ("3", "0", "gekauft"),
        ("2", "1", "teilweise_gekauft"),
        ("0", "3", "offen"),
    ]:
        response = api.patch(korrektur, json={"gekaufte_menge": menge})
        assert response.status_code == 200
        daten = response.json()
        assert Decimal(daten["gekaufte_menge"]) == Decimal(menge)
        assert Decimal(daten["restmenge"]) == Decimal(rest)
        assert daten["status"] == status
        assert Decimal(daten["menge"]) == 3 and daten["einheit"] == "kg"
        liste_danach = api.get(liste).json()
        assert liste_danach["artikel"] == [daten]
        assert liste_danach["fortschritt"]["gekauft"] == int(status == "gekauft")


def test_gekaufte_menge_korrigieren_benoetigt_artikel_mit_menge(client):
    api, _ = client
    _, artikel = teileinkauf_anlegen(api)
    assert api.patch(f"{artikel}/gekaufte-menge", json={"gekaufte_menge": "1"}).status_code == 422
    assert api.patch("/api/artikel/999/gekaufte-menge", json={"gekaufte_menge": "1"}).status_code == 404


def test_parallele_teileinkaeufe_addieren_auf_dem_aktuellen_stand(client):
    api, _ = client
    liste, artikel = teileinkauf_anlegen(api, "3")
    with ThreadPoolExecutor(max_workers=2) as executor:
        abfragen = [
            executor.submit(api.post, f"{artikel}/teileinkauf", json={"zusaetzliche_menge": menge})
            for menge in ("1", "2")
        ]
        assert [abfrage.result().status_code for abfrage in abfragen] == [200, 200]
    assert api.get(liste).json()["artikel"][0]["status"] == "gekauft"


def test_datenbankfehler_rollt_bereits_ausgefuehrte_aenderung_zurueck(client):
    api, engine = client
    liste, artikel = teileinkauf_anlegen(api, "3")
    artikel_id = int(artikel.rsplit("/", 1)[1])
    vorher = api.get(liste).json()
    with engine.begin() as verbindung:
        verbindung.exec_driver_sql("""
            CREATE TRIGGER test_fehler AFTER UPDATE OF gekaufte_menge ON einkaufsartikel
            BEGIN
                UPDATE einkaufslisten SET name = 'Fehlerhafte Aenderung';
                SELECT RAISE(FAIL, 'Testfehler nach der Aenderung');
            END
        """)
    with Session(engine) as session:
        with pytest.raises(IntegrityError, match="Testfehler"):
            business.teileinkauf_erfassen(session, artikel_id, Decimal("2"))
        assert not session.in_transaction()
        assert Decimal(session.get(Einkaufsartikel, artikel_id).gekaufte_menge) == 0
    assert api.get(liste).json() == vorher


def test_start_migriert_altbestand_einmal_ohne_datenverlust(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{(tmp_path / 'altbestand.sqlite3').as_posix()}")
    monkeypatch.setattr(main, "engine", engine)

    def test_session():
        with Session(engine, expire_on_commit=False) as session:
            yield session

    main.app.dependency_overrides[get_session] = test_session
    try:
        with engine.begin() as verbindung:
            verbindung.exec_driver_sql("CREATE TABLE einkaufslisten (id INTEGER PRIMARY KEY, name VARCHAR NOT NULL)")
            verbindung.exec_driver_sql("""
                CREATE TABLE einkaufsartikel (
                    id INTEGER PRIMARY KEY, einkaufsliste_id INTEGER NOT NULL,
                    name VARCHAR NOT NULL, menge NUMERIC, einheit VARCHAR, gekauft BOOLEAN NOT NULL,
                    FOREIGN KEY(einkaufsliste_id) REFERENCES einkaufslisten(id) ON DELETE CASCADE
                )
            """)
            verbindung.exec_driver_sql("INSERT INTO einkaufslisten VALUES (1, 'Migros')")
            verbindung.exec_driver_sql("""
                INSERT INTO einkaufsartikel VALUES
                  (1, 1, 'Milch', 1.125, 'Liter', 1), (2, 1, 'Reis', 3, 'kg', 0),
                  (3, 1, 'Brot', NULL, NULL, 1), (4, 1, 'Zucker', 1.23456, 'kg', 1)
            """)
        with TestClient(main.app) as api:
            vorher = api.get("/api/listen/1").json()
            assert vorher["name"] == "Migros"
            artikel = vorher["artikel"]
            assert [a["status"] for a in artikel] == ["gekauft", "offen", "gekauft", "gekauft"]
            assert Decimal(artikel[0]["gekaufte_menge"]) == Decimal("1.125")
            assert artikel[2]["gekaufte_menge"] is None
            assert Decimal(artikel[3]["gekaufte_menge"]) == Decimal("1.23456")
            assert vorher["fortschritt"]["gekauft"] == 3
            assert api.post("/api/artikel/4/teileinkauf", json={"zusaetzliche_menge": "0.1"}).status_code == 422
            assert api.post("/api/artikel/2/teileinkauf", json={"zusaetzliche_menge": "2"}).status_code == 200
            erwartet = api.get("/api/listen/1").json()
        with TestClient(main.app) as api:
            assert api.get("/api/listen/1").json() == erwartet
    finally:
        main.app.dependency_overrides.clear()
        engine.dispose()
