const $ = (s) => document.querySelector(s);
const state = { tab: "file", mode: "auto", level: "normal", file: null, demo: "", result: null, charts: {} };
const eur = (v, d = 0) => (v ?? 0).toLocaleString("fr-FR", { minimumFractionDigits: d, maximumFractionDigits: d }) + " €";
const esc = (s) => (s || "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

const VERDICT = {
  arnaque: ["bg-red-100 text-red-700", "#dc2626", "🚨 Arnaque"],
  "risqué": ["bg-red-100 text-red-700", "#dc2626", "🚨 Contrat risqué"],
  suspect: ["bg-amber-100 text-amber-700", "#f59e0b", "⚠️ Suspect"],
  vigilance: ["bg-amber-100 text-amber-700", "#f59e0b", "⚠️ Vigilance"],
  "légitime": ["bg-emerald-100 text-emerald-700", "#10b981", "✅ Légitime"],
  transparent: ["bg-emerald-100 text-emerald-700", "#10b981", "✅ Transparent"],
};

// ---------- init
fetch("/api/health").then((r) => r.json()).then((h) => {
  $("#engine").textContent = h.ia ? "🤖 IA Mistral active" : "⚙️ Mode moteur de règles";
  $("#engine").className = "text-xs px-3 py-1 rounded-full " + (h.ia ? "bg-emerald-600 text-white" : "bg-slate-700 text-slate-200");
});
fetch("/api/demos").then((r) => r.json()).then((ds) => {
  $("#demos").innerHTML = ds.map((d) => `<button class="demo-btn" data-demo="${d.id}">${esc(d.label)}</button>`).join("");
  document.querySelectorAll("[data-demo]").forEach((b) => b.onclick = () => { state.demo = b.dataset.demo; state.file = null; run(); });
});

document.querySelectorAll("[data-tab]").forEach((b) => b.onclick = () => {
  state.tab = b.dataset.tab;
  document.querySelectorAll("[data-tab]").forEach((x) => x.classList.toggle("tab-active", x === b));
  $("#dropzone").classList.toggle("hidden", state.tab !== "file");
  $("#text").classList.toggle("hidden", state.tab !== "text");
});
function seg(id, key, onChange) {
  document.querySelectorAll(`#${id} button`).forEach((b) => b.onclick = () => {
    state[key] = b.dataset.v; syncSeg(); onChange && onChange();
  });
}
function syncSeg() {
  for (const [id, key] of [["modeSeg", "mode"], ["levelSeg", "level"], ["levelSeg2", "level"]])
    document.querySelectorAll(`#${id} button`).forEach((b) => b.classList.toggle("seg-on", b.dataset.v === state[key]));
}
seg("modeSeg", "mode"); seg("levelSeg", "level"); seg("levelSeg2", "level", () => state.result && run(true));

const fileInput = $("#file"), dz = $("#dropzone");
fileInput.onchange = () => setFile(fileInput.files[0]);
dz.ondragover = (e) => { e.preventDefault(); dz.classList.add("border-emerald-400"); };
dz.ondragleave = () => dz.classList.remove("border-emerald-400");
dz.ondrop = (e) => { e.preventDefault(); setFile(e.dataTransfer.files[0]); };
function setFile(f) { if (!f) return; state.file = f; state.demo = ""; $("#fileLabel").textContent = "📎 " + f.name; }
$("#analyze").onclick = () => { state.demo = ""; run(); };

// ---------- analyse
async function run(relevel = false) {
  const fd = new FormData();
  fd.append("level", state.level);
  if (relevel) {
    fd.append("text", state.result.texte); fd.append("mode", state.result.mode);
    fd.append("qr", (state.result.qr || []).join("\n"));
  } else {
    fd.append("mode", state.mode);
    if (state.demo) fd.append("demo", state.demo);
    else if (state.tab === "file" && state.file) fd.append("file", state.file);
    else if ($("#text").value.trim()) fd.append("text", $("#text").value);
    else return showError("Déposez un fichier, collez un texte ou choisissez un exemple.");
  }
  $("#error").classList.add("hidden");
  if (!relevel) $("#results").classList.add("hidden");
  $("#loading").classList.remove("hidden");
  const steps = ["Lecture du document…", "Détection des clauses et signaux…", "Analyse des liens…", "Calcul du coût réel…", "Rédaction de l'explication…"];
  let i = 0; $("#loadingText").textContent = relevel ? "Réécriture de l'explication…" : steps[0];
  const t = setInterval(() => { if (!relevel) $("#loadingText").textContent = steps[++i % steps.length]; }, 700);
  try {
    const r = await fetch("/api/analyze", { method: "POST", body: fd });
    const data = await r.json();
    if (!r.ok) throw new Error(data.erreur || "Erreur d'analyse");
    state.result = data; render(data, relevel);
  } catch (e) { showError(e.message); }
  finally { clearInterval(t); $("#loading").classList.add("hidden"); }
}
function showError(m) { $("#error").textContent = m; $("#error").classList.remove("hidden"); }

// ---------- rendu
function render(a, relevel) {
  $("#results").classList.remove("hidden");
  syncSeg();
  const [cls, color, label] = VERDICT[a.verdict] || VERDICT.suspect;
  $("#verdictBadge").className = "px-3 py-1 rounded-full text-sm font-bold uppercase " + cls;
  $("#verdictBadge").textContent = label;
  $("#modeBadge").textContent = a.mode === "contrat" ? "📄 Contrat" : "✉️ Message";
  $("#engineBadge").textContent = a.moteur;
  $("#summary").textContent = a.resume;
  $("#scoreLabel").textContent = a.mode === "contrat" ? "transparence /100" : "risque /100";
  const g = $("#gauge"); g.style.stroke = color;
  requestAnimationFrame(() => g.style.strokeDashoffset = 326.7 * (1 - a.score / 100));
  animateNumber($("#scoreVal"), a.score);

  // alerts
  $("#alertsTitle").textContent = `${a.mode === "contrat" ? "⚠️ Points de vigilance" : "🚩 Signaux d'arnaque"} (${a.alertes.length})`;
  $("#alerts").innerHTML = a.alertes.length ? a.alertes.map((al, i) => `
    <div class="alert sev-${al.gravite}" data-i="${i}">
      <div class="flex items-center gap-2 flex-wrap">
        <span class="text-[11px] font-bold uppercase px-2 py-0.5 rounded badge-${al.gravite}">${al.gravite}</span>
        <span class="font-bold">${esc(al.titre)}</span>
        <span class="text-xs text-slate-400 ml-auto">${esc(al.categorie || "")} · ${esc(al.source || "")}</span>
      </div>
      <div class="mt-1 text-slate-700">${esc(al.explication)}</div>
      ${al.citation ? `<div class="mt-2 text-xs italic text-slate-500 border-l-2 border-slate-300 pl-2">« ${esc(al.citation)} »</div>` : ""}
    </div>`).join("") : `<div class="text-slate-500">Aucun signal détecté.</div>`;
  $("#positives").innerHTML = (a.points_positifs || []).length
    ? `<div class="text-sm font-semibold text-emerald-700 mb-2">Points positifs</div>` + a.points_positifs.map((p) => `<span class="inline-block mr-2 mb-2 text-sm px-3 py-1 rounded-full bg-emerald-50 text-emerald-700">✓ ${esc(p)}</span>`).join("") : "";

  // doc with highlights
  renderDoc(a);
  document.querySelectorAll(".alert").forEach((el) => el.onclick = () => {
    const m = document.querySelector(`mark[data-i="${el.dataset.i}"]`);
    if (m) { m.scrollIntoView({ behavior: "smooth", block: "center" }); m.classList.add("flash"); setTimeout(() => m.classList.remove("flash"), 1500); }
  });
  $("#docSource").textContent = [a.fichier, { "pdf-texte": "PDF texte", "pdf-ocr-local": "OCR local", "pdf-ocr-mistral": "OCR Mistral", "image-ocr-local": "OCR local", "image-ocr-mistral": "OCR Mistral", texte: "texte" }[a.source]].filter(Boolean).join(" · ");

  // links
  $("#linksCard").classList.toggle("hidden", !(a.liens || []).length);
  $("#links").innerHTML = (a.liens || []).map((u) => {
    const c = { dangereux: "badge-haute", suspect: "badge-moyenne", fiable: "bg-emerald-100 text-emerald-700", inconnu: "bg-slate-100 text-slate-600" }[u.risque];
    return `<div class="p-3 rounded-xl bg-slate-50 border border-slate-200">
      <div class="flex items-center gap-2 flex-wrap"><span class="text-[11px] font-bold uppercase px-2 py-0.5 rounded ${c}">${u.risque}</span>
      ${u.via_qr ? `<span class="text-[11px] px-2 py-0.5 rounded bg-violet-100 text-violet-700 font-semibold">QR code</span>` : ""}
      <code class="text-sm break-all">${esc(u.url)}</code><span class="ml-auto text-xs text-slate-400">${u.score}/100</span></div>
      <ul class="mt-2 text-sm text-slate-600 list-disc pl-5">${u.raisons.map((r) => `<li>${esc(r)}</li>`).join("")}</ul></div>`;
  }).join("");

  // todo
  const todo = a.mode === "contrat" ? a.questions : a.actions;
  $("#todoTitle").textContent = a.mode === "contrat" ? "❓ Questions à poser à votre banquier" : "🛡️ Que faire maintenant ?";
  $("#todo").innerHTML = (todo || []).map((t, i) => `<li class="flex gap-2"><span class="shrink-0 w-6 h-6 rounded-full bg-slate-900 text-white text-xs grid place-items-center">${i + 1}</span><span>${esc(t)}</span></li>`).join("");

  // cost
  $("#costCard").classList.toggle("hidden", !(a.mode === "contrat" && a.cout));
  if (a.mode === "contrat" && a.cout && !relevel) initCost(a);

  // chat
  if (!relevel) {
    $("#chat").innerHTML = "";
    const chips = a.mode === "contrat"
      ? ["Combien ce crédit me coûte au total ?", "Que se passe-t-il si je rembourse en avance ?", "L'assurance est-elle obligatoire ?", "Que se passe-t-il si je ne paie pas ?"]
      : ["J'ai cliqué sur le lien, que faire ?", "Pourquoi ce lien est dangereux ?", "Comment vérifier si c'est vraiment ma banque ?"];
    $("#chips").innerHTML = chips.map((c) => `<button class="chip">${esc(c)}</button>`).join("");
    document.querySelectorAll(".chip").forEach((c) => c.onclick = () => ask(c.textContent));
    $("#results").scrollIntoView({ behavior: "smooth" });
  }
}

function animateNumber(el, target) {
  const start = performance.now();
  const step = (t) => { const p = Math.min(1, (t - start) / 900); el.textContent = Math.round(target * p); if (p < 1) requestAnimationFrame(step); };
  requestAnimationFrame(step);
}

function renderDoc(a) {
  const text = a.texte || "";
  const ranges = [];
  a.alertes.forEach((al, i) => {
    if (!al.citation) return;
    const words = al.citation.split(/\s+/).filter(Boolean).slice(0, 40).map((w) => w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
    if (!words.length) return;
    const m = new RegExp(words.join("\\s+"), "i").exec(text);
    if (m && !ranges.some((r) => m.index < r.e && m.index + m[0].length > r.s)) ranges.push({ s: m.index, e: m.index + m[0].length, i, sev: al.gravite });
  });
  ranges.sort((x, y) => x.s - y.s);
  let html = "", pos = 0;
  for (const r of ranges) {
    html += esc(text.slice(pos, r.s)) + `<mark class="m-${r.sev}" data-i="${r.i}" title="${esc(a.alertes[r.i].titre)}">${esc(text.slice(r.s, r.e))}</mark>`;
    pos = r.e;
  }
  $("#doc").innerHTML = html + esc(text.slice(pos)) + ((a.qr || []).length ? `\n\n<span class="text-violet-700 font-semibold">[QR code décodé] ${esc(a.qr.join(" | "))}</span>` : "");
}

// ---------- calculateur
function mensualite(c, t, n) { const r = t / 1200; return r === 0 ? c / n : c * r / (1 - Math.pow(1 + r, -n)); }
function compute(p) {
  const m = mensualite(p.capital, p.taux, p.duree);
  const interets = m * p.duree - p.capital, assurance = p.assurance * p.duree;
  return { m, interets, assurance, frais: p.frais, total: interets + assurance + p.frais };
}
function initCost(a) {
  const c = a.cout;
  state.cost = { capital: c.capital, taux: c.taux_utilise, duree: c.duree_mois, assurance: c.total_assurance / c.duree_mois, frais: c.frais_dossier };
  const defs = [
    ["capital", "Montant emprunté", 1000, Math.max(50000, c.capital * 2), 500, (v) => eur(v)],
    ["duree", "Durée", 6, 120, 6, (v) => v + " mois"],
    ["taux", "Taux débiteur", 0, 20, 0.1, (v) => v.toFixed(1).replace(".", ",") + " %"],
    ["assurance", "Assurance / mois", 0, 100, 0.5, (v) => eur(v, 2)],
  ];
  $("#sliders").innerHTML = defs.map(([k, l, mn, mx, st]) => `
    <div><div class="flex justify-between text-sm"><span class="font-medium">${l}</span><span id="v-${k}" class="font-bold"></span></div>
    <input type="range" id="s-${k}" min="${mn}" max="${mx}" step="${st}" value="${state.cost[k]}"></div>`).join("");
  defs.forEach(([k, , , , , f]) => {
    const s = $("#s-" + k);
    const upd = () => { state.cost[k] = parseFloat(s.value); $("#v-" + k).textContent = f(state.cost[k]); updateCost(); };
    s.oninput = upd; $("#v-" + k).textContent = f(state.cost[k]);
  });
  Object.values(state.charts).forEach((ch) => ch.destroy());
  state.charts.cost = new Chart($("#costChart"), {
    type: "doughnut",
    data: { labels: ["Capital", "Intérêts", "Assurance", "Frais de dossier"], datasets: [{ data: [], backgroundColor: ["#10b981", "#ef4444", "#f59e0b", "#6366f1"], borderWidth: 0 }] },
    options: { cutout: "62%", plugins: { legend: { position: "bottom" }, tooltip: { callbacks: { label: (x) => `${x.label} : ${eur(x.raw)}` } } } },
  });
  state.charts.dur = new Chart($("#durChart"), {
    type: "bar",
    data: { labels: [], datasets: [{ label: "Coût total du crédit", data: [], backgroundColor: [] , borderRadius: 6 }] },
    options: { plugins: { legend: { display: false }, tooltip: { callbacks: { label: (x) => eur(x.raw) } } }, scales: { y: { ticks: { callback: (v) => eur(v) } } } },
  });
  updateCost();
}
function updateCost() {
  const p = state.cost, r = compute(p);
  $("#costKpis").innerHTML = `
    <div class="kpi"><div class="l">Mensualité (avec assurance)</div><div class="v">${eur(r.m + p.assurance, 2)}</div></div>
    <div class="kpi"><div class="l">Intérêts</div><div class="v">${eur(r.interets)}</div></div>
    <div class="kpi"><div class="l">Assurance + frais</div><div class="v">${eur(r.assurance + r.frais)}</div></div>
    <div class="kpi big"><div class="l">Coût total du crédit</div><div class="v">${eur(r.total)}</div><div class="l">${(r.total / p.capital * 100).toFixed(1)} % du montant emprunté</div></div>`;
  const ch = state.charts.cost; ch.data.datasets[0].data = [p.capital, r.interets, r.assurance, r.frais].map((v) => Math.round(v)); ch.update();
  const durs = [12, 24, 36, 48, 60, 72, 84, 96, 108, 120];
  if (!durs.includes(p.duree)) { durs.push(p.duree); durs.sort((a, b) => a - b); }
  const d = state.charts.dur;
  d.data.labels = durs.map((x) => x + " m");
  d.data.datasets[0].data = durs.map((n) => Math.round(compute({ ...p, duree: n }).total));
  d.data.datasets[0].backgroundColor = durs.map((n) => n === p.duree ? "#ef4444" : "#cbd5e1");
  d.update();
}

// ---------- chat
$("#chatForm").onsubmit = (e) => { e.preventDefault(); const q = $("#chatInput").value.trim(); if (q) ask(q); $("#chatInput").value = ""; };
async function ask(q) {
  const chat = $("#chat");
  chat.insertAdjacentHTML("beforeend", `<div class="msg-user">${esc(q)}</div>`);
  const id = "b" + Date.now();
  chat.insertAdjacentHTML("beforeend", `<div class="msg-bot" id="${id}"><span class="animate-pulse">Lucide réfléchit…</span></div>`);
  chat.scrollTop = chat.scrollHeight;
  const { texte, ...analyse } = state.result;
  const r = await fetch("/api/ask", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question: q, texte, analyse, niveau: state.level }) });
  const a = await r.json();
  $("#" + id).innerHTML = esc(a.reponse) + (a.citation ? `<div class="mt-2 text-xs italic text-slate-500 border-l-2 border-emerald-400 pl-2">« ${esc(a.citation)} »</div>` : "") + `<div class="mt-1 text-[10px] text-slate-400">${esc(a.moteur)}</div>`;
  chat.scrollTop = chat.scrollHeight;
}

// ---------- export
$("#export").onclick = async () => {
  const { texte, ...a } = state.result;
  const r = await fetch("/api/report", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(a) });
  const blob = await r.blob();
  const url = URL.createObjectURL(blob);
  const link = Object.assign(document.createElement("a"), { href: url, download: "rapport-lucide.pdf" });
  document.body.appendChild(link); link.click(); link.remove();
};
