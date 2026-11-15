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
    <p>Feilpriser og smarte billetter fra Bodø, Evenes, Tromsø og Oslo</p>
    <div class="meta" id="meta"></div>
  </header>

  <div class="controls">
    <div class="tabs" role="tablist">
      <button class="tab" role="tab" data-tab="feil" aria-selected="true">Feilpriser<b id="n-feil"></b></button>
      <button class="tab" role="tab" data-tab="skjult" aria-selected="false">Billigere via Oslo<b id="n-skjult"></b></button>
      <button class="tab" role="tab" data-tab="oslo" aria-selected="false">Fra Oslo<b id="n-oslo"></b></button>
    </div>
    <div class="chips" id="chips"></div>
  </div>

  <div class="info" id="info-skjult" hidden>
    <strong>Slik fungerer det:</strong> Billetten til en by lenger unna (f.eks. London) går via Oslo og er billigere enn billetten til Oslo. Du bestiller hele reisen og går av i Oslo.
    <br><strong>Husk:</strong> kun enveis, kun håndbagasje (innsjekket bagasje sendes til endestasjonen), og flyselskapene tillater det ikke i vilkårene sine – bruk det med omhu og ikke med bonuskontoen din.
  </div>
  <div class="info" id="info-feil">
    <strong>Mulige feilpriser</strong> er priser langt under normalprisen på ruten. De forsvinner ofte i løpet av timer. Ikke bestill hotell før billetten er utstedt – flyselskapet kan kansellere.
  </div>

  <div class="info" id="info-oslo" hidden>
    <strong>De 20 mest populære reisene fra Oslo</strong> med billigste enveispris de neste månedene. Pilen viser om billigste pris har gått <span style="color:var(--aurora)">ned ▼</span> eller <span style="color:var(--hot)">opp ▲</span> siden forrige prissjekk.
  </div>

  <div class="list" id="list"></div>

  <footer id="footer"></footer>
</div>

<script>
const DATA = __DATA__;
const N = DATA.names;
const state = {tab: "feil", origin: "ALL"};
try { const s = JSON.parse(localStorage.getItem("nf-state")||"{}"); Object.assign(state, s); } catch(e) {}
if (!["feil","skjult","oslo"].includes(state.tab)) state.tab = "feil";
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

function cardFeil(d){
  return `<div class="card">
    <div><div class="route">${esc(d.origin)}<span class="arrow">→</span>${esc(d.destination)}</div>
      <div class="names">${esc(N[d.origin]||d.origin)} – ${esc(N[d.destination]||d.destination)} · ${dato(d.date)}</div></div>
    <div class="price">${kr(d.price)}<small>${kr(d.normal_price)}</small>${trend(d.price, d.prev_price)}</div>
    <div class="tags"><span class="tag hot">−${d.discount_pct} %</span>
      <span class="tag">${d.transfers ? d.transfers + " bytte" : "direkte"}</span>
      <span class="tag">${esc(d.airline)}</span><span class="tag">${d.kr_per_km} kr/km</span>
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
    <div class="tags"><span class="tag hot">Spar ${kr(d.savings)}</span>${via}
      <span class="tag">${esc(d.airline)}</span>
      <a class="go" href="${esc(safeUrl(d.link))}" target="_blank" rel="noopener">Sjekk pris</a></div>
  </div>`;
}

function cardOslo(d){
  const head = `<div><div class="route"><span class="rank">${d.rank}.</span>${esc(d.origin)}<span class="arrow">→</span>${esc(d.destination)}</div>`;
  if (d.price == null) return `<div class="card">${head}
      <div class="names">${esc(N[d.destination]||d.destination)} · ingen priser hentet</div></div></div>`;
  return `<div class="card">${head}
      <div class="names">${esc(N[d.destination]||d.destination)} · billigst ${dato(d.date)}</div></div>
    <div class="price">${kr(d.price)}${d.normal_price ? `<span class="normal">normalt ${kr(d.normal_price)}</span>` : ""}${trend(d.price, d.prev_price)}</div>
    <div class="tags"><span class="tag">${d.transfers ? d.transfers + " bytte" : "direkte"}</span>
      <span class="tag">${esc(d.airline)}</span>
      <a class="go" href="${esc(safeUrl(d.link))}" target="_blank" rel="noopener">Sjekk pris</a></div>
  </div>`;
}

function render(){
  const f = d => state.origin === "ALL" || d.origin === state.origin;
  const feil = DATA.error_fares.filter(f), skjult = DATA.hidden_city.filter(f);
  document.getElementById("n-feil").textContent = feil.length;
  document.getElementById("n-skjult").textContent = skjult.length;
  document.getElementById("n-oslo").textContent = (DATA.oslo||[]).length;
  document.getElementById("chips").hidden = state.tab === "oslo";
  document.getElementById("info-oslo").hidden = state.tab !== "oslo";
  document.querySelectorAll(".tab").forEach(t => t.setAttribute("aria-selected", t.dataset.tab === state.tab));
  document.querySelectorAll(".chip").forEach(c => c.setAttribute("aria-pressed", c.dataset.o === state.origin));
  document.getElementById("info-feil").hidden = state.tab !== "feil";
  document.getElementById("info-skjult").hidden = state.tab !== "skjult";
  const items = state.tab === "feil" ? feil.map(cardFeil)
    : state.tab === "skjult" ? skjult.map(cardSkjult) : (DATA.oslo||[]).map(cardOslo);
  document.getElementById("list").innerHTML = items.length ? items.join("")
    : `<div class="empty">Ingen treff akkurat nå. Prisene sjekkes jevnlig.</div>`;
  try { localStorage.setItem("nf-state", JSON.stringify(state)); } catch(e) {}
}

document.addEventListener("click", e => {
  const t = e.target.closest(".tab"), c = e.target.closest(".chip");
  if (t) { state.tab = t.dataset.tab; render(); }
  if (c) { state.origin = c.dataset.o; render(); }
});

const upd = new Date(DATA.updated).toLocaleString("nb-NO", {day:"numeric", month:"long", hour:"2-digit", minute:"2-digit"});
document.getElementById("meta").innerHTML = `Oppdatert ${esc(upd)}` + (DATA.provider === "mock" ? `<span class="demo">Testdata</span>` : "");
document.getElementById("footer").textContent = DATA.provider === "mock"
  ? "Prisene på denne siden er testdata. Koble til en API-nøkkel for ekte priser."
  : "Prisene er bufret fra ekte søk og kan ha endret seg. Sjekk alltid prisen før du bestiller.";
chips(); render();
</script>
</body>
</html>
"""


def build(result: dict, out: Path) -> None:
    data = json.dumps(result, ensure_ascii=False).replace("</", "<\\/")
    out.write_text(TEMPLATE.replace("__DATA__", data), encoding="utf-8")
