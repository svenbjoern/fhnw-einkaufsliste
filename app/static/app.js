const listenElement = document.querySelector("#listen");
const artikelElement = document.querySelector("#artikel");
const layout = document.querySelector("#layout");
const detailTitel = document.querySelector("#detail-titel");
const meldung = document.querySelector("#meldung");
const themeSchalter = document.querySelector("#theme-schalter");

const listenForm = document.querySelector("#listen-form");
const artikelForm = document.querySelector("#artikel-form");
const listeDialog = document.querySelector("#liste-bearbeiten-dialog");
const listeForm = document.querySelector("#liste-bearbeiten-form");
const listeFelder = document.querySelector("#liste-bearbeiten-felder");
const listeFehler = document.querySelector("#liste-bearbeiten-fehler");
const bearbeitenDialog = document.querySelector("#bearbeiten-dialog");
const bearbeitenForm = document.querySelector("#bearbeiten-form");
const bearbeitenFelder = document.querySelector("#bearbeiten-felder");
const bearbeitenFehler = document.querySelector("#bearbeiten-fehler");
const bearbeitenTeilhinweis = document.querySelector("#bearbeiten-teilhinweis");
const bearbeitenTeileinkauf = document.querySelector("#bearbeiten-teileinkauf");
const teileinkaufDialog = document.querySelector("#teileinkauf-dialog");
const teileinkaufForm = document.querySelector("#teileinkauf-form");
const teileinkaufFelder = document.querySelector("#teileinkauf-felder");
const teileinkaufMenge = document.querySelector("#teileinkauf-menge");
const teileinkaufFehler = document.querySelector("#teileinkauf-fehler");
const teileinkaufRest = document.querySelector("#teileinkauf-rest");

const stift = "M16 3l5 5-12 12-6 1 1-6z M14 5l5 5";
const papierkorb = "M3 6h18 M9 6V3h6v3 M5 6l1 15h12l1-15 M10 10v7 M14 10v7";
const zahlenformat = new Intl.NumberFormat("de-CH", {
  maximumFractionDigits: 3,
  useGrouping: false,
});

let listen = [];
let ausgewaehlteListe = null;
let bearbeiteteListe = null;
let bearbeiteterArtikel = null;
let teileinkaufArtikel = null;

function themeSchalterAktualisieren() {
  const dunkel = document.documentElement.dataset.theme === "dark";
  themeSchalter.setAttribute("aria-pressed", String(dunkel));
  themeSchalter.title = dunkel ? "Zum Light Mode wechseln" : "Zum Dark Mode wechseln";
}

// Sonne-/Mond-Schalter „Dunkles Farbschema“: wechselt das Theme ohne HTTP-Anfrage.
themeSchalter.addEventListener("click", () => {
  const html = document.documentElement;
  const theme = html.dataset.theme === "dark" ? "light" : "dark";
  html.dataset.theme = theme;
  themeSchalterAktualisieren();
  try {
    localStorage.setItem("einkaufsliste.theme", theme);
  } catch {
    // Ohne Browser-Speicher gilt die Wahl nur für die geöffnete Seite.
  }
});

async function api(pfad, methode = "GET", daten) {
  // Alle API-Pfade beginnen mit /api. Nur Anfragen mit Daten bekommen einen JSON-Body.
  const optionen = { method: methode };
  if (daten !== undefined) {
    optionen.headers = { "Content-Type": "application/json" };
    optionen.body = JSON.stringify(daten);
  }
  const antwort = await fetch(`/api${pfad}`, optionen);

  // fetch wirft bei 404 oder 422 keinen Fehler. Deshalb lesen wir den Meldungstext selbst.
  if (!antwort.ok) {
    const fehler = await antwort.json().catch(() => null);
    throw new Error(fehler?.detail || "Die Anfrage ist fehlgeschlagen.");
  }
  // DELETE liefert 204 und damit keinen JSON-Body.
  if (antwort.status === 204) return null;
  return antwort.json();
}

function fehlerAnzeigen(fehler, fehlerfeld = meldung) {
  fehlerfeld.textContent = fehler instanceof TypeError
    ? "Der Server ist nicht erreichbar. Bitte versuche es erneut."
    : fehler.message;
  fehlerfeld.hidden = false;
}

