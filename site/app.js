const FAVORITES_KEY = "virada-cultural-2026-v3:favorites";
const collator = new Intl.Collator("pt-BR", { sensitivity: "base", numeric: true });

const state = {
  events: [],
  filtered: [],
  favorites: {},
  metadata: null,
};

const el = {
  totalEvents: document.querySelector("#totalEvents"),
  visibleEvents: document.querySelector("#visibleEvents"),
  favoriteEvents: document.querySelector("#favoriteEvents"),
  activeDates: document.querySelector("#activeDates"),
  searchInput: document.querySelector("#searchInput"),
  dateFilter: document.querySelector("#dateFilter"),
  categoryFilter: document.querySelector("#categoryFilter"),
  placeFilter: document.querySelector("#placeFilter"),
  neighborhoodFilter: document.querySelector("#neighborhoodFilter"),
  sortOrder: document.querySelector("#sortOrder"),
  favoritesOnly: document.querySelector("#favoritesOnly"),
  resetFilters: document.querySelector("#resetFilters"),
  status: document.querySelector("#status"),
  eventList: document.querySelector("#eventos"),
  exportVisibleCsv: document.querySelector("#exportVisibleCsv"),
  exportFavoritesCsv: document.querySelector("#exportFavoritesCsv"),
  exportFavoritesIcs: document.querySelector("#exportFavoritesIcs"),
  exportFavoritesJson: document.querySelector("#exportFavoritesJson"),
  importFavoritesJson: document.querySelector("#importFavoritesJson"),
  clearFavorites: document.querySelector("#clearFavorites"),
  dialog: document.querySelector("#eventDialog"),
  dialogContent: document.querySelector("#dialogContent"),
};

