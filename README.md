# Dinossauros para Colorir — Dinosaur Coloring Pages (pt-BR)

A fast, fully static website that publishes free dinosaur coloring pages for Brazilian children, parents and teachers — plus an interactive **online coloring tool** that runs entirely in the browser.

**Live site:** https://dinossaurosparacolorir.vercel.app
**Domain:** dinossaurosparacolorir.com.br

![Python](https://img.shields.io/badge/Python-3.12-blue) ![Dependencies](https://img.shields.io/badge/generator%20dependencies-zero-brightgreen) ![Hosting](https://img.shields.io/badge/hosted%20on-Vercel-black)

## About the project

I built this project from scratch to give Portuguese-speaking families free, print-ready coloring pages without the slow, ad-heavy experience of typical WordPress sites. Instead of a CMS or a framework, I wrote a **custom static-site generator in pure Python (standard library only)** — content is stored as JSON, templates are plain HTML, and one command builds the complete site: posts, category pages, dinosaur fact sheets, legal pages, sitemap, robots.txt and an RSS feed.

The site currently covers 7 dinosaur collections (T-Rex, Triceratops, Velociraptor, Brachiosaurus, Stegosaurus, Spinosaurus and Pterodactyl), each with 10–20 coloring pages, and is growing toward 100 dinosaur types.

## Key features

- **Zero-dependency static generator** (`build.py`) — no WordPress, no build tools, no npm; Python stdlib only
- **Interactive online coloring tool** — a region-locked, bucket-fill painting tool (100% client-side, no backend) that automatically picks up every new post the generator publishes
- **Automated image pipeline** (`brand_*.py`, `seal_gaps.py`) — brands raw line art to a locked print spec (1344×1792 canvas, closed-region check so bucket-fill never leaks, WebP under 90 KB, print-ready US Letter PDFs, SVG sources via vtracer)
- **Deterministic QA gate** (`tools/qa_audit.py`) — audits every image before publishing: verifies no artwork touches the page border and checks fill consistency
- **SEO built in** — canonical URLs, Open Graph / Twitter cards, JSON-LD (`WebSite`, `BlogPosting`, `FAQPage`), semantic HTML5, lazy-loaded images with explicit dimensions (no layout shift)
- **Performance first** — fully static output deployed on Vercel; no database, no plugins, no server code

## Tech stack

| Area | Technology |
|---|---|
| Site generator | Python 3 (standard library only) |
| Content | JSON files in `content/posts/` and `content/pages/` |
| Templates | Plain HTML with a small custom `{{PLACEHOLDER}}` renderer |
| Styling | Hand-written CSS (no framework) |
| Image pipeline | Python, Pillow, NumPy, SciPy, vtracer |
| Hosting | Vercel (static) |

## Project structure

```
├── build.py            # static-site generator: content/ + templates/ -> dist/
├── config.py           # single source of truth for brand, domain, categories
├── brand_*.py          # per-collection image branding scripts (locked print spec)
├── seal_gaps.py        # seals tiny gaps in line art so online bucket-fill can't leak
├── tools/
│   └── qa_audit.py     # pre-publish QA audit for every coloring image
├── templates/          # base, home, category, post, page, online-coloring tool
├── content/
│   ├── posts/          # one JSON file per coloring collection
│   └── pages/          # legal pages, hubs and dinosaur fact sheets
├── static/             # copied verbatim to dist/ (CSS, favicon)
└── assets/             # published WebP / PDF / SVG coloring pages (see assets/README.md)
```

## Getting started

```bash
git clone https://github.com/joelseoserviceca-sketch/dinossauros-para-colorir.git
cd dinossauros-para-colorir
python3 build.py
```

Output:

- `dist/` — the complete static site, ready to deploy to any static host
- `releases/` — a timestamped ZIP of the build

The build validates every image referenced in the content files and warns about any missing asset.

## Adding a new coloring collection

1. Copy an existing file in `content/posts/` to a new slug and fill in the title, category, focus keyword, meta description, intro, sections (image + caption + alt text), tips and FAQs.
2. Add the branded WebP / PDF / SVG files under `assets/<slug>/`.
3. Run `python3 build.py` — the new collection appears on the site, in the category pages, in the sitemap **and** in the online coloring tool automatically.

## My role

I am the creator and sole maintainer of this project: I designed and wrote the generator, the templates and CSS, the image-branding and QA pipeline, all content structure and SEO, and I operate the publishing workflow and deployment.

## License

MIT — see [LICENSE](LICENSE). The coloring-page artwork itself is © Dinossauros para Colorir and is not covered by the code license.
