#!/usr/bin/env python3
"""Build a single self-contained HTML file for v4 with embedded data."""
from __future__ import annotations
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
DATA = BASE / "data" / "programacao_v2.json"
META = BASE / "data" / "metadata_v2.json"
OUT = BASE / "site_v4" / "index.html"

rows = json.loads(DATA.read_text(encoding="utf-8"))
meta = json.loads(META.read_text(encoding="utf-8"))

payload = json.dumps({"rows": rows, "meta": meta}, ensure_ascii=False, separators=(",", ":"))

HTML = r"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Virada Cultural 2026 — Programação</title>
<style>
:root{
  color-scheme: light;
  --bg:#fff8ec; --surface:#ffffff; --ink:#261447; --muted:#6c5f7a;
  --purple:#7c3aed; --purple-dark:#4c1d95; --pink:#e11d48;
  --yellow:#facc15; --green:#16a34a; --line:#eadff7;
  --shadow:0 20px 50px rgba(38,20,71,.12);
}
*{box-sizing:border-box}
body{
  margin:0;
  background:
    radial-gradient(circle at top left, rgba(250,204,21,.35), transparent 32rem),
    radial-gradient(circle at top right, rgba(225,29,72,.18), transparent 28rem),
    var(--bg);
  color:var(--ink);
  font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
  line-height:1.5;
}
a{color:var(--purple-dark)}
button,input,select{font:inherit}

.hero,main,footer{width:min(1180px, calc(100% - 32px));margin:0 auto}
.hero{padding:56px 0 24px}
.eyebrow{margin:0 0 8px;color:var(--pink);font-size:.78rem;font-weight:900;letter-spacing:.14em;text-transform:uppercase}
.hero h1{margin:0;max-width:820px;font-size:clamp(2.1rem,6vw,5rem);line-height:.95;letter-spacing:-.06em}
.subtitle{max-width:680px;color:var(--muted);font-size:1.08rem;margin-top:10px}

.stats{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:18px 0}
.stats article{border:1px solid var(--line);background:rgba(255,255,255,.92);box-shadow:var(--shadow);border-radius:24px;padding:18px}
.stats strong{display:block;color:var(--purple-dark);font-size:clamp(1.6rem,3.5vw,2.6rem);line-height:1}
.stats span{color:var(--muted);font-weight:800}

.panel{border:1px solid var(--line);background:rgba(255,255,255,.92);box-shadow:var(--shadow);border-radius:28px;margin:18px 0;padding:22px}
.panel h2{margin:0 0 6px;font-size:clamp(1.25rem,3vw,1.8rem)}
.panel p.hint{margin:0;color:var(--muted)}

