#!/usr/bin/env python3
"""Build the Aequalyn site into public/, ready to upload as it is.

    tools/build.py --themes ../aequalyn-themes [--market db/market.json|URL] [--out public] [--sources DIR]

Reads the Market's catalog (the approved items), the themes repository (every built-in
theme and wallpaper) and the documentation of every repository, and writes every page, one
page per item, the data the scripts read, a sitemap and the PHP counters API. It asks no
GitHub API, so it has no rate limit to run into. Only the standard library: it runs the same
in Actions and at home.
"""
import argparse
import html
import json
import os
import re
import shutil
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import docs  # noqa: E402  (tools/docs.py)

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
MARKET_URL = "https://raw.githubusercontent.com/Aequalyn/aequalyn-market/main/db/market.json"
KINDS = {"plugin": "Plugin", "theme": "Theme", "wallpaper": "Wallpaper", "app": "App", "cursor": "Cursor", "look": "Look"}
CLONE = "/var/lib/aequalyn/src/aequalyn-themes"  # where aequalyn-builtin-themes keeps the themes
e = html.escape

# Icons, drawn on a 24 grid with a 1.8 stroke (the GitHub mark is GitHub's own).
_S = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
ICONS = {
    "mark": '<svg class="mark" viewBox="100 130 320 200" fill="none" stroke="currentColor" stroke-width="29.7" aria-hidden="true"><g transform="translate(0 20.5)"><circle cx="188.8" cy="204.8" r="64"/><path d="M252.8 204.8v78.8"/><path d="M380.8 204.8A64 64 0 1 0 365.8 245.9" stroke-linecap="round"/><path d="M252.8 204.8h128"/></g></svg>',
    "menu": _S + '<path d="M4 7h16M4 12h16M4 17h16"/></svg>',
    "chevron": _S + '<path d="m6 9 6 6 6-6"/></svg>',
    "sun": _S + '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>',
    "palette": _S + '<path d="M12 3a9 9 0 1 0 0 18c1.1 0 1.7-.9 1.4-1.8-.4-1.2.4-2.2 1.6-2.2H17a4 4 0 0 0 4-4c0-5.5-4-10-9-10Z"/><circle cx="7.5" cy="11" r="1.2"/><circle cx="10.5" cy="7" r="1.2"/><circle cx="15.5" cy="7.5" r="1.2"/></svg>',
    "github": '<svg viewBox="0 0 16 16" fill="currentColor" aria-hidden="true"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0 0 16 8c0-4.42-3.58-8-8-8Z"/></svg>',
    "download": _S + '<path d="M12 3v12m0 0-5-5m5 5 5-5M4 21h16"/></svg>',
    "grid": _S + '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></svg>',
    "list": _S + '<rect x="3" y="4" width="5" height="4" rx="1"/><rect x="3" y="10" width="5" height="4" rx="1"/><rect x="3" y="16" width="5" height="4" rx="1"/><path d="M11 6h10M11 12h10M11 18h10"/></svg>',
    "carousel": _S + '<rect x="7" y="5" width="10" height="14" rx="1.5"/><path d="M3 7v10M21 7v10"/></svg>',
    "film": _S + '<rect x="2" y="6" width="20" height="12" rx="1.5"/><path d="M7 6v12M12 6v12M17 6v12"/></svg>',
    "spotlight": _S + '<rect x="3" y="4" width="12" height="16" rx="1.5"/><path d="M18 5h3M18 10h3M18 15h3M18 20h3"/></svg>',
    "right": _S + '<path d="M5 12h14m-6-6 6 6-6 6"/></svg>',
    "left": _S + '<path d="M19 12H5m6 6-6-6 6-6"/></svg>',
    "star": _S + '<path d="m12 3 2.8 5.7 6.2.9-4.5 4.4 1 6.2L12 17.3 6.5 20.2l1-6.2L3 9.6l6.2-.9Z"/></svg>',
    "heart": _S + '<path d="M12 20s-7-4.4-9.3-9A5 5 0 0 1 12 6a5 5 0 0 1 9.3 5c-2.3 4.6-9.3 9-9.3 9Z"/></svg>',
    "copy": _S + '<rect x="8" y="8" width="13" height="13" rx="2"/><path d="M16 8V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h3"/></svg>',
    "eye": _S + '<path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/></svg>',
    "layout": _S + '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 10h18M10 10v11"/></svg>',
    "store": _S + '<path d="M4 9h16l-1.2 10.1a2 2 0 0 1-2 1.9H7.2a2 2 0 0 1-2-1.9Z"/><path d="M8 9V7a4 4 0 0 1 8 0v2"/></svg>',
    "bar": _S + '<rect x="2" y="4" width="20" height="5" rx="2.5"/><path d="M6 15h12M9 19h6"/></svg>',
    "lock": _S + '<rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/></svg>',
    "install": _S + '<rect x="3" y="4" width="18" height="12" rx="2"/><path d="M8 20h8M12 16v4M9 9l3 3 3-3"/></svg>',
    "bug": _S + '<rect x="7" y="8" width="10" height="12" rx="5"/><path d="M12 8V5m-3 0 1.5 2M15 5l-1.5 2M3 13h4M17 13h4M4 19l3-2M20 19l-3-2M4 7l3 2M20 7l-3 2"/></svg>',
    "send": _S + '<path d="M22 2 11 13M22 2l-7 20-4-9-9-4Z"/></svg>',
    "external": _S + '<path d="M14 4h6v6M20 4 10 14M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/></svg>',
}
SPRITE_ICONS = ["star", "heart", "copy", "eye", "left", "right"]


