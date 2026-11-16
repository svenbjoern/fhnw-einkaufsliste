# fhnw-einkaufsliste
FHNW HS2026 – Webbasierte Anwendungen – Digitale Einkaufsliste – Projektgruppe C

## Stand: Grundfunktionen mit vollständigem CRUD

Ein kleines End-to-End-Beispiel mit Python, FastAPI, SQLAlchemy 2 und SQLite.
Die Oberfläche verwendet HTML, CSS und JavaScript mit `fetch()`.

Bereits umgesetzt:

- Mehrere Einkaufslisten erstellen und anzeigen, zwischen Listen wechseln.
- Einkaufslisten über Bleistift umbenennen und über Papierkorb nach Bestätigung
  mitsamt ihren Artikeln löschen. Gleichnamige Listen sind erlaubt; Aktionen verwenden die ID.
- Artikel mit optionaler Menge und Einheit hinzufügen.
- Artikel über das Bleistift-Symbol in einem vorausgefüllten Dialog bearbeiten;
  „Abbrechen“ oder Escape verwirft die Eingabe. Der gekauft-Status bleibt erhalten.
- Offene und gekaufte Artikel über das Papierkorb-Symbol nach Bestätigung löschen.
- Artikel als gekauft und wieder als offen markieren.
- Fortschritt als Anzahl und Prozent anzeigen, bei leeren Listen 0 %.
- Namen trimmen und leere Namen ablehnen; Mengen müssen endlich, grösser als null
  und auf maximal drei Nachkommastellen beschränkt sein (nachgestellte Nullen zählen nicht).
- Daten dauerhaft speichern; Tabellen werden beim ersten Start angelegt.

Kategorien sind nicht Teil der Anwendung. Ältere Kategorienhinweise in Konzept und Mockup sind überholt.

## Einrichtung und Start (Windows / PowerShell)

Voraussetzung: Python 3.11 oder neuer. Alle Befehle im Repository-Hauptordner ausführen.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Die direkte Verwendung von `python.exe` funktioniert ohne Aktivieren der Umgebung
und ohne Änderung der PowerShell-Ausführungsrichtlinie.

- Anwendung: <http://127.0.0.1:8000/>
- Interaktive API-Dokumentation: <http://127.0.0.1:8000/docs>
- Stoppen: `Strg+C` im Terminal.

Beim Start entsteht `einkaufsliste.sqlite3` im Repository-Hauptordner. Der Pfad wird
aus dem Speicherort von `database.py` ermittelt, ohne hartcodierten absoluten Pfad.
Die Datei und die virtuelle Umgebung werden durch `.gitignore` ausgeschlossen.
`create_all()` legt fehlende Tabellen an, aktualisiert aber keine bestehenden
Tabellenstrukturen. Bei späteren Modelländerungen muss das Team die Datenübernahme planen.
SQLite eignet sich hier für die lokale Projektanwendung; sein NUMERIC-Typ garantiert
keine beliebige Dezimalgenauigkeit. Mengen werden im Python-Code als `Decimal` verarbeitet.
Die Datenbankstruktur bleibt unverändert. Vorhandene Mengen bleiben lesbar und werden
beim Lesen nicht verändert. In Artikelliste und Bearbeitungsformular werden maximal
drei Nachkommastellen ohne überflüssige Nullen angezeigt, z. B. `1.500000` als `1.5`.
Altwerte mit mehr als drei relevanten Nachkommastellen werden nur für die Anzeige gerundet;
beim Speichern des Artikelformulars wird die angezeigte Menge übernommen.
Neue Eingaben mit mehr als drei relevanten Nachkommastellen werden mit einer verständlichen
Fehlermeldung abgelehnt, auch bei direkten API-Aufrufen.

## Manuelle Demo