async function ausfuehren(button, aktion, fehlerfeld = meldung) {
  button.disabled = true;
  meldung.hidden = true;
  fehlerfeld.hidden = true;
  let gespeichert = false;
  try {
    await aktion();
    gespeichert = true;
    await laden();
  } catch (fehler) {
    // Ein Fehler beim Neuladen gehört zur Übersicht, weil die Änderung bereits gespeichert ist.
    fehlerAnzeigen(fehler, gespeichert ? meldung : fehlerfeld);
  } finally {
    button.disabled = false;
  }
  return gespeichert;
}

async function laden() {
  listen = await api("/listen");
  listenAnzeigen();
  detailsAnzeigen();
}

function fortschrittText(liste) {
  const fortschritt = liste.fortschritt;
  return `${fortschritt.gekauft} von ${fortschritt.gesamt} gekauft`;
}

function mengeFormatieren(menge) {
  if (menge === null) return "";
  return zahlenformat.format(menge);
}

function mengeAuslesen(feld) {
  const eingabe = feld.value.trim().replace(",", ".");
  return eingabe === "" ? null : eingabe;
}

function mengePruefen(feld) {
  const eingabe = mengeAuslesen(feld);
  feld.setCustomValidity("");
  if (feld.value === "") return true;
  const menge = Number(eingabe);
  if (!Number.isFinite(menge) || menge <= 0 || Number(menge.toFixed(3)) !== menge) {
    feld.setCustomValidity("Gib eine positive Menge mit maximal drei Nachkommastellen ein.");
    return false;
  }
  return true;
}

for (const feld of document.querySelectorAll('input[name="menge"]')) {
  // Felder „Geplante Menge“: prüfen Dezimalstellen vor dem Speichern.
  feld.addEventListener("input", () => mengePruefen(feld));

  // Formular-Reset: entfernt eine Meldung, wenn der Artikel gewechselt wurde.
  feld.form.addEventListener("reset", () => feld.setCustomValidity(""));
}

function symbolButton(aktion, name, pfad) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "symbol-button";
  button.title = `${aktion}: ${name}`;
  button.setAttribute("aria-label", button.title);
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("aria-hidden", "true");
  svg.setAttribute("fill", "none");
  svg.setAttribute("stroke", "currentColor");
  svg.setAttribute("stroke-width", "1.8");
  svg.setAttribute("stroke-linecap", "round");
  svg.setAttribute("stroke-linejoin", "round");
  const linie = document.createElementNS("http://www.w3.org/2000/svg", "path");
  linie.setAttribute("d", pfad);
  svg.append(linie);
  button.append(svg);
  return button;
}

function listenAnzeigen() {
  listenElement.replaceChildren();
  document.querySelector("#keine-listen").hidden = listen.length > 0;
  for (const liste of listen) {
    listenElement.append(listenZeileErstellen(liste));
  }
}

function listenZeileErstellen(liste) {
  const zeile = document.createElement("li");
  const auswahl = document.createElement("button");
  auswahl.type = "button";
  auswahl.className = "listen-auswahl";
  auswahl.setAttribute("aria-pressed", String(liste.id === ausgewaehlteListe));

  const name = document.createElement("strong");
  name.textContent = liste.name;
  const fortschritt = document.createElement("small");
  fortschritt.textContent = fortschrittText(liste);
  const balken = document.createElement("progress");
  balken.max = 100;
  balken.value = liste.fortschritt.prozent;
  balken.setAttribute("aria-hidden", "true");
  auswahl.append(name, fortschritt, balken);

  // Listenkarte: öffnet die Liste aus den bereits geladenen Daten.
  auswahl.addEventListener("click", () => {
    ausgewaehlteListe = liste.id;
    artikelForm.reset();
    listenAnzeigen();
    detailsAnzeigen();
    detailTitel.focus();
  });

  const aktionen = document.createElement("div");
  aktionen.className = "artikel-aktionen";
  const bearbeiten = symbolButton("Liste bearbeiten", liste.name, stift);
  const loeschen = symbolButton("Liste löschen", liste.name, papierkorb);
  loeschen.classList.add("loeschen");

  // Bleistift „Liste bearbeiten“: öffnet den Dialog mit dem aktuellen Namen.
  bearbeiten.addEventListener("click", () => {
    bearbeiteteListe = liste.id;
    listeForm.elements.name.value = liste.name;
    listeFehler.hidden = true;
    listeDialog.showModal();
  });

  // Papierkorb „Liste löschen“: löscht nach Bestätigung per DELETE /api/listen/{id}.
  loeschen.addEventListener("click", () => {
    if (!window.confirm(`Liste «${liste.name}» samt Artikeln löschen?`)) return;
    ausfuehren(loeschen, async () => {
      await api(`/listen/${liste.id}`, "DELETE");
      if (ausgewaehlteListe === liste.id) ausgewaehlteListe = null;
    });
  });

  aktionen.append(bearbeiten, loeschen);
  zeile.append(auswahl, aktionen);
  return zeile;
}