function normalize(text) {
  return String(text || "")
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .toLowerCase()
    .trim();
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => {
    const entities = { "&": "&", "<": "<", ">": ">", '"': """, "'": "'" };
    return entities[char];
  });
}

function loadFavorites() {
  const raw = localStorage.getItem(FAVORITES_KEY);
  if (!raw) return {};
  const parsed = JSON.parse(raw);
  return parsed && typeof parsed === "object" ? parsed : {};
}

function saveFavorites() {
  localStorage.setItem(FAVORITES_KEY, JSON.stringify(state.favorites));
}

function uniqueSorted(key) {
  return [...new Set(state.events.map((event) => event[key]).filter(Boolean))].sort(collator.compare);
}

function fillSelect(select, values, selectedValue = select.value) {
  const first = select.options[0];
  select.replaceChildren(first);
  for (const value of values) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = value;
    select.append(option);
  }
  select.value = values.includes(selectedValue) ? selectedValue : "";
}

function prepareEvents(events) {
  return events.map((event) => ({
    ...event,
    _search: normalize(
      [
        event.nome,
        event.bairro,
        event.local,
        event.categoria,
        event.endereco,
        event.descricao,
        event.data_inicio,
        event.hora_inicio,
      ].join(" ")
    ),
  }));
}

const dependentFilters = [
  { key: "data_inicio", select: el.dateFilter },
  { key: "categoria", select: el.categoryFilter },
  { key: "local", select: el.placeFilter },
  { key: "bairro", select: el.neighborhoodFilter },
];

function eventUrl(event) {
  return event.url_oficial || event.url || "";
}

function matchesCurrentFilters(event, skipKey = "") {
  const query = normalize(el.searchInput.value);
  const terms = query ? query.split(/\s+/) : [];
  if (el.dateFilter.value && skipKey !== "data_inicio" && event.data_inicio !== el.dateFilter.value) return false;
  if (el.categoryFilter.value && skipKey !== "categoria" && event.categoria !== el.categoryFilter.value) return false;
  if (el.placeFilter.value && skipKey !== "local" && event.local !== el.placeFilter.value) return false;
  if (el.neighborhoodFilter.value && skipKey !== "bairro" && event.bairro !== el.neighborhoodFilter.value) return false;
  if (el.favoritesOnly.checked && !state.favorites[event.slug]) return false;
  return terms.every((term) => event._search.includes(term));
}

function updateDependentSelects() {
  for (const filter of dependentFilters) {
    const values = [
      ...new Set(
        state.events
          .filter((event) => matchesCurrentFilters(event, filter.key))
          .map((event) => event[filter.key])
          .filter(Boolean)
      ),
    ].sort(collator.compare);
    fillSelect(filter.select, values);
  }
}

function applyFilters() {
  updateDependentSelects();
  state.filtered = state.events.filter((event) => matchesCurrentFilters(event));

  sortFiltered();
  render();
}

function sortFiltered() {
  const sortOrder = el.sortOrder.value;
  state.filtered.sort((a, b) => {
    if (sortOrder === "name") return collator.compare(a.nome, b.nome);
    if (sortOrder === "category") {
      return collator.compare(a.categoria, b.categoria) || collator.compare(a.nome, b.nome);
    }
    if (sortOrder === "neighborhood") {
      return collator.compare(a.bairro, b.bairro) || collator.compare(a.nome, b.nome);
    }
    return collator.compare(a.inicio_iso_utc, b.inicio_iso_utc) || collator.compare(a.nome, b.nome);
  });
}

function renderStats() {
  el.totalEvents.textContent = state.events.length.toLocaleString("pt-BR");
  el.visibleEvents.textContent = state.filtered.length.toLocaleString("pt-BR");
  el.favoriteEvents.textContent = favoriteRows().length.toLocaleString("pt-BR");
  el.activeDates.textContent = new Set(state.events.map((event) => event.data_inicio)).size;
}

function imageHtml(event) {
  if (!event.foto) return "";
  return `<img src="${escapeHtml(event.foto)}" alt="" loading="lazy" />`;
}

function eventCard(event) {
  const favorite = Boolean(state.favorites[event.slug]);
  const description = event.descricao ? `${event.descricao.slice(0, 150)}${event.descricao.length > 150 ? "..." : ""}` : "";
  const url = eventUrl(event);
  const officialButton = url
    ? `<a class="button secondary" href="${escapeHtml(url)}" target="_blank" rel="noopener">Oficial</a>`
    : `<span class="pill" title="Slug inválido na fonte oficial — sem página individual disponível">Sem página oficial</span>`;
  return `
    <article class="event-card" data-slug="${escapeHtml(event.slug)}">
      ${imageHtml(event)}
      <div class="event-body">
        <div class="event-meta">
          <span class="pill date">${escapeHtml(event.data_inicio)}</span>
          <span class="pill time">${escapeHtml(event.hora_inicio)}–${escapeHtml(event.hora_fim)}</span>
          <span class="pill">${escapeHtml(event.categoria || "Sem categoria")}</span>
        </div>
        <h3>${escapeHtml(event.nome)}</h3>
        <p class="event-location">${escapeHtml(event.local || "Local não informado")} · ${escapeHtml(event.bairro || "Bairro não informado")}</p>
        <p class="event-description">${escapeHtml(description)}</p>
        <div class="event-actions">
          <button class="button ghost favorite-button" type="button" data-action="favorite" aria-pressed="${favorite}">
            ${favorite ? "★ Favorito" : "☆ Favoritar"}
          </button>
          <button class="button secondary" type="button" data-action="details">Detalhes</button>
          ${officialButton}
        </div>
      </div>
    </article>
  `;
}

function render() {
  renderStats();
  el.status.textContent = `${state.filtered.length.toLocaleString("pt-BR")} evento(s) encontrado(s).`;

  if (!state.filtered.length) {
    el.eventList.innerHTML = '<div class="empty">Nenhum evento corresponde aos filtros atuais.</div>';
    return;
  }

  el.eventList.innerHTML = state.filtered.map(eventCard).join("");
}

function favoriteRows() {
  return state.events.filter((event) => state.favorites[event.slug]);
}

function toggleFavorite(slug) {
  if (state.favorites[slug]) {
    delete state.favorites[slug];
  } else {
    state.favorites[slug] = { slug, note: "", addedAt: new Date().toISOString() };
  }
  saveFavorites();
  applyFilters();
}

function updateFavoriteNote(slug, note) {
  if (!state.favorites[slug]) {
    state.favorites[slug] = { slug, note: "", addedAt: new Date().toISOString() };
  }
  state.favorites[slug].note = note;
  saveFavorites();
  renderStats();
}

function openDetails(slug) {
  const event = state.events.find((item) => item.slug === slug);
  if (!event) return;
  const favorite = Boolean(state.favorites[event.slug]);
  const note = state.favorites[event.slug]?.note || "";
  const url = eventUrl(event);
  const officialLink = url
    ? `<a class="button secondary" href="${escapeHtml(url)}" target="_blank" rel="noopener">Abrir no site oficial</a>`
    : `<span class="pill" title="Slug inválido na fonte oficial">Sem página oficial disponível</span>`;
  el.dialogContent.innerHTML = `
    <div class="dialog-body">
      ${imageHtml(event)}
      <div class="event-meta">
        <span class="pill date">${escapeHtml(event.data_inicio)}</span>
        <span class="pill time">${escapeHtml(event.hora_inicio)}–${escapeHtml(event.hora_fim)}</span>
        <span class="pill">${escapeHtml(event.categoria || "Sem categoria")}</span>
      </div>
      <h2>${escapeHtml(event.nome)}</h2>
      <p><strong>Local:</strong> ${escapeHtml(event.local || "Não informado")} · ${escapeHtml(event.bairro || "Bairro não informado")}</p>
      <p><strong>Endereço:</strong> ${escapeHtml(event.endereco || "Não informado")}</p>
      <p>${escapeHtml(event.descricao || "Sem descrição.")}</p>
      <div class="event-actions">
        <button class="button ghost favorite-button" type="button" data-dialog-favorite="${escapeHtml(event.slug)}" aria-pressed="${favorite}">
          ${favorite ? "★ Favorito" : "☆ Favoritar"}
        </button>
        ${officialLink}
      </div>
      <label class="note-box">
        Nota pessoal para este evento
        <textarea data-note-for="${escapeHtml(event.slug)}" rows="4" placeholder="Ex.: chegar cedo, combinar com amigos, ver transporte...">${escapeHtml(note)}</textarea>
      </label>
    </div>
  `;
  el.dialog.showModal();
}

function csvEscape(value) {
  const text = String(value ?? "");
  return /[",\n\r;]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
}

function rowsToCsv(rows) {
  const headers = [
    "nome",
    "data_inicio",
    "hora_inicio",
    "data_fim",
    "hora_fim",
    "bairro",
    "local",
    "tipo_local",
    "categoria",
    "endereco",
    "latitude",
    "longitude",
    "instagram",
    "playlist",
    "url_oficial",
    "foto",
    "descricao",
  ];
  const lines = [headers.join(",")];
  for (const row of rows) {
    lines.push(headers.map((header) => csvEscape(row[header])).join(","));
  }
  return lines.join("\n");
}

function downloadText(filename, text, type) {
  const blob = new Blob([text], { type });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.append(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function icsEscape(value) {
  return String(value ?? "")
    .replaceAll("\\", "\\\\")
    .replaceAll(";", "\\;")
    .replaceAll(",", "\\,")
    .replaceAll("\n", "\\n");
}

function toIcsDate(date, time) {
  const [day, month, year] = date.split("/");
  const [hour, minute] = time.split(":");
  return `${year}${month}${day}T${hour}${minute}00`;
}

function rowsToIcs(rows) {
  const now = new Date().toISOString().replace(/[-:]/g, "").replace(/\.\d{3}Z$/, "Z");
  const lines = [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//Virada Cultural 2026 V3//PT-BR",
    "CALSCALE:GREGORIAN",
    "METHOD:PUBLISH",
    "BEGIN:VTIMEZONE",
    "TZID:America/Sao_Paulo",
    "X-LIC-LOCATION:America/Sao_Paulo",
    "BEGIN:STANDARD",
    "TZOFFSETFROM:-0300",
    "TZOFFSETTO:-0300",
    "TZNAME:BRT",
    "DTSTART:19700101T000000",
    "END:STANDARD",
    "END:VTIMEZONE",
  ];

  for (const event of rows) {
    lines.push(
      "BEGIN:VEVENT",
      `UID:${event.slug}@virada-cultural-2026-v3`,
      `DTSTAMP:${now}`,
      `DTSTART;TZID=America/Sao_Paulo:${toIcsDate(event.data_inicio, event.hora_inicio)}`,
      `DTEND;TZID=America/Sao_Paulo:${toIcsDate(event.data_fim, event.hora_fim)}`,
      `SUMMARY:${icsEscape(event.nome)}`,
      `LOCATION:${icsEscape([event.local, event.endereco].filter(Boolean).join(" - "))}`,
      `DESCRIPTION:${icsEscape([event.descricao, eventUrl(event)].filter(Boolean).join("\\n\\n"))}`,
      "END:VEVENT"
    );
  }

  lines.push("END:VCALENDAR");
  return lines.join("\r\n");
}

function exportFavoritesJson() {
  const payload = {
    version: 2,
    exportedAt: new Date().toISOString(),
    favorites: state.favorites,
  };
  downloadText("virada-cultural-2026-minha-lista.json", JSON.stringify(payload, null, 2), "application/json;charset=utf-8");
}

function importFavoritesJson(file) {
  const reader = new FileReader();
  reader.addEventListener("load", () => {
    const payload = JSON.parse(String(reader.result || "{}"));
    if (!payload.favorites || typeof payload.favorites !== "object") {
      throw new Error("Arquivo JSON sem objeto favorites.");
    }
    state.favorites = payload.favorites;
    saveFavorites();
    applyFilters();
    el.status.textContent = "Lista importada com sucesso.";
  });
  reader.readAsText(file);
}

function bindEvents() {
  const filterInputs = [el.searchInput, el.dateFilter, el.categoryFilter, el.placeFilter, el.neighborhoodFilter, el.sortOrder, el.favoritesOnly];
  for (const input of filterInputs) input.addEventListener("input", applyFilters);

  el.resetFilters.addEventListener("click", () => {
    el.searchInput.value = "";
    el.dateFilter.value = "";
    el.categoryFilter.value = "";
    el.placeFilter.value = "";
    el.neighborhoodFilter.value = "";
    el.sortOrder.value = "time";
    el.favoritesOnly.checked = false;
    applyFilters();
  });

  el.eventList.addEventListener("click", (event) => {
    const button = event.target.closest("[data-action]");
    if (!button) return;
    const card = button.closest("[data-slug]");
    if (!card) return;
    const slug = card.dataset.slug;
    if (button.dataset.action === "favorite") toggleFavorite(slug);
    if (button.dataset.action === "details") openDetails(slug);
  });

  el.dialogContent.addEventListener("click", (event) => {
    const favoriteButton = event.target.closest("[data-dialog-favorite]");
    if (favoriteButton) toggleFavorite(favoriteButton.dataset.dialogFavorite);
  });

  el.dialogContent.addEventListener("input", (event) => {
    const note = event.target.closest("[data-note-for]");
    if (note) updateFavoriteNote(note.dataset.noteFor, note.value);
  });

  el.exportVisibleCsv.addEventListener("click", () => {
    downloadText("virada-cultural-2026-filtrado.csv", rowsToCsv(state.filtered), "text/csv;charset=utf-8");
  });

  el.exportFavoritesCsv.addEventListener("click", () => {
    downloadText("virada-cultural-2026-favoritos.csv", rowsToCsv(favoriteRows()), "text/csv;charset=utf-8");
  });

  el.exportFavoritesIcs.addEventListener("click", () => {
    const rows = favoriteRows();
    if (!rows.length) {
      el.status.textContent = "Favorite ao menos um evento antes de exportar o calendário.";
      return;
    }
    downloadText("virada-cultural-2026-favoritos.ics", rowsToIcs(rows), "text/calendar;charset=utf-8");
  });

  el.exportFavoritesJson.addEventListener("click", exportFavoritesJson);

  el.importFavoritesJson.addEventListener("change", () => {
    const [file] = el.importFavoritesJson.files;
    if (file) importFavoritesJson(file);
    el.importFavoritesJson.value = "";
  });

  el.clearFavorites.addEventListener("click", () => {
    if (!confirm("Limpar todos os favoritos e notas deste navegador?")) return;
    state.favorites = {};
    saveFavorites();
    applyFilters();
  });
}

async function init() {
  state.favorites = loadFavorites();

  const [eventsResponse, metadataResponse] = await Promise.all([fetch("data/events.json"), fetch("data/metadata.json")]);
  if (!eventsResponse.ok) throw new Error("Não foi possível carregar data/events.json");
  if (!metadataResponse.ok) throw new Error("Não foi possível carregar data/metadata.json");

  state.events = prepareEvents(await eventsResponse.json());
  state.metadata = await metadataResponse.json();

  fillSelect(el.dateFilter, uniqueSorted("data_inicio"));
  fillSelect(el.categoryFilter, uniqueSorted("categoria"));
  fillSelect(el.placeFilter, uniqueSorted("local"));
  fillSelect(el.neighborhoodFilter, uniqueSorted("bairro"));
  bindEvents();
  applyFilters();
}

init().catch((error) => {
  console.error(error);
  el.status.textContent = `Erro ao carregar dados: ${error.message}. Para testar localmente, rode um servidor estático como python -m http.server.`;
});
