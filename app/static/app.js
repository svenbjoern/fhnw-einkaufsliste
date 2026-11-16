const listenElement = document.querySelector("#listen");
const artikelElement = document.querySelector("#artikel");
const meldung = document.querySelector("#meldung");
const bearbeitenDialog = document.querySelector("#bearbeiten-dialog");
const bearbeitenForm = document.querySelector("#bearbeiten-form");
const bearbeitenFelder = document.querySelector("#bearbeiten-felder");
const bearbeitenFehler = document.querySelector("#bearbeiten-fehler");
const listeDialog = document.querySelector("#liste-bearbeiten-dialog");
const listeForm = document.querySelector("#liste-bearbeiten-form");
const listeFelder = document.querySelector("#liste-bearbeiten-felder");
const listeFehler = document.querySelector("#liste-bearbeiten-fehler");
let bearbeiteteListe = null;
let bearbeiteterArtikel = null;
let ausgewaehlteListe = null;
let listen = [];

async function api(pfad, methode = "GET", daten) {
  const antwort = await fetch(`/api${pfad}`, {
    method: methode,
    headers: { "Content-Type": "application/json" },
    body: daten === undefined ? undefined : JSON.stringify(daten),
  });
  if (!antwort.ok) {
    const fehler = await antwort.json();
    throw new Error(fehler.detail || "Die Anfrage ist fehlgeschlagen.");
  }
  return antwort.status === 204 ? null : antwort.json();
}

function fehlerAnzeigen(fehler) {
  meldung.textContent = fehler.message === "Failed to fetch"
    ? "Der Server ist nicht erreichbar. Bitte versuche es erneut."
    : fehler.message;
  meldung.hidden = false;
}

function fortschrittText(liste) {
  const f = liste.fortschritt;
  return `${f.gekauft} / ${f.gesamt} gekauft (${f.prozent.toLocaleString("de-CH")} %)`;
}

function mengeFormatieren(menge) {
  if (menge === null) return "";
  // Nur die Anzeige wird gerundet; gespeicherte Altwerte bleiben unverändert.
  return Number(menge).toLocaleString("en-US", {
    useGrouping: false, maximumFractionDigits: 3,
  });
}

function mengePruefen(feld) {
  feld.setCustomValidity("");
  if (!feld.value || !feld.validity.valid) return;
  if (Number(feld.value) <= 0) {
    feld.setCustomValidity("Die Menge muss grösser als null sein.");
  } else if (Number(feld.value) !== Number(mengeFormatieren(feld.value))) {
    feld.setCustomValidity("Die Menge darf maximal drei Nachkommastellen haben.");
  }
}

for (const feld of document.querySelectorAll('input[name="menge"]')) {
  feld.addEventListener("input", () => mengePruefen(feld));
  feld.form.addEventListener("reset", () => feld.setCustomValidity(""));
}

function listenAnzeigen() {
  listenElement.replaceChildren();
  document.querySelector("#keine-listen").hidden = listen.length > 0;
  for (const liste of listen) {
    const li = document.createElement("li");
    const button = document.createElement("button");
    button.type = "button";
    button.className = "listen-auswahl";
    button.setAttribute("aria-pressed", String(liste.id === ausgewaehlteListe));
    const name = document.createElement("strong");
    name.textContent = liste.name;
    const fortschritt = document.createElement("small");
    fortschritt.textContent = fortschrittText(liste);
    button.append(name, fortschritt);
    button.addEventListener("click", () => {
      ausgewaehlteListe = liste.id;
      document.querySelector("#artikel-form").reset();
      listenAnzeigen();
      detailsAnzeigen();
    });
    // Die Aktionsbuttons sind Geschwister der Auswahl, keine verschachtelten Buttons.
    const aktionen = document.createElement("div");
    aktionen.className = "artikel-aktionen";
    const bearbeiten = symbolButton("Liste bearbeiten", liste.name, "M16 3l5 5-12 12-6 1 1-6z M14 5l5 5");
    const loeschen = symbolButton("Liste löschen", liste.name, "M3 6h18 M9 6V3h6v3 M5 6l1 15h12l1-15 M10 10v7 M14 10v7");
    loeschen.classList.add("loeschen");
    bearbeiten.addEventListener("click", () => {
      bearbeiteteListe = liste.id;
      listeForm.elements.name.value = liste.name;
      listeFehler.hidden = true;
      listeDialog.showModal();
    });
    loeschen.addEventListener("click", async () => {
      if (!window.confirm(`Möchtest du die Einkaufsliste "${liste.name}" wirklich löschen? Alle enthaltenen Artikel werden ebenfalls gelöscht.`)) return;
      bearbeiten.disabled = true;
      loeschen.disabled = true;
      button.disabled = true;
      meldung.hidden = true;
      try {
        await api(`/listen/${liste.id}`, "DELETE");
        if (ausgewaehlteListe === liste.id) {
          ausgewaehlteListe = null;
          document.querySelector("#artikel-form").reset();
        }
        await laden();
      } catch (fehler) {
        fehlerAnzeigen(fehler);
      } finally {
        bearbeiten.disabled = false;
        loeschen.disabled = false;
        button.disabled = false;
      }
    });
    aktionen.append(bearbeiten, loeschen);
    li.append(button, aktionen);
    listenElement.append(li);
  }
}

