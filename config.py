# -*- coding: utf-8 -*-
"""
Site-wide configuration — THE single place to set the brand.

Brand name is UNDECIDED: every template, title, meta tag, logo text and
footer reads SITE_NAME from here. When the brand is chosen, replace the
placeholder value below with the real name and re-run build.py.
"""

SITE_NAME = "Dinossauros para Colorir"
SITE_TAGLINE = "Desenhos de dinossauros para colorir"
SITE_DOMAIN = "dinossaurosparacolorir.com.br"
BASE_URL = "https://" + SITE_DOMAIN
CONTACT_EMAIL = "contato@" + SITE_DOMAIN

# Display dimensions of coloring images (1344x1792 pipeline spec).
# Used for width/height attributes to prevent layout shift.
IMAGE_WIDTH = 1344
IMAGE_HEIGHT = 1792

# Brand color accents used by the minimal stylesheet.
BRAND_PRIMARY = "#2e7d32"   # verde dinossauro
BRAND_ACCENT = "#f9a825"    # âmbar

# Categorias permanentes: existem mesmo sem posts (o pipeline diário as preenche).
EXTRA_CATEGORIES = [
    {"name": "Triceratops", "slug": "triceratops",
     "intro": "Desenhos de Triceratops para colorir: o dinossauro dos três chifres em páginas grátis para imprimir em PDF."},
    {"name": "Velociraptor", "slug": "velociraptor",
     "intro": "Desenhos de Velociraptor para colorir: o caçador veloz em páginas grátis para imprimir em PDF."},
    {"name": "Braquiossauro", "slug": "braquiossauro",
     "intro": "Desenhos de Braquiossauro para colorir: o gigante gentil de pescoço longo em páginas grátis para imprimir em PDF."},
    {"name": "Estegossauro", "slug": "estegossauro",
     "intro": "Desenhos de Estegossauro para colorir: o dinossauro das placas nas costas em páginas grátis para imprimir em PDF."},
    {"name": "Dinossauros Bebês", "slug": "dinossauros-bebes",
     "intro": "Desenhos de dinossauros bebês para colorir: fofinhos e fáceis, perfeitos para crianças pequenas. Grátis para imprimir em PDF."},
]
