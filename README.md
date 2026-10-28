# joshuaritchey.com

Personal site for Joshua A. Ritchey, Ph.D. Static pages built from YAML content and Jinja templates, deployed to GitHub Pages on every push to `main`.

## Layout

| Path | What it holds |
|------|---------------|
| `site/content/career.yaml` | Public CV facts: roles, years, highlights, recognition, patents, publications, education |
| `site/content/site.yaml` | Page copy (hero, capabilities, data tools, contact) and settings (analytics token) |
| `site/templates/` | `base.html` (shared head, nav, footer, theme tokens), `index.html` (About), `cv.html` (public CV) |
| `site/static/` | Headshot and favicon |
| `site/build.py` | Renders `site/dist/` with pages, sitemap.xml, robots.txt |

## Build locally

```sh
uv run python site/build.py
open site/dist/index.html
```

## Content rules

The CV here is a public summary, not the full CV:

- Years only for roles; no degree years
- No phone number, street, or town (location is "Greater Boston")
- No raw email address in the HTML; the contact alias is assembled in the browser
- Public metrics only; no customer names or internal figures
