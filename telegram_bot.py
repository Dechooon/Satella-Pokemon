"""
Interaktiver Telegram-Bot-Listener für den Pokémon-TCG-Wächter.
Ermöglicht die Steuerung und Statusabfrage via Telegram-Befehle (/status, /check, /shops, /addshop etc.).
"""
import logging
import threading
import time
import requests
import config

log = logging.getLogger("tcg.telegram_bot")


class TelegramBotListener:
    def __init__(self, state_manager, trigger_check_callback=None):
        self.state_manager = state_manager
        self.trigger_check_callback = trigger_check_callback
        self.token = config.TELEGRAM_BOT_TOKEN
        self.chat_id = config.TELEGRAM_CHAT_ID
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self.last_update_id = 0
        self.is_running = False
        self.thread = None

    def start(self):
        if not self.token:
            log.info("Kein TELEGRAM_BOT_TOKEN konfiguriert - Telegram-Listener inaktiv.")
            return
        self.is_running = True
        self.thread = threading.Thread(target=self._poll_loop, daemon=True, name="TelegramListener")
        self.thread.start()
        log.info("Telegram-Bot-Listener gestartet. Höre auf Befehle...")

    def stop(self):
        self.is_running = False

    def send_reply(self, chat_id, text, parse_mode="HTML"):
        try:
            requests.post(
                f"{self.base_url}/sendMessage",
                data={"chat_id": chat_id, "text": text, "parse_mode": parse_mode},
                timeout=10,
            )
        except Exception as e:
            log.error("Fehler beim Senden der Telegram-Antwort: %s", e)

    def _poll_loop(self):
        while self.is_running:
            try:
                params = {"timeout": 20, "offset": self.last_update_id + 1}
                resp = requests.get(f"{self.base_url}/getUpdates", params=params, timeout=25)
                if resp.status_code != 200:
                    time.sleep(5)
                    continue

                data = resp.json()
                if not data.get("ok"):
                    time.sleep(5)
                    continue

                for update in data.get("result", []):
                    self.last_update_id = update["update_id"]
                    msg = update.get("message")
                    if not msg or "text" not in msg:
                        continue

                    sender_chat_id = str(msg["chat"]["id"])
                    text = msg["text"].strip()

                    self._handle_command(sender_chat_id, text)

            except requests.RequestException:
                time.sleep(5)
            except Exception as e:
                log.error("Unerwarteter Fehler im Telegram-Listener: %s", e)
                time.sleep(5)

    def _handle_command(self, sender_chat_id, text):
        # Falls Chat-ID noch nicht gesetzt ist, informieren
        if not self.chat_id:
            reply = (
                f"👋 <b>Willkommen beim Pokémon-TCG-Wächter!</b>\n\n"
                f"Deine Telegram Chat-ID lautet:\n<code>{sender_chat_id}</code>\n\n"
                f"👉 Bitte trage diese in deiner <code>.env</code> Datei ein:\n"
                f"<code>TELEGRAM_CHAT_ID={sender_chat_id}</code>\n"
                f"Danach kannst du alle Bot-Befehle nutzen!"
            )
            self.send_reply(sender_chat_id, reply)
            return

        # Sicherheitsprüfung: Nur der autorisierte Nutzer darf Befehle ausführen
        if sender_chat_id != self.chat_id:
            log.warning("Nicht autorisierter Zugriff von Chat-ID %s versucht: %s", sender_chat_id, text)
            self.send_reply(sender_chat_id, "⛔ Zugriff verweigert: Unbekannter Chat.")
            return

        cmd_parts = text.split(maxsplit=2)
        cmd = cmd_parts[0].lower()

        if cmd in ("/start", "/help", "hilfe"):
            self._cmd_help(sender_chat_id)
        elif cmd in ("/status", "status"):
            self._cmd_status(sender_chat_id)
        elif cmd in ("/check", "check", "/scan"):
            self._cmd_check(sender_chat_id)
        elif cmd in ("/shops", "shops"):
            self._cmd_shops(sender_chat_id)
        elif cmd in ("/addshop", "addshop"):
            self._cmd_addshop(sender_chat_id, cmd_parts)
        elif cmd in ("/delshop", "delshop", "/removeshop"):
            self._cmd_delshop(sender_chat_id, cmd_parts)
        elif cmd in ("/toggleshop", "toggleshop"):
            self._cmd_toggleshop(sender_chat_id, cmd_parts)
        elif cmd in ("/last", "last", "/letzte"):
            self._cmd_last(sender_chat_id)
        elif cmd in ("/test", "test"):
            self._cmd_test(sender_chat_id)
        else:
            self.send_reply(sender_chat_id, "Unbekannter Befehl. Tippe /help für eine Übersicht.")

    def _cmd_help(self, chat_id):
        msg = (
            "🤖 <b>Pokémon-TCG-Wächter Befehle</b>\n\n"
            "🔍 <b>/check</b> - Sofortige Überprüfung aller Shops anstoßen\n"
            "📊 <b>/status</b> - Aktueller Zustand & Statistiken\n"
            "🏪 <b>/shops</b> - Liste aller überwachten Shops anzeigen\n"
            "➕ <b>/addshop &lt;Name&gt; &lt;URL&gt;</b> - Neuen Shop hinzufügen\n"
            "🔄 <b>/toggleshop &lt;Name&gt;</b> - Shop aktivieren/pausieren\n"
            "❌ <b>/delshop &lt;Name&gt;</b> - Shop aus der Überwachung entfernen\n"
            "📦 <b>/last</b> - Die letzten 5 erkannten Produkte anzeigen\n"
            "🧪 <b>/test</b> - Test-Alarm senden\n"
            "ℹ️ <b>/help</b> - Diese Hilfe anzeigen"
        )
        self.send_reply(chat_id, msg)

    def _cmd_status(self, chat_id):
        shops = self.state_manager.load_shops()
        active_shops = sum(1 for s in shops if s.get("enabled", True))
        total_products = len(self.state_manager.products)
        stats = self.state_manager.state.get("stats", {})
        last_check = self.state_manager.state.get("last_check") or "Noch kein Durchlauf"

        msg = (
            "📊 <b>Systemstatus</b>\n\n"
            f"🏪 <b>Überwachte Shops:</b> {active_shops}/{len(shops)} aktiv\n"
            f"📦 <b>Bekannte Produkte:</b> {total_products}\n"
            f"🕒 <b>Letzte Prüfung:</b> {last_check}\n"
            f"⏱ <b>Prüfintervall:</b> ca. {config.CHECK_INTERVAL_MINUTES} Min.\n"
            f"🚨 <b>Gesendete Alerts:</b> {stats.get('alerts_sent', 0)}\n"
            f"🔄 <b>Durchgeführte Scans:</b> {stats.get('checks_total', 0)}\n"
            f"🌐 <b>Erlaubte Sprachen:</b> Deutsch, Englisch, Japanisch"
        )
        self.send_reply(chat_id, msg)

    def _cmd_check(self, chat_id):
        self.send_reply(chat_id, "⏳ <b>Sofortige Prüfung gestartet!</b> Ich scanne jetzt alle Shops...")
        if self.trigger_check_callback:
            threading.Thread(target=self.trigger_check_callback, args=(chat_id,), daemon=True).start()

    def _cmd_shops(self, chat_id):
        shops = self.state_manager.load_shops()
        if not shops:
            self.send_reply(chat_id, "Aktuell sind keine Shops konfiguriert.")
            return

        lines = ["🏪 <b>Konfigurierte Shops:</b>\n"]
        for s in shops:
            status_icon = "🟢" if s.get("enabled", True) else "⏸"
            lines.append(f"{status_icon} <b>{s['name']}</b>\n🔗 <code>{s['url']}</code>\n")

        self.send_reply(chat_id, "\n".join(lines))

    def _cmd_addshop(self, chat_id, parts):
        if len(parts) < 3:
            self.send_reply(chat_id, "Format: <code>/addshop &lt;Shopname&gt; &lt;URL&gt;</code>")
            return
        name = parts[1]
        url = parts[2].strip()
        if not url.startswith("http"):
            self.send_reply(chat_id, "❌ Bitte eine gültige URL angeben (beginnend mit http:// oder https://).")
            return

        res = self.state_manager.add_shop(name, url)
        if res == "added":
            self.send_reply(chat_id, f"✅ Shop <b>{name}</b> erfolgreich hinzugefügt und aktiviert!")
        else:
            self.send_reply(chat_id, f"🔄 Shop <b>{name}</b> wurde aktualisiert!")

    def _cmd_toggleshop(self, chat_id, parts):
        if len(parts) < 2:
            self.send_reply(chat_id, "Format: <code>/toggleshop &lt;Shopname&gt;</code>")
            return
        name = parts[1]
        new_state = self.state_manager.toggle_shop(name)
        if new_state is None:
            self.send_reply(chat_id, f"❌ Shop '{name}' wurde nicht gefunden.")
        else:
            state_text = "aktiviert 🟢" if new_state else "pausiert ⏸"
            self.send_reply(chat_id, f"Shop <b>{name}</b> ist jetzt {state_text}.")

    def _cmd_delshop(self, chat_id, parts):
        if len(parts) < 2:
            self.send_reply(chat_id, "Format: <code>/delshop &lt;Shopname&gt;</code>")
            return
        name = parts[1]
        if self.state_manager.remove_shop(name):
            self.send_reply(chat_id, f"🗑 Shop <b>{name}</b> wurde entfernt.")
        else:
            self.send_reply(chat_id, f"❌ Shop '{name}' wurde nicht gefunden.")

    def _cmd_last(self, chat_id):
        recent = self.state_manager.get_recent_alerts(5)
        if not recent:
            self.send_reply(chat_id, "Bisher wurden noch keine neuen Produkte gemeldet.")
            return

        lines = ["📦 <b>Die letzten erkannten Produkte:</b>\n"]
        for p in recent:
            lines.append(
                f"• <b>{p.get('title')}</b>\n"
                f"  🏪 {p.get('shop')} | {p.get('price') or 'k.A.'} | {p.get('status')}\n"
                f"  🕒 {p.get('timestamp')}\n"
                f"  🔗 <a href=\"{p.get('url')}\">Link zum Shop</a>\n"
            )
        self.send_reply(chat_id, "\n".join(lines))

    def _cmd_test(self, chat_id):
        self.send_reply(chat_id, "🧪 Sende Test-Benachrichtigung an alle konfigurierten Kanäle...")
        import notifier
        notifier.notify_admin(
            "Pokémon-TCG-Wächter Test",
            "✅ Verbindung erfolgreich!\nDer Bot überwacht aktiv Shops auf Booster, Displays, ETBs und Tins."
        )
