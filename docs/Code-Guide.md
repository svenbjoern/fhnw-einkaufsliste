# Code-Guide für die Projektverteidigung

FHNW · Webbasierte Anwendungen · HS2026 · Projektgruppe C

Legt für die Demo «Kartoffeln, 3 kg» an. Geht dann einen Teileinkauf vom Klick bis zur Datenbank und zurück durch. Die Links im Guide zeigen auf den Code dieses Branches.

## 1. Architektur auf einen Blick

| Schicht | Dateien | Aufgabe |
| --- | --- | --- |
| Presentation | [index.html](../app/static/index.html), [style.css](../app/static/style.css), [app.js](../app/static/app.js) | Zeigt die Oberfläche, verarbeitet Eingaben und tauscht JSON mit der API aus. |
| Service | [main.py](../app/main.py), [services.py](../app/services.py), [schemas.py](../app/schemas.py) | Ordnet HTTP-Anfragen den Routen zu, prüft Eingaben und baut Antworten. |
| Business | [business.py](../app/business.py) | Prüft Geschäftsregeln, berechnet Status und Mengen und speichert Änderungen. |
| Persistence | [repository.py](../app/repository.py), [models.py](../app/models.py), [database.py](../app/database.py) | Bildet die zwei Tabellen auf Python-Objekte ab und greift mit SQLAlchemy auf SQLite zu. |

~~~mermaid
sequenceDiagram
    participant P as Browser
    participant S as FastAPI und Pydantic
    participant B as Business Layer
    participant R as Repository und Session
    participant D as SQLite
    P->>S: POST /api/artikel/7/teileinkauf mit Zusatzmenge
    S->>S: Eingabeformat prüfen
    S->>B: teileinkauf_erfassen(session, 7, menge)
    B->>R: artikel_finden(session, 7)
    R->>D: SELECT
    D-->>R: Artikelzeile
    R-->>B: Einkaufsartikel
    B->>B: Restmenge prüfen und neuen Status bestimmen
    B->>R: session.commit()
    R->>D: UPDATE und COMMIT
    D-->>R: Änderung gespeichert
    R-->>B: Commit abgeschlossen
    B-->>S: Aktualisierter Einkaufsartikel
    S-->>P: HTTP 200 mit Artikel als JSON
~~~

## 2. Was macht dieser Button?