1. Auf `/` eine Liste namens „Migros“ erstellen.
2. „Milch“, Menge `2`, Einheit „Liter“ hinzufügen.
3. Die Checkbox aktivieren: Der Fortschritt steigt von 0/1 auf 1/1 (100 %).
4. Checkbox deaktivieren: Der Artikel ist wieder offen.
5. Eine zweite Liste erstellen und zwischen den Listen wechseln.
6. Die Seite neu laden: Die Daten bleiben erhalten.
7. Eine Menge von `0` oder `-1` eingeben: Es erscheint eine Fehlermeldung.
8. Beim Artikel auf den Bleistift klicken, Name/Menge/Einheit ändern und speichern.
   Mit „Abbrechen“ werden keine Änderungen gespeichert.
9. Auf den Papierkorb klicken und zuerst abbrechen, danach bestätigen:
   Erst nach Bestätigung verschwindet der Artikel und der Fortschritt wird aktualisiert.
10. Eine Liste links über den Bleistift umbenennen: Ihre Artikel bleiben erhalten.
11. Zwei Listen mit gleichem Namen erstellen und eine davon löschen: Nur die gewählte
    Liste mit ihren Artikeln verschwindet. Beim Löschen der ausgewählten Liste erscheint
    rechts wieder die Startansicht ohne Auswahl.
12. Die Mengen `1.5`, `0.75` und `1.125` prüfen; `1.1251` muss abgelehnt werden.

## Dateien und Schichten

| Datei | Verantwortung |
| --- | --- |
| `app/__init__.py` | Kennzeichnet `app` als Python-Paket. |
| `app/main.py` | Initialisiert FastAPI, legt beim Start Tabellen an, registriert Routen, liefert Frontend aus und übersetzt Fehler in HTTP-Antworten. |
| `app/static/index.html` | Präsentation: Listenübersicht, Detailansicht und Formulare. |
| `app/static/style.css` | Präsentation: Gestaltung und einfacher schmaler Bildschirmaufbau. |
| `app/static/app.js` | Präsentation: `fetch()`-Aufrufe, DOM-Anzeige und Fehlerausgabe. Namen werden über `textContent` angezeigt. |
| `app/services.py` | Service Layer: REST-Routen, Ein-/Ausgabeschemas und Aufruf der Business-Funktionen. |
| `app/schemas.py` | Pydantic-Datentypen für API-Anfragen und Antworten; keine fachlichen Regeln. |
| `app/business.py` | Business Layer: Namen/Mengen prüfen, Datensätze auf Existenz prüfen, Fortschritt berechnen. |
| `app/repository.py` | Persistenz: Datensätze mit SQLAlchemy abfragen und speichern. |
| `app/models.py` | Persistenz: die zwei Entitäten mit Pflichtfeldern, Fremdschlüssel und Beziehung. |
| `app/database.py` | Persistenz: Engine, DeclarativeBase, Sessions und SQLite-Fremdschlüsselaktivierung. |
| `tests/test_business.py` | Mengen-, Namens- und Fortschrittstests. |
| `tests/test_api.py` | API-Ablauf, Fehlercodes, Frontend-Auslieferung und Löschkaskade mit eigener Testdatenbank. |
| `requirements.txt` | Laufzeit- und Testabhängigkeiten mit Versionsbereichen. |
| `.gitignore` | Schliesst lokale Umgebungen, Python-Cache, `.env` und SQLite-Dateien aus. |
| `README.md` | Einrichtung, Architektur, Implementierungsstand und nächste Aufgaben. |

Beispiel „Artikel hinzufügen“:

```text
app.js → POST /api/listen/{id}/artikel → services.py
       → business.py (prüfen) → repository.py (speichern)
       → models.py / database.py → SQLite
```

FastAPI prüft mit Pydantic das Eingabeformat (z. B. ob eine Menge eine Zahl ist).
Die fachliche Prüfung (z. B. Menge > 0) erfolgt in `business.py`.
Pro Anfrage wird eine Session geöffnet und anschliessend geschlossen.
Schreiboperationen werden im Repository mit `commit()` gespeichert.

## Datenmodell