def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "aequalyn-site-build"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def circles(t, pal):
    """the backdrop's three circles in the theme's own colours: one each when it has three,
    repeated when it has fewer, and a gradient through the rest when it has more"""
    cols = list(dict.fromkeys(c for c in (pal.get("borderColors") or t.get("colors") or []) if isinstance(c, str) and c))
    cols = cols or [c for c in (pal.get("accentPrimary"), pal.get("accentCyan")) if c]
    if not cols:
        return []
    groups = [cols[i::3] or [cols[i % len(cols)]] for i in range(3)]
    return [g[0] if len(g) == 1 else f"linear-gradient(135deg,{','.join(g)})" for g in groups]


def load_themes(themes_dir, themes_repo):
    """every built-in theme's palette, and the catalog entries for themes and wallpapers"""
    # jsDelivr serves the repository fast and cached; THEMES_CDN overrides it (a local preview)
    cdn = os.environ.get("THEMES_CDN") or f"https://cdn.jsdelivr.net/gh/{themes_repo}@main"
    themes, items = {}, []
    for tj in sorted((themes_dir / "themes").glob("*/theme.json")):
        tid = tj.parent.name
        t = json.loads(tj.read_text())
        pal = t.get("palette") or {}
        if not pal.get("bgBase"):
            # no palette of its own: its colours come from its backgrounds (matugen), so it
            # is in the Market but cannot dress the site
            items.append({
                "key": f"theme:{tid}", "kind": "theme", "id": tid, "name": t.get("name", tid),
                "about": t.get("about") or "Colours drawn from its own backgrounds.", "by": t.get("author", "Aequalyn"),
                "license": "", "source": "built-in", "variant": "dark",
                "repo": f"https://github.com/{themes_repo}/tree/main/themes/{tid}",
                "preview": f"{cdn}/themes/{tid}/preview.jpg" if (tj.parent / "preview.jpg").is_file() else "",
                "media": "image", "colors": [], "approved": "",
                "install": f"aequalyn-themes install {CLONE}/themes/{tid} && aequalyn-themes set {tid}",
            })
            continue
        rings = circles(t, pal)  # before borderColors leaves the palette
        border = pal.pop("borderColors", None) or t.get("colors", [])[1:3]
        themes[tid] = {"name": t.get("name", tid), "family": t.get("family", t.get("name", tid)),
                       "variant": "light" if t.get("variant") == "light" else "dark",
                       "about": t.get("about", ""), "palette": pal, "border": border,
                       "preview": f"{cdn}/themes/{tid}/preview.jpg" if (tj.parent / "preview.jpg").is_file() else "",
                       "circles": rings}
        items.append({
            "key": f"theme:{tid}", "kind": "theme", "id": tid, "name": t.get("name", tid), "about": t.get("about", ""),
            "by": t.get("author", "Aequalyn"), "license": "", "source": "built-in", "variant": themes[tid]["variant"],
            "repo": f"https://github.com/{themes_repo}/tree/main/themes/{tid}",
            "preview": f"{cdn}/themes/{tid}/preview.jpg" if (tj.parent / "preview.jpg").is_file() else "",
            "media": "image", "colors": [pal.get(k) for k in ("bgBase", "bgSurface", "accentPrimary", "accentCyan", "accentGreen", "accentRed") if pal.get(k)],
            "install": f"aequalyn-themes install {CLONE}/themes/{tid} && aequalyn-themes set {tid}",
            "palette": pal, "approved": "",
        })
    for tid, t in themes.items():
        other = tid[:-4] if tid.endswith("-day") else tid + "-day"
        if other in themes:
            t["pair"] = other
    for w in sorted((themes_dir / "wallpapers").glob("*")):
        if w.suffix.lower() not in (".jpg", ".jpeg", ".png", ".webp", ".mp4"):
            continue
        wid = re.sub(r"[^a-z0-9._-]", "-", w.stem.lower())
        live = w.suffix.lower() == ".mp4"
        items.append({
            "key": f"wallpaper:{wid}", "kind": "wallpaper", "id": wid,
            "name": ("Live: " if live else "") + w.stem.replace("-", " ").title(),
            "about": "A live wallpaper that plays behind your windows." if live else "A wallpaper that comes with Aequalyn.",
            "by": "Aequalyn", "license": "", "source": "built-in",
            "repo": f"https://github.com/{themes_repo}/blob/main/wallpapers/{w.name}",
            "preview": f"{cdn}/wallpapers/{w.name}", "media": "video" if live else "image",
            "install": f"aequalyn-wallpaper set {CLONE}/wallpapers/{w.name}", "approved": "",
        })
    lic = themes_dir / "LICENSE"
    if lic.is_file():
        first = lic.read_text(errors="ignore").strip().splitlines()[0].strip()
        for it in items:
            it["license"] = first[:60]
    return themes, items


