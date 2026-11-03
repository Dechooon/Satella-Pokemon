"""
Konfigurationsdatei für den Pokémon-TCG-Wächter (Satella).
Lädt Umgebungsvariablen aus .env und definiert Filter, Regex-Muster und Standardwerte.
"""
import os
import re
from pathlib import Path
from dotenv import load_dotenv

# Basisverzeichnis des Projekts
BASE_DIR = Path(__file__).resolve().parent

# .env Datei laden
load_dotenv(BASE_DIR / ".env")

# ==================== DATEIPFADE ====================
SHOPS_FILE = BASE_DIR / "shops.json"
STATE_FILE = BASE_DIR / "tcg_state.json"
LOG_FILE = BASE_DIR / "tcg_bot.log"

# ==================== BENACHRICHTIGUNGEN ====================
# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", os.getenv("TG_TOKEN", "")).strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", os.getenv("TG_CHAT", "")).strip()

# Discord Webhook
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "").strip()

# ntfy.sh (kostenlose Push-App ohne Registrierung)
NTFY_TOPIC = os.getenv("NTFY_TOPIC", "").strip()
NTFY_SERVER = os.getenv("NTFY_SERVER", "https://ntfy.sh").rstrip("/")

# ==================== WEB-SERVER & DASHBOARD ====================
WEB_ENABLED = os.getenv("WEB_ENABLED", "true").lower() in ("1", "true", "yes")
WEB_HOST = os.getenv("WEB_HOST", "0.0.0.0")
WEB_PORT = int(os.getenv("WEB_PORT", "5000"))

# ==================== ZEITEN & SCRAPING ====================
# Prüfintervall in Minuten
CHECK_INTERVAL_MINUTES = int(os.getenv("CHECK_INTERVAL_MINUTES", "10"))

# Pause zwischen Web-Anfragen in Sekunden (schont Shops und verhindert IP-Blocks)
REQUEST_DELAY_MIN = float(os.getenv("REQUEST_DELAY_MIN", "1.5"))
REQUEST_DELAY_MAX = float(os.getenv("REQUEST_DELAY_MAX", "3.5"))

# Detaillierte Produktseite aufrufen für genaue Status- und Preisprüfung?
CHECK_PRODUCT_PAGES = os.getenv("CHECK_PRODUCT_PAGES", "true").lower() in ("1", "true", "yes")

# Beim allerersten Start bereits vorhandene Produkte melden? (False = erst ab 2. Lauf Änderungen melden)
NOTIFY_FIRST_RUN = os.getenv("NOTIFY_FIRST_RUN", "false").lower() in ("1", "true", "yes")

# ==================== FILTER & KEYWORDS ====================
# Muss im Titel oder in der URL vorkommen
REQUIRE_KEYWORDS = [
    r"pok[eé]mon",
]

# Erlaubte Produkttypen (mindestens einer muss passen)
PRODUCT_KEYWORDS = [
    r"booster", r"display", r"top[\s-]?trainer[\s-]?box", r"\bTTB\b",
    r"elite[\s-]?trainer[\s-]?box", r"\bETB\b", r"blister", r"\btin\b",
    r"kollektion|collection", r"premium", r"build\s*&?\s*battle|baue?\s*&?\s*k(?:ä|ae)mpfe",
    r"theme ?deck|themendeck|starter ?deck|battle ?deck|league", r"bundle",
    r"sammelkarten|trading ?card|\bTCG\b|karten|cards", r"\bbox\b",
    r"case", r"koffer", r"mini[\s-]?tin", r"ultra[\s-]?premium", r"\bUPC\b"
]

# Kein Sammelkarten-Produkt -> ignorieren
EXCLUDE_KEYWORDS = [
    r"plüsch|plush|figur(?:en)?|figure|amiibo|\bnintendo[\s-]?switch\b|videospiel|\bvideo[\s-]?games?\b|spielzeug|\btoys?\b",
    r"lunchbox|rucksack|backpack|tasse|mug|t-shirt|shirt|hoodie|kleidung|socken",
    r"sleeves|hüllen|kartenhüllen|ordner|binder|album|playmat|spielmatte|deckbox",
    r"kostüm|costume|lego|puzzle|schlüsselanhänger|keychain|münze|coin|pin[\s-]?set"
]

# Erlaubte Sprachen (Deutsch, Englisch, Japanisch)
LANGUAGES_ALLOWED = {
    "Deutsch": r"deutsch|german|\(de\)|\bdeu\b|(?-i:\bDE\b|\bGER\b)",
    "Englisch": r"englisch|english|\(en\)|\beng\b|(?-i:\bEN\b|\bENG\b)",
    "Japanisch": r"japan|japanese|\(jp\)|\bjap\b|(?-i:\bJP\b|\bJPN\b|\bJAP\b)",
}

# Blockierte Sprachen (werden komplett ignoriert)
LANGUAGES_BLOCKED = (
    r"französisch|french|français|(?-i:\bFR\b|\bFRA\b)|italienisch|italian|italiano|(?-i:\bIT\b|\bITA\b)"
    r"|spanisch|spanish|español|(?-i:\bES\b|\bSP\b|\bESP\b)|koreanisch|korean|(?-i:\bKR\b|\bKOR\b)"
    r"|chinesisch|chinese|(?-i:\bCN\b|\bCHN\b|\bSCN\b|\bTCN\b)|portugies|portuguese|(?-i:\bPT\b)"
    r"|niederländisch|dutch|(?-i:\bNL\b)|polnisch|polish|thai|indonesisch|indonesian"
)

# Produkte ohne explizit genannte Sprache erlauben? (in DE-Shops meist deutsche Ware)
UNKNOWN_LANGUAGE_OK = os.getenv("UNKNOWN_LANGUAGE_OK", "true").lower() in ("1", "true", "yes")

# Status-Erkennung (Priorität von oben nach unten)
STATUS_PATTERNS = [
    ("vorbestellbar", r"vorbestell|vorverkauf|pre-?order|jetzt vorbestellen"),
    ("verfügbar", r"in den warenkorb|auf lager|sofort lieferbar|jetzt kaufen|in stock|lieferbar"),
    ("ausverkauft", r"ausverkauft|nicht verfügbar|nicht lieferbar|sold out|out of stock|derzeit vergriffen"),
]

# Statuswerte, bei denen Alarm geschlagen werden soll
ALERT_STATUSES = {"vorbestellbar", "verfügbar"}

# User-Agents zur Rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0",
]
