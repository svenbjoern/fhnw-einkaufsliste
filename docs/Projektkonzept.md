# Projektkonzept – Digitale Einkaufsliste – Projektgruppe C

## 1. Projektidee

Entwicklung einer einfachen Webapplikation zur Verwaltung einer Einkaufsliste. Alle Artikel werden dauerhaft in einer Datenbank gespeichert.

## 2. Funktionen

### 2.1 Must

1. Einkaufslisten (Aldi, Migros, Silvester)
2. Artikel hinzufügen, bearbeiten und löschen (Entity)
3. Mengen und Einheiten erfassen (Feld ist optional) -> Eingaben überprüfen (z. B. keine negativen Mengen)
4. Artikel als gekauft markieren
5. Einkaufsfortschritt anzeigen (z. B. 3/5 gekauft)

### 2.2 Nice

6. Darkmode
7. Alle gekauften Artikel gesammelt entfernen
8. Kategorien erstellen und verwalten (Zusatz-Entity)
9. Artikel nach Status und Kategorie filtern

### 2.3 Nicht vorgesehen:

10. Teilnahme von mehreren Personen
11. Login
12. Preise, Gesamtkosten
13. Artikelsuche (Zusatz)
14. Einkaufshistorie.

## 3. Technischer Aufbau

- Frontend: HTML, CSS, JavaScript
- Backend: Python, FastAPI (REST)
- Geschäftslogik: Validierung, Fortschritt, Sammellöschen
- Datenhaltung: SQLAlchemy und SQLite
- Datenmodell: 2 verbundene Entitäten (Einkaufsliste, Artikel und Kategorie(Zusatz, 1)

## 4. Abgabe

- Funktionsfähige Webapplikation mit requirements.txt und Startanleitung
- Kurze Dokumentation mit ER-Diagramm, Architektur, Reflexion und Quellen-/KI-Deklaration
- Live-Demo und individuelle Verteidigung durch alle Gruppenmitglieder

## 5. Bewertung

- 10 Punkte: Gruppenprojekt (Mindestanforderungen + gezielte Erweiterungen)
- 10 Punkte: Individuelle Verteidigung (jeder versteht den gesamten Code)

**Ziel:** Eine einfache, vollständige und technisch saubere Anwendung mit sinnvollen Zusatzfunktionen entwickeln.