def load_market(src):
    data = fetch_json(src) if re.match(r"^https?://", src) else json.loads(Path(src).read_text())
    items = []
    for it in data.get("items", []):
        kind = it.get("kind", "")
        shown = "app" if kind == "appimage" else kind
        iid = str(it.get("id", ""))
        if shown not in KINDS or not re.match(r"^[a-z0-9][a-z0-9._-]{0,79}$", iid):
            continue
        prev = it.get("preview", "")
        items.append({
            "key": f"{shown}:{iid}", "kind": shown, "id": iid, "name": it.get("name", iid), "about": it.get("about", ""),
            "by": it.get("by", ""), "license": it.get("license", ""), "source": "community",
            "repo": it.get("repo", ""), "commit": it.get("commit", ""),
            "issue": it.get("issue"), "approved": it.get("approved", ""), "approvedBy": it.get("approvedBy", ""),
            "preview": prev, "media": "icon" if (shown in ("app", "cursor") or re.search(r"/icon\.[a-z]+$", prev)) else
                       ("video" if prev.endswith(".mp4") else "image"),
            "install": f"aequalyn-store install-market {kind}:{iid}",
        })
    return data, items


# ------------------------------------------------------------------ rendering
def media_html(it, cls="shot"):
    if not it.get("preview"):
        return f'<div class="{cls} icon"><span class="muted">No preview</span></div>'
    if it["media"] == "video":
        return f'<div class="{cls}"><video src="{e(it["preview"])}" autoplay muted loop playsinline></video></div>'
    if it["media"] == "icon":
        return f'<div class="{cls} icon"><img src="{e(it["preview"])}" alt="{e(it["name"])}"></div>'
    return f'<div class="{cls}"><img src="{e(it["preview"])}" alt="{e(it["name"])}, a preview"></div>'