// Button „Neue Liste“: erstellt die Liste per POST /api/listen.
listenForm.addEventListener("submit", async (ereignis) => {
  ereignis.preventDefault();
  const gespeichert = await ausfuehren(listenForm.querySelector("button"), async () => {
    const liste = await api("/listen", "POST", { name: listenForm.elements.name.value });
    ausgewaehlteListe = liste.id;
    artikelForm.reset();
    listenForm.reset();
  });
  if (gespeichert) detailTitel.focus();
});

// Button „Alle Listen“: zeigt die Übersicht ohne weiteren Request.
document.querySelector("#zur-uebersicht").addEventListener("click", () => {
  ausgewaehlteListe = null;
  listenAnzeigen();
  detailsAnzeigen();
  document.querySelector("#listen-titel").focus();
});

function detailsAnzeigen() {
  const liste = listen.find((eintrag) => eintrag.id === ausgewaehlteListe);
  layout.classList.toggle("hat-auswahl", Boolean(liste));
  document.querySelector("#listen-detail").hidden = !liste;
  artikelElement.replaceChildren();
  if (!liste) return;

  detailTitel.textContent = liste.name;
  document.querySelector("#fortschritt-text").textContent = fortschrittText(liste);
  document.querySelector("#fortschritt-prozent").textContent = `${liste.fortschritt.prozent.toLocaleString("de-CH")} %`;
  document.querySelector("#fortschritt").value = liste.fortschritt.prozent;
  document.querySelector("#keine-artikel").hidden = liste.artikel.length > 0;
  for (const artikel of liste.artikel) {
    artikelElement.append(artikelZeileErstellen(artikel));
  }
}

function artikelZeileErstellen(artikel) {
  const zeile = document.createElement("li");
  zeile.classList.toggle("gekauft", artikel.status === "gekauft");
  const info = document.createElement("div");
  info.className = "artikel-info";

  const label = document.createElement("label");
  const beschreibung = document.createElement("span");
  const name = document.createElement("span");
  name.className = "artikel-name";
  name.textContent = artikel.name;
  const zusatz = document.createElement("small");
  zusatz.textContent = artikelZusatztext(artikel);
  beschreibung.append(name, zusatz);
  label.append(artikelCheckboxErstellen(artikel), beschreibung);

  const mengenAktionen = document.createElement("div");
  mengenAktionen.className = "mengen-aktionen";
  const teileinkauf = document.createElement("button");
  teileinkauf.type = "button";
  teileinkauf.className = "sekundaer teileinkauf-button";
  teileinkauf.textContent = "Teileinkauf erfassen";
  teileinkauf.disabled = !teileinkaufMoeglich(artikel);
  if (teileinkauf.disabled) teileinkauf.title = teileinkaufSperrgrund(artikel);
  // Button „Teileinkauf erfassen“: öffnet den Dialog mit der aktuellen Restmenge.
  teileinkauf.addEventListener("click", () => teileinkaufOeffnen(artikel));
  mengenAktionen.append(teileinkauf);

  info.append(label, mengenAktionen);
  zeile.append(info, artikelAktionenErstellen(artikel));
  return zeile;
}

function artikelZusatztext(artikel) {
  const geplant = mitEinheit(artikel.menge, artikel.einheit);
  if (artikel.status === "teilweise_gekauft") {
    const gekauft = mengeFormatieren(artikel.gekaufte_menge);
    const offen = mitEinheit(artikel.restmenge, artikel.einheit);
    return `Teilweise gekauft · ${gekauft} von ${geplant} gekauft · ${offen} offen`;
  }
  const status = artikel.status === "gekauft" ? "Gekauft" : "Offen";
  return geplant ? `${geplant} · ${status}` : status;
}