function detailsAnzeigen() {
  const liste = listen.find((eintrag) => eintrag.id === ausgewaehlteListe);
  document.querySelector("#auswahl-hinweis").hidden = Boolean(liste);
  document.querySelector("#listen-detail").hidden = !liste;
  document.querySelector("#detail-titel").textContent = liste ? liste.name : "Dein Einkauf";
  if (!liste) {
    artikelElement.replaceChildren();
    return;
  }
  document.querySelector("#fortschritt-text").textContent = fortschrittText(liste);
  document.querySelector("#fortschritt").value = liste.fortschritt.prozent;
  document.querySelector("#keine-artikel").hidden = liste.artikel.length > 0;
  artikelElement.replaceChildren();
  for (const artikel of liste.artikel) {
    const li = document.createElement("li");
    li.classList.toggle("gekauft", artikel.gekauft);
    const label = document.createElement("label");
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = artikel.gekauft;
    const beschreibung = document.createElement("span");
    const name = document.createElement("span");
    name.className = "artikel-name";
    name.textContent = artikel.name;
    const zusatz = document.createElement("small");
    const menge = mengeFormatieren(artikel.menge);
    zusatz.textContent = [menge, artikel.einheit, artikel.gekauft ? "Gekauft" : "Offen"].filter(Boolean).join(" · ");
    beschreibung.append(name, zusatz);
    label.append(checkbox, beschreibung);
    const aktionen = document.createElement("div");
    aktionen.className = "artikel-aktionen";
    const bearbeiten = symbolButton("Bearbeiten", artikel.name, "M16 3l5 5-12 12-6 1 1-6z M14 5l5 5");
    const loeschen = symbolButton("Löschen", artikel.name, "M3 6h18 M9 6V3h6v3 M5 6l1 15h12l1-15 M10 10v7 M14 10v7");
    loeschen.classList.add("loeschen");
    bearbeiten.addEventListener("click", () => bearbeitenOeffnen(artikel));
    loeschen.addEventListener("click", async () => {
      if (!window.confirm("Möchtest du diesen Artikel wirklich löschen?")) return;
      bearbeiten.disabled = true;
      loeschen.disabled = true;
      checkbox.disabled = true;
      meldung.hidden = true;
      try {
        await api(`/artikel/${artikel.id}`, "DELETE");
        await laden();
      } catch (fehler) {
        fehlerAnzeigen(fehler);
      } finally {
        bearbeiten.disabled = false;
        loeschen.disabled = false;
        checkbox.disabled = false;
      }
    });
    aktionen.append(bearbeiten, loeschen);
    li.append(label, aktionen);
    artikelElement.append(li);
    checkbox.addEventListener("change", async () => {
      checkbox.disabled = true;
      meldung.hidden = true;
      try {
        await api(`/artikel/${artikel.id}/status`, "PATCH", { gekauft: checkbox.checked });
        await laden();
      } catch (fehler) {
        checkbox.checked = artikel.gekauft;
        fehlerAnzeigen(fehler);
      } finally {
        checkbox.disabled = false;
      }
    });
  }
}

async function laden() {
  listen = await api("/listen");
  listenAnzeigen();
  detailsAnzeigen();
}

