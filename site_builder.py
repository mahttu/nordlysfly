"""Bygger én selvstendig HTML-side med funnene innebygd."""
import json
from pathlib import Path

TEMPLATE = r"""<!DOCTYPE html>
<html lang="nb">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Nordlys Fly – feilpriser fra Nord-Norge</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,400;9..40,500;9..40,700&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet">
<style>
:root{
  --bg:#0b1220; --panel:#121b2e; --panel2:#18233a; --line:#24314d;
  --text:#e8edf7; --muted:#8f9bb5; --aurora:#5df2b0; --aurora2:#7cc8ff; --warn:#ffcf6b; --hot:#ff7a8a;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font-family:"DM Sans",system-ui,sans-serif;line-height:1.45}
body::before{content:"";position:fixed;inset:0 0 auto 0;height:340px;pointer-events:none;z-index:-1;
  background:radial-gradient(60% 120% at 20% -10%,rgba(93,242,176,.18),transparent 70%),
             radial-gradient(50% 100% at 85% -20%,rgba(124,200,255,.16),transparent 70%)}
.wrap{max-width:860px;margin:0 auto;padding:28px 16px 60px}
header h1{font-size:clamp(28px,6vw,40px);margin:0 0 4px;letter-spacing:-.02em}
header h1 span{background:linear-gradient(90deg,var(--aurora),var(--aurora2));-webkit-background-clip:text;background-clip:text;color:transparent}
header p{margin:0;color:var(--muted)}
.meta{font-size:13px;color:var(--muted);margin-top:10px}
.demo{display:inline-block;background:rgba(255,207,107,.12);color:var(--warn);border:1px solid rgba(255,207,107,.35);
  padding:2px 8px;border-radius:99px;font-size:12px;margin-left:6px}
.controls{position:sticky;top:0;background:rgba(11,18,32,.92);backdrop-filter:blur(8px);padding:14px 0 10px;margin:18px 0 6px;z-index:5}
.tabs{display:flex;gap:6px;background:var(--panel);padding:4px;border-radius:12px;border:1px solid var(--line)}
.tab{flex:1;border:0;background:none;color:var(--muted);font:inherit;font-weight:500;padding:9px 6px;border-radius:9px;cursor:pointer}
.tab[aria-selected=true]{background:var(--panel2);color:var(--text);box-shadow:inset 0 0 0 1px var(--line)}
.tab b{font-family:"JetBrains Mono",monospace;font-size:12px;color:var(--aurora);margin-left:4px}
.chips{display:flex;gap:6px;margin-top:10px;flex-wrap:wrap}
.chips[hidden]{display:none}
.search{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:10px}
.search[hidden]{display:none}
.search label{display:flex;flex-direction:column;gap:4px;font-size:12px;color:var(--muted)}
.search select,.search input[type=date]{font:inherit;font-size:15px;color:var(--text);background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:9px 10px;color-scheme:dark;width:100%}
.search .flex{grid-column:1/-1;flex-direction:row;align-items:center;gap:8px;font-size:14px;color:var(--text)}
.search .flex input{width:18px;height:18px;accent-color:var(--aurora)}
.live{display:block;text-align:center;margin:0 0 10px;padding:10px;border:1px dashed var(--line);border-radius:12px;color:var(--aurora2);text-decoration:none;font-size:14px}
.chip{border:1px solid var(--line);background:none;color:var(--muted);font:inherit;font-size:14px;padding:6px 12px;border-radius:99px;cursor:pointer}
.chip[aria-pressed=true]{border-color:var(--aurora);color:var(--aurora);background:rgba(93,242,176,.08)}
.info{background:var(--panel);border:1px solid var(--line);border-left:3px solid var(--warn);border-radius:10px;padding:12px 14px;font-size:14px;color:var(--muted);margin:10px 0 14px}
.info strong{color:var(--text)}
.list{display:grid;gap:10px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:14px 16px;display:grid;grid-template-columns:1fr auto;gap:6px 14px;align-items:center}
.route{font-family:"JetBrains Mono",monospace;font-weight:700;font-size:15px;letter-spacing:.02em}
.route .arrow{color:var(--muted);font-weight:500;margin:0 4px}
.route .skip{color:var(--muted);text-decoration:line-through;text-decoration-color:var(--hot)}
.names{color:var(--muted);font-size:13px}
.price{text-align:right;font-family:"JetBrains Mono",monospace;font-size:22px;font-weight:700;color:var(--aurora)}
.price small{display:block;font-size:12px;color:var(--muted);font-weight:500;text-decoration:line-through}
.tags{grid-column:1/-1;display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin-top:4px}
.tag{font-size:12px;padding:3px 8px;border-radius:6px;background:var(--panel2);color:var(--muted)}
.tag.hot{background:rgba(255,122,138,.14);color:var(--hot);font-weight:700}
.tag.ok{background:rgba(93,242,176,.12);color:var(--aurora)}
.tag.warn{background:rgba(255,207,107,.12);color:var(--warn)}
.tag.bad{background:rgba(255,122,138,.10);color:var(--hot)}
.trend{display:block;font-size:12px;font-weight:700;margin-top:2px}
.trend.down{color:var(--aurora)}
.trend.up{color:var(--hot)}
.trend.same{color:var(--muted);font-weight:500}
.price .normal{display:block;font-size:12px;color:var(--muted);font-weight:500}
.rank{display:inline-block;min-width:22px;color:var(--muted);font-weight:500}
.go{margin-left:auto;color:var(--bg);background:var(--aurora);text-decoration:none;font-weight:700;font-size:13px;padding:7px 12px;border-radius:8px}
.go:hover{filter:brightness(1.1)}
.empty{text-align:center;color:var(--muted);padding:40px 10px;border:1px dashed var(--line);border-radius:14px}
footer{margin-top:30px;font-size:12px;color:var(--muted)}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>Nordlys <span>Fly</span></h1>
    <p>Feilpriser og smarte billetter fra Bodø, Evenes og Tromsø</p>
    <div class="meta" id="meta"></div>
  </header>

  <div class="controls">
    <div class="tabs" role="tablist">
      <button class="tab" role="tab" data-tab="feil" aria-selected="true">Feilpriser<b id="n-feil"></b></button>
      <button class="tab" role="tab" data-tab="skjult" aria-selected="false">Via Oslo<b id="n-skjult"></b></button>
      <button class="tab" role="tab" data-tab="sok" aria-selected="false">Søk</button>
    </div>
    <div class="chips" id="chips"></div>
    <div class="search" id="search" hidden>
      <label>Fra<select id="s-from"></select></label>
      <label>Til<select id="s-to"></select></label>
      <label>Dato<input type="date" id="s-date"></label>
      <label>Sortering<select id="s-sort"><option value="price">Billigst først</option><option value="date">Dato</option></select></label>
      <label class="flex"><input type="checkbox" id="s-flex"> Vis også ± 3 dager</label>
    </div>
  </div>

  <div class="info" id="info-skjult" hidden>
    <strong>Slik fungerer det:</strong> Billetten til en by lenger unna (f.eks. London) går via Oslo og er billigere enn billetten til Oslo. Du bestiller hele reisen og går av i Oslo.
    <br><strong>Husk:</strong> kun enveis, kun håndbagasje (innsjekket bagasje sendes til endestasjonen), og flyselskapene tillater det ikke i vilkårene sine – bruk det med omhu og ikke med bonuskontoen din.
  </div>
  <div class="info" id="info-feil">
    <strong>Mulige feilpriser</strong> er priser langt under normalprisen på ruten. De forsvinner ofte i løpet av timer. Ikke bestill hotell før billetten er utstedt – flyselskapet kan kansellere.
  </div>

  <div class="info" id="info-sok" hidden>
    <strong>Søk i lagrede priser</strong> for de neste månedene. Prisene er bufret og kan ha endret seg – trykk «Sjekk pris» for live pris på Aviasales. Velg «Alle» for å se alle reisemål samme dag.
  </div>

  <div class="list" id="list"></div>

  <footer id="footer"></footer>
</div>

<script>
const DATA = __DATA__;
const N = DATA.names;
const state = {tab: "feil", origin: "ALL"};
try { const s = JSON.parse(localStorage.getItem("nf-state")||"{}"); Object.assign(state, s); } catch(e) {}
if (!["feil","skjult","sok"].includes(state.tab)) state.tab = "feil";
if (state.origin !== "ALL" && !(state.origin in DATA.origins)) state.origin = "ALL";

const esc = s => String(s).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const kr = n => Math.round(n).toLocaleString("nb-NO") + " kr";
const dato = d => new Date(d + "T12:00:00").toLocaleDateString("nb-NO", {weekday:"short", day:"numeric", month:"short"});
const safeUrl = u => /^https?:\/\//.test(u) ? u : "#";
// Pris ned (grønn) eller opp (rød) siden forrige henting
function trend(price, prev){
  if (prev == null || price == null) return `<span class="trend same">ny</span>`;
  const diff = Math.round(price - prev);
  if (diff < 0) return `<span class="trend down" title="Var ${kr(prev)}">▼ ${kr(-diff)}</span>`;
  if (diff > 0) return `<span class="trend up" title="Var ${kr(prev)}">▲ ${kr(diff)}</span>`;
  return `<span class="trend same">uendret</span>`;
}

function chips(){
  const opts = [["ALL","Alle"], ...Object.entries(DATA.origins).map(([k,v]) => [k, v.split(" ")[0]])];
  document.getElementById("chips").innerHTML = opts.map(([k,v]) =>
    `<button class="chip" data-o="${k}" aria-pressed="${state.origin===k}">${esc(v)}</button>`).join("");
}

// Live-sjekk i Google Flights (SerpApi)
function liveTag(d){
  if (!DATA.live || !DATA.live.enabled) return "";
  const v = d.live;
  if (!v) return `<span class="tag">Ikke sjekket live ennå</span>`;
  const when = new Date(v.checked_at).toLocaleDateString("nb-NO", {day:"numeric", month:"short"});
  if (v.source === "utforsk")
    return `<span class="tag ok">✓ Fra Google Flights</span>`;
  if (v.status === "bekreftet")
    return `<span class="tag ok" title="Sjekket ${esc(when)}">✓ Bekreftet live ${kr(v.price)}</span>`;
  if (v.status === "endret")
    return `<span class="tag bad" title="Sjekket ${esc(when)}">✗ Live nå ${v.price != null ? kr(v.price) : "–"}</span>`;
  return `<span class="tag bad" title="Sjekket ${esc(when)}">✗ Ikke funnet live</span>`;
}

function cardFeil(d){
  return `<div class="card">
    <div><div class="route">${esc(d.origin)}<span class="arrow">→</span>${esc(d.destination)}</div>
      <div class="names">${esc(N[d.origin]||d.origin)} – ${esc(N[d.destination]||d.destination)} · ${dato(d.date)}</div></div>
    <div class="price">${kr(d.price)}<small>${kr(d.normal_price)}</small>${trend(d.price, d.prev_price)}</div>
    <div class="tags"><span class="tag hot">−${d.discount_pct} %</span>${liveTag(d)}
      <span class="tag">${d.transfers ? d.transfers + " bytte" : "direkte"}</span>
      <span class="tag">${esc(d.airline)}</span>${d.kr_per_km != null ? `<span class="tag">${d.kr_per_km} kr/km</span>` : ""}
      <a class="go" href="${esc(safeUrl(d.link))}" target="_blank" rel="noopener">Sjekk pris</a></div>
  </div>`;
}

function cardSkjult(d){
  const via = d.via_verified
    ? `<span class="tag ok">✓ går via ${esc(d.hub)}</span>`
    : `<span class="tag warn">Sjekk at den går via ${esc(d.hub)}</span>`;
  return `<div class="card">
    <div><div class="route">${esc(d.origin)}<span class="arrow">→</span>${esc(d.hub)}<span class="arrow">→</span><span class="skip">${esc(d.destination)}</span></div>
      <div class="names">Skal til ${esc(N[d.hub])}: bestill til ${esc(N[d.destination]||d.destination)} · ${dato(d.date)}</div></div>
    <div class="price">${kr(d.price)}<small>${kr(d.hub_price)}</small>${trend(d.price, d.prev_price)}</div>
    <div class="tags"><span class="tag hot">Spar ${kr(d.savings)}</span>${via}${liveTag(d)}
      <span class="tag">${esc(d.airline)}</span>
      <a class="go" href="${esc(safeUrl(d.link))}" target="_blank" rel="noopener">Sjekk pris</a></div>
  </div>`;
}

// ---------- Søk på dato ----------
const S = DATA.search || {};
const routesFrom = o => Object.keys(S).filter(k => k.startsWith(o + "-")).map(k => k.split("-")[1]);
const allDates = Object.values(S).flatMap(r => Object.keys(r.d)).sort();
function aviasalesLink(o, d, day){
  const [y, m, dd] = day.split("-");
  return `https://www.aviasales.com/search/${o}${dd}${m}${d}1` + (DATA.marker ? `?marker=${encodeURIComponent(DATA.marker)}` : "");
}
function setupSearch(){
  const from = document.getElementById("s-from"), dt = document.getElementById("s-date");
  from.innerHTML = Object.keys(DATA.origins).filter(o => routesFrom(o).length)
    .map(o => `<option value="${o}">${esc(DATA.origins[o])}</option>`).join("");
  if (state.sFrom && routesFrom(state.sFrom).length) from.value = state.sFrom;
  fillTo();
  if (allDates.length){ dt.min = allDates[0]; dt.max = allDates[allDates.length-1]; }
  dt.value = (state.sDate && state.sDate >= dt.min && state.sDate <= dt.max) ? state.sDate : (allDates[0] || "");
  document.getElementById("s-flex").checked = !!state.sFlex;
  document.getElementById("s-sort").value = state.sSort || "price";
}
function fillTo(){
  const o = document.getElementById("s-from").value, to = document.getElementById("s-to");
  const dests = routesFrom(o).sort((a, b) => (N[a]||a).localeCompare(N[b]||b, "nb"));
  to.innerHTML = `<option value="ALL">Alle reisemål</option>` +
    dests.map(d => `<option value="${d}">${esc(N[d]||d)}</option>`).join("");
  if (state.sTo && dests.includes(state.sTo)) to.value = state.sTo;
}
function addDays(day, n){ const t = new Date(day + "T12:00:00Z"); t.setUTCDate(t.getUTCDate() + n); return t.toISOString().slice(0, 10); }
function searchResults(){
  const o = state.sFrom = document.getElementById("s-from").value;
  const to = state.sTo = document.getElementById("s-to").value;
  const day = state.sDate = document.getElementById("s-date").value;
  state.sFlex = document.getElementById("s-flex").checked;
  state.sSort = document.getElementById("s-sort").value;
  if (!o || !day) return {items: [], live: ""};
  const days = state.sFlex ? [-3,-2,-1,0,1,2,3].map(n => addDays(day, n)) : [day];
  const dests = to === "ALL" ? routesFrom(o) : [to];
  const rows = [];
  for (const d of dests){
    const r = S[`${o}-${d}`]; if (!r) continue;
    for (const x of days){ const v = r.d[x]; if (v) rows.push({o, d, day: x, price: v[0], airline: v[1], transfers: v[2], prev: v[3], normal: r.n}); }
  }
  rows.sort(state.sSort === "date" ? (a, b) => a.day.localeCompare(b.day) || a.price - b.price : (a, b) => a.price - b.price);
  const live = to !== "ALL"
    ? `<a class="live" href="${esc(aviasalesLink(o, to, day))}" target="_blank" rel="noopener">Søk live på Aviasales: ${esc(N[o]||o)} → ${esc(N[to]||to)}, ${dato(day)} ↗</a>` : "";
  return {items: rows.slice(0, 60).map(cardSok), live};
}
function cardSok(r){
  return `<div class="card">
    <div><div class="route">${esc(r.o)}<span class="arrow">→</span>${esc(r.d)}</div>
      <div class="names">${esc(N[r.o]||r.o)} – ${esc(N[r.d]||r.d)} · ${dato(r.day)}</div></div>
    <div class="price">${kr(r.price)}${r.normal ? `<span class="normal">normalt ${kr(r.normal)}</span>` : ""}${trend(r.price, r.prev)}</div>
    <div class="tags"><span class="tag">${r.transfers ? r.transfers + " bytte" : "direkte"}</span>
      <span class="tag">${esc(r.airline)}</span>
      <a class="go" href="${esc(aviasalesLink(r.o, r.d, r.day))}" target="_blank" rel="noopener">Sjekk pris</a></div>
  </div>`;
}

function render(){
  const f = d => state.origin === "ALL" || d.origin === state.origin;
  const feil = DATA.error_fares.filter(f), skjult = DATA.hidden_city.filter(f);
  document.getElementById("n-feil").textContent = feil.length;
  document.getElementById("n-skjult").textContent = skjult.length;
  document.getElementById("chips").hidden = state.tab === "sok";
  document.getElementById("search").hidden = state.tab !== "sok";
  document.getElementById("info-sok").hidden = state.tab !== "sok";
  document.querySelectorAll(".tab").forEach(t => t.setAttribute("aria-selected", t.dataset.tab === state.tab));
  document.querySelectorAll(".chip").forEach(c => c.setAttribute("aria-pressed", c.dataset.o === state.origin));
  document.getElementById("info-feil").hidden = state.tab !== "feil";
  document.getElementById("info-skjult").hidden = state.tab !== "skjult";
  let items, live = "", empty = "Ingen treff akkurat nå. Prisene sjekkes jevnlig.";
  if (state.tab === "sok") {
    ({items, live} = searchResults());
    empty = "Ingen lagrede priser for denne datoen. Prøv «± 3 dager» eller søk live på Aviasales.";
  } else {
    items = state.tab === "feil" ? feil.map(cardFeil)
      : skjult.map(cardSkjult);
  }
  document.getElementById("list").innerHTML = live + (items.length ? items.join("")
    : `<div class="empty">${empty}</div>`);
  try { localStorage.setItem("nf-state", JSON.stringify(state)); } catch(e) {}
}

document.getElementById("search").addEventListener("change", e => {
  if (e.target.id === "s-from") { state.sTo = "ALL"; fillTo(); }
  render();
});
document.addEventListener("click", e => {
  const t = e.target.closest(".tab"), c = e.target.closest(".chip");
  if (t) { state.tab = t.dataset.tab; render(); }
  if (c) { state.origin = c.dataset.o; render(); }
});

const upd = new Date(DATA.updated).toLocaleString("nb-NO", {day:"numeric", month:"long", hour:"2-digit", minute:"2-digit"});
document.getElementById("meta").innerHTML = `Oppdatert ${esc(upd)}` + (DATA.provider === "mock" ? `<span class="demo">Testdata</span>` : "");
document.getElementById("footer").textContent = (DATA.provider === "mock"
  ? "Prisene på denne siden er testdata. Koble til en API-nøkkel for ekte priser."
  : "Prisene er bufret fra ekte søk og kan ha endret seg. Sjekk alltid prisen før du bestiller.")
  + (DATA.live && DATA.live.enabled
     ? ` Live-sjekk (Google Flights): ${DATA.live.used_month} av ${DATA.live.limit} søk brukt denne måneden.` : "");
chips(); setupSearch(); render();
</script>
</body>
</html>
"""


def build(result: dict, out: Path) -> None:
    data = json.dumps(result, ensure_ascii=False).replace("</", "<\\/")
    out.write_text(TEMPLATE.replace("__DATA__", data), encoding="utf-8")
