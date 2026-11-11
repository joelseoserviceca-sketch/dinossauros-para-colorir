#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gerador de site estático — blog de dinossauros para colorir (pt-BR).

Uso:  python3 build.py
Saída: dist/ (site pronto) + releases/*.zip (pronto para deploy)

Zero dependências externas: só biblioteca padrão do Python.
"""

import json
import shutil
import zipfile
from datetime import date, datetime
from pathlib import Path

import config

ROOT = Path(__file__).resolve().parent
TPL_DIR = ROOT / "templates"
POSTS_DIR = ROOT / "content" / "posts"
PAGES_DIR = ROOT / "content" / "pages"
STATIC_DIR = ROOT / "static"
ASSETS_DIR = ROOT / "assets"
DIST = ROOT / "dist"
RELEASES = ROOT / "releases"

MESES = ["", "janeiro", "fevereiro", "março", "abril", "maio", "junho",
         "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]

missing_assets = []  # avisos de imagens referenciadas mas ausentes


# ---------------------------------------------------------------- templates
def load_template(name):
    return (TPL_DIR / name).read_text(encoding="utf-8")


def render(name, ctx):
    """Substitui {{CHAVE}} pelo valor em ctx. Sem dependências.

    Múltiplas passadas: valores (ex. BODY) podem conter placeholders
    (ex. {{ROOT_PATH}}) que só existem no texto após a primeira passada.
    """
    text = load_template(name)
    for _ in range(5):
        new = text
        for key, value in ctx.items():
            new = new.replace("{{" + key + "}}", str(value))
        if new == text:
            break
        text = new
    return text


def base_ctx(**extra):
    """Contexto global: marca, URLs, ano."""
    ctx = {
        "SITE_NAME": config.SITE_NAME,
        "SITE_TAGLINE": config.SITE_TAGLINE,
        "SITE_DOMAIN": config.SITE_DOMAIN,
        "BASE_URL": config.BASE_URL,
        "CONTACT_EMAIL": config.CONTACT_EMAIL,
        "YEAR": str(date.today().year),
        "EXTRA_HEAD": "",
        "OG_IMAGE": "",
    }
    ctx.update(extra)
    return ctx


# ------------------------------------------------------------------ helpers
def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def parse_date(iso):
    y, m, d = (int(x) for x in iso.split("-"))
    return date(y, m, d)


def date_long(iso):
    d = parse_date(iso)
    return f"{d.day} de {MESES[d.month]} de {d.year}"


def rel_parts_to_url(parts):
    """['desenhos','x','index.html'] -> 'desenhos/x/' (ou '' p/ home)."""
    if parts == ["index.html"]:
        return ""
    return "/".join(parts[:-1]) + "/"


SECTION_LABELS = {
    "dinossauros": "Dinossauros",
    "desenhos": "Desenhos para Colorir",
    "categoria": "Desenhos para Colorir",
    "colorir-online": "Colorir Online",
    "curiosidades": "Curiosidades",
    "atividades": "Atividades",
}


def breadcrumb(url_parts, title, root_path):
    """Migalha de pão. url_parts: segmentos sem 'index.html', ex. ['dinossauros','triceratops']."""
    home = root_path or "./"
    crumbs = [f'<a href="{home}">Início</a>']
    for i, seg in enumerate(url_parts):
        if i < len(url_parts) - 1:
            href = root_path + "/".join(url_parts[: i + 1]) + "/"
            label = SECTION_LABELS.get(seg, seg.replace("-", " ").title())
            crumbs.append(f'<a href="{href}">{label}</a>')
        else:
            crumbs.append(title)
    return ('<nav class="breadcrumbs" aria-label="Você está aqui">\n  '
            + " ›\n  ".join(crumbs) + "\n</nav>")


def write_page(parts, html):
    out = DIST.joinpath(*parts)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")


def page_shell(parts, page_title, meta_desc, content_html,
               og_type="website", og_title=None, og_desc=None,
               extra_head="", og_image=""):
    url_path = rel_parts_to_url(parts)
    depth = len(parts) - 1  # nº de diretórios até a raiz
    root_path = "../" * depth
    ctx = base_ctx(
        PAGE_TITLE=f"{page_title} | {config.SITE_NAME}",
        META_DESCRIPTION=meta_desc,
        CANONICAL_URL=config.BASE_URL + "/" + url_path,
        ROOT_PATH=root_path,
        CONTENT=content_html,
        OG_TYPE=og_type,
        OG_TITLE=og_title or page_title,
        OG_DESCRIPTION=og_desc or meta_desc,
        EXTRA_HEAD=extra_head,
        OG_IMAGE=(f'<meta property="og:image" content="{og_image}">'
                  if og_image else ""),
    )
    return render("base.html", ctx)


# -------------------------------------------------------------------- cards
def post_card(post, root_path):
    url = f"{root_path}desenhos/{post['slug']}/"
    return (f'<article class="card">\n'
            f'  <h3><a href="{url}">{post["title"]}</a></h3>\n'
            f'  <p>{post["meta_description"]}</p>\n'
            f'</article>')


# -------------------------------------------------------------------- posts
def section_html(post, sec, root_path):
    slug = post["slug"]
    webp = f"{root_path}assets/{slug}/{sec['image']}.webp"
    pdf = f"{root_path}assets/{slug}/{sec['image']}.pdf"
    for ext in ("webp", "pdf"):
        if not (ASSETS_DIR / slug / f"{sec['image']}.{ext}").exists():
            missing_assets.append(f"{slug}/{sec['image']}.{ext}")
    online_url = f"{root_path}colorir-online/{slug}/{sec['image']}/"
    return (
        f"<section>\n"
        f"  <h2>{sec['heading']}</h2>\n"
        f"  {sec.get('text', '')}\n"
        f"  <figure>\n"
        f'    <img src="{webp}" alt="{sec["alt"]}" loading="lazy" '
        f'width="{config.IMAGE_WIDTH}" height="{config.IMAGE_HEIGHT}">\n'
        f"    <figcaption>{sec['caption']}</figcaption>\n"
        f"  </figure>\n"
        f'  <div class="img-actions">\n'
        f'    <a class="btn btn-pdf" href="{pdf}" download>Baixar PDF</a>\n'
        f'    <a class="btn btn-online" href="{online_url}">Colorir Online</a>\n'
        f"  </div>\n"
        f"</section>"
    )


def build_post(post, all_posts, root_path_unused=None):
    parts = ["desenhos", post["slug"], "index.html"]
    root_path = "../../"

    sections = "\n\n".join(
        section_html(post, s, root_path) for s in post["sections"])

    tips = "\n".join(
        f'      <li><strong>{t["title"]}:</strong> {t["text"]}</li>'
        for t in post["tips"])

    faqs_html = "\n".join(
        f'    <details>\n      <summary>{f["q"]}</summary>\n'
        f'      <p>{f["a"]}</p>\n    </details>'
        for f in post["faqs"])

    # JSON-LD: BlogPosting + FAQPage
    post_url = config.BASE_URL + f"/desenhos/{post['slug']}/"
    blogposting = {
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        "headline": post["title"],
        "description": post["meta_description"],
        "inLanguage": "pt-BR",
        "datePublished": post["date"],
        "author": {"@type": "Organization", "name": config.SITE_NAME},
        "publisher": {"@type": "Organization", "name": config.SITE_NAME},
        "mainEntityOfPage": {"@type": "WebPage", "@id": post_url},
    }
    faqpage = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": f["q"],
             "acceptedAnswer": {"@type": "Answer", "text": f["a"]}}
            for f in post["faqs"]
        ],
    }
    extra_head = (
        '<script type="application/ld+json">\n'
        + json.dumps(blogposting, ensure_ascii=False, indent=2)
        + '\n</script>\n<script type="application/ld+json">\n'
        + json.dumps(faqpage, ensure_ascii=False, indent=2)
        + "\n</script>"
    )

    related = [p for p in all_posts
               if p["slug"] != post["slug"]
               and p["category"]["slug"] == post["category"]["slug"]][:6]
    related_html = ""
    if related:
        cards = "\n".join(post_card(p, root_path) for p in related)
        related_html = (
            '  <section class="related" aria-labelledby="rel">\n'
            '    <h2 id="rel">Você também pode gostar</h2>\n'
            '    <div class="cards">\n' + cards + "\n    </div>\n  </section>"
        )

    content = render("post.html", base_ctx(
        ROOT_PATH=root_path,
        TITLE=post["title"],
        DATE_ISO=post["date"],
        DATE_LONG=date_long(post["date"]),
        CATEGORY_NAME=post["category"]["name"],
        CATEGORY_SLUG=post["category"]["slug"],
        INTRO=post["intro"],
        SECTIONS=sections,
        TIPS=tips,
        FAQS=faqs_html,
        RELATED=related_html,
    ))
    html = page_shell(
        parts, post["title"], post["meta_description"], content,
        og_type="article",
        extra_head=extra_head,
        og_image=(config.BASE_URL + f"/assets/{post['slug']}/"
                  f"{post['sections'][0]['image']}.webp"
                  if post.get("sections") else ""),
    )
    write_page(parts, html)
    return post_url, post["date"]


# --------------------------------------------------------------- categorias
def build_category(cat_slug, cat_name, posts, intro=""):
    parts = ["categoria", cat_slug, "index.html"]
    root_path = "../../"
    if posts:
        cards = "\n".join(post_card(p, root_path) for p in posts)
    else:
        cards = ('<p class="empty-note">Estamos preparando novos desenhos! '
                 'Volte em breve ou <a href="../../desenhos/">veja todos os '
                 "desenhos</a>.</p>")
    if not intro:
        intro = (f"Todos os nossos desenhos de {cat_name.lower()} para "
                 f"colorir: grátis para imprimir em PDF.")
    content = render("category.html", base_ctx(
        ROOT_PATH=root_path,
        CATEGORY_NAME=cat_name,
        CATEGORY_INTRO=intro,
        POST_CARDS=cards,
    ))
    title = f"{cat_name} para Colorir"
    meta = (f"Desenhos de {cat_name.lower()} para colorir grátis. "
            f"Imprima desenhos de dinossauros para colorir em PDF.")
    html = page_shell(parts, title, meta, content)
    write_page(parts, html)
    return config.BASE_URL + f"/categoria/{cat_slug}/"


# -------------------------------------------------------------------- home
def build_home(posts, categories):
    parts = ["index.html"]
    root_path = ""
    cards = "\n".join(post_card(p, root_path) for p in posts[:6])

    # círculos de categoria: primeira imagem do primeiro post da categoria
    posts_por_cat = {}
    for p in posts:
        posts_por_cat.setdefault(p["category"]["slug"], []).append(p)

    def primeira_imagem(post):
        s = post["sections"][0]
        return f"assets/{post['slug']}/{s['image']}.webp", s["alt"]

    circulos = []
    # imagens de reserva distintas para categorias ainda sem posts
    todas_imgs = []
    for p in posts:
        for s in p.get("sections", []):
            todas_imgs.append((f"assets/{p['slug']}/{s['image']}.webp",
                               s["alt"]))
    usadas = set()
    for c in categories:
        thumb, alt = None, f"Desenhos de {c['name']} para colorir"
        for p in posts_por_cat.get(c["slug"], []):
            if p.get("sections"):
                thumb, alt = primeira_imagem(p)
                break
        if not thumb:
            for t_img, t_alt in todas_imgs:
                if t_img not in usadas:
                    thumb, alt = t_img, t_alt
                    break
            if not thumb and todas_imgs:
                thumb, alt = todas_imgs[0]
        usadas.add(thumb)
        circulos.append(
            f'    <li><a href="{root_path}categoria/{c["slug"]}/">'
            f'<img src="{root_path}{thumb}" alt="{alt}" loading="lazy" '
            f'width="208" height="208"><span>{c["name"]}</span></a></li>')
    circulos_html = "\n".join(circulos)

    # grade de desenhos populares: 8 primeiros de todos os posts
    grade = []
    for post in posts:
        for sec in post.get("sections", []):
            webp = f"assets/{post['slug']}/{sec['image']}.webp"
            pdf = f"assets/{post['slug']}/{sec['image']}.pdf"
            online = f"colorir-online/{post['slug']}/{sec['image']}/"
            grade.append(
                f'    <article class="desenho-card">\n'
                f'      <a href="{root_path}desenhos/{post["slug"]}/" '
                f'aria-label="{sec["alt"]}">'
                f'<img src="{root_path}{webp}" alt="{sec["alt"]}" '
                f'loading="lazy" width="400" height="533"></a>\n'
                f'      <div class="dc-corpo">\n'
                f'        <h3><a href="{root_path}desenhos/{post["slug"]}/">'
                f'{sec["heading"]}</a></h3>\n'
                f'        <div class="dc-acoes">\n'
                f'          <a class="pdf" href="{root_path}{pdf}" '
                f'download>🖨️ PDF</a>\n'
                f'          <a class="online" href="{root_path}{online}">'
                f'🖌️ Online</a>\n'
                f'        </div>\n'
                f'      </div>\n'
                f'    </article>')
            if len(grade) >= 8:
                break
        if len(grade) >= 8:
            break
    grade_html = "\n".join(grade)

    # FAQ da home (SEO)
    faqs_home = [
        ("Os desenhos para colorir são realmente grátis?",
         "Sim! Todos os desenhos para colorir do site são 100% grátis. "
         "Você pode baixar o PDF, imprimir quantas vezes quiser e pintar "
         "online no navegador, sem cadastro e sem pagar nada."),
        ("Como funciona o Colorir Online?",
         "É o nosso estúdio de pintura no navegador: escolha um desenho, "
         "use o balde, o pincel, o lápis ou o spray — a tinta nunca sai da "
         "área do desenho — e baixe sua arte em PNG ou imprima na hora."),
        ("Posso usar os desenhos na escola ou na festa de aniversário?",
         "Pode! Os desenhos são liberados para uso educacional e pessoal: "
         "sala de aula, lição de casa, festa de aniversário de dinossauro "
         "e atividades em família."),
        ("Quais dinossauros têm desenhos para colorir?",
         "Tiranossauro Rex, Triceratops, Velociraptor, Braquiossauro, "
         "Estegossauro, Pterossauro e dinossauros bebês — e adicionamos "
         "desenhos novos todos os dias."),
        ("Como imprimo com boa qualidade?",
         "Clique em Baixar PDF no desenho escolhido: o arquivo é em alta "
         "resolução, pronto para imprimir em tamanho A4 com traços nítidos."),
    ]
    faq_home_html = "\n".join(
        f'    <details>\n      <summary>{q}</summary>\n'
        f'      <p>{a}</p>\n    </details>'
        for q, a in faqs_home)

    # índice de busca client-side
    indice = []
    for p in posts:
        indice.append({
            "t": p["title"],
            "u": f"{root_path}desenhos/{p['slug']}/",
            "k": p["focus_keyword"],
        })
        for sec in p.get("sections", []):
            indice.append({
                "t": sec["heading"],
                "u": f"{root_path}colorir-online/{p['slug']}/{sec['image']}/",
                "k": sec["alt"],
            })
    search_json = json.dumps(indice, ensure_ascii=False)

    total_desenhos = sum(len(p.get("sections", [])) for p in posts)
    total_dinos = len(posts)
    content = render("home.html", base_ctx(
        ROOT_PATH=root_path,
        H1="Desenhos de Dinossauros para Colorir",
        LEDE=("Desenhos para colorir grátis com T-Rex, Triceratops, "
              "Braquiossauro e muito mais. Baixe o PDF, imprima ou pinte "
              "online no navegador!"),
        TOTAL_DESENHOS=f"{total_desenhos}+",
        TOTAL_DINOS=str(total_dinos),
        CIRCULOS=circulos_html,
        GRADE=grade_html,
        POST_CARDS=cards,
        FAQ_HOME=faq_home_html,
        SEARCH_INDEX=search_json,
    ))
    website_ld = {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": config.SITE_NAME,
        "url": config.BASE_URL + "/",
        "inLanguage": "pt-BR",
        "description": ("Desenhos de dinossauros para colorir grátis, "
                        "prontos para imprimir."),
    }
    faq_ld = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": q,
             "acceptedAnswer": {"@type": "Answer", "text": a}}
            for q, a in faqs_home
        ],
    }
    extra_head = (
        '<script type="application/ld+json">\n'
        + json.dumps(website_ld, ensure_ascii=False, indent=2)
        + '\n</script>\n<script type="application/ld+json">\n'
        + json.dumps(faq_ld, ensure_ascii=False, indent=2)
        + "\n</script>")
    title = f"{config.SITE_NAME} — Desenhos de Dinossauros para Colorir Grátis"
    meta = ("Desenhos de dinossauros para colorir grátis! T-Rex, Triceratops e "
            "muito mais. Baixe o PDF, imprima ou pinte online no navegador.")
    html = page_shell(parts, title, meta, content, extra_head=extra_head)
    write_page(parts, html)


# ------------------------------------------- páginas de conteúdo (com path)
def build_content_pages():
    """Páginas de content/pages/*.json. Suporta 'path' opcional para URLs
    aninhadas (ex. 'dinossauros/triceratops') e 'article': true para JSON-LD."""
    urls = []
    for path in sorted(PAGES_DIR.glob("*.json")):
        page = load_json(path)
        url_parts = page.get("path", page["slug"]).split("/")
        parts = url_parts + ["index.html"]
        depth = len(parts) - 1
        root_path = "../" * depth
        crumb = breadcrumb(url_parts, page["title"], root_path)
        content = render("page.html", base_ctx(
            ROOT_PATH=root_path,
            TITLE=page["title"],
            BODY=page["body"],
            BREADCRUMB=crumb,
        ))
        extra_head = ""
        if page.get("article"):
            page_url = config.BASE_URL + "/" + "/".join(url_parts) + "/"
            article_ld = {
                "@context": "https://schema.org",
                "@type": "Article",
                "headline": page["title"],
                "description": page["meta_description"],
                "inLanguage": "pt-BR",
                "datePublished": date.today().isoformat(),
                "author": {"@type": "Organization",
                           "name": config.SITE_NAME},
                "publisher": {"@type": "Organization",
                              "name": config.SITE_NAME},
                "mainEntityOfPage": {"@type": "WebPage", "@id": page_url},
            }
            extra_head = ('<script type="application/ld+json">\n'
                          + json.dumps(article_ld, ensure_ascii=False,
                                       indent=2)
                          + "\n</script>")
        html = page_shell(parts, page["title"],
                          page["meta_description"], content,
                          extra_head=extra_head)
        write_page(parts, html)
        urls.append((config.BASE_URL + "/" + "/".join(url_parts) + "/",
                     date.today().isoformat()))
    return urls


# ------------------------------------------------------- índice de desenhos
def build_desenhos_index(posts, categories):
    """Página /desenhos/ — todos os posts agrupados por categoria."""
    parts = ["desenhos", "index.html"]
    root_path = "../"
    sections = []
    for cat in categories:
        if cat["posts"]:
            cards = "\n".join(post_card(p, root_path) for p in cat["posts"])
        else:
            cards = (f'<p class="empty-note">Novos desenhos de '
                     f'{cat["name"].lower()} em breve!</p>')
        sections.append(
            f'  <section aria-labelledby="cat-{cat["slug"]}">\n'
            f'    <h2 id="cat-{cat["slug"]}"><a href="{root_path}categoria/'
            f'{cat["slug"]}/">{cat["name"]}</a></h2>\n'
            f'    <div class="cards">\n{cards}\n    </div>\n  </section>')
    content = render("desenhos.html", base_ctx(
        ROOT_PATH=root_path,
        BREADCRUMB=breadcrumb(["desenhos"], "Desenhos para Colorir",
                              root_path),
        SECTIONS="\n\n".join(sections),
    ))
    title = "Desenhos para Colorir"
    meta = ("Todos os desenhos para colorir do site: dinossauros grátis para "
            "baixar em PDF e imprimir.")
    html = page_shell(parts, title, meta, content)
    write_page(parts, html)
    return config.BASE_URL + "/desenhos/"


# ----------------------------------------------------------- colorir online
def lista_desenhos(posts):
    """Todos os desenhos coloríveis (galeria da ferramenta)."""
    desenhos = []
    for post in posts:
        slug = post["slug"]
        for sec in post.get("sections", []):
            desenhos.append({
                "pasta": slug,
                "img": sec["image"],
                "alt": sec["alt"],
                "label": sec["caption"],
            })
    return desenhos


def ferramenta_head_extra():
    app_ld = {
        "@context": "https://schema.org",
        "@type": "WebApplication",
        "name": "Colorir Online",
        "applicationCategory": "GameApplication",
        "operatingSystem": "Qualquer navegador",
        "inLanguage": "pt-BR",
        "offers": {"@type": "Offer", "price": "0"},
    }
    return ('<script type="application/ld+json">\n'
            + json.dumps(app_ld, ensure_ascii=False, indent=2)
            + "\n</script>")


def build_colorir_online(posts, desenhos):
    """Ferramenta interativa /colorir-online/ (100% estática).

    A galeria da ferramenta é gerada dinamicamente a partir de TODOS os
    posts: cada seção de cada post vira um item colorível. Assim o
    pipeline diário adiciona imagens novas à ferramenta automaticamente.
    """
    parts = ["colorir-online", "index.html"]
    root_path = "../"
    desenhos_json = json.dumps(desenhos, ensure_ascii=False)
    content = render("colorir-online.html", base_ctx(
        ROOT_PATH=root_path,
        DESENHOS_JSON=desenhos_json,
        PRESET_IMG="",
        TITULO_FERRAMENTA="Colorir Online: pinte dinossauros no navegador",
        BREADCRUMB=breadcrumb(["colorir-online"], "Colorir Online",
                              root_path),
    ))
    title = "Colorir Online: pinte dinossauros no navegador grátis"
    meta = ("Pinte desenhos de dinossauros online grátis: escolha cores, "
            "clique para preencher e baixe sua arte em PNG. Sem cadastro.")
    html = page_shell(parts, title, meta, content,
                      extra_head=ferramenta_head_extra())
    write_page(parts, html)
    return config.BASE_URL + "/colorir-online/"


def build_ferramenta_desenho(post, sec, desenhos):
    """Página própria de cada desenho: /colorir-online/<slug>/<img>/.

    URL com palavra-chave, título e meta únicos — cada desenho vira uma
    página indexável que abre a ferramenta já com aquele desenho.
    """
    slug = post["slug"]
    img = sec["image"]
    parts = ["colorir-online", slug, img, "index.html"]
    root_path = "../../../"
    desenhos_json = json.dumps(desenhos, ensure_ascii=False)
    titulo = f"{sec['heading']} — Colorir Online"
    content = render("colorir-online.html", base_ctx(
        ROOT_PATH=root_path,
        DESENHOS_JSON=desenhos_json,
        PRESET_IMG=f"{slug}/{img}",
        TITULO_FERRAMENTA=titulo,
        BREADCRUMB=breadcrumb(["colorir-online"], sec["heading"],
                              root_path),
    ))
    meta = (f"Pinte {sec['alt']} online grátis no navegador: balde, pincel, "
            f"lápis e spray com cores do dinossauro. Sem cadastro, funciona "
            f"no celular e no computador.")
    html = page_shell(parts, titulo, meta, content,
                      extra_head=ferramenta_head_extra())
    write_page(parts, html)
    return config.BASE_URL + f"/colorir-online/{slug}/{img}/"


# ------------------------------------------------------- sitemap/robots/rss
def build_sitemap(urls):
    items = []
    for loc, lastmod in urls:
        items.append(
            f"  <url>\n    <loc>{loc}</loc>\n"
            f"    <lastmod>{lastmod}</lastmod>\n"
            f"    <changefreq>weekly</changefreq>\n  </url>")
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
           + "\n".join(items) + "\n</urlset>\n")
    (DIST / "sitemap.xml").write_text(xml, encoding="utf-8")


def build_robots():
    (DIST / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\n\nSitemap: {config.BASE_URL}/sitemap.xml\n",
        encoding="utf-8")


def build_feed(posts):
    items = []
    for p in posts[:20]:
        link = config.BASE_URL + f"/desenhos/{p['slug']}/"
        pub = datetime(*[int(x) for x in p["date"].split("-")],
                       9, 0, 0).strftime("%a, %d %b %Y %H:%M:%S +0000")
        items.append(
            f"    <item>\n      <title>{p['title']}</title>\n"
            f"      <link>{link}</link>\n"
            f"      <guid>{link}</guid>\n"
            f"      <pubDate>{pub}</pubDate>\n"
            f"      <description>{p['meta_description']}</description>\n"
            f"    </item>")
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<rss version="2.0">\n  <channel>\n'
           f"    <title>{config.SITE_NAME}</title>\n"
           f"    <link>{config.BASE_URL}/</link>\n"
           f"    <description>{config.SITE_TAGLINE} — grátis para imprimir.</description>\n"
           '    <language>pt-BR</language>\n'
           + "\n".join(items) + "\n  </channel>\n</rss>\n")
    (DIST / "feed.xml").write_text(xml, encoding="utf-8")


# --------------------------------------------------------------------- main
def main():
    print("== Build do site ==")
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True)

    # Arquivos estáticos (css, favicon...)
    if STATIC_DIR.exists():
        for item in STATIC_DIR.iterdir():
            dest = DIST / item.name
            if item.is_dir():
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)
    # Assets (imagens .webp, .pdf, .svg)
    if ASSETS_DIR.exists():
        shutil.copytree(ASSETS_DIR, DIST / "assets", dirs_exist_ok=True)

    posts = [load_json(p) for p in sorted(POSTS_DIR.glob("*.json"))]
    posts.sort(key=lambda p: p["date"], reverse=True)
    print(f"  {len(posts)} post(s) carregado(s)")

    urls = []
    post_urls = []
    categories = {}
    for post in posts:
        url, lastmod = build_post(post, posts)
        post_urls.append(url)
        urls.append((url, lastmod))
        c = post["category"]
        categories.setdefault(c["slug"], {"name": c["name"],
                                          "slug": c["slug"],
                                          "intro": "",
                                          "posts": []})["posts"].append(post)
    print(f"  {len(post_urls)} página(s) de post")

    # Categorias permanentes (mesmo vazias — o pipeline diário as preenche)
    for extra in getattr(config, "EXTRA_CATEGORIES", []):
        categories.setdefault(extra["slug"], {"name": extra["name"],
                                              "slug": extra["slug"],
                                              "intro": extra.get("intro", ""),
                                              "posts": []})
    cat_list = [{"name": v["name"], "slug": v["slug"]}
                for v in categories.values()]
    for slug, cat in categories.items():
        curl = build_category(slug, cat["name"], cat["posts"],
                              cat.get("intro", ""))
        urls.append((curl, date.today().isoformat()))
    print(f"  {len(cat_list)} categoria(s)")

    build_home(posts, cat_list)
    urls.append((config.BASE_URL + "/", date.today().isoformat()))
    print("  home")

    desenhos_url = build_desenhos_index(posts, list(categories.values()))
    urls.append((desenhos_url, date.today().isoformat()))
    print("  /desenhos/")

    colorir_url = build_colorir_online(posts, lista_desenhos(posts))
    urls.append((colorir_url, date.today().isoformat()))
    print("  /colorir-online/")

    # páginas próprias de cada desenho (SEO: URL com palavra-chave)
    desenhos = lista_desenhos(posts)
    n_desenhos = 0
    for post in posts:
        for sec in post.get("sections", []):
            durl = build_ferramenta_desenho(post, sec, desenhos)
            urls.append((durl, post["date"]))
            n_desenhos += 1
    print(f"  {n_desenhos} página(s) de desenho no Colorir Online")

    content_urls = build_content_pages()
    urls.extend(content_urls)
    print(f"  {len(content_urls)} página(s) de conteúdo")

    build_sitemap(urls)
    build_robots()
    build_feed(posts)
    print("  sitemap.xml, robots.txt, feed.xml")

    if missing_assets:
        print("\n  AVISO — imagens referenciadas mas ausentes em assets/:")
        for m in sorted(set(missing_assets)):
            print(f"    - assets/{m}")
        print("  (adicione os .webp/.pdf e rode o build de novo)")
    else:
        print("  todos os assets referenciados existem ✔")

    # Zip pronto para deploy
    RELEASES.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    zip_name = f"dino-colorir-{stamp}.zip"
    zip_path = RELEASES / zip_name
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(DIST.rglob("*")):
            if f.is_file():
                z.write(f, f.relative_to(DIST))
    size_kb = zip_path.stat().st_size / 1024
    n_files = sum(1 for _ in DIST.rglob("*") if _.is_file())
    print(f"\n  dist/: {n_files} arquivo(s)")
    print(f"  zip: releases/{zip_name} ({size_kb:.1f} KB)")
    print("\n== Build concluído ==")


if __name__ == "__main__":
    main()