- `Einkaufsliste`: Integer-PK `id`, Pflichtfeld `name`.
- `Einkaufsartikel`: Integer-PK `id`, Pflicht-FK `einkaufsliste_id`, Pflichtfeld
  `name`, optionale Felder `menge` (Decimal/Numeric) und `einheit`, Boolean
  `gekauft` (Standard `False`).
- Eine Liste hat 0 bis n Artikel; ein Artikel gehört genau zu einer Liste.
- Beim Löschen einer Liste werden ihre Artikel mitgelöscht (`delete-orphan` und
  `ON DELETE CASCADE`, SQLite-Fremdschlüssel sind pro Verbindung aktiviert).
- Fortschritt wird aus den Artikeln berechnet und nicht redundant gespeichert.
  Die Prozentanzeige wird auf eine Nachkommastelle gerundet.

## REST-Endpunkte

| Methode | Pfad | Funktion |
| --- | --- | --- |
| GET | `/api/listen` | Alle Listen inklusive Artikeln und Fortschritt |
| POST | `/api/listen` | Liste erstellen: `{"name": "Migros"}` |
| GET | `/api/listen/{liste_id}` | Einzelne Liste inklusive Artikeln und Fortschritt |
| PUT | `/api/listen/{liste_id}` | Liste umbenennen: `{"name": "Aldi"}`; Artikel bleiben unverändert |
| DELETE | `/api/listen/{liste_id}` | Liste mitsamt Artikeln löschen, HTTP 204 ohne Antwortinhalt |
| POST | `/api/listen/{liste_id}/artikel` | Artikel hinzufügen: `{"name": "Milch", "menge": "2", "einheit": "Liter"}` |
| PATCH | `/api/artikel/{artikel_id}/status` | Status setzen: `{"gekauft": true}` bzw. `false` |
| PUT | `/api/artikel/{artikel_id}` | Name, Menge und Einheit ersetzen; gleiches Eingabeschema wie beim Hinzufügen, Status bleibt erhalten |
| DELETE | `/api/artikel/{artikel_id}` | Artikel löschen, HTTP 204 ohne Antwortinhalt |

Erfolgreiche Erstellung liefert HTTP 201, Lesen/Statusänderung HTTP 200.
Fehlende Datensätze liefern HTTP 404, ungültige Eingaben HTTP 422 mit einer
deutschen Meldung unter `detail`. Decimal-Mengen werden in JSON als Strings
ausgegeben. Optionale Felder können fehlen oder `null` sein.
Beim Bearbeiten ersetzt `PUT` alle drei bearbeitbaren Felder. Fehlende optionale
Felder werden daher geleert. Der Status wird ausschliesslich über die Statusroute geändert.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Die Tests verwenden temporäre Datenbanken und verändern die lokale Anwendung nicht.

## Nächste Aufgaben im Team

Die grundlegenden Must-Funktionen sind umgesetzt. Als Nächstes:

1. Gemeinsam die vollständige CRUD-Demo prüfen und jedes Teammitglied den Weg
   eines Aufrufs durch alle Schichten erklären lassen.
2. Für die Abgabe Architektur-/Modelldokumentation, Reflexion und vollständige
   Quellen-/Hilfsmittelliste nach den Modulvorgaben ergänzen. Dieses Grundgerüst
   wurde mit Codex (KI-Unterstützung) erstellt und muss vom Team geprüft und verstanden werden.

Optional bleiben Dark Mode und Sammellöschen. Login, Benutzerverwaltung, Preise,
Artikelsuche und Einkaufshistorie gehören nicht zum vorgesehenen Umfang.

## Vorhandene Projektunterlagen

Berücksichtigt wurden `docs/Projektarbeit_py.pdf`, `docs/Projektkonzept.md`,
`docs/ER-Modell_Digitale_Einkaufsliste_konzeptionell.png` und `docs/GUI-Mockup.png`.
Eine `.docx`- bzw. `.drawio`-Fassung war nicht vorhanden. Die Dokumente wurden nicht verändert.
