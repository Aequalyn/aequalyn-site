// The market: every built-in and approved item, filtered, sorted and shown nine to a page,
// in one of five views: grid and list (as on the Omarchy site), and three after Aequalyn's
// own pickers: carousel (the theme picker), filmstrip (the wallpaper picker), spotlight
// (the layout picker's large preview beside its list).
(() => {
  "use strict";
  const { $, $$, esc, num, store, stats } = window.AE;
  const PER_PAGE = 9;
  const KINDS = { plugin: "Plugin", theme: "Theme", wallpaper: "Wallpaper", app: "App", cursor: "Cursor", look: "Look" };
  const SORTS = {
    featured: (a, b) => score(b) - score(a),
    newest: (a, b) => (b.approved || "").localeCompare(a.approved || "") || a.name.localeCompare(b.name),
    rating: (a, b) => rated(b) - rated(a) || (b.n || 0) - (a.n || 0),
    stars: (a, b) => (b.stars || 0) - (a.stars || 0),
    hearts: (a, b) => (b.h || 0) - (a.h || 0),
    copies: (a, b) => (b.c || 0) - (a.c || 0),
    views: (a, b) => (b.v || 0) - (a.v || 0),
    name: (a, b) => a.name.localeCompare(b.name),
  };
  // Best rated: the average pulled toward the Market's mean by three imagined votes, so one
  // five-star rating does not outrank twenty fours (a Bayesian average).
  let meanRating = 3.5;
  const rated = i => ((i.r || 0) * (i.n || 0) + meanRating * 3) / ((i.n || 0) + 3);
  // Featured: what people keep, then what they look at; community work first among equals.
  const score = i => (i.n ? (rated(i) - 3) * 8 : 0) + (i.h || 0) * 5 + (i.c || 0) * 3 + (i.stars || 0) * 2 + (i.v || 0) * .2 + (i.source === "community" ? 1 : 0);
  const icon = n => (document.getElementById("i-" + n)?.innerHTML || "");

  let catalog = [], st = {};
  const state = {
    kind: "", q: "", source: "all", variant: "all", sort: "featured", page: 1,
    view: store.get("ae-view", "grid"),
  };

  function media(it, big) {
    if (it.media === "video") return `<div class="media"><video src="${esc(it.preview)}" muted loop playsinline preload="metadata" ${big ? "autoplay" : ""}></video>${chips(it)}</div>`;
    if (it.media === "icon") return `<div class="media icon"><img src="${esc(it.preview)}" alt="" loading="lazy" decoding="async"></div>`;
    return `<div class="media"><img src="${esc(it.preview)}" alt="" loading="lazy" decoding="async">${chips(it)}</div>`;
  }
  const chips = it => it.colors?.length ? `<span class="palette">${it.colors.map(c => `<i style="background:${esc(c)}"></i>`).join("")}</span>` : "";
  const metaLine = it => `<div class="meta">
      <span class="rated" title="${it.n ? `Rated ${(+it.r).toFixed(1)} of 5 by ${it.n}` : "Not rated yet"}">${icon("star")}${it.n ? `${(+it.r).toFixed(1)} <small>(${it.n})</small>` : "–"}</span>
      <span title="GitHub stars">${icon("github")}${num(it.stars)}</span>
      <span title="Hearts">${icon("heart")}${num(it.h)}</span>
      <span title="Copies of the install command">${icon("copy")}${num(it.c)}</span>
      <span title="Views">${icon("eye")}${num(it.v)}</span></div>`;

  function card(it, i = 0) {
    return `<a class="item" href="${esc(it.url)}" data-tilt style="--i:${i}">
      <span class="glare"></span>${media(it)}
      <div class="body"><div class="text">
        <h3>${esc(it.name)}</h3><p>${esc(it.about)}</p>
        <span class="by">${esc(KINDS[it.kind] || it.kind)} · ${it.source === "built-in" ? "Built in" : "by " + esc(it.by)}${it.variant === "light" ? " · Day" : ""}</span>
      </div>${metaLine(it)}</div></a>`;
  }

  // ----------------------------------------------------------------- views
  const VIEWS = {
    grid: items => `<div class="view grid">${items.map(card).join("")}</div>`,
    list: items => `<div class="view list">${items.map(card).join("")}</div>`,
    filmstrip: items => `<div class="view filmstrip" tabindex="0" aria-label="Filmstrip, scroll sideways">${items.map(card).join("")}</div>`,
    carousel: items => `<div class="view carousel" tabindex="0" aria-roledescription="carousel">
        <button class="icon-btn nav-arrow prev" type="button" aria-label="Previous">${icon("left")}</button>
        ${items.map(card).join("")}
        <button class="icon-btn nav-arrow next" type="button" aria-label="Next">${icon("right")}</button></div>`,
    spotlight: items => `<div class="view spotlight">
        <div class="stage"></div>
        <div class="rail">${items.map((it, i) => `<button type="button" data-i="${i}" aria-pressed="${i === 0}">
          <img src="${esc(it.preview)}" alt="" loading="lazy"><span>${esc(it.name)}<small>${esc(KINDS[it.kind])} · ${it.source === "built-in" ? "Built in" : esc(it.by)}</small></span></button>`).join("")}</div></div>`,
  };
  const AFTER = {
    carousel(el) {
      const cards = $$(".item", el); let at = 0;
      const place = () => cards.forEach((c, i) => {
        let d = i - at; const n = cards.length; if (d > n / 2) d -= n; if (d < -n / 2) d += n;
        const a = Math.abs(d);
        c.style.transform = `translateX(${d * 62}%) translateZ(${-a * 160}px) rotateY(${d * -28}deg)`;
        c.style.zIndex = 10 - a; c.style.opacity = a > 2 ? 0 : 1; c.classList.toggle("center", d === 0);
        c.tabIndex = d === 0 ? 0 : -1; c.style.pointerEvents = a > 2 ? "none" : "";
      });
      const go = s => { at = (at + s + cards.length) % cards.length; place(); };
      $(".prev", el).onclick = () => go(-1); $(".next", el).onclick = () => go(1);
      el.addEventListener("keydown", e => { if (e.key === "ArrowLeft") go(-1); if (e.key === "ArrowRight") go(1); });
      cards.forEach((c, i) => c.addEventListener("click", e => { if (i !== at) { e.preventDefault(); at = i; place(); } }));
      let x0 = null; el.addEventListener("pointerdown", e => (x0 = e.clientX));
      el.addEventListener("pointerup", e => { if (x0 !== null && Math.abs(e.clientX - x0) > 40) go(e.clientX < x0 ? 1 : -1); x0 = null; });
      place();
    },
    spotlight(el, items) {
      const stage = $(".stage", el);
      const show = i => {
        const it = items[i];
        stage.innerHTML = `${media(it, true)}<div class="info"><span class="chip accent">${esc(KINDS[it.kind])}</span>
          <h2 style="margin:12px 0 6px">${esc(it.name)}</h2><p>${esc(it.about)}</p>${metaLine(it)}
          <p style="margin-top:16px"><a class="btn primary" href="${esc(it.url)}">Open its page ${icon("right")}</a></p></div>`;
        $$(".rail button", el).forEach(b => b.setAttribute("aria-pressed", String(+b.dataset.i === i)));
      };
      $$(".rail button", el).forEach(b => { b.addEventListener("click", () => show(+b.dataset.i)); b.addEventListener("mouseenter", () => show(+b.dataset.i)); });
      show(0);
    },
    filmstrip(el) { el.addEventListener("wheel", e => { if (Math.abs(e.deltaY) > Math.abs(e.deltaX)) { el.scrollLeft += e.deltaY; e.preventDefault(); } }, { passive: false }); },
  };

  // --------------------------------------------------------------- filters
  function filtered() {
    const q = state.q.trim().toLowerCase();
    return catalog.filter(it =>
      (!state.kind || it.kind === state.kind) &&
      (state.source === "all" || it.source === state.source) &&
      (state.variant === "all" || (it.variant || "dark") === state.variant) &&
      (!q || (it.name + " " + it.about + " " + it.by + " " + it.id + " " + (it.tags || []).join(" ")).toLowerCase().includes(q))
    ).sort(SORTS[state.sort] || SORTS.featured);
  }

  function render() {
    const all = filtered(), pages = Math.max(1, Math.ceil(all.length / PER_PAGE));
    state.page = Math.min(Math.max(1, state.page), pages);
    const items = all.slice((state.page - 1) * PER_PAGE, state.page * PER_PAGE);
    const out = $("#results");
    $("#count").textContent = `${all.length} ${all.length === 1 ? "item" : "items"}`;
    $("#pageinfo").textContent = all.length ? `page ${state.page} of ${pages}` : "";
    out.innerHTML = items.length ? VIEWS[state.view](items)
      : `<div class="empty"><p>Nothing matches yet.</p><p><a href="https://github.com/Aequalyn/aequalyn-market#publish">Publish the first one</a></p></div>`;
    if (items.length) { AFTER[state.view]?.($(".view", out), items); window.AE.tilt(out); }
    pager(pages);
    $$("[data-view]").forEach(b => b.setAttribute("aria-pressed", String(b.dataset.view === state.view)));
    $$(".kinds a").forEach(a => a.setAttribute("aria-current", String((a.dataset.kind || "") === state.kind)));
    $("#variant-wrap").hidden = !(state.kind === "theme" || state.kind === "");
    document.title = (state.kind ? (KINDS[state.kind] + "s") : "Market") + " · Aequalyn";
    sync();
  }
  function pager(pages) {
    const p = $("#pager"); if (pages < 2) { p.innerHTML = ""; return; }
    const btn = (n, label = n, dis = false, cur = false) =>
      `<button type="button" data-page="${n}" ${dis ? "disabled" : ""} ${cur ? 'aria-current="page"' : ""} aria-label="${typeof label === "number" ? "Page " + n : label}">${typeof label === "number" ? n : icon(label === "Previous" ? "left" : "right")}</button>`;
    let h = btn(state.page - 1, "Previous", state.page === 1);
    for (let n = 1; n <= pages; n++) {
      if (n === 1 || n === pages || Math.abs(n - state.page) <= 1) h += btn(n, n, false, n === state.page);
      else if (Math.abs(n - state.page) === 2) h += `<span class="muted">…</span>`;
    }
    p.innerHTML = h + btn(state.page + 1, "Next", state.page === pages);
  }
  // The address keeps the filters, so a filtered page can be shared.
  function sync() {
    const u = new URLSearchParams();
    if (state.kind) u.set("kind", state.kind); if (state.q) u.set("q", state.q);
    if (state.source !== "all") u.set("source", state.source); if (state.variant !== "all") u.set("variant", state.variant);
    if (state.sort !== "featured") u.set("sort", state.sort); if (state.page > 1) u.set("page", state.page);
    const s = u.toString(); history.replaceState(null, "", location.pathname + (s ? "?" + s : ""));
  }
  function readUrl() {
    const u = new URLSearchParams(location.search);
    state.kind = KINDS[u.get("kind")] ? u.get("kind") : "";
    state.q = u.get("q") || ""; state.source = u.get("source") || "all"; state.variant = u.get("variant") || "all";
    state.sort = SORTS[u.get("sort")] ? u.get("sort") : "featured"; state.page = +u.get("page") || 1;
    if (VIEWS[u.get("view")]) state.view = u.get("view");
  }

  async function load() {
    const [cat, s] = await Promise.all([fetch("/data/catalog.json").then(r => r.json()), stats.all()]);
    st = s;
    catalog = cat.items.map(it => ({ ...it, ...(st[it.key] || {}) }));
    const r = catalog.filter(i => i.n), votes = r.reduce((a, i) => a + i.n, 0);
    if (votes) meanRating = r.reduce((a, i) => a + i.r * i.n, 0) / votes;
    return cat;
  }

  function initMarket() {
    readUrl();
    const q = $("#q"), src = $("#source"), sort = $("#sort"), variant = $("#variant");
    q.value = state.q; src.value = state.source; sort.value = state.sort; variant.value = state.variant;
    let t; q.addEventListener("input", () => { clearTimeout(t); t = setTimeout(() => { state.q = q.value; state.page = 1; render(); }, 160); });
    src.onchange = () => { state.source = src.value; state.page = 1; render(); };
    variant.onchange = () => { state.variant = variant.value; state.page = 1; render(); };
    sort.onchange = () => { state.sort = sort.value; state.page = 1; render(); };
    $$("[data-view]").forEach(b => b.addEventListener("click", () => { state.view = b.dataset.view; store.set("ae-view", state.view); render(); }));
    $$(".kinds a").forEach(a => a.addEventListener("click", e => { e.preventDefault(); state.kind = a.dataset.kind || ""; state.page = 1; render(); }));
    $("#pager").addEventListener("click", e => {
      const b = e.target.closest("[data-page]"); if (!b || b.disabled) return;
      state.page = +b.dataset.page; render(); $("#results").scrollIntoView({ behavior: window.AE.reduced ? "auto" : "smooth", block: "start" });
    });
    addEventListener("popstate", () => { readUrl(); render(); });
    load().then(cat => {
      const counts = {}; catalog.forEach(i => (counts[i.kind] = (counts[i.kind] || 0) + 1));
      $$(".kinds a").forEach(a => { const k = a.dataset.kind; const s = $("small", a); if (s) s.textContent = k ? counts[k] || 0 : catalog.length; });
      $("#updated").textContent = cat.updated ? "Catalog updated " + new Date(cat.updated).toLocaleDateString() : "";
      render();
    }).catch(() => { $("#results").innerHTML = `<div class="empty"><p>The catalog could not be loaded.</p></div>`; });
  }

  // The home page shows the most loved, newest community items, three of them.
  function initShelf(el) {
    load().then(() => {
      const pick = catalog.filter(i => i.source === "community").sort(SORTS.featured).slice(0, 3);
      el.innerHTML = `<div class="view grid">${(pick.length ? pick : catalog.slice(0, 3)).map(card).join("")}</div>`;
      window.AE.tilt(el);
      const n = {}; catalog.forEach(i => (n[i.source] = (n[i.source] || 0) + 1));
      $$("[data-stat]").forEach(s => (s.textContent = s.dataset.stat === "all" ? catalog.length : (n[s.dataset.stat] || 0)));
    }).catch(() => {});
  }

  document.addEventListener("DOMContentLoaded", () => {
    if ($("#results")) initMarket();
    const shelf = $("#shelf"); if (shelf) initShelf(shelf);
  });
  window.AE.market = { card, KINDS };
})();