def item_body(it, related, cfg):
    kind = KINDS[it["kind"]]
    facts = [("Kind", kind), ("By", e(it["by"]) if it["source"] == "community" else "Aequalyn (built in)")]
    if it.get("license"):
        facts.append(("Licence", e(it["license"])))
    if it.get("variant"):
        facts.append(("Variant", "Day" if it["variant"] == "light" else "Night"))
    if it.get("commit"):
        facts.append(("Reviewed at", f'<a href="{e(it["repo"])}/tree/{e(it["commit"])}" rel="noopener"><code>{e(it["commit"][:12])}</code></a>'))
    if it.get("approved"):
        facts.append(("Approved", e(it["approved"]) + (f' by {e(it["approvedBy"])}' if it.get("approvedBy") else "")))
    if it.get("issue"):
        facts.append(("Submission", f'<a href="{e(cfg["market_repo"])}/issues/{int(it["issue"])}" rel="noopener">#{int(it["issue"])}</a>'))
    dl = "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in facts)
    palette = ""
    if it.get("palette"):
        sw = "".join(f'<button type="button" data-hex="{e(v)}" title="Copy {e(v)}"><i style="background:{e(v)}"></i><span>{e(k)}<br>{e(v)}</span></button>'
                     for k, v in it["palette"].items())
        palette = f'<section style="margin-top:28px"><h2 style="font-size:1.1rem">Palette</h2><div class="palette-big">{sw}</div></section>'
    wear = (f'<button class="btn" type="button" data-wear="{e(it["id"])}">{ICONS["palette"]} Try it here</button>'
            if it["kind"] == "theme" and it["source"] == "built-in" else "")
    rel = "".join(
        f'<a class="item" href="/market/{r["kind"]}/{r["id"]}/" data-tilt style="--i:{n}"><span class="glare"></span>'
        f'{media_html(r, "media")}<div class="body"><h3>{e(r["name"])}</h3><p>{e(r["about"])}</p></div></a>'
        for n, r in enumerate(related))
    gh = (f'<a class="btn" href="{e(it["repo"])}" rel="noopener">{ICONS["github"]} Source</a>' if it.get("repo") else "")
    return f"""<div class="wrap" data-item="{e(it["key"])}">
  <nav class="crumbs" aria-label="Breadcrumb"><a href="/market/">Market</a> / <a href="/market/?kind={it["kind"]}">{kind}s</a> / {e(it["name"])}</nav>
  <div class="detail">
    <div>
      {media_html(it)}
      <h1 style="margin-top:24px">{e(it["name"])}</h1>
      <p style="font-size:1.08rem">{e(it["about"])}</p>
      {palette}
      <section class="card rating" style="margin-top:28px" aria-label="Ratings">
        <div class="rating-sum">
          <b data-rating="avg">–</b>
          <span class="stars-show" data-rating="stars" style="--r:0" role="img" aria-label="Not rated yet"></span>
          <span class="muted" data-rating="count">No ratings yet</span>
        </div>
        <div class="rating-bars">{"".join(f'<div><span>{s}</span><i><b data-bar="{s}"></b></i><small data-barn="{s}">0</small></div>' for s in range(5, 0, -1))}</div>
        <div class="rating-mine">
          <span>Your rating</span>
          <div class="stars-pick" role="radiogroup" aria-label="Your rating">{"".join(f'<button type="button" role="radio" aria-checked="false" data-stars="{s}" aria-label="{s} star{"s" if s > 1 else ""}">{ICONS["star"]}</button>' for s in range(1, 6))}</div>
          <small class="muted" data-rating="note">Click a star; click it again to take it back.</small>
        </div>
      </section>
    </div>
    <aside>
      <div class="card" style="display:grid;gap:14px">
        <span><span class="chip accent">{kind}</span> <span class="chip">{"Built in" if it["source"] == "built-in" else "Community"}</span></span>
        <div class="counters">
          <div><b data-count="h">–</b><span>hearts</span></div>
          <div><b data-count="c">–</b><span>copies</span></div>
          <div><b data-count="v">–</b><span>views</span></div>
        </div>
        <div><span class="muted" style="font-size:13px">Install from a terminal</span>
          <div class="copy-box"><code>{e(it["install"])}</code>
          <button class="icon-btn" type="button" data-install="{e(it["install"])}" aria-label="Copy the command">{ICONS["copy"]}</button></div></div>
        <div style="display:flex;gap:8px;flex-wrap:wrap">
          <button class="btn heart" type="button" data-heart aria-pressed="false">{ICONS["heart"]} Heart</button>
          {wear}{gh}
        </div>
        <dl class="facts">{dl}</dl>
      </div>
      <p class="muted" style="font-size:13px;margin:0">Or open the Store on your Aequalyn desktop and find it under {kind}s.</p>
    </aside>
  </div>
  {f'<section class="section" style="padding-top:0"><h2>More {kind.lower()}s</h2><div class="view grid">{rel}</div></section>' if rel else ""}
</div>"""


def team_html(team):
    """the people in site.json: picture, name, role, areas and their GitHub profile"""
    out = []
    for n, m in enumerate(team):
        login = m["login"]
        name = m.get("name") or login
        areas = "".join(f'<span class="chip accent">{e(a)}</span>' for a in m.get("areas", []))
        out.append(f"""<article class="card person reveal" style="--d:{n * .08}s">
      <img src="https://github.com/{e(login)}.png?size=240" alt="{e(name)}" width="120" height="120" loading="lazy">
      <div>
        <h2>{e(name)}</h2>
        <p class="muted" style="margin:0 0 10px">@{e(login)} · {e(m.get("role", ""))}</p>
        <p style="display:flex;gap:6px;flex-wrap:wrap">{areas}</p>
        <p style="margin:14px 0 0"><a class="btn" href="https://github.com/{e(login)}" rel="noopener">{ICONS["github"]} GitHub profile</a></p>
      </div>
    </article>""")
    return "".join(out)


