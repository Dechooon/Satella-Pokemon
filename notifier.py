"""
Benachrichtigungsmodul für den Pokémon-TCG-Wächter.
Sendet strukturierte Alerts an Telegram (mit Bild), Discord (Webhook mit Embeds) und ntfy.sh.
"""
import logging
import requests
import config

log = logging.getLogger("tcg.notifier")

# Emojis für Sprachen und Status
LANGUAGE_BADGES = {
    "Deutsch": "🇩🇪 Deutsch",
    "Englisch": "🇬🇧 Englisch",
    "Japanisch": "🇯🇵 Japanisch",
    "unbekannt": "❓ Unbekannt",
}

STATUS_BADGES = {
    "vorbestellbar": "🟡 Vorbestellbar",
    "verfügbar": "🟢 Verfügbar",
    "ausverkauft": "🔴 Ausverkauft",
    "unbekannt": "⚪ Gelistet",
}


def send_telegram(title, text, url=None, image_url=None):
    """Sendet eine Nachricht oder ein Bild mit Beschriftung an Telegram."""
    if not (config.TELEGRAM_BOT_TOKEN and config.TELEGRAM_CHAT_ID):
        return False

    base_api = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}"

    # Versuche zuerst mit Foto zu senden
    if image_url:
        try:
            r = requests.post(
                f"{base_api}/sendPhoto",
                data={
                    "chat_id": config.TELEGRAM_CHAT_ID,
                    "photo": image_url,
                    "caption": f"<b>{title}</b>\n\n{text}",
                    "parse_mode": "HTML",
                },
                timeout=12,
            )
            if r.status_code == 200:
                return True
            log.warning("Telegram sendPhoto fehlgeschlagen (HTTP %d). Fallback auf Text.", r.status_code)
        except Exception as e:
            log.warning("Telegram sendPhoto Fehler: %s. Fallback auf Text.", e)

    # Fallback: Reine Textnachricht
    try:
        content = f"<b>{title}</b>\n\n{text}"
        if url:
            content += f'\n\n🛒 <a href="{url}"><b>Hier direkt zum Angebot öffnen</b></a>'

        r = requests.post(
            f"{base_api}/sendMessage",
            data={
                "chat_id": config.TELEGRAM_CHAT_ID,
                "text": content,
                "parse_mode": "HTML",
                "disable_web_page_preview": False,
            },
            timeout=12,
        )
        return r.status_code == 200
    except Exception as e:
        log.error("Telegram sendMessage fehlgeschlagen: %s", e)
        return False


def send_discord(title, text, url=None, image_url=None, color=0x3498DB):
    """Sendet ein formatiertes Rich Embed an einen Discord Webhook."""
    if not config.DISCORD_WEBHOOK_URL:
        return False

    embed = {
        "title": title[:256],
        "description": text[:2000],
        "color": color,
    }
    if url:
        embed["url"] = url
    if image_url:
        embed["thumbnail"] = {"url": image_url}

    payload = {
        "username": "Pokémon TCG Wächter",
        "avatar_url": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/poke-ball.png",
        "embeds": [embed]
    }

    try:
        r = requests.post(config.DISCORD_WEBHOOK_URL, json=payload, timeout=12)
        return r.status_code in (200, 204)
    except Exception as e:
        log.error("Discord Webhook fehlgeschlagen: %s", e)
        return False


def send_ntfy(title, text, url=None):
    """Sendet eine Push-Nachricht an ntfy.sh."""
    if not config.NTFY_TOPIC:
        return False

    headers = {
        "Title": title.encode("utf-8"),
        "Priority": "high",
        "Tags": "rotating_light,package",
    }
    if url:
        headers["Click"] = url

    try:
        endpoint = f"{config.NTFY_SERVER}/{config.NTFY_TOPIC}"
        r = requests.post(endpoint, data=text.encode("utf-8"), headers=headers, timeout=12)
        return r.status_code == 200
    except Exception as e:
        log.error("ntfy fehlgeschlagen: %s", e)
        return False


def notify_product(product, reason="new", old_status=None):
    """
    Formatiert und sendet einen Produkt-Alarm an alle aktiven Kanäle.
    reason kann 'new' oder 'restock' sein.
    """
    title_prefix = "🚨 NEUES POKÉMON-PRODUKT!" if reason == "new" else "🎉 POKÉMON-PRODUKT JETZT VERFÜGBAR!"
    if product.get("status") == "vorbestellbar":
        title_prefix = "⏰ POKÉMON JETZT VORBESTELLBAR!"

    lang_display = LANGUAGE_BADGES.get(product.get("language"), product.get("language") or "Unbekannt")
    status_display = STATUS_BADGES.get(product.get("status"), product.get("status") or "Gelistet")
    price_display = product.get("price") or "Preis im Shop prüfen"

    body_lines = [
        f"📦 <b>{product.get('title')}</b>",
        f"🏪 <b>Shop:</b> {product.get('shop')}",
        f"💰 <b>Preis:</b> {price_display}",
        f"🌐 <b>Sprache:</b> {lang_display}",
        f"⚡ <b>Status:</b> {status_display}",
    ]
    if old_status and old_status != product.get("status"):
        body_lines.append(f"🔄 <b>Änderung:</b> {old_status} ➔ {product.get('status')}")

    prod_url = product.get("url")
    if prod_url:
        body_lines.append(f'\n🛒 <a href="{prod_url}"><b>Zum Produkt im Shop</b></a>')

    text = "\n".join(body_lines)

    # Discord Farbwahl
    color = 0x2ECC71 if product.get("status") == "verfügbar" else (0xF1C40F if product.get("status") == "vorbestellbar" else 0x3498DB)

    log.info("ALARM: [%s] %s (%s)", product.get("shop"), product.get("title"), product.get("status"))

    send_telegram(title_prefix, text, url=product.get("url"), image_url=product.get("image"))
    send_discord(title_prefix, text.replace("<b>", "**").replace("</b>", "**"),
                 url=product.get("url"), image_url=product.get("image"), color=color)
    send_ntfy(title_prefix, f"{product.get('title')}\nShop: {product.get('shop')} | {status_display} | {price_display}",
              url=product.get("url"))


def notify_admin(title, message, url=None):
    """Sendet eine System-/Statusmeldung an alle Kanäle."""
    log.info("ADMIN-INFO: %s | %s", title, message)
    send_telegram(title, message, url)
    send_discord(title, message, url, color=0x95A5A6)
    send_ntfy(title, message, url)
