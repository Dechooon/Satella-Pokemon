"""
Scraper-Modul für den Pokémon-TCG-Wächter.
Überprüft Shop-Kataloge und Produktseiten auf neue und verfügbare TCG-Artikel.
"""
import hashlib
import html
import json
import logging
import random
import re
import time
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
import config

log = logging.getLogger("tcg.scraper")


def create_session():
    """Erstellt eine requests-Session mit Standard-Headern."""
    s = requests.Session()
    s.headers.update({
        "User-Agent": random.choice(config.USER_AGENTS),
        "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    })
    return s


def fetch(url, session=None, retries=3, timeout=15):
    """Ruft eine URL sicher mit Retries und wechselndem User-Agent ab."""
    if session is None:
        session = create_session()

    for attempt in range(1, retries + 1):
        try:
            # Leicht variierender User-Agent bei Retries
            headers = {"User-Agent": random.choice(config.USER_AGENTS)}
            r = session.get(url, headers=headers, timeout=timeout)
            if r.status_code == 200:
                return r.text
            elif r.status_code in (404, 410):
                log.warning("Seite existiert nicht mehr (HTTP %d): %s", r.status_code, url)
                return None
            log.warning("HTTP %s bei %s (Versuch %d/%d)", r.status_code, url, attempt, retries)
        except requests.RequestException as e:
            log.warning("Verbindungsfehler bei %s: %s (Versuch %d/%d)", url, e, attempt, retries)

        if attempt < retries:
            time.sleep(attempt * 2)

    return None


def is_tcg_product(text):
    """Prüft, ob der Text/URL-Pfad auf ein Pokémon-Sammelkarten-Produkt zutrifft."""
    # 1. Ausschlusskriterien prüfen (Plüsch, Konsolen, Kleidung, Zubehör etc.)
    if any(re.search(pat, text, re.I) for pat in config.EXCLUDE_KEYWORDS):
        return False

    # 2. Pflichtkriterien (z. B. 'pokemon')
    if not all(re.search(req, text, re.I) for req in config.REQUIRE_KEYWORDS):
        return False

    # 3. Mindestens ein TCG-Schlüsselwort (Booster, Display, ETB, Tin etc.)
    return any(re.search(prod, text, re.I) for prod in config.PRODUCT_KEYWORDS)


def detect_language(text):
    """
    Erkennt die Sprache des Produkts anhand von Titel, Beschreibung oder Attributen.
    Gibt 'Deutsch', 'Englisch', 'Japanisch', 'blockiert' oder 'unbekannt' zurück.
    """
    if not text:
        return "unbekannt"

    # Zuerst erlaubte Sprachen prüfen
    for lang_name, pattern in config.LANGUAGES_ALLOWED.items():
        if re.search(pattern, text, re.I):
            return lang_name

    # Blockierte Sprachen prüfen (z. B. Französisch, Spanisch, Koreanisch etc.)
    if re.search(config.LANGUAGES_BLOCKED, text, re.I):
        return "blockiert"

    return "unbekannt"


def extract_price(soup, text=""):
    """Versucht den Artikelpreis aus Schema.org, Meta-Tags oder HTML-Klassen zu extrahieren."""
    # 1. OpenGraph / Itemprop Meta-Tags
    meta_price = (
        soup.find("meta", property="product:price:amount") or
        soup.find("meta", property="og:price:amount") or
        soup.find("meta", itemprop="price")
    )
    if meta_price and meta_price.get("content"):
        val = meta_price["content"].replace(",", ".").strip()
        try:
            return f"{float(val):.2f} €".replace(".", ",")
        except ValueError:
            pass

    # 2. Schema.org JSON-LD
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            if isinstance(data, dict):
                offers = data.get("offers", {})
                if isinstance(offers, list) and offers:
                    offers = offers[0]
                if isinstance(offers, dict) and "price" in offers:
                    val = str(offers["price"]).replace(",", ".").strip()
                    return f"{float(val):.2f} €".replace(".", ",")
        except Exception:
            pass

    # 3. Typische CSS-Klassen für Hauptpreise
    for selector in [".product-price", ".price--highlight", ".price-wrapper", ".current-price", ".price"]:
        for el in soup.select(selector):
            el_text = el.get_text(" ", strip=True)
            m = re.search(r"(\d+(?:[\.,]\d{2}))\s*(?:€|EUR)", el_text)
            if m:
                val = m.group(1).replace(".", "").replace(",", ".")
                try:
                    return f"{float(val):.2f} €".replace(".", ",")
                except ValueError:
                    return f"{m.group(1)} €"

    # 4. Fallback: Suche im gesamten Text
    m = re.search(r"(\d{1,4}[,\.]\d{2})\s*(?:€|EUR)", text)
    if m:
        return f"{m.group(1)} €"

    return None


def extract_image(soup, base_url):
    """Extrahiert das Produktbild."""
    # 1. OpenGraph Bild
    og_img = soup.find("meta", property="og:image")
    if og_img and og_img.get("content"):
        return urljoin(base_url, og_img["content"].strip())

    # 2. Itemprop image
    item_img = soup.find("img", itemprop="image")
    if item_img and item_img.get("src"):
        return urljoin(base_url, item_img["src"].strip())

    # 3. Erste große Produkt-Klasse
    for el in soup.select(".product-image img, .gallery img, .product-featured-media img"):
        src = el.get("src") or el.get("data-src")
        if src:
            return urljoin(base_url, src.strip())

    return None


def check_product_page(url, session=None):
    """
    Ruft eine einzelne Produktseite auf und ermittelt:
    - Status ('vorbestellbar', 'verfügbar', 'ausverkauft', 'unbekannt')
    - Sprache
    - Preis
    - Bild-URL
    - Genauen Produkttitel
    """
    html_content = fetch(url, session=session)
    if not html_content:
        return {
            "status": "unbekannt",
            "language": "unbekannt",
            "price": None,
            "image": None,
            "title": None,
        }

    soup = BeautifulSoup(html_content, "html.parser")
    page_text = soup.get_text(" ", strip=True)

    # 1. Status prüfen
    status = "unbekannt"
    for s_name, pattern in config.STATUS_PATTERNS:
        if re.search(pattern, page_text, re.I):
            status = s_name
            break

    # 2. Sprache ermitteln
    # Häufig gibt es explizite Attribute wie "Sprache: Deutsch"
    m_lang = re.search(r"sprache\s*[:\-]?\s*([A-Za-zÄÖÜäöüß]+)", page_text, re.I)
    if m_lang:
        lang = detect_language(m_lang.group(1))
    else:
        # Fallback auf Titel oder URL
        title_meta = soup.find("meta", property="og:title")
        t_text = title_meta["content"] if title_meta else page_text[:200]
        lang = detect_language(f"{t_text} {url}")

    # 3. Preis & Bild
    price = extract_price(soup, page_text)
    image = extract_image(soup, url)

    # 4. Titel bereinigen
    title = None
    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        title = og_title["content"].strip()
    elif soup.find("h1"):
        title = soup.find("h1").get_text(" ", strip=True)

    return {
        "status": status,
        "language": lang,
        "price": price,
        "image": image,
        "title": title,
    }


def find_products_in_shop(shop, session=None):
    """
    Durchsucht die Übersichts- oder Kategorieseite des Shops nach Pokémon-Produkten.
    Gibt ein Dict mit {product_key: product_info} zurück.
    """
    if not shop.get("enabled", True):
        return {}

    shop_url = shop["url"]
    html_content = fetch(shop_url, session=session)
    if not html_content:
        return {}

    soup = BeautifulSoup(html_content, "html.parser")
    found = {}

    # Links mit relevantem Text durchgehen
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue

        full_url = urljoin(shop_url, href).split("#")[0].split("?")[0]
        parsed = urlparse(full_url)
        path = parsed.path.lower()

        # Filtere offensichtliche Systemseiten, Self-Links & Paginierung aus
        if full_url.rstrip("/") == shop_url.rstrip("/"):
            continue
        if any(bad in path for bad in [
            "/cart", "/checkout", "/account", "/warenkorb", "/kasse", "/login",
            "/faq", "/impressum", "/datenschutz", "/contact", "/kontakt",
            "/collections/", "/category/", "/kategorie/", "/blogs/", "/pages/",
            "/ueber-uns", "/about", "/versand", "/widerruf", "/agb", "/hilfe"
        ]):
            continue
        if re.search(r"(/_s\d+|[?&]page=|[?&]p=\d+|\bseite\s*\d+\b)", full_url, re.I):
            continue
        # URLs die mit Slash enden sind meist Kategorie-Ordner (sofern kein /produkt/ etc. im Pfad ist)
        if full_url.endswith("/") and not any(k in path for k in ["/produkt/", "/product/", "/item/", "/artikel/", "/p/"]):
            continue

        img_alt = ""
        img_tag = a.find("img")
        if img_tag and img_tag.get("alt"):
            img_alt = img_tag["alt"].strip()

        link_text = " ".join(filter(None, [
            a.get_text(" ", strip=True),
            img_alt,
            a.get("title", ""),
            a.get("aria-label", "")
        ])).strip()

        # Ausschluss- und TCG-Prüfung nur auf Linktext und URL-Pfad (ohne Domainname)
        check_text = f"{link_text} {path}"

        # Prüfe, ob es ein TCG-Produkt ist
        if not is_tcg_product(check_text):
            continue

        # Eindeutiger Hash aus URL
        key = hashlib.sha1(full_url.encode("utf-8")).hexdigest()[:16]

        raw_title = link_text if link_text else path.strip("/").split("/")[-1].replace("-", " ").title()
        title = html.unescape(raw_title).strip()
        if len(title) > 160:
            title = title[:160] + "..."

        if key not in found or len(link_text) > len(found[key]["title"]):
            found[key] = {
                "key": key,
                "title": title,
                "url": full_url,
                "shop": shop["name"],
                "price": None,
                "image": None,
                "status": "unbekannt",
                "language": "unbekannt",
            }

    return found
