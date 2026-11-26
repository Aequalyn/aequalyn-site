// Shared by every page: the theme (any built-in theme, dark or day, kept across pages),
// the nav bar, the effects, and the counters API (views, hearts, copies).
(() => {
  "use strict";
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const store = {
    get(k, d) { try { const v = localStorage.getItem(k); return v === null ? d : JSON.parse(v); } catch { return d; } },
    set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* private mode */ } },
  };
  const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const num = n => n == null ? "–" : n >= 1e6 ? (n / 1e6).toFixed(1) + "M" : n >= 1e3 ? (n / 1e3).toFixed(1) + "k" : String(n);

  // ------------------------------------------------------------------ theme
  let themes = null;
  const loadThemes = () => themes ? Promise.resolve(themes)
    : fetch("/data/themes.json").then(r => r.json()).then(j => (themes = j)).catch(() => (themes = {}));

  function paint(t) {
    const root = document.documentElement;
    for (const [k, v] of Object.entries(t.palette)) root.style.setProperty("--ae-" + k, v);
    const edge = t.border && t.border.length ? t.border : [t.palette.accentPrimary, t.palette.accentCyan];
    root.style.setProperty("--ae-edgeA", edge[0]);
    root.style.setProperty("--ae-edgeB", edge[1] || edge[0]);
    root.dataset.variant = t.variant === "light" ? "light" : "dark";
    root.dataset.theme = t.id;
    const meta = $('meta[name="theme-color"]'); if (meta) meta.content = t.palette.bgBase;
  }
  function wear(id, from) {
    loadThemes().then(all => {
      const t = all[id]; if (!t) return;
      store.set("ae-theme", { id, variant: t.variant, palette: t.palette, border: t.border });
      const go = () => { paint({ id, ...t }); syncPicker(); document.dispatchEvent(new CustomEvent("ae:theme", { detail: id })); };
      if (document.startViewTransition && !reduced) {
        if (from) { const r = from.getBoundingClientRect(); const s = document.documentElement.style;
          s.setProperty("--vx", (r.left + r.width / 2) + "px"); s.setProperty("--vy", (r.top + r.height / 2) + "px"); }
        document.startViewTransition(go);
      } else go();
    });
  }
  // Day and night: the same family in its other variant.
  function flip(btn) {
    loadThemes().then(all => {
      const cur = document.documentElement.dataset.theme || "aequalyn";
      const t = all[cur]; if (!t) return wear("aequalyn", btn);
      const want = t.variant === "light" ? "dark" : "light";
      const pair = t.pair && all[t.pair] ? t.pair
        : Object.keys(all).find(k => all[k].family === t.family && all[k].variant === want);
      wear(pair || (want === "light" ? "aequalyn-day" : "aequalyn"), btn);
    });
  }

  let pickerFilter = "all";
  function buildPicker() {
    const box = $("#picker"); if (!box || box.dataset.built) return;
    box.dataset.built = "1";
    loadThemes().then(all => {
      const list = $(".list", box);
      list.innerHTML = Object.entries(all).map(([id, t]) => `
        <button class="swatch" type="button" data-id="${esc(id)}" data-variant="${t.variant}" aria-pressed="false" title="${esc(t.about || t.name)}">
          <span class="chips">${[t.palette.bgBase, t.palette.bgSurface, t.palette.accentPrimary, t.palette.accentCyan, t.palette.accentGreen]
            .map(c => `<i style="background:${esc(c)}"></i>`).join("")}</span>
          <span>${esc(t.name)}</span><small>${t.variant === "light" ? "Day" : "Night"}</small>
        </button>`).join("");
      syncPicker(); filterPicker();
    });
  }
  function filterPicker() {
    const box = $("#picker"); if (!box) return;
    const q = ($("input", box).value || "").toLowerCase();
    $$(".swatch", box).forEach(s => {
      const okV = pickerFilter === "all" || s.dataset.variant === pickerFilter;
      s.hidden = !(okV && s.textContent.toLowerCase().includes(q));
    });
  }
  function syncPicker() {
    const cur = document.documentElement.dataset.theme;
    $$("#picker .swatch").forEach(s => s.setAttribute("aria-pressed", String(s.dataset.id === cur)));
    const day = document.documentElement.dataset.variant === "light";
    $$("[data-flip]").forEach(b => { b.setAttribute("aria-pressed", String(day)); b.title = day ? "Switch to night" : "Switch to day"; });
  }

  // -------------------------------------------------------------- counters
  // /api/stats.php on the host keeps views, hearts and copies; without it (a local preview)
  // the counters stay empty and nothing breaks.
  const API = "/api/stats.php";
  let statsCache = null;
  const stats = {
    all() {
      if (!statsCache) statsCache = fetch(API, { credentials: "same-origin" })
        .then(r => r.ok ? r.json() : {}).then(j => j.items || {}).catch(() => ({}));
      return statsCache;
    },
    send(key, act, extra = {}) {
      return fetch(API, { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ key, act, ...extra }) }).then(r => r.ok ? r.json() : null).catch(() => null);
    },
  };
  const hearted = () => new Set(store.get("ae-hearts", []));
  function setHeart(key, on) { const h = hearted(); on ? h.add(key) : h.delete(key); store.set("ae-hearts", [...h]); }

  // ----------------------------------------------------------------- effects
  function toast(msg) {
    let t = $(".toast"); if (!t) { t = document.createElement("div"); t.className = "toast"; t.setAttribute("role", "status"); document.body.append(t); }
    t.textContent = msg; t.classList.add("show"); clearTimeout(t._h); t._h = setTimeout(() => t.classList.remove("show"), 1800);
  }
  function burst(el) {
    if (reduced) return;
    const r = el.getBoundingClientRect(), cs = getComputedStyle(document.documentElement);
    const colors = ["--ae-accentRed", "--ae-accentPrimary", "--ae-accentCyan", "--ae-accentOrange"].map(v => cs.getPropertyValue(v));
    for (let i = 0; i < 14; i++) {
      const p = document.createElement("i"), a = Math.PI * 2 * i / 14, d = 30 + Math.random() * 30;
      p.className = "burst"; p.style.left = r.left + r.width / 2 + "px"; p.style.top = r.top + r.height / 2 + "px";
      p.style.background = colors[i % colors.length];
      p.style.setProperty("--tx", Math.cos(a) * d + "px"); p.style.setProperty("--ty", Math.sin(a) * d + "px");
      document.body.append(p); setTimeout(() => p.remove(), 750);
    }
  }
  async function copy(text) {
    try { await navigator.clipboard.writeText(text); }
    catch { const ta = document.createElement("textarea"); ta.value = text; document.body.append(ta); ta.select(); document.execCommand("copy"); ta.remove(); }
    toast("Copied to the clipboard");
  }
  // A card leans toward the pointer and catches the light.
  function tilt(root = document) {
    if (reduced || matchMedia("(hover: none)").matches) return;
    $$(".item[data-tilt]", root).forEach(card => {
      card.addEventListener("pointermove", e => {
        const r = card.getBoundingClientRect(), x = (e.clientX - r.left) / r.width, y = (e.clientY - r.top) / r.height;
        card.style.setProperty("--ry", (x - .5) * 10 + "deg"); card.style.setProperty("--rx", (.5 - y) * 8 + "deg");
        card.style.setProperty("--gx", x * 100 + "%"); card.style.setProperty("--gy", y * 100 + "%");
      });
      card.addEventListener("pointerleave", () => { card.style.setProperty("--rx", "0deg"); card.style.setProperty("--ry", "0deg"); });
    });
  }
  function reveal(root = document) {
    const io = new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); } }), { threshold: .12 });
    $$(".reveal", root).forEach(el => io.observe(el));
  }

  // ----------------------------------------------------------------- wiring
  document.addEventListener("DOMContentLoaded", () => {
    const nav = $(".nav");
    $(".nav-burger")?.addEventListener("click", e => { const o = nav.classList.toggle("open"); e.currentTarget.setAttribute("aria-expanded", String(o)); });
    $$(".nav-drop > button").forEach(b => b.addEventListener("click", () => {
      const o = b.parentElement.classList.toggle("open"); b.setAttribute("aria-expanded", String(o)); }));
    const here = location.pathname.replace(/index\.html$/, "");
    $$(".nav-links a").forEach(a => {
      const p = new URL(a.href, location.href).pathname;
      if (p === here || (p !== "/" && here.startsWith(p) && !a.closest(".menu"))) a.setAttribute("aria-current", "page");
    });
    if (here.startsWith("/market/")) $(".nav-drop")?.classList.add("on");

    const picker = $("#picker"), pickBtn = $("[data-picker]");
    pickBtn?.addEventListener("click", e => {
      e.stopPropagation(); buildPicker(); const o = picker.classList.toggle("open"); pickBtn.setAttribute("aria-expanded", String(o));
      if (o) setTimeout(() => $("input", picker).focus(), 50);
    });
    picker?.addEventListener("click", e => { e.stopPropagation(); const s = e.target.closest(".swatch"); if (s) wear(s.dataset.id, s); });
    picker && $("input", picker).addEventListener("input", filterPicker);
    $$("[data-variant-filter]").forEach(b => b.addEventListener("click", () => {
      pickerFilter = b.dataset.variantFilter;
      $$("[data-variant-filter]").forEach(x => x.setAttribute("aria-pressed", String(x === b))); filterPicker();
    }));
    document.addEventListener("click", () => { picker?.classList.remove("open"); pickBtn?.setAttribute("aria-expanded", "false"); });
    document.addEventListener("keydown", e => { if (e.key === "Escape") { picker?.classList.remove("open"); nav?.classList.remove("open"); } });
    $$("[data-flip]").forEach(b => b.addEventListener("click", () => flip(b)));
    syncPicker();

    document.addEventListener("pointerdown", e => {
      const b = e.target.closest(".btn"); if (!b || reduced) return;
      const r = b.getBoundingClientRect(), s = Math.max(r.width, r.height), i = document.createElement("span");
      i.className = "ripple"; i.style.width = i.style.height = s + "px";
      i.style.left = e.clientX - r.left - s / 2 + "px"; i.style.top = e.clientY - r.top - s / 2 + "px";
      b.append(i); setTimeout(() => i.remove(), 650);
    });
    const glow = $(".backdrop .glow");
    if (glow && !reduced) addEventListener("pointermove", e => {
      glow.style.setProperty("--mx", e.clientX + "px"); glow.style.setProperty("--my", e.clientY + "px"); }, { passive: true });
    $$("[data-copy]").forEach(b => b.addEventListener("click", () => copy(b.dataset.copy)));
    $$("[data-year]").forEach(el => (el.textContent = new Date().getFullYear()));
    reveal(); tilt();
  });

  window.AE = { $, $$, esc, num, store, stats, hearted, setHeart, toast, burst, copy, tilt, reveal, wear, loadThemes, reduced };
})();