function mitEinheit(menge, einheit) {
  const zahl = mengeFormatieren(menge);
  return [zahl, einheit].filter(Boolean).join(" ");
}

function artikelCheckboxErstellen(artikel) {
  const checkbox = document.createElement("input");
  checkbox.type = "checkbox";
  checkbox.checked = artikel.status === "gekauft";
  checkbox.indeterminate = artikel.status === "teilweise_gekauft";

  // Artikel-Checkbox: setzt „gekauft“ per PATCH /api/artikel/{id}/status.
  checkbox.addEventListener("change", async () => {
    const gespeichert = await ausfuehren(checkbox, () =>
      api(`/artikel/${artikel.id}/status`, "PATCH", { gekauft: checkbox.checked })
    );
    if (!gespeichert) {
      checkbox.checked = artikel.status === "gekauft";
      checkbox.indeterminate = artikel.status === "teilweise_gekauft";
    }
  });
  return checkbox;
}

function artikelAktionenErstellen(artikel) {
  const aktionen = document.createElement("div");
  aktionen.className = "artikel-aktionen";
  const bearbeiten = symbolButton("Bearbeiten", artikel.name, stift);
  const loeschen = symbolButton("Löschen", artikel.name, papierkorb);
  loeschen.classList.add("loeschen");

  // Bleistift „Bearbeiten“: öffnet die gespeicherten Artikeldaten im Dialog.
  bearbeiten.addEventListener("click", () => bearbeitenOeffnen(artikel));

  // Papierkorb „Löschen“: entfernt den Artikel per DELETE /api/artikel/{id}.
  loeschen.addEventListener("click", () => {
    if (!window.confirm("Möchtest du diesen Artikel wirklich löschen?")) return;
    ausfuehren(loeschen, () => api(`/artikel/${artikel.id}`, "DELETE"));
  });

  aktionen.append(bearbeiten, loeschen);
  return aktionen;
}

function artikelEingabe(form) {
  return {
    name: form.elements.name.value,
    menge: mengeAuslesen(form.elements.menge),
    einheit: form.elements.einheit.value || null,
  };
}

// Button „Hinzufügen“: legt den Artikel per POST /api/listen/{id}/artikel an.
artikelForm.addEventListener("submit", (ereignis) => {
  ereignis.preventDefault();
  ausfuehren(artikelForm.querySelector("button"), async () => {
    await api(`/listen/${ausgewaehlteListe}/artikel`, "POST", artikelEingabe(artikelForm));
    artikelForm.reset();
  });
});

function teileinkaufMoeglich(artikel) {
  return artikel.status !== "gekauft" && artikel.restmenge > 0;
}

function teileinkaufSperrgrund(artikel) {
  if (artikel.status === "gekauft") return "Dieser Artikel ist bereits vollständig gekauft.";
  return "Speichere zuerst eine positive geplante Menge.";
}

function bearbeitenOeffnen(artikel) {
  bearbeiteterArtikel = artikel;
  bearbeitenForm.elements.name.value = artikel.name;
  bearbeitenForm.elements.menge.value = artikel.menge ?? "";
  bearbeitenForm.elements.menge.setCustomValidity("");
  bearbeitenForm.elements.einheit.value = artikel.einheit ?? "";
  bearbeitenFehler.hidden = true;
  bearbeitenTeileinkaufAktualisieren();
  bearbeitenDialog.showModal();
}

function bearbeitenTeileinkaufAktualisieren() {
  const artikel = bearbeiteterArtikel;
  const eingabe = artikelEingabe(bearbeitenForm);
  const geaendert = eingabe.name !== artikel.name
    || eingabe.menge !== (artikel.menge === null ? null : String(artikel.menge))
    || eingabe.einheit !== artikel.einheit;
  bearbeitenTeileinkauf.disabled = geaendert || !teileinkaufMoeglich(artikel);
  if (geaendert) {
    bearbeitenTeilhinweis.textContent = "Speichere zuerst deine Änderungen.";
  } else if (bearbeitenTeileinkauf.disabled) {
    bearbeitenTeilhinweis.textContent = teileinkaufSperrgrund(artikel);
  } else {
    bearbeitenTeilhinweis.textContent = "Einen Einkauf erfasst du über «Teileinkauf erfassen».";
  }
}

