const listenElement = document.querySelector("#listen");
const artikelElement = document.querySelector("#artikel");
const layout = document.querySelector("#layout");
const detailTitel = document.querySelector("#detail-titel");
const themeSchalter = document.querySelector("#theme-schalter");
const meldung = document.querySelector("#meldung");
const bearbeitenDialog = document.querySelector("#bearbeiten-dialog");
const bearbeitenForm = document.querySelector("#bearbeiten-form");
const bearbeitenFelder = document.querySelector("#bearbeiten-felder");
const bearbeitenFehler = document.querySelector("#bearbeiten-fehler");
const bearbeitenTeilhinweis = document.querySelector("#bearbeiten-teilhinweis");
const bearbeitenTeileinkauf = document.querySelector("#bearbeiten-teileinkauf");
const bearbeitenKorrigieren = document.querySelector("#bearbeiten-korrigieren");
const teileinkaufDialog = document.querySelector("#teileinkauf-dialog");
const teileinkaufForm = document.querySelector("#teileinkauf-form");
const teileinkaufFelder = document.querySelector("#teileinkauf-felder");
const teileinkaufMenge = document.querySelector("#teileinkauf-menge");
const teileinkaufFehler = document.querySelector("#teileinkauf-fehler");
const teileinkaufRest = document.querySelector("#teileinkauf-rest");
const listeDialog = document.querySelector("#liste-bearbeiten-dialog");
const listeForm = document.querySelector("#liste-bearbeiten-form");
const listeFelder = document.querySelector("#liste-bearbeiten-felder");
const listeFehler = document.querySelector("#liste-bearbeiten-fehler");
let bearbeiteteListe = null;
let bearbeiteterArtikel = null;
let teileinkaufArtikel = null;
let gekaufteMengeKorrigieren = false;
let ausgewaehlteListe = null;
let listen = [];

function themeSchalterAktualisieren() {
  const dunkel = document.documentElement.dataset.theme === "dark";
  themeSchalter.setAttribute("aria-pressed", String(dunkel));
  themeSchalter.title = dunkel ? "Zum Light Mode wechseln" : "Zum Dark Mode wechseln";
}

themeSchalterAktualisieren();
themeSchalter.addEventListener("click", () => {
  const html = document.documentElement;
  const theme = html.dataset.theme === "dark" ? "light" : "dark";
  html.dataset.theme = theme;
  themeSchalterAktualisieren();
  try {
    localStorage.setItem("einkaufsliste.theme", theme);
  } catch {
    // Der Wechsel funktioniert auch für die aktuelle Seite ohne Browser-Speicher.
  }
});

document.querySelector("#zur-uebersicht").addEventListener("click", () => {
  ausgewaehlteListe = null;
  listenAnzeigen();
  detailsAnzeigen();
  document.querySelector("#listen-titel").focus();
});