function symbolButton(aktion, artikelname, pfad) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "symbol-button";
  button.title = `${aktion}: ${artikelname}`;
  button.setAttribute("aria-label", button.title);
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("aria-hidden", "true");
  svg.setAttribute("fill", "none");
  svg.setAttribute("stroke", "currentColor");
  svg.setAttribute("stroke-width", "1.8");
  svg.setAttribute("stroke-linecap", "round");
  svg.setAttribute("stroke-linejoin", "round");
  const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
  path.setAttribute("d", pfad);
  svg.append(path);
  button.append(svg);
  return button;
}

function bearbeitenOeffnen(artikel) {
  bearbeiteterArtikel = artikel.id;
  bearbeitenForm.elements.name.value = artikel.name;
  bearbeitenForm.elements.menge.value = mengeFormatieren(artikel.menge);
  bearbeitenForm.elements.menge.setCustomValidity("");
  bearbeitenForm.elements.einheit.value = artikel.einheit ?? "";
  bearbeitenFehler.hidden = true;
  bearbeitenDialog.showModal();
}

document.querySelector("#bearbeiten-abbrechen").addEventListener("click", () => bearbeitenDialog.close());
bearbeitenDialog.addEventListener("cancel", (event) => {
  // Während des Speicherns bleibt das Formular offen, bis die Antwort vorliegt.
  if (bearbeitenFelder.disabled) event.preventDefault();
});
bearbeitenDialog.addEventListener("close", () => {
  bearbeiteterArtikel = null;
  bearbeitenForm.reset();
});

bearbeitenForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  bearbeitenFelder.disabled = true;
  bearbeitenFehler.hidden = true;
  meldung.hidden = true;
  try {
    // PUT ersetzt nur die drei bearbeitbaren Felder; der Status wird nicht gesendet.
    await api(`/artikel/${bearbeiteterArtikel}`, "PUT", {
      name: bearbeitenForm.elements.name.value,
      menge: bearbeitenForm.elements.menge.value || null,
      einheit: bearbeitenForm.elements.einheit.value || null,
    });
  } catch (fehler) {
    bearbeitenFehler.textContent = fehler.message;
    bearbeitenFehler.hidden = false;
    return;
  } finally {
    bearbeitenFelder.disabled = false;
  }
  bearbeitenDialog.close();
  try {
    await laden();
  } catch (fehler) {
    fehlerAnzeigen(fehler);
  }
});

document.querySelector("#liste-bearbeiten-abbrechen").addEventListener("click", () => listeDialog.close());
listeDialog.addEventListener("cancel", (event) => {
  if (listeFelder.disabled) event.preventDefault();
});
listeDialog.addEventListener("close", () => {
  bearbeiteteListe = null;
  listeForm.reset();
});

listeForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  listeFelder.disabled = true;
  listeFehler.hidden = true;
  meldung.hidden = true;
  try {
    await api(`/listen/${bearbeiteteListe}`, "PUT", { name: listeForm.elements.name.value });
  } catch (fehler) {
    listeFehler.textContent = fehler.message;
    listeFehler.hidden = false;
    return;
  } finally {
    listeFelder.disabled = false;
  }
  listeDialog.close();
  try {
    await laden();
  } catch (fehler) {
    fehlerAnzeigen(fehler);
  }
});

// Die Formulare warten auf den Server; der Button verhindert doppelte Klicks.
document.querySelector("#listen-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const button = form.querySelector("button");
  button.disabled = true;
  meldung.hidden = true;
  try {
    const liste = await api("/listen", "POST", { name: form.elements.name.value });
    ausgewaehlteListe = liste.id;
    form.reset();
    await laden();
  } catch (fehler) {
    fehlerAnzeigen(fehler);
  } finally {
    button.disabled = false;
  }
});

document.querySelector("#artikel-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const button = form.querySelector("button");
  button.disabled = true;
  meldung.hidden = true;
  try {
    await api(`/listen/${ausgewaehlteListe}/artikel`, "POST", {
      name: form.elements.name.value,
      menge: form.elements.menge.value || null,
      einheit: form.elements.einheit.value || null,
    });
    form.reset();
    await laden();
  } catch (fehler) {
    fehlerAnzeigen(fehler);
  } finally {
    button.disabled = false;
  }
});

laden().catch(fehlerAnzeigen);
