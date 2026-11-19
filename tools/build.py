#!/usr/bin/env python3
"""
Sitenin sayfalarını üretir (arama motorları için).

Pages CMS ile bir şey kaydettiğinde GitHub bu dosyayı otomatik çalıştırır
(.github/workflows/build.yml). Elle çalıştırmana gerek yok.

Ürettiği dosyalar:
  index.html              ana sayfa
  contact/index.html      iletişim sayfası
  work/<proje>/index.html her proje için ayrı sayfa
  404.html                bulunamayan sayfa
  sitemap.xml, robots.txt arama motorları için

Tasarım tools/template.html dosyasındadır.
"""
import html
import json
import os
import re
import shutil
from datetime import date
from urllib.parse import urlparse

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE_TITLE = "socalan portfolio ©SeDaT ÖCaLaN"
DEFAULT_FULLNAME = "SeDaT ÖCaLaN"


def read(path):
    with open(os.path.join(ROOT_DIR, path), encoding="utf-8") as f:
        return f.read()


def write(path, text):
    full = os.path.join(ROOT_DIR, path)
    os.makedirs(os.path.dirname(full) or ".", exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(text)


def site_url():
    """Sitenin tam adresi: CNAME (kendi alan adın) varsa o, yoksa GitHub Pages adresi."""
    cname = os.path.join(ROOT_DIR, "CNAME")
    if os.path.exists(cname):
        domain = open(cname, encoding="utf-8").read().strip()
        if domain:
            return "https://" + domain.strip("/") + "/"
    repo = os.environ.get("GITHUB_REPOSITORY", "socalan/portfolio")
    owner, name = repo.split("/", 1)
    if name.lower() == owner.lower() + ".github.io":
        return "https://%s.github.io/" % owner.lower()
    return "https://%s.github.io/%s/" % (owner.lower(), name)


TR = str.maketrans({"ç": "c", "ğ": "g", "ı": "i", "İ": "i", "ö": "o", "ş": "s", "ü": "u",
                    "Ç": "c", "Ğ": "g", "Ö": "o", "Ş": "s", "Ü": "u"})


def slugify(t):
    s = str(t or "").translate(TR).lower().replace("&", "and")
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def slug_of(p):
    return slugify(p.get("slug") or p.get("title"))


def cover_of(p):
    if p.get("cover"):
        return p["cover"]
    for f in p.get("photos") or []:
        if f and f.get("image"):
            return f["image"]
    return ""


def e(s):
    return html.escape(str(s or ""), quote=True)


ICONS = {
    "instagram": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><rect x="3" y="3" width="18" height="18" rx="5"/><circle cx="12" cy="12" r="4"/><circle cx="17.5" cy="6.5" r="1" fill="currentColor"/></svg>',
    "px500": '<svg viewBox="0 0 24 24" fill="currentColor"><text x="1" y="17" font-size="11" font-family="Arial" font-weight="700">500</text></svg>',
}


def build():
    site = json.loads(read("data/site.json"))
    projects = json.loads(read("data/projects.json"))
    if isinstance(projects, dict):
        projects = projects.get("projects", [])
    projects = [p for p in projects if p and p.get("title")]
    template = read("tools/template.html")
    url = site_url()
    base_path = urlparse(url).path or "/"
    fullname = site.get("fullname") or DEFAULT_FULLNAME

    def img(path, root):
        return root + str(path or "").lstrip("/")

    def abs_img(path):
        return url + str(path or "").lstrip("/") if path else ""

    def alt_of(p, f=None, i=None):
        if f and f.get("caption"):
            return f["caption"]
        a = p["title"] + (", " + p["subtitle"] if p.get("subtitle") else "") + " — photo by " + fullname
        return a + (" (%d)" % (i + 1) if i is not None else "")

    def social():
        h = ""
        if site.get("instagram"):
            h += '<a href="%s" target="_blank" rel="noopener" aria-label="Instagram">%s</a>' % (e(site["instagram"]), ICONS["instagram"])
        if site.get("px500"):
            h += '<a href="%s" target="_blank" rel="noopener" aria-label="500px">%s</a>' % (e(site["px500"]), ICONS["px500"])
        return h

    def card(p, root):
        return ('<a class="card" href="%swork/%s/"><div class="ph"><img loading="lazy" src="%s" alt="%s"></div>'
                '<h2>%s</h2>%s</a>') % (root, slug_of(p), e(img(cover_of(p), root)), e(alt_of(p)), e(p["title"]),
                                        "<span>%s</span>" % e(p["subtitle"]) if p.get("subtitle") else "")

    same_as = [u for u in (site.get("instagram"), site.get("px500")) if u]
    person = {"@type": "Person", "@id": url + "#person", "name": fullname, "alternateName": site.get("name") or "socalan",
              "jobTitle": "Photographer", "url": url, "sameAs": same_as,
              "address": {"@type": "PostalAddress", "addressLocality": "Ankara", "addressCountry": "TR"}}
    if site.get("email"):
        person["email"] = "mailto:" + site["email"]
    default_image = abs_img(cover_of(projects[0])) if projects else ""
    default_desc = " ".join(x for x in [fullname + " —", site.get("tagline"), site.get("about")] if x).strip()

    def head(title, desc, canonical, image, og_type="website", jsonld=None, noindex=False):
        desc = re.sub(r"\s+", " ", desc or default_desc).strip()[:300]
        image = image or default_image
        h = [
            "<title>%s</title>" % e(title),
            '<meta name="description" content="%s">' % e(desc),
            '<meta name="author" content="%s">' % e(fullname),
        ]
        if noindex:
            h.append('<meta name="robots" content="noindex">')
        else:
            h.append('<link rel="canonical" href="%s">' % e(canonical))
        h += [
            '<meta property="og:type" content="%s">' % og_type,
            '<meta property="og:site_name" content="%s">' % e(SITE_TITLE),
            '<meta property="og:title" content="%s">' % e(title),
            '<meta property="og:description" content="%s">' % e(desc),
            '<meta property="og:url" content="%s">' % e(canonical),
            '<meta property="og:locale" content="tr_TR">',
            '<meta name="twitter:card" content="summary_large_image">',
            '<meta name="twitter:title" content="%s">' % e(title),
            '<meta name="twitter:description" content="%s">' % e(desc),
        ]
        if image:
            h += ['<meta property="og:image" content="%s">' % e(image),
                  '<meta name="twitter:image" content="%s">' % e(image)]
        if jsonld:
            h.append('<script type="application/ld+json">%s</script>'
                     % json.dumps(jsonld, ensure_ascii=False).replace("</", "<\\/"))
        return "\n".join(h)

    def page(root, page_id, head_html, content):
        out = template
        for k, v in {"HEAD": head_html, "ROOT": root, "PAGE": page_id, "LOGO": e(site.get("name")),
                     "SOCIAL": social(), "FOOTER": e(site.get("footer")), "CONTENT": content}.items():
            out = out.replace("{{%s}}" % k, v)
        return out

    # Eski üretilmiş sayfaları temizle
    shutil.rmtree(os.path.join(ROOT_DIR, "work"), ignore_errors=True)

    # Ana sayfa
    home_content = ('<section class="intro"><h1>%s</h1><p>%s</p></section><section class="grid">%s</section>'
                    % (e(fullname), e(site.get("tagline")), "".join(card(p, "./") for p in projects)))
    website = {"@context": "https://schema.org", "@graph": [
        {"@type": "WebSite", "@id": url + "#website", "url": url, "name": SITE_TITLE, "inLanguage": "tr",
         "publisher": {"@id": url + "#person"}},
        person,
        {"@type": "CollectionPage", "url": url, "name": SITE_TITLE, "about": {"@id": url + "#person"},
         "hasPart": [{"@type": "ImageGallery", "name": p["title"], "url": "%swork/%s/" % (url, slug_of(p))} for p in projects]},
    ]}
    write("index.html", page("./", "home", head(SITE_TITLE, default_desc, url, default_image, jsonld=website), home_content))

    # İletişim
    contact_content = ('<section class="contact"><h1>Contact</h1>%s%s<div class="social">%s</div></section>' % (
        "<p>%s</p>" % e(site["about"]) if site.get("about") else "",
        '<a class="mail" href="mailto:%s">%s</a>' % (e(site["email"]), e(site["email"])) if site.get("email") else "",
        social()))
    write("contact/index.html", page("../", "contact",
                                     head(SITE_TITLE + " - Contact", "Contact %s, photographer based in Ankara, Türkiye. %s" % (fullname, site.get("about") or ""),
                                          url + "contact/", default_image,
                                          jsonld={"@context": "https://schema.org", "@type": "ContactPage", "url": url + "contact/", "mainEntity": person}),
                                     contact_content))

    # Projeler
    pages = [(url, None), (url + "contact/", None)]
    used = set()
    for p in projects:
        slug = slug_of(p)
        if not slug or slug in used:
            continue
        used.add(slug)
        root = "../../"
        photos = [f for f in (p.get("photos") or []) if f and f.get("image")]
        others = [x for x in projects if x is not p][:8]
        content = ('<section class="proj-head"><h1>%s</h1>%s</section><section class="photos">%s</section>%s' % (
            e(p["title"]), "<p>%s</p>" % e(p["subtitle"]) if p.get("subtitle") else "",
            "".join('<figure><img loading="%s" src="%s" alt="%s">%s</figure>' % (
                "eager" if i < 2 else "lazy", e(img(f["image"], root)), e(alt_of(p, f, i)),
                "<figcaption>%s</figcaption>" % e(f["caption"]) if f.get("caption") else "") for i, f in enumerate(photos)),
            '<section class="more"><h3>You may also like</h3><div class="grid">%s</div></section>' % "".join(card(x, root) for x in others) if others else ""))
        page_url = "%swork/%s/" % (url, slug)
        desc = "%s%s — photography by %s, photographer based in Ankara, Türkiye." % (
            p["title"], " (" + p["subtitle"] + ")" if p.get("subtitle") else "", fullname)
        gallery = {"@context": "https://schema.org", "@type": "ImageGallery", "name": p["title"], "url": page_url,
                   "description": desc, "author": person, "isPartOf": {"@type": "WebSite", "url": url, "name": SITE_TITLE},
                   "image": [{"@type": "ImageObject", "contentUrl": abs_img(f["image"]), "name": alt_of(p, f, i),
                              "creator": {"@type": "Person", "name": fullname},
                              "creditText": fullname, "copyrightNotice": "© " + fullname}
                             for i, f in enumerate(photos)]}
        write("work/%s/index.html" % slug, page(root, "work:" + slug,
                                                head(SITE_TITLE + " - " + p["title"], desc, page_url,
                                                     abs_img(cover_of(p)), og_type="article", jsonld=gallery), content))
        pages.append((page_url, [abs_img(f["image"]) for f in photos]))

    # 404
    write("404.html", page(base_path, "notfound", head(SITE_TITLE + " - Not found", default_desc, url, default_image, noindex=True),
                           '<div class="msg">This page was not found. <a href="%s">Back to home</a></div>' % e(base_path)))

    # sitemap.xml (fotoğraflar dahil)
    today = date.today().isoformat()
    sm = ['<?xml version="1.0" encoding="UTF-8"?>',
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">']
    for loc, images in pages:
        sm.append("  <url>\n    <loc>%s</loc>\n    <lastmod>%s</lastmod>" % (e(loc), today))
        for im in images or []:
            sm.append("    <image:image><image:loc>%s</image:loc></image:image>" % e(im))
        sm.append("  </url>")
    sm.append("</urlset>")
    write("sitemap.xml", "\n".join(sm) + "\n")

    write("robots.txt", "User-agent: *\nAllow: /\n\nSitemap: %ssitemap.xml\n" % url)
    print("Site üretildi: %s (%d proje)" % (url, len(used)))


if __name__ == "__main__":
    build()