.filters{display:grid;grid-template-columns:2fr repeat(4,minmax(140px,1fr));gap:12px;margin-top:16px}
label{display:grid;gap:6px;color:var(--muted);font-size:.78rem;font-weight:900;text-transform:uppercase;letter-spacing:.06em}
input,select{width:100%;border:1px solid var(--line);border-radius:14px;background:#fff;color:var(--ink);padding:11px 13px}
input:focus,select:focus{outline:3px solid rgba(124,58,237,.22);border-color:var(--purple)}
.toolbar{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-top:14px}
.button{display:inline-flex;align-items:center;gap:8px;border:0;border-radius:999px;padding:9px 16px;cursor:pointer;font-weight:800;text-decoration:none;transition:transform .15s,box-shadow .15s}
.button:hover{transform:translateY(-1px)}
.button.primary{background:var(--purple);color:#fff;box-shadow:0 12px 24px rgba(124,58,237,.28)}
.button.ghost{background:#f5efff;color:var(--purple-dark)}
.status{margin-left:auto;color:var(--muted);font-weight:800}

.day-group{margin:28px 0}
.day-head{display:flex;align-items:baseline;gap:14px;margin:0 0 14px}
.day-head h2{margin:0;font-size:clamp(1.4rem,3.2vw,2.2rem);letter-spacing:-.03em}
.day-head .count{color:var(--muted);font-weight:800}

.venue-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:16px}
.venue-card{border:1px solid var(--line);background:rgba(255,255,255,.95);box-shadow:var(--shadow);border-radius:26px;overflow:hidden;display:flex;flex-direction:column}
.venue-head{padding:16px 18px;background:linear-gradient(135deg,#f5efff,#fff);border-bottom:1px solid var(--line)}
.venue-head h3{margin:0;font-size:1.1rem;line-height:1.2}
.venue-head .meta{margin-top:6px;color:var(--muted);font-size:.85rem}
.pill{display:inline-flex;align-items:center;border-radius:999px;padding:3px 9px;font-size:.72rem;font-weight:900;background:#f5efff;color:var(--purple-dark);margin-right:6px}
.pill.region{background:#fef3c7;color:#92400e}
.pill.cat{background:#ffe4e6;color:#9f1239}

ul.times{list-style:none;margin:0;padding:6px 0;flex:1}
ul.times li{display:grid;grid-template-columns:84px 1fr;gap:10px;align-items:start;padding:9px 18px;border-top:1px dashed var(--line)}
ul.times li:first-child{border-top:none}
ul.times li.live{background:linear-gradient(90deg,rgba(250,204,21,.25),transparent)}
.time{font-variant-numeric:tabular-nums;color:var(--purple-dark);font-weight:900}
.atr{color:var(--ink);font-weight:600}
.live-tag{display:inline-block;margin-left:8px;font-size:.65rem;font-weight:900;text-transform:uppercase;letter-spacing:.08em;background:var(--green);color:#fff;padding:1px 7px;border-radius:999px;vertical-align:middle}
.djs{padding:10px 18px;color:var(--muted);font-size:.85rem;border-top:1px dashed var(--line)}
.djs strong{color:var(--ink)}

.empty{border:2px dashed var(--line);border-radius:28px;padding:48px;text-align:center;color:var(--muted)}

footer{padding:24px 0 48px;color:var(--muted);font-size:.92rem}

@media (max-width:980px){
  .stats{grid-template-columns:repeat(2,minmax(0,1fr))}
  .filters{grid-template-columns:repeat(2,minmax(0,1fr))}
  .filters label.wide{grid-column:1 / -1}
}
@media (max-width:640px){
  .stats,.filters{grid-template-columns:1fr}
  ul.times li{grid-template-columns:72px 1fr}
}
</style>
</head>
<body>
<header class="hero">
  <p class="eyebrow">Programação oficial · 23–24 de maio de 2026</p>
  <h1>Virada Cultural 2026</h1>
  <p class="subtitle">Pesquise palcos, pistas e equipamentos culturais. Tudo num arquivo só, sem login, sem nada para instalar.</p>
</header>

<main>
  <section class="stats" id="stats"></section>

  <section class="panel">
    <h2>Filtros</h2>
    <p class="hint">Combine busca livre, dia, região e local. Tudo acontece localmente no seu navegador.</p>
    <div class="filters">
      <label class="wide">Busca livre
        <input id="q" type="search" placeholder="Procure por atração, local ou bairro…" autocomplete="off">
      </label>
      <label>Dia
        <select id="data"><option value="">Todos</option></select>
      </label>
      <label>Região
        <select id="regiao"><option value="">Todas</option></select>
      </label>
      <label>Categoria
        <select id="categoria"><option value="">Todas</option></select>
      </label>
      <label>Local
        <select id="local"><option value="">Todos</option></select>
      </label>
    </div>
    <div class="toolbar">
      <button class="button primary" id="now">Acontecendo agora</button>
      <button class="button ghost" id="next">Próximas 2h</button>
      <button class="button ghost" id="reset">Limpar filtros</button>
      <span class="status" id="status">—</span>
    </div>
  </section>

  <section id="results"></section>
</main>

<footer>
  <p id="meta">—</p>
  <p>Dados extraídos de <a href="https://prefeitura.sp.gov.br/web/cultura/w/programa%C3%A7%C3%A3o-completa-da-virada-cultural" target="_blank" rel="noopener">prefeitura.sp.gov.br</a>. Página estática, feita para consulta rápida.</p>
</footer>

<script id="payload" type="application/json">__PAYLOAD__</script>
<script>
const PAYLOAD = JSON.parse(document.getElementById("payload").textContent);
const ROWS = PAYLOAD.rows;
const META = PAYLOAD.meta;

const $ = (s) => document.querySelector(s);
const escapeHtml = (s) => { const d = document.createElement("div"); d.textContent = String(s); return d.innerHTML; };
const uniq = (arr) => [...new Set(arr)].filter(Boolean).sort((a,b)=>a.localeCompare(b,"pt-BR"));

function fmtDate(iso){
  if(!iso) return "";
  const [y,m,d] = iso.split("-");
  const dt = new Date(+y, +m-1, +d);
  const days = ["domingo","segunda-feira","terça-feira","quarta-feira","quinta-feira","sexta-feira","sábado"];
  const months = ["janeiro","fevereiro","março","abril","maio","junho","julho","agosto","setembro","outubro","novembro","dezembro"];
  return `${days[dt.getDay()]}, ${+d} de ${months[+m-1]}`;
}

function fillSelect(sel, values, fmt){
  for(const v of values){
    const o = document.createElement("option");
    o.value = v; o.textContent = fmt ? fmt(v) : v;
    sel.appendChild(o);
  }
}

fillSelect($("#data"), uniq(ROWS.map(r=>r.data)), iso => {
  const [y,m,d] = iso.split("-"); return `${d}/${m}/${y}`;
});
fillSelect($("#regiao"), uniq(ROWS.map(r=>r.regiao)));
fillSelect($("#categoria"), uniq(ROWS.map(r=>r.categoria)));
fillSelect($("#local"), uniq(ROWS.map(r=>r.local)));

function filtered(){
  const q = $("#q").value.trim().toLowerCase();
  const data = $("#data").value;
  const regiao = $("#regiao").value;
  const categoria = $("#categoria").value;
  const local = $("#local").value;
  return ROWS.filter(r => {
    if(data && r.data !== data) return false;
    if(regiao && r.regiao !== regiao) return false;
    if(categoria && r.categoria !== categoria) return false;
    if(local && r.local !== local) return false;
    if(q){
      const hay = `${r.atracao} ${r.local} ${r.endereco} ${r.regiao} ${r.djs_intervalo||""}`.toLowerCase();
      if(!hay.includes(q)) return false;
    }
    return true;
  });
}

function renderStats(rows){
  const wrap = $("#stats");
  const venues = new Set(rows.map(r=>r.local));
  const dates = new Set(rows.map(r=>r.data));
  const regions = new Set(rows.map(r=>r.regiao));
  wrap.innerHTML = `
    <article><strong>${rows.length.toLocaleString("pt-BR")}</strong><span>Eventos</span></article>
    <article><strong>${venues.size}</strong><span>Locais</span></article>
    <article><strong>${regions.size}</strong><span>Regiões</span></article>
    <article><strong>${dates.size}</strong><span>Dias</span></article>`;
}

function render(){
  const rows = filtered();
  $("#status").textContent = `${rows.length} eventos exibidos`;
  renderStats(rows);
  const root = $("#results");
  if(!rows.length){
    root.innerHTML = `<div class="empty">Nada encontrado com esses filtros.</div>`;
    return;
  }
  // Group by date -> venue
  const byDate = new Map();
  for(const r of rows){
    if(!byDate.has(r.data)) byDate.set(r.data, new Map());
    const v = byDate.get(r.data);
    if(!v.has(r.local)) v.set(r.local, []);
    v.get(r.local).push(r);
  }
  const now = new Date();
  const dates = [...byDate.keys()].sort();
  let html = "";
  for(const d of dates){
    const venues = byDate.get(d);
    const venueNames = [...venues.keys()].sort((a,b)=>a.localeCompare(b,"pt-BR"));
    const total = [...venues.values()].reduce((a,b)=>a+b.length,0);
    html += `<section class="day-group">
      <div class="day-head"><h2>${escapeHtml(fmtDate(d))}</h2><span class="count">${total} eventos · ${venueNames.length} locais</span></div>
      <div class="venue-grid">`;
    for(const v of venueNames){
      const items = venues.get(v).sort((a,b)=>(a.inicio_iso||"").localeCompare(b.inicio_iso||""));
      const first = items[0];
      const djs = first.djs_intervalo;
      html += `<article class="venue-card">
        <header class="venue-head">
          <h3>${escapeHtml(v)}</h3>
          <div>
            ${first.regiao ? `<span class="pill region">${escapeHtml(first.regiao)}</span>`:""}
            ${first.categoria ? `<span class="pill cat">${escapeHtml(first.categoria)}</span>`:""}
          </div>
          ${first.endereco ? `<div class="meta">${escapeHtml(first.endereco)}</div>` : ""}
        </header>
        <ul class="times">
          ${items.map(r => {
            const live = r.inicio_iso && r.fim_iso && new Date(r.inicio_iso) <= now && now < new Date(r.fim_iso);
            const range = r.hora_fim ? `${r.hora_inicio}–${r.hora_fim}` : r.hora_inicio;
            return `<li class="${live?"live":""}">
              <span class="time">${escapeHtml(range)}</span>
              <span class="atr">${escapeHtml(r.atracao)}${live?'<span class="live-tag">ao vivo</span>':""}</span>
            </li>`;
          }).join("")}
        </ul>
        ${djs ? `<div class="djs"><strong>DJs de intervalo:</strong> ${escapeHtml(djs)}</div>` : ""}
      </article>`;
    }
    html += `</div></section>`;
  }
  root.innerHTML = html;
}

function setOnly(id, value){
  ["q","data","regiao","categoria","local"].forEach(x => $("#"+x).value = "");
  if(id) $("#"+id).value = value;
  render();
}

["q","data","regiao","categoria","local"].forEach(id =>
  $("#"+id).addEventListener("input", render));

$("#reset").addEventListener("click", () => setOnly());

$("#now").addEventListener("click", () => {
  const now = new Date();
  const live = ROWS.filter(r => r.inicio_iso && r.fim_iso && new Date(r.inicio_iso)<=now && now<new Date(r.fim_iso));
  if(!live.length){
    $("#status").textContent = "Nada acontecendo agora — mostrando próximas 2h.";
    $("#next").click(); return;
  }
  // Filter ROWS to live ones via a temporary q match by slug list — simpler: just filter visually
  $("#results").innerHTML = renderCustom(live, "Acontecendo agora");
  $("#status").textContent = `${live.length} eventos ao vivo`;
  renderStats(live);
});

$("#next").addEventListener("click", () => {
  const now = new Date(); const horizon = new Date(now.getTime()+2*3600*1000);
  const soon = ROWS.filter(r => r.inicio_iso && new Date(r.inicio_iso)>=now && new Date(r.inicio_iso)<=horizon);
  $("#results").innerHTML = renderCustom(soon, "Próximas 2 horas");
  $("#status").textContent = `${soon.length} eventos nas próximas 2h`;
  renderStats(soon);
});

function renderCustom(rows, label){
  if(!rows.length) return `<div class="empty">Nada por aqui — tente "Limpar filtros".</div>`;
  rows = rows.slice().sort((a,b)=>(a.inicio_iso||"").localeCompare(b.inicio_iso||""));
  return `<section class="day-group">
    <div class="day-head"><h2>${label}</h2><span class="count">${rows.length} eventos</span></div>
    <div class="venue-grid">
      ${rows.map(r => `<article class="venue-card">
        <header class="venue-head">
          <h3>${escapeHtml(r.atracao)}</h3>
          <div>
            ${r.regiao ? `<span class="pill region">${escapeHtml(r.regiao)}</span>`:""}
            ${r.categoria ? `<span class="pill cat">${escapeHtml(r.categoria)}</span>`:""}
          </div>
          <div class="meta">${escapeHtml(r.local)}${r.endereco?` · ${escapeHtml(r.endereco)}`:""}</div>
        </header>
        <ul class="times"><li>
          <span class="time">${escapeHtml(r.hora_fim?`${r.hora_inicio}–${r.hora_fim}`:r.hora_inicio)}</span>
          <span class="atr">${escapeHtml(fmtDate(r.data))}</span>
        </li></ul>
      </article>`).join("")}
    </div></section>`;
}

$("#meta").textContent = `${META.event_count} eventos · ${META.venues.length} locais · gerado em ${META.generated_at}`;
render();
</script>
</body>
</html>
"""

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(HTML.replace("__PAYLOAD__", payload), encoding="utf-8")
print(f"Wrote {OUT} ({OUT.stat().st_size:,} bytes)")