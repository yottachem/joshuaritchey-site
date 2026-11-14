"""Build the site into site/dist from site/content (YAML) and site/templates (Jinja).
Pages: About (index.html), CV (cv.html), Data tools (tools.html). Usage: uv run python site/build.py"""
import html
import json
import shutil
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined

HERE = Path(__file__).resolve().parent
CONTENT, TEMPLATES, STATIC, DIST = HERE / "content", HERE / "templates", HERE / "static", HERE / "dist"

# Shorter company names for the track-record strip on the About page.
SHORT = {"Bio-Rad Laboratories, Digital Biology Center": "Bio-Rad Laboratories", "E Ink Corporation": "E Ink"}


def span(start, end):
    if end == "present":
        return f"{start}–now"
    return str(start) if start == end else f"{start}–{end}"


def load():
    career = yaml.safe_load((CONTENT / "career.yaml").read_text())
    site = yaml.safe_load((CONTENT / "site.yaml").read_text())
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
    hero = site["hero"]
    headline = html.escape(hero["headline"])
    if hero.get("emphasis"):
        e = html.escape(hero["emphasis"])
        headline = headline.replace(e, f"<em>{e}</em>", 1)
    featured, groups = tools(site)
    common = dict(career=career, site=site, person_ld=person_ld(career, site), featured_tools=featured, tool_groups=groups)
    pages = {
        "index": dict(page_title=f'{career["short_name"]} · R&D and product development', canonical="",
                      page_description=site["description"], hero_headline=headline),
        "cv": dict(page_title=f'CV · {career["short_name"]}', canonical="cv.html",
                   page_description=f'Public CV of {career["name"]}: experience, recognition, patents, publications, education.'),
        "tools": dict(page_title=f'Data tools · {career["short_name"]}', canonical="tools.html",
                      page_description=f'Data tools by {career["name"]}: market trackers, technical references, and economics, with public code and data.'),
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
