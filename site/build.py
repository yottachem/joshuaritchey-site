"""Build the site into site/dist from site/content (YAML) and site/templates (Jinja).
Pages: About (index.html), CV (cv.html), Data tools (tools.html), AI at work (ai.html), Operating Cadence overview (cadence.html). Usage: uv run python site/build.py"""
import html
import json
import re
import shutil
from datetime import date
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from markupsafe import Markup

HERE = Path(__file__).resolve().parent
CONTENT, TEMPLATES, STATIC, DIST = HERE / "content", HERE / "templates", HERE / "static", HERE / "dist"

# Shorter company names for the track-record strip on the About page.
SHORT = {"Bio-Rad Laboratories, Digital Biology Center": "Bio-Rad Laboratories", "E Ink Corporation": "E Ink"}


# Status chips for page copy: [[amber]] renders as a labeled chip whose color matches the status.
STATUS = {"red": "bad", "critical": "bad", "amber": "warn", "high": "warn", "re-check": "warn", "green": "good", "passes": "good"}


def rich(text):
    """Escape copy, then render **bold** and [[status]] chips. Color never carries meaning alone: the chip says the word."""
    out = html.escape(str(text))
    out = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", out)

    def chip(m):
        word = m.group(1).lower()
        if word not in STATUS:
            raise SystemExit(f"unknown status chip [[{m.group(1)}]] (use one of {', '.join(STATUS)})")
        return f'<span class="st {STATUS[word]}">{html.escape(m.group(1))}</span>'
    return Markup(re.sub(r"\[\[([A-Za-z-]+)\]\]", chip, out))


def span(start, end):
    if end == "present":
        return f"{start}–now"
    return str(start) if start == end else f"{start}–{end}"


SENTENCE = re.compile(r"(?<=[a-z0-9)*][.?])\s+(?=[A-Z])")


def lead(text):
    """First sentence of a paragraph. About shows it; the rest opens on tap."""
    return SENTENCE.split(str(text).strip(), maxsplit=1)[0]


def rest(text):
    parts = SENTENCE.split(str(text).strip(), maxsplit=1)
    return parts[1] if len(parts) > 1 else ""


def timeline(roles):
    """Year grid for the About career timeline: each role's titles as bar segments, end year inclusive."""
    now = date.today().year
    first = min(t["start"] for r in roles for t in r["titles"])
    cols = now - first + 1
    rows = []
    for r in roles:
        segs = []
        for t in sorted(r["titles"], key=lambda t: t["start"]):
            end = now if t["end"] == "present" else t["end"]
            segs.append({"title": t["title"], "years": t["years"], "c0": t["start"] - first + 1, "c1": end - first + 2})
        rows.append({"role": r, "segs": segs})
    ticks = [{"year": y, "col": y - first + 1} for y in range(first, now + 1) if y % 5 == 0]
    return {"cols": cols, "rows": rows, "ticks": ticks}


def load():
    career = yaml.safe_load((CONTENT / "career.yaml").read_text())
    site = yaml.safe_load((CONTENT / "site.yaml").read_text())
    site["ai"] = yaml.safe_load((CONTENT / "ai.yaml").read_text())
    site["cadence"] = yaml.safe_load((CONTENT / "cadence.yaml").read_text())
    for r in career["roles"]:
        for t in r["titles"]:
            t["years"] = span(t["start"], t["end"])
        starts = [t["start"] for t in r["titles"]]
        ends = [t["end"] for t in r["titles"]]
        r["years"] = span(min(starts), "present" if "present" in ends else max(ends))
        r["company_short"] = SHORT.get(r["company"], r["company"])
    return career, site


def tools(site):
    """Featured tools for the About page and tools grouped for tools.html, with checks."""
    dt = site["data_tools"]
    groups = {g["id"]: {**g, "items": []} for g in dt["groups"]}
    for t in dt["items"]:
        if t.get("group") not in groups:
            raise SystemExit(f'data tool {t["name"]!r} has no valid group (one of {", ".join(groups)})')
        groups[t["group"]]["items"].append(t)
    featured = [t for t in dt["items"] if t.get("featured")]
    if not 1 <= len(featured) <= 3:
        raise SystemExit(f"feature 1 to 3 data tools on the About page, not {len(featured)}")
    return featured, [g for g in groups.values() if g["items"]]


def person_ld(career, site):
    return json.dumps({
        "@context": "https://schema.org", "@type": "Person", "name": career["name"],
        "url": site["url"], "image": f'{site["url"]}/static/headshot.jpg', "sameAs": [career["linkedin"]],
        "jobTitle": "R&D and product development leader", "homeLocation": {"@type": "Place", "name": career["location"]},
        "alumniOf": [e["school"] for e in career["education"]],
    }).replace("</", "<\\/")


def main():
    career, site = load()
    env = Environment(loader=FileSystemLoader(TEMPLATES), undefined=StrictUndefined, autoescape=True)
    env.filters["rich"] = rich
    env.filters["lead"] = lead
    env.filters["rest"] = rest
    hero = site["hero"]
    headline = html.escape(hero["headline"])
    if hero.get("emphasis"):
        e = html.escape(hero["emphasis"])
        headline = headline.replace(e, f"<em>{e}</em>", 1)
    featured, groups = tools(site)
    common = dict(career=career, site=site, tl=timeline(career["roles"]), person_ld=person_ld(career, site), featured_tools=featured, tool_groups=groups)
    pages = {
        "index": dict(page_title=f'{career["short_name"]} · R&D and product development', canonical="",
                      page_description=site["description"], hero_headline=headline),
        "cv": dict(page_title=f'CV · {career["short_name"]}', canonical="cv.html",
                   page_description=f'Public CV of {career["name"]}: experience, recognition, patents, publications, education.'),
        "tools": dict(page_title=f'Data tools · {career["short_name"]}', canonical="tools.html",
                      page_description=f'Data tools by {career["name"]}: market trackers, technical references, and economics, with public code and data.'),
        "ai": dict(page_title=f'AI at work · {career["short_name"]}', canonical="ai.html",
                   page_description=f'How {career["name"]} puts AI to work in R&D leadership: rules decide, AI drafts, a person approves.',
                   ai=site["ai"], lane_names={l["id"]: l["chip"] for l in site["ai"]["lanes"]["items"]}),
        "cadence": dict(page_title=f'Operating Cadence · {career["short_name"]}', canonical="cadence.html",
                        page_description="Operating Cadence: seven leadership workflows for a small product team, where rules decide, AI drafts, and a person approves.",
                        cd=site["cadence"]),
    }
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()
    for name, ctx in pages.items():
        out = env.get_template(f"{name}.html").render(page=name, **common, **ctx)
        (DIST / f"{name}.html").write_text(out)
    shutil.copytree(STATIC, DIST / "static")
    (DIST / "robots.txt").write_text(f'User-agent: *\nAllow: /\nSitemap: {site["url"]}/sitemap.xml\n')
    urls = "".join(f'<url><loc>{site["url"]}/{p["canonical"]}</loc></url>' for p in pages.values())
    (DIST / "sitemap.xml").write_text(
        f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>\n')
    (DIST / ".nojekyll").write_text("")
    print(f"built {len(pages)} pages -> {DIST}")


if __name__ == "__main__":
    main()