def news_posts(news):
    """the news, newest first, each with its own page: /news/<slug>/ (its "slug", or one made
    from its title) and its full text from src/news/<slug>.md when there is one"""
    posts, seen = [], set()
    for it in sorted(news.get("items", []), key=lambda x: x.get("date", ""), reverse=True):
        slug = docs.slugify(it.get("slug") or it["title"])
        if slug in seen:
            slug = f'{slug}-{it.get("date", "")}'.rstrip("-")
        seen.add(slug)
        md = SRC / "news" / f"{slug}.md"
        html_body = docs.render(md.read_text(), lambda href, image: href)[0] if md.is_file() else ""
        posts.append({**it, "slug": slug, "url": f"/news/{slug}/", "html": html_body})
    return posts


def news_html(news, n=None):
    items = news_posts(news)
    if n:
        items = items[:n]
    out = []
    for it in items:
        title = f'<a href="{e(it["url"])}">{e(it["title"])}</a>'
        out.append(f'<article class="card reveal"><time datetime="{e(it["date"])}">{e(it["date"])}</time><div><h3>{title}</h3><p>{e(it["body"])}</p></div></article>')
    return "".join(out) or '<p class="muted">No news yet.</p>'


def news_page(posts, n):
    it = posts[n]
    newer = posts[n - 1] if n > 0 else None
    older = posts[n + 1] if n + 1 < len(posts) else None
    link = it.get("link", "")
    more = ""
    if link:
        rel = ' rel="noopener"' if re.match(r"^https?:", link) else ""
        label = "Read more on GitHub" if "github.com" in link else "Take a look"
        more = f'<p><a class="btn" href="{e(link)}"{rel}>{label}</a></p>'
    pn = (f'<a class="card" href="{older["url"]}"><small>Older</small>{e(older["title"])}</a>' if older else "<span></span>") + \
         (f'<a class="card next" href="{newer["url"]}"><small>Newer</small>{e(newer["title"])}</a>' if newer else "")
    body = it["html"].replace("{", "&#123;").replace("}", "&#125;")
    lead = e(it["body"]).replace("{", "&#123;").replace("}", "&#125;")
    title = e(it["title"]).replace("{", "&#123;").replace("}", "&#125;")
    return f"""<article class="wrap prose post">
  <nav class="crumbs" aria-label="Breadcrumb"><a href="/news/">News</a></nav>
  <h1>{title}</h1>
  <time datetime="{e(it["date"])}">{e(it["date"])}</time>
  <p class="lead">{lead}</p>
  {f'<div class="docs-body">{body}</div>' if body else ""}
  {more}
  <footer class="docs-pn">{pn}</footer>
</article>"""


def themes_gallery(themes, items):
    by = {i["id"]: i for i in items if i["kind"] == "theme" and i["source"] == "built-in"}
    out = []
    for n, (tid, t) in enumerate(t for t in themes.items() if t[1]["variant"] == "dark" or t[1].get("pair") is None):
        it = by[tid]
        pair = t.get("pair")
        btns = f'<button class="btn" type="button" data-wear="{e(tid)}">{"Night" if pair else "Try it here"}</button>'
        if pair:
            btns += f'<button class="btn" type="button" data-wear="{e(pair)}">{ICONS["sun"]} Day</button>'
        chips = theme_dot(t["palette"])
        out.append(f'<div class="item" data-tilt style="--i:{n % 9}"><span class="glare"></span>'
                   f'<a href="/market/theme/{e(tid)}/" class="media" style="display:block"><img src="{e(it["preview"])}" alt="{e(t["name"])}, a preview" loading="lazy">{chips}</a>'
                   f'<div class="body"><h3><a href="/market/theme/{e(tid)}/" style="color:inherit">{e(t["name"])}</a></h3><p>{e(t["about"])}</p>'
                   f'<div style="display:flex;gap:8px;margin-top:8px">{btns}</div></div></div>')
    return "".join(out)


def dot(colors):
    """a theme's colours as one small square, in quarters"""
    c = [x for x in colors if x][:4] or ["#888"]
    c += [c[-1]] * (4 - len(c))
    return f'<span class="dot" style="background:conic-gradient({e(c[0])} 0 25%,{e(c[1])} 0 50%,{e(c[2])} 0 75%,{e(c[3])} 0)" aria-hidden="true"></span>'


