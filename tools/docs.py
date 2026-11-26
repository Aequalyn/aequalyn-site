"""The documentation: pages put together from the Aequalyn repositories' own Markdown.

src/docs/manifest.json lists the sections and their pages; each page is made of parts, a
file in src/docs/ or a file (or one ## section of it) of a repository. The parts are fetched
at their newest commit, turned into HTML by the small Markdown renderer below (GitHub's
flavour, as far as these files use it) and wrapped in the docs layout by build.py.
"""
import html
import json
import re
import urllib.request
from pathlib import Path

e = html.escape
RAW = "https://raw.githubusercontent.com/{org}/{repo}/main/{path}"
BLOB = "https://github.com/{org}/{repo}/blob/main/{path}"
TREE = "https://github.com/{org}/{repo}/tree/main/{path}"


# ------------------------------------------------------------------ sources
class Sources:
    """reads repository files from local checkouts (--sources) or from GitHub"""

    def __init__(self, org, local=None):
        self.org, self.local, self.cache = org, Path(local) if local else None, {}

    def read(self, repo, path):
        k = (repo, path)
        if k not in self.cache:
            if self.local and (self.local / repo / path).is_file():
                self.cache[k] = (self.local / repo / path).read_text()
            else:
                url = RAW.format(org=self.org, repo=repo, path=path)
                req = urllib.request.Request(url, headers={"User-Agent": "aequalyn-site-build"})
                with urllib.request.urlopen(req, timeout=30) as r:
                    self.cache[k] = r.read().decode("utf-8")
        return self.cache[k]


def split_sections(text):
    """{"_intro": lines before the first ##, "Heading": the lines of that ## section}"""
    out, cur, fence = {"_intro": []}, "_intro", False
    for line in text.splitlines():
        if re.match(r"^\s*(```|~~~)", line):
            fence = not fence
        m = None if fence else re.match(r"^## +(.+?)\s*#*\s*$", line)
        if m:
            cur = m.group(1).strip()
            out[cur] = []
        out[cur].append(line)
    return out


def drop_title(lines):
    """the page has its own title: leave out a leading # or ## heading of a part"""
    i = 0
    while i < len(lines) and not lines[i].strip():
        i += 1
    if i < len(lines) and re.match(r"^#{1,2} ", lines[i]):
        return lines[i + 1:]
    return lines


def demote_h1(lines):
    fence, out = False, []
    for line in lines:
        if re.match(r"^\s*(```|~~~)", line):
            fence = not fence
        out.append("#" + line if not fence and re.match(r"^# ", line) else line)
    return out


# ----------------------------------------------------------------- markdown
def slugify(s):
    s = re.sub(r"<[^>]+>", "", s)
    s = re.sub(r"[^\w\s-]", "", s.lower()).strip()
    return re.sub(r"[\s]+", "-", s) or "section"


SAFE_TAGS = r"kbd|br|sub|sup|b|i|em|strong|small|mark"


