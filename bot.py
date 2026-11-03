#!/usr/bin/env python3
"""
Pokémon-TCG-Wächter (Satella)
Hauptskript: Überwacht Shops kontinuierlich auf Pokémon-Sammelkarten-Produkte
(Booster, Displays, ETBs/TTBs, Tins, Kollektionen) in DEUTSCH, ENGLISCH und JAPANISCH.

Start:
  python bot.py           # Kontinuierlicher Wächter-Betrieb
  python bot.py --once    # Einmalige Prüfung (z. B. für Windows Aufgabenplanung / Cron)
  python bot.py --test    # Test-Benachrichtigung an alle Kanäle
"""
import logging
import random
import sys
import time

import config
import notifier
import scraper
import web_server
from state_manager import StateManager
from telegram_bot import TelegramBotListener

# ==================== WINDOWS UTF-8 UNTERSTÜTZUNG ====================
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ==================== LOGGING SETUP ====================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (%(name)s) %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(config.LOG_FILE, encoding="utf-8"),
    ]
)
log = logging.getLogger("tcg.main")


class PokemonTCGWatcher:
    def __init__(self):
        self.state_manager = StateManager()
        self.session = scraper.create_session()
        self.telegram_listener = None
        self.is_checking = False

    def start_telegram_listener(self):
        if config.TELEGRAM_BOT_TOKEN:
            self.telegram_listener = TelegramBotListener(
                self.state_manager,
                trigger_check_callback=self.run_manual_check
            )
            self.telegram_listener.start()
        else:
            log.info("Hinweis: TELEGRAM_BOT_TOKEN ist nicht gesetzt. Befehle via Telegram deaktiviert.")

    def run_manual_check(self, chat_id=None):
        if self.is_checking:
            if self.telegram_listener and chat_id:
                self.telegram_listener.send_reply(chat_id, "⚠️ Ein Scan läuft bereits!")
            return

        self.is_checking = True
        try:
            stats = self.check_all_shops()
            if self.telegram_listener and chat_id:
                self.telegram_listener.send_reply(
                    chat_id,
                    f"✅ <b>Prüfung abgeschlossen!</b>\n"
                    f"🏪 {stats['shops_checked']} Shops durchsucht\n"
                    f"📦 {stats['products_found']} relevante Pokémon-Produkte erfasst\n"
                    f"🚨 {stats['alerts_sent']} neue Alarme ausgelöst"
                )
        except Exception as e:
            log.exception("Fehler beim manuellen Check: %s", e)
            if self.telegram_listener and chat_id:
                self.telegram_listener.send_reply(chat_id, f"❌ Fehler bei der Prüfung: {e}")
        finally:
            self.is_checking = False

    def check_all_shops(self):
        first_run = len(self.state_manager.products) == 0
        if first_run:
            log.info("Erster Durchlauf: Erfasse initialen Produktbestand...")

        shops = self.state_manager.load_shops()
        enabled_shops = [s for s in shops if s.get("enabled", True)]

        total_found = 0
        total_alerts = 0

        for shop in enabled_shops:
            log.info("Scanne Shop: '%s' (%s)", shop["name"], shop["url"])
            try:
                products = scraper.find_products_in_shop(shop, session=self.session)
                log.info("[%s] %d relevante Treffer gefunden", shop["name"], len(products))
            except Exception as e:
                log.warning("Fehler beim Scannen von %s: %s", shop["name"], e)
                continue

            for key, p in products.items():
                # Vorab-Sprachcheck auf Basis des Linktextes / URL
                quick_lang = scraper.detect_language(f"{p['title']} {p['url']}")
                if quick_lang == "blockiert":
                    continue

                total_found += 1

                # Detaillierte Produktseite abrufen
                if config.CHECK_PRODUCT_PAGES:
                    time.sleep(random.uniform(config.REQUEST_DELAY_MIN, config.REQUEST_DELAY_MAX))
                    details = scraper.check_product_page(p["url"], session=self.session)

                    p["status"] = details["status"]
                    p["price"] = details["price"]
                    p["image"] = details["image"]
                    if details["title"]:
                        p["title"] = details["title"]

                    final_lang = details["language"] if details["language"] != "unbekannt" else quick_lang
                    p["language"] = final_lang
                else:
                    p["status"] = "gelistet"
                    p["language"] = quick_lang

                # Sprache verifizieren
                if p["language"] == "blockiert":
                    continue
                if p["language"] == "unbekannt" and not config.UNKNOWN_LANGUAGE_OK:
                    continue

                old_product = self.state_manager.get_product(key)

                # Prüfe auf Neuerscheinung oder Statusänderung
                if old_product is None:
                    # Neues Produkt
                    if not first_run or config.NOTIFY_FIRST_RUN:
                        if p["status"] in config.ALERT_STATUSES or not config.CHECK_PRODUCT_PAGES:
                            notifier.notify_product(p, reason="new")
                            self.state_manager.record_alert(p)
                            total_alerts += 1
                else:
                    # Bekanntes Produkt: Prüfe Statusänderung (z. B. ausverkauft -> verfügbar)
                    old_status = old_product.get("status")
                    new_status = p["status"]

                    if old_status != new_status and new_status in config.ALERT_STATUSES:
                        notifier.notify_product(p, reason="restock", old_status=old_status)
                        self.state_manager.record_alert(p)
                        total_alerts += 1

                # Zustand aktualisieren
                p["last_seen"] = time.strftime("%Y-%m-%d %H:%M:%S")
                if "first_seen" not in p:
                    p["first_seen"] = old_product.get("first_seen", p["last_seen"]) if old_product else p["last_seen"]

                self.state_manager.set_product(key, p)
                self.state_manager.save()

            # Pause zwischen den Shops
            time.sleep(random.uniform(config.REQUEST_DELAY_MIN, config.REQUEST_DELAY_MAX))

        self.state_manager.record_check_finished()

        if first_run:
            log.info("Erster Durchlauf abgeschlossen: %d Produkte als Basis gespeichert. Ab jetzt werden Änderungen gemeldet!", len(self.state_manager.products))

        return {
            "shops_checked": len(enabled_shops),
            "products_found": total_found,
            "alerts_sent": total_alerts,
        }

    def run_loop(self):
        log.info("==================================================")
        log.info("🚀 Pokémon-TCG-Wächter (Satella) gestartet!")
        log.info("Intervall: %d Minuten | Sprachen: DE, EN, JP", config.CHECK_INTERVAL_MINUTES)
        log.info("Aktive Kanäle:")
        log.info(" - Telegram: %s", "✅ Aktiv" if config.TELEGRAM_BOT_TOKEN else "❌ Nicht konfiguriert")
        log.info(" - Discord:  %s", "✅ Aktiv" if config.DISCORD_WEBHOOK_URL else "❌ Nicht konfiguriert")
        log.info(" - ntfy.sh:  %s", f"✅ Aktiv ({config.NTFY_TOPIC})" if config.NTFY_TOPIC else "❌ Nicht konfiguriert")
        log.info("==================================================")

        self.start_telegram_listener()

        if config.WEB_ENABLED:
            try:
                web_server.start_web_server(self.state_manager, self, host=config.WEB_HOST, port=config.WEB_PORT)
            except Exception as e:
                log.warning("Konnte Web-Server nicht starten: %s", e)

        while True:
            try:
                self.is_checking = True
                self.check_all_shops()
            except Exception as e:
                log.exception("Unerwarteter Fehler im Hauptzyklus: %s", e)
            finally:
                self.is_checking = False

            # Pause bis zum nächsten Durchlauf (+ zufälliger Versatz)
            jitter = random.uniform(0, 90)
            sleep_seconds = (config.CHECK_INTERVAL_MINUTES * 60) + jitter
            log.info("Nächste geplante Überprüfung in %.1f Minuten.", sleep_seconds / 60)
            time.sleep(sleep_seconds)


def main():
    # CLI-Optionen
    if "--test" in sys.argv:
        print("Sende Test-Benachrichtigung an alle konfigurierten Kanäle...")
        notifier.notify_admin(
            "Pokémon-TCG-Wächter Test",
            "✅ Benachrichtigungen funktionieren einwandfrei!\n\n"
            "Der Bot ist bereit zur Überwachung von Displays, Boostern, ETBs und Tins."
        )
        print("Fertig!")
        return

    watcher = PokemonTCGWatcher()

    if "--once" in sys.argv:
        print("Führe einmaligen Scan durch...")
        stats = watcher.check_all_shops()
        print(f"Scan fertig: {stats['shops_checked']} Shops, {stats['products_found']} Produkte erfasst.")
        return

    try:
        watcher.run_loop()
    except KeyboardInterrupt:
        log.info("Bot durch Benutzer beendet (Strg+C). Auf Wiedersehen!")


if __name__ == "__main__":
    main()
