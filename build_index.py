#!/usr/bin/env python3
"""
Build index.html for the my-insights GitHub Pages site.

Scans every *.html in the repo root (except index.html), pulls title / date /
TLDR with sensible fallbacks, and writes a dated, newest-first listing in the
Above the Fold house style. Standard library only, so the Action needs no pip.

Metadata precedence per file:
  title : <meta name="insight-title">  -> <title>            -> prettified filename
  date  : <meta name="insight-date">   -> date in filename   -> git last-commit date
  tldr  : <meta name="insight-tldr">   -> <meta description> -> ""

Exclude a file from the index with:
  <meta name="insight-publish" content="false">
"""

import html
import re
import subprocess
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
IGNORE = {"index.html"}

MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun",
     "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}


class MetaReader(HTMLParser):
    def __init__(self):
        super().__init__()
        self.metas = {}
        self._in_title = False
        self.title = ""

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "meta" and a.get("name") and a.get("content") is not None:
            self.metas[a["name"].lower()] = a["content"].strip()
        if tag == "title":
            self._in_title = True

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data


def read_file(path):
    r = MetaReader()
    try:
        r.feed(path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        pass
    return r.metas, r.title.strip()


def git_date(path):
    try:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%cs", "--", path.name],
            cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.strip()
        return out or None
    except Exception:
        return None


def date_from_name(name):
    # MMDDYYYY, e.g. 04302026
    m = re.search(r"(\d{2})(\d{2})(20\d{2})", name)
    if m:
        mm, dd, yy = m.groups()
        try:
            return datetime(int(yy), int(mm), int(dd)).date().isoformat()
        except ValueError:
            pass
    # monYYYY, e.g. apr2026
    m = re.search(r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)(20\d{2})",
                  name.lower())
    if m:
        return datetime(int(m.group(2)), MONTHS[m.group(1)], 1).date().isoformat()
    return None


def prettify(name):
    s = re.sub(r"\.html$", "", name)
    s = re.sub(r"^above_the_fold_", "", s)
    toks = s.split("_")
    drop = re.compile(
        r"^(v\d+|\d+|final|draft|\d{8}|"
        r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)20\d{2})$", re.I)
    while toks and drop.match(toks[-1]):
        toks.pop()
    out = " ".join(toks).strip()
    return out.title() if out else re.sub(r"\.html$", "", name)


def collect():
    rows = []
    for path in sorted(ROOT.glob("*.html")):
        if path.name in IGNORE:
            continue
        metas, title_tag = read_file(path)
        if metas.get("insight-publish", "").lower() == "false":
            continue

        title = metas.get("insight-title") or title_tag or prettify(path.name)
        date = (metas.get("insight-date")
                or date_from_name(path.name)
                or git_date(path)
                or "")
        tldr = metas.get("insight-tldr") or metas.get("description") or ""
        rows.append({"file": path.name, "title": title, "date": date, "tldr": tldr})

    rows.sort(key=lambda r: r["date"], reverse=True)
    return rows


def fmt_date(iso):
    if not iso:
        return "Undated"
    try:
        return datetime.fromisoformat(iso).strftime("%b %-d, %Y")
    except Exception:
        return iso


def year_of(iso):
    try:
        return datetime.fromisoformat(iso).year
    except Exception:
        return "Undated"


def render(rows):
    e = html.escape
    items = []
    last_year = object()
    for r in rows:
        y = year_of(r["date"])
        if y != last_year:
            items.append(f'<h2 class="year">{e(str(y))}</h2>')
            last_year = y
        tldr = f'<p class="tldr">{e(r["tldr"])}</p>' if r["tldr"] else ""
        items.append(
            f'<article class="item">'
            f'<div class="date">{e(fmt_date(r["date"]))}</div>'
            f'<div class="body">'
            f'<h3><a href="{e(r["file"])}">{e(r["title"])}</a></h3>'
            f'{tldr}'
            f'</div></article>'
        )
    listing = "\n".join(items)
    built = datetime.now().strftime("%b %-d, %Y, %-I:%M %p")
    count = len(rows)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Insights</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Frank+Ruhl+Libre:wght@500;700&family=Libre+Franklin:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  :root {{ --ink:#111; --muted:#666; --rule:#e6e6e6; --accent:#c00000; --col:720px; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:#fff; color:var(--ink);
    font-family:'Libre Franklin',sans-serif; line-height:1.55;
    -webkit-font-smoothing:antialiased; }}
  .wrap {{ max-width:var(--col); margin:0 auto; padding:64px 24px 96px; }}
  header {{ border-bottom:3px solid var(--ink); padding-bottom:20px; margin-bottom:8px; }}
  h1 {{ font-family:'Frank Ruhl Libre',serif; font-weight:700;
    font-size:44px; line-height:1.05; margin:0; letter-spacing:-0.01em; }}
  .sub {{ color:var(--muted); font-size:14px; margin-top:10px; }}
  .sub b {{ color:var(--accent); font-weight:600; }}
  h2.year {{ font-family:'Libre Franklin',sans-serif; font-weight:600;
    font-size:13px; text-transform:uppercase; letter-spacing:0.12em;
    color:var(--muted); margin:48px 0 0; padding-bottom:8px;
    border-bottom:1px solid var(--rule); }}
  .item {{ display:grid; grid-template-columns:120px 1fr; gap:24px;
    padding:22px 0; border-bottom:1px solid var(--rule); }}
  .date {{ color:var(--muted); font-size:13px; font-variant-numeric:tabular-nums;
    padding-top:4px; }}
  .body h3 {{ font-family:'Frank Ruhl Libre',serif; font-weight:500;
    font-size:22px; line-height:1.25; margin:0 0 6px; }}
  .body h3 a {{ color:var(--ink); text-decoration:none;
    background-image:linear-gradient(var(--accent),var(--accent));
    background-size:0% 2px; background-repeat:no-repeat;
    background-position:0 100%; transition:background-size .2s ease; }}
  .body h3 a:hover {{ background-size:100% 2px; color:var(--accent); }}
  .tldr {{ margin:0; color:#333; font-size:15px; }}
  footer {{ margin-top:56px; color:var(--muted); font-size:12px; }}
  @media (max-width:560px) {{
    h1 {{ font-size:34px; }}
    .item {{ grid-template-columns:1fr; gap:4px; }}
    .date {{ padding-top:0; }}
  }}
</style>
</head>
<body>
  <div class="wrap">
    <header>
      <h1>Insights</h1>
      <div class="sub"><b>{count}</b> reports &nbsp;&middot;&nbsp; rebuilt {built}</div>
    </header>
    {listing}
    <footer>Auto-generated from the repository on every push.</footer>
  </div>
</body>
</html>
"""


def main():
    rows = collect()
    (ROOT / "index.html").write_text(render(rows), encoding="utf-8")
    print(f"Wrote index.html with {len(rows)} entries.")


if __name__ == "__main__":
    main()
