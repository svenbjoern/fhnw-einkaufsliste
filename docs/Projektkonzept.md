# Projektkonzept – Digitale Einkaufsliste – Projektgruppe C

## Projektidee

Im FHNW-Modul Webbasierte Anwendungen (HS2026) setzt die Projektgruppe eine einfache lokale Webanwendung für Einkaufslisten um. Wer beim Einkauf nur einen Teil einer geplanten Menge findet, erfasst die tatsächlich gekaufte Menge. Beim nächsten Einkauf ist die offene Restmenge auf derselben Liste sichtbar.

## Funktionsumfang

- Listen erstellen, anzeigen, umbenennen und mitsamt ihren Artikeln löschen.
- Artikel hinzufügen, anzeigen, bearbeiten und löschen. Menge und Einheit sind optional. Neue Mengen sind positiv und haben maximal drei relevante Nachkommastellen.
- Artikel offen lassen, einen Teileinkauf erfassen oder vollständig abhaken. Beim Öffnen eines abgehakten Artikels wird der Status zurückgesetzt.
- Den Fortschritt anhand der vollständig gekauften Artikel anzeigen.

## Technischer Aufbau

Die HTML/CSS-Oberfläche verwendet JavaScript und `fetch()`. FastAPI nimmt JSON-Anfragen entgegen. Der Business Layer prüft und berechnet die Mengen, bestimmt den Status und schliesst Transaktionen ab. SQLAlchemy speichert Einkaufslisten und Einkaufsartikel in SQLite. Ein Artikel gehört genau einer Liste, eine Liste kann mehrere Artikel enthalten.

Die [README mit dem aktuellen ER-Diagramm](../README.md#datenmodell) dokumentiert die Anwendung und ihre API. [GUI-Mockup](GUI-Mockup.png) und [ursprüngliches ER-Modell](ER-Modell_Digitale_Einkaufsliste_konzeptionell.png) zeigen die frühe Entwurfsphase.

## Abgabe und Verteidigung

Abgegeben werden der startfähige Python-Code mit `requirements.txt` und die Markdown-Dokumentation mit Zielsetzung, Datenmodell, Architektur, Reflexion sowie Quellen und KI-Deklaration. Die Anwendung wird vorgeführt. Jedes Gruppenmitglied soll alle Schichten und ihren Code erklären können. Die Bewertung umfasst laut Aufgabenstellung bis zu 10 Punkte für das Gruppenprojekt und bis zu 10 Punkte für die individuelle Verteidigung. [FHNW-Aufgabenstellung](Projektarbeit_py.pdf)