async function api(pfad, methode = "GET", daten) {
  const antwort = await fetch(`/api${pfad}`, {
    method: methode,
    headers: { "Content-Type": "application/json" },
    body: daten === undefined ? undefined : JSON.stringify(daten),
  });
  if (!antwort.ok) {
    const fehler = await antwort.json().catch(() => null);
    throw new Error(fehler?.detail || "Die Anfrage ist fehlgeschlagen.");
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
  return `${f.gekauft} von ${f.gesamt} gekauft`;
}

function mengeFormatieren(menge) {
  if (menge === null) return "";
  if (mengeInTausendsteln(menge) !== null) return menge.replace(/(\.\d*?)0+$/, "$1").replace(/\.$/, "");
  // Nur die Anzeige wird gerundet; gespeicherte Altwerte bleiben unverändert.
  return Number(menge).toLocaleString("en-US", {
    useGrouping: false, maximumFractionDigits: 3,
  });
}

function mengeInTausendsteln(text) {
  const teile = text?.trim().replace(",", ".").match(/^(\d*)(?:\.(\d*))?$/);
  if (!teile) return null;
  const [, ganze, nachkomma = ""] = teile;
  if ((!ganze && !nachkomma) || /[1-9]/.test(nachkomma.slice(3))) return null;
  return BigInt(ganze + nachkomma.slice(0, 3).padEnd(3, "0"));
}

function tausendstelFormatieren(menge) {
  const ganz = menge / 1000n;
  const dezimal = String(menge % 1000n).padStart(3, "0").replace(/0+$/, "");
  return dezimal ? `${ganz}.${dezimal}` : String(ganz);
}

function mitEinheit(menge, einheit) {
  return einheit ? `${menge} ${einheit}` : menge;
}

function teileinkaufMoeglich(artikel) {
  return !artikel.gekauft && (mengeInTausendsteln(artikel.restmenge) ?? 0n) > 0n;
}

function teileinkaufSperrgrund(artikel) {
  if (artikel.gekauft) return "Dieser Artikel ist bereits vollständig gekauft.";
  return "Speichere zuerst eine positive geplante Menge mit maximal drei Nachkommastellen.";
}

function mengenkorrekturMoeglich(artikel) {
  return (mengeInTausendsteln(artikel.menge) ?? 0n) > 0n
    && (mengeInTausendsteln(artikel.gekaufte_menge) ?? 0n) > 0n;
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
    const balken = document.createElement("progress");
    balken.max = 100;
    balken.value = liste.fortschritt.prozent;
    balken.setAttribute("aria-hidden", "true");
    button.append(name, fortschritt, balken);
    button.addEventListener("click", () => {
      ausgewaehlteListe = liste.id;
      document.querySelector("#artikel-form").reset();
      listenAnzeigen();
      detailsAnzeigen();
      detailTitel.focus();
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
  layout.classList.toggle("hat-auswahl", Boolean(liste));
  document.querySelector("#listen-detail").hidden = !liste;
  detailTitel.textContent = liste?.name ?? "";
  if (!liste) {
    artikelElement.replaceChildren();
    return;
  }
  document.querySelector("#fortschritt-text").textContent = fortschrittText(liste);
  document.querySelector("#fortschritt-prozent").textContent = `${liste.fortschritt.prozent.toLocaleString("de-CH")} %`;
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
    checkbox.indeterminate = artikel.status === "teilweise_gekauft";
    const info = document.createElement("div");
    info.className = "artikel-info";
    const beschreibung = document.createElement("span");
    const name = document.createElement("span");
    name.className = "artikel-name";
    name.textContent = artikel.name;
    const zusatz = document.createElement("small");
    zusatz.textContent = artikel.status === "teilweise_gekauft"
      ? `Teilweise gekauft · ${mengeFormatieren(artikel.gekaufte_menge)} von ${mitEinheit(mengeFormatieren(artikel.menge), artikel.einheit)} gekauft · ${mitEinheit(mengeFormatieren(artikel.restmenge), artikel.einheit)} offen`
      : [mengeFormatieren(artikel.menge), artikel.einheit, artikel.gekauft ? "Gekauft" : "Offen"].filter(Boolean).join(" · ");
    beschreibung.append(name, zusatz);
    label.append(checkbox, beschreibung);
    info.append(label);
    const mengenAktionen = document.createElement("div");
    mengenAktionen.className = "mengen-aktionen";
    const teileinkauf = mengenButton("Teileinkauf erfassen", artikel);
    if (!teileinkaufMoeglich(artikel)) {
      teileinkauf.disabled = true;
      teileinkauf.title = teileinkaufSperrgrund(artikel);
    }
    mengenAktionen.append(teileinkauf);
    if (artikel.status === "teilweise_gekauft" && mengenkorrekturMoeglich(artikel)) {
      mengenAktionen.append(mengenButton("Gekaufte Menge korrigieren", artikel, true));
    }
    info.append(mengenAktionen);
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
    li.append(info, aktionen);
    artikelElement.append(li);
    checkbox.addEventListener("change", async () => {
      checkbox.disabled = true;
      meldung.hidden = true;
      try {
        await api(`/artikel/${artikel.id}/status`, "PATCH", { gekauft: checkbox.checked });
        await laden();
      } catch (fehler) {
        checkbox.checked = artikel.gekauft;
        checkbox.indeterminate = artikel.status === "teilweise_gekauft";
        fehlerAnzeigen(fehler);
      } finally {
        checkbox.disabled = false;
      }
    });
  }
}

function mengenButton(text, artikel, korrigieren = false) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "sekundaer teileinkauf-button";
  button.textContent = text;
  button.setAttribute("aria-label", `${text}: ${artikel.name}`);
  button.addEventListener("click", () => teileinkaufOeffnen(artikel, korrigieren));
  return button;
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
  bearbeiteterArtikel = artikel;
  bearbeitenForm.elements.name.value = artikel.name;
  bearbeitenForm.elements.menge.value = mengeFormatieren(artikel.menge);
  bearbeitenForm.elements.menge.setCustomValidity("");
  bearbeitenForm.elements.einheit.value = artikel.einheit ?? "";
  bearbeitenFehler.hidden = true;
  bearbeitenTeileinkauf.disabled = !teileinkaufMoeglich(artikel);
  bearbeitenKorrigieren.hidden = !mengenkorrekturMoeglich(artikel);
  bearbeitenKorrigieren.disabled = false;
  bearbeitenTeilhinweis.textContent = mengendialogHinweis();
  bearbeitenDialog.showModal();
}

function mengendialogHinweis() {
  if (!bearbeitenKorrigieren.hidden) return "Über «Gekaufte Menge korrigieren» änderst du die bisher gekaufte Menge.";
  if (teileinkaufMoeglich(bearbeiteterArtikel)) return "Einen Einkauf erfasst du über «Teileinkauf erfassen».";
  return teileinkaufSperrgrund(bearbeiteterArtikel);
}

bearbeitenForm.addEventListener("input", () => {
  const artikel = bearbeiteterArtikel;
  const felder = bearbeitenForm.elements;
  const geaendert = felder.name.value !== artikel.name
    || felder.menge.value !== mengeFormatieren(artikel.menge)
    || felder.einheit.value !== (artikel.einheit ?? "");
  bearbeitenTeileinkauf.disabled = geaendert || !teileinkaufMoeglich(artikel);
  bearbeitenKorrigieren.disabled = geaendert;
  bearbeitenTeilhinweis.textContent = geaendert
    ? "Speichere zuerst deine Änderungen. Danach kannst du die gekaufte Menge erfassen oder korrigieren."
    : mengendialogHinweis();
});
for (const button of [bearbeitenTeileinkauf, bearbeitenKorrigieren]) {
  button.addEventListener("click", () => {
    const artikel = bearbeiteterArtikel;
    bearbeitenDialog.close();
    teileinkaufOeffnen(artikel, button === bearbeitenKorrigieren);
  });
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
    const menge = bearbeitenForm.elements.menge.value;
    await api(`/artikel/${bearbeiteterArtikel.id}`, "PUT", {
      name: bearbeitenForm.elements.name.value,
      menge: menge === mengeFormatieren(bearbeiteterArtikel.menge) ? bearbeiteterArtikel.menge : menge || null,
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

function teileinkaufOeffnen(artikel, korrigieren = false) {
  teileinkaufArtikel = artikel;
  gekaufteMengeKorrigieren = korrigieren;
  document.querySelector("#teileinkauf-titel").textContent = korrigieren ? "Gekaufte Menge korrigieren" : "Teileinkauf erfassen";
  document.querySelector("#teileinkauf-menge-label").textContent = korrigieren ? "Neue gekaufte Gesamtmenge" : "Jetzt zusätzlich gekauft";
  document.querySelector("#teileinkauf-artikel").textContent = artikel.name;
  document.querySelector("#teileinkauf-geplant").textContent = mitEinheit(mengeFormatieren(artikel.menge), artikel.einheit);
  document.querySelector("#teileinkauf-gekauft").textContent = mitEinheit(mengeFormatieren(artikel.gekaufte_menge), artikel.einheit);
  teileinkaufForm.reset();
  if (korrigieren) teileinkaufMenge.value = mengeFormatieren(artikel.gekaufte_menge);
  teileinkaufFehler.hidden = true;
  teileinkaufVorschau();
  teileinkaufDialog.showModal();
}

function teileinkaufVorschau() {
  const korrektur = gekaufteMengeKorrigieren;
  const obergrenze = mengeInTausendsteln(korrektur ? teileinkaufArtikel.menge : teileinkaufArtikel.restmenge);
  const eingabe = teileinkaufMenge.value.trim();
  const menge = eingabe ? mengeInTausendsteln(eingabe) : 0n;
  let fehler = "";
  if (teileinkaufMenge.value && (!eingabe || menge === null || (!korrektur && menge === 0n))) {
    fehler = korrektur
      ? "Gib eine Menge ab null mit maximal drei Nachkommastellen ein."
      : "Gib eine positive Menge mit maximal drei Nachkommastellen ein.";
  } else if (menge > obergrenze) {
    fehler = korrektur
      ? "Die gekaufte Menge darf die geplante Menge nicht überschreiten."
      : "Die zusätzliche Menge darf die offene Restmenge nicht überschreiten.";
  }
  teileinkaufMenge.setCustomValidity(fehler);
  teileinkaufRest.textContent = fehler || (korrektur && !eingabe)
    ? "–"
    : mitEinheit(tausendstelFormatieren(obergrenze - menge), teileinkaufArtikel.einheit);
}

teileinkaufMenge.addEventListener("input", teileinkaufVorschau);
document.querySelector("#teileinkauf-abbrechen").addEventListener("click", () => teileinkaufDialog.close());
teileinkaufDialog.addEventListener("cancel", (event) => {
  if (teileinkaufFelder.disabled) event.preventDefault();
});
teileinkaufForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  teileinkaufFelder.disabled = true;
  teileinkaufFehler.hidden = true;
  meldung.hidden = true;
  try {
    const artikelPfad = `/artikel/${teileinkaufArtikel.id}`;
    const menge = teileinkaufMenge.value.trim().replace(",", ".");
    if (gekaufteMengeKorrigieren) {
      await api(`${artikelPfad}/gekaufte-menge`, "PATCH", { gekaufte_menge: menge });
    } else {
      await api(`${artikelPfad}/teileinkauf`, "POST", { zusaetzliche_menge: menge });
    }
  } catch (fehler) {
    teileinkaufFehler.textContent = fehler.message;
    teileinkaufFehler.hidden = false;
    return;
  } finally {
    teileinkaufFelder.disabled = false;
  }
  teileinkaufDialog.close();
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
    document.querySelector("#artikel-form").reset();
    form.reset();
    await laden();
    detailTitel.focus();
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
