// An item's own page: counts the view, shows its counters, keeps the heart and counts copies.
(() => {
  "use strict";
  const { $, $$, num, stats, hearted, setHeart, burst, copy, wear } = window.AE;
  document.addEventListener("DOMContentLoaded", () => {
    const page = $("[data-item]"); if (!page) return;
    const key = page.dataset.item;
    let my = 0;
    const show = s => {
      if (!s) return;
      for (const k of ["v", "h", "c"]) { const el = $(`[data-count="${k}"]`); if (el) el.textContent = num(s[k] || 0); }
      if (typeof s.n === "number" && $('[data-rating="avg"]')) {
        $('[data-rating="avg"]').textContent = s.n ? s.r.toFixed(1) : "–";
        const bar = $('[data-rating="stars"]');
        bar.style.setProperty("--r", s.n ? s.r : 0);
        bar.setAttribute("aria-label", s.n ? `Rated ${s.r.toFixed(1)} of 5` : "Not rated yet");
        $('[data-rating="count"]').textContent = s.n ? `${s.n} rating${s.n === 1 ? "" : "s"}` : "No ratings yet";
        const d = s.d || [0, 0, 0, 0, 0], top = Math.max(1, ...d);
        for (let i = 1; i <= 5; i++) {
          $(`[data-bar="${i}"]`).style.width = (d[i - 1] / top * 100) + "%";
          $(`[data-barn="${i}"]`).textContent = d[i - 1];
        }
      }
      if (typeof s.my === "number") pick(s.my);
    };
    // Your own stars: hovering shows what a click would give; clicking your current rating takes it back.
    const picks = $$(".stars-pick button");
    const light = n => picks.forEach(b => b.classList.toggle("lit", +b.dataset.stars <= n));
    const note = $('[data-rating="note"]');
    const pick = n => {
      my = n; light(n);
      picks.forEach(b => b.setAttribute("aria-checked", String(+b.dataset.stars === n)));
      if (note) note.textContent = n ? `You gave it ${n} star${n > 1 ? "s" : ""}.` : "Click a star; click it again to take it back.";
    };
    picks.forEach(b => {
      b.addEventListener("mouseenter", () => light(+b.dataset.stars));
      b.addEventListener("focus", () => light(+b.dataset.stars));
      b.addEventListener("click", () => {
        const n = +b.dataset.stars === my ? 0 : +b.dataset.stars;
        pick(n); if (n === 5) burst(b);
        stats.send(key, "rate", { stars: n }).then(r => r && r.item && show(r.item));
      });
    });
    const group = $(".stars-pick");
    group?.addEventListener("mouseleave", () => light(my));
    group?.addEventListener("keydown", e => {
      if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
      const n = Math.min(5, Math.max(1, (my || 0) + (e.key === "ArrowRight" ? 1 : -1)));
      e.preventDefault(); picks[n - 1].focus(); if (n !== my) picks[n - 1].click();
    });
    const heart = $("[data-heart]");
    const mark = on => heart && heart.setAttribute("aria-pressed", String(on));
    mark(hearted().has(key));

    // One view per visit of a page in this tab; the server also counts a visitor once a day.
    const seen = "ae-seen-" + key;
    let first = false; try { first = !sessionStorage.getItem(seen); sessionStorage.setItem(seen, "1"); } catch { first = true; }
    (first ? stats.send(key, "view") : Promise.resolve(null))
      .then(r => r && r.item ? r.item : stats.all().then(all => all[key]))
      .then(s => { show(s); if (s && typeof s.mine === "boolean") { mark(s.mine); setHeart(key, s.mine); } });

    heart?.addEventListener("click", () => {
      const on = heart.getAttribute("aria-pressed") !== "true";
      mark(on); setHeart(key, on); if (on) burst(heart);
      const el = $('[data-count="h"]'); if (el && /^\d+$/.test(el.textContent)) el.textContent = String(Math.max(0, +el.textContent + (on ? 1 : -1)));
      stats.send(key, on ? "heart" : "unheart").then(r => r && r.item && show(r.item));
    });
    $$("[data-install]").forEach(b => b.addEventListener("click", () => {
      copy(b.dataset.install);
      stats.send(key, "copy").then(r => r && r.item && show(r.item));
    }));
    $$("[data-wear]").forEach(b => b.addEventListener("click", () => wear(b.dataset.wear, b)));
    $$("[data-hex]").forEach(b => b.addEventListener("click", () => copy(b.dataset.hex)));
  });
})();
