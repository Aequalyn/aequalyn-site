# aequalyn-site

The Aequalyn website: the desktop, its news, and the whole Market (plugins, themes,
wallpapers, apps, cursors and looks), each item with a page of its own. It looks like the
shell's Control Center and Store, and every built-in theme, night or day, can dress the site
from the palette button in the bar; the choice stays on from page to page.

## How it fits together

```
aequalyn-market  ── an item is approved ──▶  db/market.json   (the catalog)
       │                                          │
       └─ repository_dispatch "market-updated" ──▶ aequalyn-site Actions: tools/build.py
                                                      │  + aequalyn-themes (built-in themes, wallpapers)
                                                      │  + the docs of every repository
                                                      ▼
                                                   public/  ──▶  the web host
```

The site is static HTML, CSS and JavaScript, plus two small PHP scripts on the host: one
for the counters (views, hearts, copies of an install command, star ratings) and one for
the contact form. No database.

## The Market on the site

- Nine items to a page: three by three on a computer, one on a phone.
- Five views: **grid** and **list** (as on the Omarchy site), and three after Aequalyn's own
  pickers: **carousel** (the theme picker), **filmstrip** (the wallpaper picker) and
  **spotlight** (the layout picker's large preview beside its list).
- Filters for the kind, built in or community, night or day, and a search; sorting by
  featured, best rated, newest, hearts, copies, views or name. The address keeps
  the filters, so a filtered page can be shared.
- Ratings: one to five stars, one rating per visitor that can be changed or taken back, shown
  as an average with the count and how many gave each number of stars. "Best rated" uses a
  Bayesian average, so one five-star vote does not outrank twenty fours.

## News

Each post is an entry in `src/data/news.json` (`date`, `title`, a one- or two-sentence
`body`, and an optional `link`) and gets a page of its own at `/news/<slug>/`, the slug made
from its title unless the entry gives a `slug`. A longer post goes in `src/news/<slug>.md`,
in Markdown, shown on its page under the short text. The home page and `/news/` list the
posts and link to their pages.

## Build it

```bash
git clone --depth 1 https://github.com/Aequalyn/aequalyn-themes ../aequalyn-themes
python3 tools/build.py --themes ../aequalyn-themes        # writes public/
cd public && php -S 127.0.0.1:8080                        # a local preview, counters included
```

`--market` takes another catalog (a path or a URL), `--sources`
reads the documentation from a folder of Aequalyn checkouts instead of GitHub, `SITE_URL`
sets the address used in links and the sitemap, and `THEMES_CDN` replaces jsDelivr for the
theme pictures. Only Python's standard library is needed.
