// The documentation: search across every page, the sections menu on a phone, the
// "On this page" list that follows the reading, and a copy button on every code block.
(() => {
  "use strict";
  const { $, $$, esc, copy } = window.AE;

  // ---------------------------------------------------------------- search
  let index = null;
  const load = () => index ? Promise.resolve(index)
    : fetch("/data/docs-index.json").then(r => r.json()).then(j => (index = j.map(p => ({ ...p, lt: p.t.toLowerCase(), lh: p.h.join(" ").toLowerCase(), lx: p.x.toLowerCase() })))).catch(() => (index = []));
  // A page whose title has every word comes first, then its headings, then its text.
  function search(q) {
    const words = q.toLowerCase().split(/\s+/).filter(w => w.length > 1);
    if (!words.length) return [];
    return index.map(p => {
      let score = 0;
      for (const w of words) {
        const t = p.lt.includes(w) ? 10 : 0, h = p.lh.includes(w) ? 4 : 0, x = p.lx.includes(w) ? 1 : 0;
        if (!t && !h && !x) return null;
        score += t + h + x;
      }
      return { p, score };
    }).filter(Boolean).sort((a, b) => b.score - a.score).slice(0, 8);
  }
  function snippet(p, words) {
    const at = Math.max(0, Math.min(...words.map(w => { const i = p.lx.indexOf(w); return i < 0 ? Infinity : i; })));
    const start = isFinite(at) ? Math.max(0, at - 50) : 0;
    let s = esc(p.x.slice(start, start + 150));
    for (const w of words) s = s.replace(new RegExp(w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "gi"), m => `<mark>${m}</mark>`);
    return (start ? "…" : "") + s + "…";
  }
  function wireSearch() {
    const q = $("#docs-q"), hits = $("#docs-hits"); if (!q) return;
    let at = -1;
    const show = () => {
      load().then(() => {
        const words = q.value.toLowerCase().split(/\s+/).filter(w => w.length > 1);
        const res = search(q.value); at = -1;
        if (!q.value.trim()) { hits.hidden = true; return; }
        hits.innerHTML = res.length ? res.map(({ p }) => `<li><a href="/docs/${p.s}/"><b>${esc(p.t)}</b><small>${esc(p.g)}</small><span>${snippet(p, words)}</span></a></li>`).join("")
          : `<li class="none">Nothing found for “${esc(q.value)}”.</li>`;
        hits.hidden = false;
      });
    };
    q.addEventListener("input", show);
    q.addEventListener("focus", () => { load(); if (q.value.trim()) show(); });
    q.addEventListener("keydown", e => {
      const links = $$("a", hits);
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        e.preventDefault(); if (!links.length) return;
        at = (at + (e.key === "ArrowDown" ? 1 : -1) + links.length) % links.length;
        links.forEach((l, i) => l.classList.toggle("on", i === at)); links[at].scrollIntoView({ block: "nearest" });
      } else if (e.key === "Enter" && links.length) { e.preventDefault(); location.href = links[Math.max(0, at)].href; }
      else if (e.key === "Escape") { hits.hidden = true; q.blur(); }
    });
    document.addEventListener("click", e => { if (!e.target.closest(".docs-search")) hits.hidden = true; });
    document.addEventListener("keydown", e => {
      if (e.key === "/" && !/input|textarea|select/i.test(document.activeElement.tagName)) { e.preventDefault(); q.focus(); q.select(); }
    });
  }

  // ------------------------------------------------------------- the rest
  function wireMenu() {
    const btn = $(".docs-menu"), side = $("#docs-side"); if (!btn || !side) return;
    btn.addEventListener("click", () => { const o = side.classList.toggle("open"); btn.setAttribute("aria-expanded", String(o)); });
  }
  // The heading being read is lit in "On this page".
  function wireToc() {
    const links = $$(".docs-toc a"); if (!links.length) return;
    const map = new Map(links.map(a => [decodeURIComponent(a.hash.slice(1)), a]));
    const heads = [...map.keys()].map(id => document.getElementById(id)).filter(Boolean);
    const io = new IntersectionObserver(es => {
      const vis = es.filter(x => x.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)[0];
      if (vis) { links.forEach(a => a.classList.remove("on")); map.get(vis.target.id)?.classList.add("on"); }
    }, { rootMargin: "-70px 0px -70% 0px" });
    heads.forEach(h => io.observe(h));
  }
  function wireCode() {
    $$(".docs-body .copy-code").forEach(b => b.addEventListener("click", () => copy($("code", b.parentElement).textContent)));
  }

  document.addEventListener("DOMContentLoaded", () => { wireSearch(); wireMenu(); wireToc(); wireCode(); });
})();