def theme_dot(pal):
    return dot([pal.get("bgBase"), pal.get("accentPrimary"), pal.get("accentCyan"), pal.get("textPrimary")])


def quick_themes(themes):
    pick = [t for t in ("aequalyn", "aequalyn-day", "gold", "emerald", "ruby", "cobalt", "frost-day", "lotus-day") if t in themes]
    return "".join(f'<button type="button" data-wear="{e(t)}" title="Try {e(themes[t]["name"])} on this site">'
                   f'<span class="pic"><img src="{e(themes[t]["preview"])}" alt="" loading="lazy">{theme_dot(themes[t]["palette"])}</span>'
                   f'<span class="name">{e(themes[t]["name"])}</span></button>' for t in pick)


def wall_style(t):
    """the blurred wallpaper for a visitor who has not chosen a theme yet (the default's preview)"""
    return e(f'--ae-wall:url("{t["preview"]}")') if t and t.get("preview") else ""


def page(body, meta, ctx, path):
    head = (SRC / "partials/head.html").read_text()
    nav = (SRC / "partials/nav.html").read_text()
    foot = (SRC / "partials/footer.html").read_text()
    scripts = "".join(f'<script src="/assets/js/{s}.js?v={ctx["version"]}" defer></script>' for s in meta.get("scripts", []))
    doc = head + nav + body + foot
    url = ctx["cfg"]["url"].rstrip("/") + path
    vals = {"title": e(meta["title"]), "description": e(meta["description"]), "canonical": e(url),
            "image": e(meta.get("image") or f'https://cdn.jsdelivr.net/gh/{ctx["cfg"]["themes_repo"]}@main/themes/aequalyn/preview.jpg'),
            "scripts": scripts, **ctx["vars"]}

    def sub(m):
        k = m.group(1)
        if k.startswith("icon:"):
            return ICONS.get(k[5:], "")
        if k.startswith("count:"):
            return str(ctx["counts"].get(k[6:], 0))
        if k.startswith("repo:"):
            return e(ctx["cfg"]["org"].rstrip("/") + "/" + k[5:])
        if k.startswith("news:"):
            return news_html(ctx["news"], None if k[5:] == "all" else int(k[5:]))
        if k in vals:
            return str(vals[k])
        raise KeyError(f"{path}: unknown placeholder {{{{{k}}}}}")
    return re.sub(r"\{\{([a-z_:0-9-]+)\}\}", sub, doc)


def write(out, rel, text):
    p = out / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


def docs_sidebar(man, pages, cur):
    by = {p["slug"]: p for p in pages}
    groups = []
    for sec in man["sections"]:
        links = "".join(f'<li><a href="/docs/{s["slug"]}/"{" aria-current=page" if s["slug"] == cur else ""}>{e(s["title"])}</a></li>'
                        for s in sec["pages"] if s["slug"] in by)
        groups.append(f'<li class="group"><span>{ICONS.get(sec.get("icon"), "")}{e(sec["title"])}</span><ul>{links}</ul></li>')
    return f"""<aside class="docs-side" id="docs-side">
      <div class="docs-search" role="search">
        <input type="search" id="docs-q" placeholder="Search the docs" aria-label="Search the docs" autocomplete="off">
        <kbd>/</kbd>
        <ol class="docs-hits" id="docs-hits" hidden></ol>
      </div>
      <nav aria-label="Documentation"><ul class="docs-nav"><li><a href="/docs/"{" aria-current=page" if cur == "" else ""}>Overview</a></li>{"".join(groups)}</ul></nav>
    </aside>"""


def docs_page(pg, man, pages, n):
    prev = pages[n - 1] if n > 0 else None
    nxt = pages[n + 1] if n + 1 < len(pages) else None
    toc = "".join(f'<li class="l{lvl}"><a href="#{hid}">{e(txt)}</a></li>' for lvl, hid, txt in pg["toc"])
    srcs = " · ".join(f'<a href="{e(s["url"])}" rel="noopener">{e(s["repo"])}/{e(s["path"])}</a>' for s in pg["sources"])
    edit = pg["sources"][0]["url"].replace("/blob/", "/edit/") if pg["sources"] else ""
    pn = (f'<a class="card" href="/docs/{prev["slug"]}/"><small>Previous</small>{e(prev["title"])}</a>' if prev else "<span></span>") + \
         (f'<a class="card next" href="/docs/{nxt["slug"]}/"><small>Next</small>{e(nxt["title"])}</a>' if nxt else "")
    body = pg["html"].replace("{", "&#123;").replace("}", "&#125;")
    return f"""<div class="wrap docs">
  <button class="btn docs-menu" type="button" aria-expanded="false" aria-controls="docs-side">{ICONS["menu"]} {e(pg["section"])}</button>
  {docs_sidebar(man, pages, pg["slug"])}
  <article class="docs-main">
    <nav class="crumbs" aria-label="Breadcrumb"><a href="/docs/">Docs</a> / {e(pg["section"])}</nav>
    <h1>{e(pg["title"])}</h1>
    <div class="docs-body">{body}</div>
    <footer class="docs-foot">
      {f'<p class="muted">From {srcs}. Something wrong? <a href="{e(edit)}" rel="noopener">Edit it on GitHub</a>.</p>' if srcs else ""}
      <div class="docs-pn">{pn}</div>
    </footer>
  </article>
  <aside class="docs-toc">{f'<span>On this page</span><ol>{toc}</ol>' if toc else ""}</aside>
</div>"""


