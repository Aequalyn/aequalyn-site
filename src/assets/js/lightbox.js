/* Click any picture to enlarge it; click backdrop, ×, or Esc to close. */
(function () {
  var overlay = null, img = null, caption = null, lastFocus = null, openSrc = "";

  function ensure() {
    if (overlay) return;
    overlay = document.createElement("div");
    overlay.className = "lightbox";
    overlay.setAttribute("role", "dialog");
    overlay.setAttribute("aria-modal", "true");
    overlay.setAttribute("aria-label", "Enlarged picture");
    overlay.hidden = true;
    overlay.innerHTML =
      '<button type="button" class="lightbox-close" aria-label="Close">×</button>' +
      '<figure class="lightbox-figure">' +
      '<img class="lightbox-img" alt="">' +
      '<figcaption class="lightbox-caption"></figcaption>' +
      '</figure>';
    document.body.appendChild(overlay);
    img = overlay.querySelector(".lightbox-img");
    caption = overlay.querySelector(".lightbox-caption");
    // clicks inside the figure don't close; backdrop click does
    overlay.querySelector(".lightbox-figure").addEventListener("click", function (e) {
      e.stopPropagation();
    });
    overlay.addEventListener("click", function () { close(); });
    overlay.querySelector(".lightbox-close").addEventListener("click", function (e) {
      e.stopPropagation(); close();
    });
    // toggle: clicking the enlarged picture itself closes it
    img.addEventListener("click", function (e) { e.stopPropagation(); close(); });
  }

  function open(src, alt, trigger) {
    ensure();
    lastFocus = trigger || document.activeElement;
    openSrc = src;
    img.src = src;
    img.alt = alt || "";
    if (caption) {
      caption.textContent = alt || "";
      caption.hidden = !alt;
    }
    overlay.hidden = false;
    document.documentElement.classList.add("lightbox-open");
    document.body.classList.add("lightbox-open");
    var btn = overlay.querySelector(".lightbox-close");
    if (btn) btn.focus();
  }

  function close() {
    if (!overlay || overlay.hidden) return;
    overlay.hidden = true;
    document.documentElement.classList.remove("lightbox-open");
    document.body.classList.remove("lightbox-open");
    if (img) { img.removeAttribute("src"); }
    openSrc = "";
    if (lastFocus && typeof lastFocus.focus === "function") {
      try { lastFocus.focus(); } catch (_) {}
    }
  }

  function pictureFrom(target) {
    var el = target;
    while (el && el !== document.body) {
      if (el.tagName === "IMG") return el;
      el = el.parentNode;
    }
    return null;
  }

  // delegate: works for pictures present now and any added later
  document.addEventListener("click", function (e) {
    if (overlay && !overlay.hidden && overlay.contains(e.target)) return; // inside lightbox
    var pic = pictureFrom(e.target);
    if (!pic) return;
    var src = pic.currentSrc || pic.getAttribute("src") || pic.src;
    if (!src) return;
    // don't enlarge the tiny brand/icon glyphs; only real pictures
    if (pic.classList.contains("mark")) return;
    e.preventDefault();
    e.stopPropagation();
    open(src, pic.getAttribute("alt") || "", pic);
  }, true); // capture phase: win over link/button handlers on pictures

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" || e.key === "Esc") { close(); }
  });
})();