// Felder im Dialog „Artikel bearbeiten“: sichern Änderungen vor einem Dialogwechsel.
bearbeitenForm.addEventListener("input", bearbeitenTeileinkaufAktualisieren);

// Button „Teileinkauf erfassen“ im Bearbeitungsdialog: wechselt zum Teileinkauf.
bearbeitenTeileinkauf.addEventListener("click", () => {
  bearbeitenDialog.close();
  teileinkaufOeffnen(bearbeiteterArtikel);
});

// Button „Speichern“ für Artikel: aktualisiert per PUT /api/artikel/{id}.
bearbeitenForm.addEventListener("submit", (ereignis) => {
  ereignis.preventDefault();
  ausfuehren(bearbeitenFelder, async () => {
    await api(`/artikel/${bearbeiteterArtikel.id}`, "PUT", artikelEingabe(bearbeitenForm));
    bearbeitenDialog.close();
  }, bearbeitenFehler);
});

// Button „Speichern“ für Listen: aktualisiert per PUT /api/listen/{id}.
listeForm.addEventListener("submit", (ereignis) => {
  ereignis.preventDefault();
  ausfuehren(listeFelder, async () => {
    await api(`/listen/${bearbeiteteListe}`, "PUT", { name: listeForm.elements.name.value });
    listeDialog.close();
  }, listeFehler);
});

function teileinkaufOeffnen(artikel) {
  teileinkaufArtikel = artikel;
  document.querySelector("#teileinkauf-artikel").textContent = artikel.name;
  document.querySelector("#teileinkauf-geplant").textContent = mitEinheit(artikel.menge, artikel.einheit);
  document.querySelector("#teileinkauf-gekauft").textContent = mitEinheit(artikel.gekaufte_menge, artikel.einheit);
  teileinkaufForm.reset();
  teileinkaufFehler.hidden = true;
  teileinkaufVorschau();
  teileinkaufDialog.showModal();
}

function teileinkaufVorschau() {
  const rest = teileinkaufArtikel.restmenge;
  const menge = Number(mengeAuslesen(teileinkaufMenge));
  if (!mengePruefen(teileinkaufMenge) || menge > rest) {
    teileinkaufRest.textContent = "–";
    return;
  }
  teileinkaufRest.textContent = mitEinheit(rest - menge, teileinkaufArtikel.einheit);
}

// Feld „Jetzt zusätzlich gekauft“: zeigt die berechnete Restmenge als Vorschau.
teileinkaufMenge.addEventListener("input", teileinkaufVorschau);

// Button „Speichern“ für Teileinkäufe: sendet die Zusatzmenge per POST /api/artikel/{id}/teileinkauf.
teileinkaufForm.addEventListener("submit", (ereignis) => {
  ereignis.preventDefault();
  ausfuehren(teileinkaufFelder, async () => {
    const menge = mengeAuslesen(teileinkaufMenge);
    await api(`/artikel/${teileinkaufArtikel.id}/teileinkauf`, "POST", { zusaetzliche_menge: menge });
    teileinkaufDialog.close();
  }, teileinkaufFehler);
});

function dialogAbbrechen(dialog, buttonId, felder) {
  // Button „Abbrechen“: schliesst den Dialog und verwirft die Formulareingabe.
  document.querySelector(buttonId).addEventListener("click", () => dialog.close());

  // Escape: hält den Dialog offen, bis ein laufendes Speichern beantwortet ist.
  dialog.addEventListener("cancel", (ereignis) => {
    if (felder.disabled) ereignis.preventDefault();
  });
}

dialogAbbrechen(listeDialog, "#liste-bearbeiten-abbrechen", listeFelder);
dialogAbbrechen(bearbeitenDialog, "#bearbeiten-abbrechen", bearbeitenFelder);
dialogAbbrechen(teileinkaufDialog, "#teileinkauf-abbrechen", teileinkaufFelder);
themeSchalterAktualisieren();
laden().catch(fehlerAnzeigen);
