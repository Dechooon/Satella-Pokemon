# ⚡ Pokémon-TCG-Wächter (Satella)

Ein automatisierter Wächter & Bot, der Onlineshops kontinuierlich auf **Pokémon-Sammelkarten-Produkte** (Booster, Displays, Top-Trainer-Boxen / ETBs, Tins, Kollektionen & Blister) überwacht.

Unterstützt **Deutsch 🇩🇪**, **Englisch 🇬🇧** und **Japanisch 🇯🇵**. Andere Sprachen (Französisch, Italienisch, Spanisch, Koreanisch, Chinesisch etc.) und Non-TCG-Merchandise (Plüsch, Konsolen, Videospiele, Hüllen) werden automatisch gefiltert.

Meldet sofort per Push über **Telegram** (inkl. Produktbild & Schnellkauf-Link), **Discord Webhook** und **ntfy.sh**, sobald ein neues Produkt gelistet wird oder ein Artikel wieder verfügbar/vorbestellbar ist!

---

## 🌟 Features

- 🔍 **Intelligentes Scraping:** Erkennt Titel, Preis in Euro, Produktbilder, Verfügbarkeit (`vorbestellbar`, `verfügbar`, `ausverkauft`) und Sprache.
- 💬 **Interaktiver Telegram-Bot:** Steuerbar direkt aus dem Chat mit Befehlen (`/check`, `/status`, `/shops`, `/addshop`, `/last`, etc.).
- 📸 **Bilder & Schnellkauf-Links:** Push-Nachrichten zeigen direkt das Produktfoto, den aktuellen Preis und den direkten Shop-Link.
- 🛡️ **Bannschutz:** Rotierende User-Agents und zufällige Zeitversätze (Jitter) schützen vor Blockaden.
- 🏪 **Einfache Shop-Verwaltung:** Vorkonfigurierte Shops in `shops.json` oder direkt via Telegram-Befehl `/addshop`.
- 📁 **Lokale Zustandsspeicherung:** Merkt sich bekannte Produkte in `tcg_state.json` und verhindert doppelte Alarme.

---

## 🚀 Schnellanleitung (3 Schritte)

### 1. Abhängigkeiten installieren
Die benötigten Bibliotheken (`requests`, `beautifulsoup4`, `python-dotenv`) sind bereits vorbereitet. Falls nötig:
```cmd
install_requirements.bat
```

### 2. Benachrichtigungskanal einrichten (`.env`)
Öffne die Datei `.env` mit einem Texteditor (z. B. Notepad).

#### Option A: Telegram (Empfohlen)
1. Öffne Telegram und starte einen Chat mit **[@BotFather](https://t.me/BotFather)**.
2. Sende `/newbot`, wähle einen Namen (z. B. `MeinPokemonWaechterBot`) und einen Nutzernamen.
3. Kopiere den Token in deine `.env`:
   ```env
   TELEGRAM_BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ
   ```
4. **Deine Chat-ID herausfinden:**
   - Starte den Bot mit `start.bat`.
   - Öffne Telegram, suche nach deinem neuen Bot und sende ihm einfach: `/start`.
   - Der Bot antwortet dir sofort mit deiner genauen **Chat-ID**!
   - Trage diese Chat-ID in die `.env` ein:
     ```env
     TELEGRAM_CHAT_ID=123456789
     ```

#### Option B: Discord Webhook (Optional)
- In Discord: *Server-Einstellungen* ➔ *Integrationen* ➔ *Webhooks* ➔ *Neuer Webhook*.
- URL kopieren und in `.env` eintragen:
  ```env
  DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
  ```

#### Option C: ntfy.sh (Kostenlos & ohne Registrierung)
- Installiere die kostenlose **ntfy**-App auf deinem Smartphone (iOS/Android).
- Wähle ein beliebiges geheimes Topic (z. B. `mein-pokemon-alarm-8899`) und trage es ein:
  ```env
  NTFY_TOPIC=mein-pokemon-alarm-8899
  ```

### 3. Starten
Klicke doppelt auf:
```cmd
start.bat
```
Der Bot beginnt nun sofort mit der Überwachung!

---

## 📱 Telegram-Befehle (Chat-Steuerung)

Sobald der Bot läuft, kannst du ihm im Telegram-Chat folgende Befehle senden:

| Befehl | Beschreibung |
|---|---|
| `/check` | Startet sofort einen manuellen Scan über alle aktiven Shops |
| `/status` | Zeigt Uptime, Anzahl Shops, überwachte Produkte & Statistiken |
| `/shops` | Listet alle konfigurierten Shops und deren Status (`🟢 aktiv` / `⏸ pausiert`) |
| `/addshop <Name> <URL>` | Fügt direkt einen neuen Shop oder eine neue Kategorie-URL hinzu |
| `/toggleshop <Name>` | Aktiviert oder pausiert einen bestimmten Shop |
| `/delshop <Name>` | Entfernt einen Shop aus der Überwachungsliste |
| `/last` | Zeigt die letzten 5 erkannten Produkte/Alarme an |
| `/test` | Sendet eine Test-Benachrichtigung an alle konfigurierten Kanäle |
| `/help` | Zeigt die Übersicht aller Befehle |

---

## 🏪 Shops anpassen (`shops.json`)

Die zu überwachenden Shops sind in der Datei `shops.json` hinterlegt:

```json
[
  {
    "name": "Gate to the Games - Displays",
    "url": "https://www.gate-to-the-games.de/Pokemon-Karten/Pokemon-Displays/",
    "enabled": true
  },
  {
    "name": "Card-Corner - Displays",
    "url": "https://www.card-corner.de/Pokemon-Display",
    "enabled": true
  }
]
```

Du kannst beliebig viele Shops oder Unterkategorien hinzufügen:
- Kategorieseiten (z. B. `/pokemon-displays`, `/pokemon-booster`)
- Suchseiten (z. B. `/suche?q=pokemon+display`)

---

## ⚙️ Erweiterte Konfiguration (`config.py` & `.env`)

In der `.env` kannst du das Verhalten feinjustieren:

| Einstellung | Standard | Beschreibung |
|---|---|---|
| `CHECK_INTERVAL_MINUTES` | `10` | Grundintervall zwischen Prüfungen in Minuten |
| `REQUEST_DELAY_MIN` / `MAX` | `1.5` / `3.5` | Zufällige Pause zwischen einzelnen Seitenaufrufen |
| `CHECK_PRODUCT_PAGES` | `true` | Ruft Produktseiten für genauen Preis, Bild und Live-Status auf |
| `UNKNOWN_LANGUAGE_OK` | `true` | Akzeptiert Produkte ohne explizite Sprachangabe (in DE-Shops meist deutsch) |
| `NOTIFY_FIRST_RUN` | `false` | Verhindert Nachrichten-Spam beim allerersten Start (legt nur die Datenbasis an) |

---

## 🧪 Verbindung testen

Um sofort zu testen, ob deine Push-Nachrichten ankommen:
```cmd
test_notification.bat
```
oder im Terminal:
```bash
python bot.py --test
```