def docs_index(man, pages):
    by = {p["slug"]: p for p in pages}
    cards = []
    for n, sec in enumerate(man["sections"]):
        links = "".join(f'<li><a href="/docs/{s["slug"]}/">{e(s["title"])}</a></li>' for s in sec["pages"] if s["slug"] in by)
        cards.append(f'<div class="card feature reveal" style="--d:{(n % 3) * .08}s"><div class="ico">{ICONS.get(sec.get("icon"), "")}</div>'
                     f'<h3>{e(sec["title"])}</h3><ul class="docs-list">{links}</ul></div>')
    return f"""<div class="wrap docs">
  <button class="btn docs-menu" type="button" aria-expanded="false" aria-controls="docs-side">{ICONS["menu"]} Sections</button>
  {docs_sidebar(man, pages, "")}
  <article class="docs-main">
    <span class="eyebrow">Documentation</span>
    <h1>Everything about Aequalyn</h1>
    <p style="font-size:1.08rem">How to install it, use it, make it yours, publish to the Market and build it, in {len(pages)} pages made from the repositories' own documentation. Press <kbd>/</kbd> to search.</p>
    <div class="grid-3 docs-cards">{"".join(cards)}</div>
  </article>
</div>"""


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--themes", required=True, help="a checkout of aequalyn-themes")
    ap.add_argument("--market", default=MARKET_URL, help="db/market.json of aequalyn-market, a path or a URL")
    ap.add_argument("--out", default=str(ROOT / "public"))
    ap.add_argument("--sources", help="a folder with checkouts of the Aequalyn repositories, read for the docs instead of GitHub")
    a = ap.parse_args()

    cfg = json.loads((SRC / "site.json").read_text())
    if os.environ.get("SITE_URL"):
        cfg["url"] = os.environ["SITE_URL"]
    out = Path(a.out).resolve()
    if out in (ROOT, SRC, Path.home(), Path("/")) or (out.exists() and any(out.iterdir()) and not (out / ".aequalyn-site").exists()):
        sys.exit(f"refusing to write into {out}: not an earlier build")
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    (out / ".aequalyn-site").write_text("built by tools/build.py\n")

    themes, builtin = load_themes(Path(a.themes), cfg["themes_repo"])
    market, community = load_market(a.market)
    items = community + builtin
    org = cfg["org"].rstrip("/").rsplit("/", 1)[-1]
    man, dpages = docs.load(SRC / "docs", org, a.sources)
    for i in items:
        i["url"] = f"/market/{i['kind']}/{i['id']}/"
    seen = set()
    items = [i for i in items if not (i["key"] in seen or seen.add(i["key"]))]

    counts = {"all": len(items), "community": sum(i["source"] == "community" for i in items),
              "families": sum(1 for t in themes.values() if t["variant"] == "dark" or not t.get("pair"))}
    for k in KINDS:
        counts[k] = sum(i["kind"] == k for i in items)
    version = datetime.now(timezone.utc).strftime("%Y%m%d%H%M")
    sprite = '<div hidden>' + "".join(f'<span id="i-{n}">{ICONS[n]}</span>' for n in SPRITE_ICONS) + '</div>'
    news = json.loads((SRC / "data/news.json").read_text())
    email = cfg.get("contact_email") or ""
    ctx = {"cfg": cfg, "counts": counts, "news": news, "version": version, "vars": {
        "org": e(cfg["org"]), "market_repo": e(cfg["market_repo"]), "iso_releases": e(cfg["iso_releases"]),
        "operator": e(cfg["operator"]), "updated_legal": e(cfg["updated_legal"]), "version": version,
        "contact_email_line": f' Or email <a href="mailto:{e(email)}">{e(email)}</a>.' if email else "",
        "quick_themes": quick_themes(themes), "themes_gallery": themes_gallery(themes, items), "sprite": sprite,
        "team": team_html(cfg.get("team", [])), "default_wall": wall_style(themes.get("aequalyn"))}}

    # pages
    for src in sorted((SRC / "pages").rglob("*.html")):
        raw = src.read_text()
        m = re.match(r"<!--meta (\{.*?\}) -->\n", raw)
        if not m:
            sys.exit(f"{src}: no <!--meta {{...}} --> line")
        rel = src.relative_to(SRC / "pages")
        path = "/" + str(rel).replace("index.html", "").replace("\\", "/")
        write(out, rel, page(raw[m.end():], json.loads(m.group(1)), ctx, path))
    # one page per news post
    posts = news_posts(news)
    for n, it in enumerate(posts):
        write(out, f"news/{it['slug']}/index.html",
              page(news_page(posts, n), {"title": f'{it["title"]} · News · Aequalyn', "description": it["body"][:155]}, ctx, it["url"]))
    # one page per item
    for it in items:
        related = [r for r in items if r["kind"] == it["kind"] and r["key"] != it["key"] and r.get("preview")]
        related = sorted(related, key=lambda r: (r["source"] != it["source"], r["name"]))[:3]
        meta = {"title": f'{it["name"]} · {KINDS[it["kind"]]} · Aequalyn', "description": it["about"] or f'{it["name"]} for Aequalyn',
                "scripts": ["item"], "image": it.get("preview") if it.get("media") == "image" else None}
        write(out, f"market/{it['kind']}/{it['id']}/index.html", page(item_body(it, related, cfg), meta, ctx, it["url"]))

    # the documentation
    dmeta = {"scripts": ["docs"]}
    write(out, "docs/index.html", page(docs_index(man, dpages), {**dmeta, "title": "Docs · Aequalyn",
          "description": "How to install, use, customise, publish to and build Aequalyn."}, ctx, "/docs/"))
    for n, pg in enumerate(dpages):
        desc = (pg["text"][:155].rsplit(" ", 1)[0] + "…") if len(pg["text"]) > 155 else pg["text"]
        html_out = page(docs_page(pg, man, dpages, n), {**dmeta, "title": f'{pg["title"]} · Docs · Aequalyn', "description": desc},
                        ctx, f"/docs/{pg['slug']}/")
        write(out, f"docs/{pg['slug']}/index.html", html_out.replace("\x01copy\x01", ICONS["copy"]))
    write(out, "data/docs-index.json", json.dumps([{"s": p["slug"], "t": p["title"], "g": p["section"],
          "h": [x[2] for x in p["toc"]], "x": p["text"][:4000]} for p in dpages], separators=(",", ":")))

    # data for the scripts
    public = [{k: v for k, v in i.items() if k != "palette"} for i in items]
    write(out, "data/catalog.json", json.dumps({"updated": market.get("updated", ""), "version": market.get("version"), "items": public}, separators=(",", ":")))
    write(out, "data/themes.json", json.dumps(themes, separators=(",", ":")))
    # assets, the API and the server's settings
    shutil.copytree(SRC / "assets", out / "assets")
    shutil.copytree(SRC / "api", out / "api", ignore=shutil.ignore_patterns("config.php", "stats.json", "salt.txt", "*.json"))
    shutil.copy(SRC / ".htaccess", out / ".htaccess")
    mark = ICONS["mark"].replace('class="mark" ', 'xmlns="http://www.w3.org/2000/svg" ').replace("currentColor", "#4fc1b0")
    write(out, "assets/img/favicon.svg", mark)
    base = cfg["url"].rstrip("/")
    urls = (["/", "/market/", "/themes/", "/docs/", "/news/", "/team/", "/contact/", "/privacy/", "/terms/"]
            + [f"/docs/{p['slug']}/" for p in dpages] + [p["url"] for p in posts] + [i["url"] for i in items])
    write(out, "sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
          + "".join(f"  <url><loc>{e(base + u)}</loc></url>\n" for u in urls) + "</urlset>\n")
    write(out, "robots.txt", f"User-agent: *\nAllow: /\nDisallow: /api/\nSitemap: {base}/sitemap.xml\n")
    print(f"built {len(items)} items ({counts['community']} community), {len(themes)} themes, {len(dpages)} docs pages into {out}")


if __name__ == "__main__":
    main()