def inline(text, link):
    """code spans, links, images, emphasis; everything else is escaped"""
    codes = []

    def keep_code(m):
        codes.append(f"<code>{e(m.group(2))}</code>")
        return f"\x00{len(codes) - 1}\x00"
    text = re.sub(r"(`+)(.+?)\1", keep_code, text)
    text = e(text, quote=False)
    text = re.sub(rf"&lt;(/?)({SAFE_TAGS})\s*/?&gt;", r"<\1\2>", text)
    text = re.sub(r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+&quot;[^&]*&quot;)?\)",
                  lambda m: f'<img src="{e(link(m.group(2), True))}" alt="{m.group(1)}" loading="lazy">', text)
    text = re.sub(r"\[([^\]]+)\]\(([^)\s]+)(?:\s+&quot;[^&]*&quot;)?\)",
                  lambda m: f'<a href="{e(link(m.group(2), False))}">{m.group(1)}</a>', text)
    text = re.sub(r"&lt;(https?://[^\s&]+)&gt;", r'<a href="\1">\1</a>', text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", text)
    text = re.sub(r"(?<![\w])_(?!\s)(.+?)(?<!\s)_(?![\w])", r"<em>\1</em>", text)
    text = re.sub(r"~~(.+?)~~", r"<del>\1</del>", text)
    return re.sub(r"\x00(\d+)\x00", lambda m: codes[int(m.group(1))], text)


def render(md, link):
    """Markdown to HTML; returns (html, [(level, id, text)]) for the table of contents"""
    lines = md.splitlines()
    out, toc, ids = [], [], {}
    i = 0

    def heading_id(t):
        base = slugify(t)
        n = ids.get(base, 0)
        ids[base] = n + 1
        return base if n == 0 else f"{base}-{n}"

    def para(buf):
        if buf:
            out.append("<p>" + inline(" ".join(s.strip() for s in buf), link) + "</p>")

    def list_block(start):
        """a list and its nested lists, by indentation"""
        j, items = start, []
        base = len(lines[start]) - len(lines[start].lstrip())
        ordered = bool(re.match(r"^\s*\d+[.)]\s", lines[start]))
        while j < len(lines):
            ln = lines[j]
            ind = len(ln) - len(ln.lstrip())
            m = re.match(r"^\s*([-*+]|\d+[.)])\s+(.*)$", ln)
            if m and ind == base:
                items.append([m.group(2)])
                j += 1
            elif ln.strip() and items and ind > base:
                if re.match(r"^\s*([-*+]|\d+[.)])\s+", ln):
                    sub, j = list_block(j)
                    items[-1].append(sub)
                else:
                    items[-1].append(ln.strip())
                    j += 1
            elif not ln.strip() and j + 1 < len(lines) and (len(lines[j + 1]) - len(lines[j + 1].lstrip()) > base or
                                                           re.match(rf"^\s{{{base}}}([-*+]|\d+[.)])\s", lines[j + 1])):
                j += 1
            else:
                break
        tag = "ol" if ordered else "ul"
        body = ""
        for it in items:
            texts = [x for x in it if isinstance(x, str)]
            subs = "".join(x for x in it if not isinstance(x, str))
            task = re.match(r"^\[([ xX])\]\s+", texts[0]) if texts else None
            first = texts[0][task.end():] if task else (texts[0] if texts else "")
            box = (f'<input type="checkbox" disabled {"checked" if task.group(1).lower() == "x" else ""}> ' if task else "")
            body += f"<li>{box}{inline(' '.join([first] + texts[1:]), link)}{subs}</li>"
        return f"<{tag}>{body}</{tag}>", j

    buf = []
    while i < len(lines):
        ln = lines[i]
        fence = re.match(r"^\s*(```|~~~)\s*([\w+-]*)", ln)
        if fence:
            para(buf); buf = []
            mark, lang, code = fence.group(1), fence.group(2), []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith(mark):
                code.append(lines[i]); i += 1
            i += 1
            cls = f' class="lang-{e(lang)}"' if lang else ""
            out.append(f'<div class="code"><pre><code{cls}>{e(chr(10).join(code))}</code></pre>'
                       f'<button class="icon-btn copy-code" type="button" aria-label="Copy">\x01copy\x01</button></div>')
            continue
        h = re.match(r"^(#{1,6})\s+(.+?)\s*#*\s*$", ln)
        if h:
            para(buf); buf = []
            lvl = len(h.group(1))
            txt = inline(h.group(2), link)
            hid = heading_id(re.sub(r"<[^>]+>", "", txt))
            if lvl in (2, 3):
                toc.append((lvl, hid, re.sub(r"<[^>]+>", "", txt)))
            out.append(f'<h{lvl} id="{hid}"><a class="anchor" href="#{hid}" aria-hidden="true">#</a>{txt}</h{lvl}>')
            i += 1
            continue
        if re.match(r"^\s*\|.*\|\s*$", ln) and i + 1 < len(lines) and re.match(r"^\s*\|?\s*:?-{2,}", lines[i + 1]):
            para(buf); buf = []
            row = lambda s: [c.strip() for c in re.split(r"(?<!\\)\|", s.strip().strip("|"))]
            head = row(ln)
            aligns = ["right" if c.endswith(":") and not c.startswith(":") else "center" if c.startswith(":") and c.endswith(":") else ""
                      for c in row(lines[i + 1])]
            i += 2
            rows = []
            while i < len(lines) and re.match(r"^\s*\|.*\|\s*$", lines[i]):
                rows.append(row(lines[i])); i += 1
            st = lambda n: f' style="text-align:{aligns[n]}"' if n < len(aligns) and aligns[n] else ""
            th = "".join(f"<th{st(n)}>{inline(c.replace(chr(92) + '|', '|'), link)}</th>" for n, c in enumerate(head))
            tb = "".join("<tr>" + "".join(f"<td{st(n)}>{inline(c.replace(chr(92) + '|', '|'), link)}</td>" for n, c in enumerate(r)) + "</tr>" for r in rows)
            empty_head = not any(head)
            out.append(f'<div class="table"><table>{"" if empty_head else f"<thead><tr>{th}</tr></thead>"}<tbody>{tb}</tbody></table></div>')
            continue
        if re.match(r"^\s*\|.*\|\s*$", ln):
            # rows with no delimiter line under them: the READMEs use them to set
            # screenshots side by side, so they become a row of pictures
            para(buf); buf = []
            rows = []
            while i < len(lines) and re.match(r"^\s*\|.*\|\s*$", lines[i]):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")]); i += 1
            tb = "".join("<tr>" + "".join(f"<td>{inline(c, link)}</td>" for c in r) + "</tr>" for r in rows)
            out.append(f'<div class="table gallery"><table><tbody>{tb}</tbody></table></div>')
            continue
        if re.match(r"^\s*>", ln):
            para(buf); buf = []
            quote = []
            while i < len(lines) and re.match(r"^\s*>", lines[i]):
                quote.append(re.sub(r"^\s*>\s?", "", lines[i])); i += 1
            inner, sub = render("\n".join(quote), link)
            note = re.match(r"^<p>\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]\s*", inner)
            if note:
                inner = "<p>" + inner[note.end():]
            out.append(f'<blockquote class="{"note " + note.group(1).lower() if note else ""}">{inner}</blockquote>')
            continue
        if re.match(r"^\s*([-*+]|\d+[.)])\s+", ln) and not re.match(r"^\s*([-*_])(\s*\1){2,}\s*$", ln):
            para(buf); buf = []
            block, i = list_block(i)
            out.append(block)
            continue
        if re.match(r"^\s*([-*_])(\s*\1){2,}\s*$", ln):
            para(buf); buf = []
            out.append("<hr>")
            i += 1
            continue
        if re.match(r"^\s*<(/?)(p|div|details|summary|img|picture|table|br|h\d|center)\b", ln, re.I):
            para(buf); buf = []
            block = []
            while i < len(lines) and lines[i].strip():
                block.append(lines[i]); i += 1
            raw = "\n".join(block)
            # images and links inside raw HTML get the same treatment as Markdown ones
            raw = re.sub(r'(src|href)="([^"]+)"', lambda m: f'{m.group(1)}="{e(link(m.group(2), m.group(1) == "src"))}"', raw)
            out.append(re.sub(r"<(script|style|iframe)[^>]*>.*?</\1>", "", raw, flags=re.S | re.I))
            continue
        if not ln.strip():
            para(buf); buf = []
            i += 1
            continue
        buf.append(ln)
        i += 1
    para(buf)
    return "\n".join(out), toc


# ------------------------------------------------------------------- pages
def load(src_dir, org, local=None):
    """every page of the manifest, rendered: [{slug, title, section, html, toc, sources, text}]"""
    man = json.loads((src_dir / "manifest.json").read_text())
    srcs = Sources(org, local)
    # a whole repository file that is a page here: links to it go to that page
    page_of = {}
    for sec in man["sections"]:
        for pg in sec["pages"]:
            for part in pg["parts"]:
                if ":" in part and not part.startswith("local:") and "#" not in part:
                    page_of[tuple(part.split(":", 1))] = pg["slug"]
    pages = []
    for sec in man["sections"]:
        for pg in sec["pages"]:
            chunks, sources = [], []
            for n, part in enumerate(pg["parts"]):
                where, _, section = part.partition("#")
                kind, _, path = where.partition(":")
                if kind == "local":
                    lines = (src_dir / path).read_text().splitlines()
                    repo = None
                else:
                    repo = kind
                    text = srcs.read(repo, path)
                    if section:
                        secs = split_sections(text)
                        if section not in secs:
                            raise SystemExit(f"docs: {repo}/{path} has no section '## {section}' (page {pg['slug']})")
                        lines = secs[section]
                    else:
                        lines = text.splitlines()
                    sources.append({"repo": repo, "path": path, "section": section or "",
                                    "url": BLOB.format(org=org, repo=repo, path=path)})
                if n == 0 or kind == "local" or section in ("", "_intro"):
                    lines = drop_title(lines)
                lines = demote_h1(lines)
                chunks.append((repo, path, "\n".join(lines)))
            body, toc = [], []
            ids_seen = set()
            for repo, path, md in chunks:
                link = linker(org, repo, path, page_of)
                h, t = render(md, link)
                body.append(h)
                for item in t:
                    if item[1] not in ids_seen:
                        ids_seen.add(item[1]); toc.append(item)
            html_out = "\n".join(body)
            text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(html_out))).strip()
            pages.append({"slug": pg["slug"], "title": pg["title"], "section": sec["title"], "icon": sec.get("icon", ""),
                          "html": html_out, "toc": toc, "sources": sources, "text": text})
    return man, pages


def linker(org, repo, path, page_of):
    """where a link or picture in a repository file points once it is on the site"""
    base = path.rsplit("/", 1)[0] if "/" in path else ""

    def link(href, image):
        if re.match(r"^(https?:|mailto:|#|/)", href) or repo is None:
            return href
        target, _, frag = href.partition("#")
        parts = []
        for p in (base + "/" + target if base else target).split("/"):
            if p in ("", "."):
                continue
            if p == "..":
                if parts:
                    parts.pop()
                continue
            parts.append(p)
        rel = "/".join(parts)
        if not image and (repo, rel) in page_of:
            return f"/docs/{page_of[(repo, rel)]}/" + (f"#{frag}" if frag else "")
        if image:
            return RAW.format(org=org, repo=repo, path=rel)
        url = (TREE if not re.search(r"\.[A-Za-z0-9]+$", rel) else BLOB).format(org=org, repo=repo, path=rel)
        return url + (f"#{frag}" if frag else "")
    return link