Nach einer erfolgreichen Änderung rufen [`ausfuehren`, app.js:85](../app/static/app.js#L85) und [`laden`, app.js:103](../app/static/app.js#L103) zusätzlich `GET /api/listen` auf. Damit baut der Browser die Übersicht und die gerade ausgewählte Liste aus den aktuellen Daten neu auf.

| GUI-Element | JS-Funktion oder Handler (Datei und Zeile) | HTTP-Methode und Pfad | Service-Funktion | Business-Funktion | Repository oder DB-Aktion | Was du danach siehst |
| --- | --- | --- | --- | --- | --- | --- |
| «Neue Liste» | [Submit, app.js:228](../app/static/app.js#L228) | `POST /api/listen` | [liste_erstellen, services.py:39](../app/services.py#L39) | [liste_erstellen, business.py:60](../app/business.py#L60) | [liste_erstellen, repository.py:16](../app/repository.py#L16) merkt die Liste zum Speichern vor. | Die neue Liste ist ausgewählt. |
| Liste auswählen | [Klick in listenZeileErstellen, app.js:191](../app/static/app.js#L191) | Kein Request | — | — | — | Artikel und Fortschritt der Liste erscheinen. |
| «Liste bearbeiten» (Bleistift) | [Klick in listenZeileErstellen, app.js:206](../app/static/app.js#L206) | Kein Request beim Öffnen | — | — | — | Der Dialog zeigt den bisherigen Namen. |
| «Speichern» für die Liste | [Submit, app.js:424](../app/static/app.js#L424) | `PUT /api/listen/{liste_id}` | [liste_bearbeiten, services.py:49](../app/services.py#L49) | [liste_bearbeiten, business.py:66](../app/business.py#L66) | [liste_bearbeiten, repository.py:22](../app/repository.py#L22) setzt den neuen Namen. | Die Karte zeigt den neuen Namen. |
| «Liste löschen» (Papierkorb) | [Klick in listenZeileErstellen, app.js:214](../app/static/app.js#L214) | `DELETE /api/listen/{liste_id}` nach Bestätigung | [liste_loeschen, services.py:54](../app/services.py#L54) | [liste_loeschen, business.py:73](../app/business.py#L73) | [liste_loeschen, repository.py:26](../app/repository.py#L26) merkt die Liste zum Löschen vor. Ihre Artikel werden mitgelöscht. | Die Karte verschwindet. |
| Artikel «Hinzufügen» | [Submit, app.js:361](../app/static/app.js#L361) | `POST /api/listen/{liste_id}/artikel` | [artikel_hinzufuegen, services.py:60](../app/services.py#L60) | [artikel_hinzufuegen, business.py:78](../app/business.py#L78) | [artikel_erstellen, repository.py:30](../app/repository.py#L30) verknüpft den Artikel mit seiner Liste. | Die neue Zeile erscheint. |
| Artikel-Checkbox | [Change in artikelCheckboxErstellen, app.js:320](../app/static/app.js#L320) | `PATCH /api/artikel/{artikel_id}/status` | [artikel_status_setzen, services.py:65](../app/services.py#L65) | [artikel_status_setzen, business.py:87](../app/business.py#L87) | [artikel_finden, repository.py:41](../app/repository.py#L41) lädt den Artikel. Die Session speichert die geänderten Werte. | Häkchen, Kaufstatus und Fortschritt ändern sich. |
| «Teileinkauf erfassen» in der Zeile oder im Bearbeiten-Dialog | [Klick, app.js:289](../app/static/app.js#L289) oder [Klick im Dialog, app.js:409](../app/static/app.js#L409) ruft [teileinkaufOeffnen, app.js:432](../app/static/app.js#L432) auf. | Kein Request beim Öffnen | — | — | — | Der Dialog zeigt geplante und bereits gekaufte Menge. |
| «Jetzt zusätzlich gekauft» | [teileinkaufVorschau, app.js:443](../app/static/app.js#L443) | Kein Request beim Tippen | — | — | — | Die Restmenge erscheint als Vorschau. |
| «Speichern» für den Teileinkauf | [Submit, app.js:457](../app/static/app.js#L457) | `POST /api/artikel/{artikel_id}/teileinkauf` | [teileinkauf_erfassen, services.py:70](../app/services.py#L70) | [teileinkauf_erfassen, business.py:95](../app/business.py#L95) | [artikel_finden, repository.py:41](../app/repository.py#L41) lädt den Artikel. Die Session speichert neue Menge und Häkchen. | Die Zeile aktualisiert sich oder der Dialog zeigt einen Fehler. |
| Artikel «Bearbeiten» (Bleistift) | [Klick in artikelAktionenErstellen, app.js:340](../app/static/app.js#L340) | Kein Request beim Öffnen | — | — | — | Der Dialog zeigt Name, Menge und Einheit. |
| «Speichern» für den Artikel | [Submit, app.js:415](../app/static/app.js#L415) | `PUT /api/artikel/{artikel_id}` | [artikel_bearbeiten, services.py:75](../app/services.py#L75) | [artikel_bearbeiten, business.py:117](../app/business.py#L117) | [artikel_bearbeiten, repository.py:45](../app/repository.py#L45) ersetzt die drei Felder. | Die Zeile zeigt die gespeicherten Angaben. |
| Artikel «Löschen» (Papierkorb) | [Klick in artikelAktionenErstellen, app.js:343](../app/static/app.js#L343) | `DELETE /api/artikel/{artikel_id}` nach Bestätigung | [artikel_loeschen, services.py:81](../app/services.py#L81) | [artikel_loeschen, business.py:140](../app/business.py#L140) | [artikel_loeschen, repository.py:53](../app/repository.py#L53) merkt den Artikel zum Löschen vor. | Die Zeile verschwindet. |
| Sonne-/Mond-Schalter | [Klick, app.js:47](../app/static/app.js#L47) | Kein Request | — | — | Der Browser speichert die Auswahl in `localStorage`. | Die Farben wechseln sofort. |
| «Alle Listen» | [Klick, app.js:240](../app/static/app.js#L240) | Kein Request | — | — | — | Die Übersicht erscheint. |
| Felder für Namen, Menge und Einheit | [mengePruefen, app.js:124](../app/static/app.js#L124), [artikelEingabe, app.js:352](../app/static/app.js#L352) | Erst beim Absenden | — | — | — | Die Eingaben sind sichtbar und ungültige Mengen werden gemeldet. |
| «Abbrechen» oder Escape | [dialogAbbrechen, app.js:466](../app/static/app.js#L466) | Kein Request | — | — | — | Der Dialog schliesst. Während des Speicherns bleibt er offen. |

## 3. Abläufe Schritt für Schritt

### A. App starten

1. Der Befehl `uvicorn app.main:app --reload` lädt das FastAPI-Objekt `app`. [README.md:16](../README.md#L16) · [main.py:22](../app/main.py#L22)
2. Beim Start läuft `lifespan`. `datenbank_initialisieren` legt fehlende Tabellen mit `create_all` an. [main.py:17](../app/main.py#L17) · [database.py:19](../app/database.py#L19)
3. Ein Aufruf von `/` liefert das HTML aus. `defer` lässt das JavaScript nach dem Einlesen des Markups laufen. [main.py:49](../app/main.py#L49) · [index.html:17](../app/static/index.html#L17)
4. `laden()` startet `GET /api/listen`. Die Route gibt die vom Repository gelesenen Listen als JSON zurück. JavaScript zeichnet daraus die Karten. [app.js:480](../app/static/app.js#L480) · [app.js:103](../app/static/app.js#L103) · [services.py:34](../app/services.py#L34) · [business.py:49](../app/business.py#L49) · [repository.py:7](../app/repository.py#L7)

### B. Neue Liste erstellen

1. Der Submit-Handler liest den Namen aus dem Formular. `api` wandelt ihn in JSON um und sendet `POST /api/listen`. [app.js:228](../app/static/app.js#L228) · [app.js:59](../app/static/app.js#L59)
2. Pydantic trimmt den Namen und verlangt mindestens ein Zeichen. Die Route reicht ihn an die Business-Funktion weiter. [schemas.py:6](../app/schemas.py#L6) · [services.py:39](../app/services.py#L39)
3. Das Repository erstellt die Liste und merkt sie mit `session.add()` vor. Der Business Layer speichert sie mit `session.commit()`. [repository.py:16](../app/repository.py#L16) · [business.py:62](../app/business.py#L62)
4. Die Route antwortet mit 201. JavaScript merkt sich die ID der neuen Liste und lädt die Übersicht neu. [services.py:38](../app/services.py#L38) · [app.js:228](../app/static/app.js#L228) · [app.js:85](../app/static/app.js#L85)

### C. Artikel abhaken

1. Beim Checkbox-Wechsel liest JavaScript `checkbox.checked` und sendet diesen Boolean als `gekauft`. [app.js:320](../app/static/app.js#L320)
2. Die Route reicht Artikel-ID und Boolean an die Business-Funktion weiter. Diese lädt den Artikel über das Repository. [services.py:65](../app/services.py#L65) · [business.py:87](../app/business.py#L87) · [repository.py:41](../app/repository.py#L41)
3. Das Häkchen setzt `gekauft` auf wahr und bei einem Mengenartikel die gekaufte Menge auf die geplante Menge. Beim Öffnen wird `gekauft` falsch und die gekaufte Menge auf 0. `session.commit()` speichert beide Werte. [business.py:87](../app/business.py#L87) · [business.py:91](../app/business.py#L91)
4. Beim Neuladen liefert der Business Layer den neuen Fortschritt. JavaScript zeichnet die Checkbox und den Balken. [business.py:42](../app/business.py#L42) · [app.js:313](../app/static/app.js#L313) · [app.js:247](../app/static/app.js#L247)

### D. Teileinkauf erfassen

1. Der Dialog zeigt die bisher gekaufte Menge. Beim Tippen ersetzt JavaScript ein Dezimalkomma durch einen Punkt und berechnet die Vorschau. [app.js:432](../app/static/app.js#L432) · [app.js:119](../app/static/app.js#L119) · [app.js:443](../app/static/app.js#L443)
2. «Speichern» sendet die Zusatzmenge per POST. Pydantic prüft das Format. Danach ruft die Route die Business-Funktion auf. [app.js:457](../app/static/app.js#L457) · [schemas.py:31](../app/schemas.py#L31) · [services.py:70](../app/services.py#L70)
3. Der Business Layer lädt den Artikel und prüft die Restmenge. Bei Erfolg addiert er die Zusatzmenge, rundet auf drei Nachkommastellen, setzt den Einkaufsstatus und speichert. [business.py:95](../app/business.py#L95) · [business.py:28](../app/business.py#L28) · [business.py:106](../app/business.py#L106)
4. Die Route antwortet mit dem aktualisierten Artikel. JavaScript schliesst den Dialog und zeigt nach dem Neuladen die Restmenge und den Status. [services.py:15](../app/services.py#L15) · [app.js:457](../app/static/app.js#L457) · [app.js:297](../app/static/app.js#L297)
5. Ist die Zusatzmenge grösser als die Restmenge, wirft der Business Layer `UngueltigeDaten`. `main.py` liefert 422 mit einem Text in `detail`. `api()` wirft daraus einen JavaScript-`Error`. `ausfuehren` fängt ihn ab und zeigt den Text im offenen Dialog. [business.py:102](../app/business.py#L102) · [main.py:28](../app/main.py#L28) · [app.js:71](../app/static/app.js#L71) · [app.js:85](../app/static/app.js#L85)

### E. Liste mit ihren Artikeln löschen

1. Der Papierkorb zeigt eine Bestätigung. Danach sendet JavaScript `DELETE /api/listen/{liste_id}`. [app.js:214](../app/static/app.js#L214)
2. Die Route ruft die Business-Funktion auf. Diese lässt das Repository die Liste per `session.delete()` zum Löschen vormerken und schliesst mit `session.commit()` ab. [services.py:54](../app/services.py#L54) · [business.py:73](../app/business.py#L73) · [repository.py:26](../app/repository.py#L26)
3. Die ORM-Beziehung hat eine Löschkaskade. Der Fremdschlüssel in SQLite verwendet ebenfalls `ON DELETE CASCADE`. Der Listener aktiviert Fremdschlüssel für jede Verbindung. [models.py:13](../app/models.py#L13) · [models.py:22](../app/models.py#L22) · [database.py:24](../app/database.py#L24)
4. Der Service sendet 204 ohne Inhalt. `api()` versucht hier kein JSON zu lesen und die Seite lädt die Listen neu. [services.py:54](../app/services.py#L54) · [app.js:74](../app/static/app.js#L74) · [app.js:85](../app/static/app.js#L85)

## 4. Wahrscheinliche Prüfungsfragen

**Was macht `Depends(get_session)`?** FastAPI ruft `get_session` für die Anfrage auf und gibt die Session an die Route weiter. Die Funktion schliesst die Session am Ende der Anfrage. [database.py:29](../app/database.py#L29)

**Wozu dienen Pydantic-Schemas?** Die Eingabeschemas prüfen, ob Name und Menge im erwarteten Format ankommen. Die Ausgabeschemas legen fest, welche Felder der Browser erhält. [schemas.py:12](../app/schemas.py#L12) · [schemas.py:42](../app/schemas.py#L42)

**Warum prüft der Business Layer die Restmenge?** Die Vorschau verwendet den zuletzt geladenen Stand. Der Business Layer liest den aktuellen Stand aus der Datenbank und wendet die Regel auch an, wenn jemand die API direkt benutzt. [app.js:443](../app/static/app.js#L443) · [business.py:95](../app/business.py#L95)

**Was bedeuten `relationship` und `cascade`?** Über die Beziehung kann Python mit `liste.artikel` auf die Artikel zugreifen. Die Löschkaskade sorgt dafür, dass keine Artikel einer gelöschten Liste zurückbleiben. [models.py:13](../app/models.py#L13)

**Was machen `fetch` und `await`?** `fetch` startet eine HTTP-Anfrage. `await` hält die asynchrone Funktion bis zur Antwort an, während der Browser weiter Eingaben verarbeiten kann. [app.js:59](../app/static/app.js#L59)

**Warum 204 bei DELETE?** 204 bestätigt die erfolgreiche Anfrage ohne Antwortinhalt. Darum gibt `api()` bei 204 `null` zurück. [services.py:81](../app/services.py#L81) · [app.js:74](../app/static/app.js#L74)

**Was ist der Unterschied zwischen POST, PUT und PATCH?** POST legt bei uns Listen und Artikel an oder erfasst einen Teileinkauf. PUT ersetzt die bearbeitbaren Felder, PATCH setzt gezielt den Checkbox-Status. [services.py:60](../app/services.py#L60) · [services.py:75](../app/services.py#L75) · [services.py:65](../app/services.py#L65)

**Wie entsteht der Fortschrittsbalken?** Der Business Layer zählt alle Artikel und davon die vollständig gekauften. JavaScript setzt den berechneten Prozentwert auf das HTML-Element `progress`. [business.py:42](../app/business.py#L42) · [app.js:247](../app/static/app.js#L247)

**Wo bleiben die Daten nach dem Neuladen?** Einkaufslisten und Artikel liegen in der SQLite-Datei. Die Farbauswahl liegt getrennt im Browser und wird beim nächsten Aufruf vor dem Laden der Styles gelesen. [database.py:11](../app/database.py#L11) · [index.html:9](../app/static/index.html#L9)

## 5. Mini-Glossar

| Begriff | Kurz erklärt |
| --- | --- |
| Session | SQLAlchemy-Arbeitsbereich für eine Anfrage. `commit()` speichert die bisher vorgemerkten Änderungen. |
| ORM | Object-Relational Mapping. Es verbindet Python-Objekte mit Zeilen einer SQL-Tabelle. |
| `Mapped` | SQLAlchemy-Typangabe für ein Attribut, das als Spalte oder Beziehung abgebildet wird. |
| Router | Gruppe von zusammengehörigen HTTP-Routen. Unser Router verwendet das Präfix `/api`. |
| Endpoint | Kombination aus HTTP-Methode und Pfad, zum Beispiel `POST /api/listen`. |
| JSON | Textformat für Daten, die Browser und API austauschen. |
| Statuscode | Zahl für das Ergebnis einer HTTP-Anfrage, etwa 201 für einen neuen Datensatz. |
| DOM | Struktur der eingelesenen HTML-Seite. JavaScript kann ihre Elemente lesen und verändern. |
| Event-Listener | Funktion, die bei einem Ereignis wie Klick, Eingabe oder Checkbox-Wechsel aufgerufen wird. |
| `async` und `await` | `async` kennzeichnet eine asynchrone Funktion. `await` wartet innerhalb dieser Funktion auf das Ergebnis. |
