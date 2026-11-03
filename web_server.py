"""
Web-Dashboard-Server für den Pokémon-TCG-Wächter (Satella).
Bietet eine übersichtliche Benutzeroberfläche im Browser unter http://localhost:5000
"""
import json
import logging
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import config
import notifier

log = logging.getLogger("tcg.web")

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Pokémon-TCG-Wächter (Satella)</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #0f172a;
      --card-bg: #1e293b;
      --card-border: #334155;
      --primary: #3b82f6;
      --primary-hover: #2563eb;
      --text: #f8fafc;
      --text-muted: #94a3b8;
      --success: #10b981;
      --warning: #f59e0b;
      --danger: #ef4444;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      background-color: var(--bg);
      color: var(--text);
      line-height: 1.5;
      padding: 24px;
    }
    .container { max-width: 1300px; margin: 0 auto; }
    header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 24px;
      flex-wrap: wrap;
      gap: 16px;
      padding-bottom: 16px;
      border-bottom: 1px solid var(--card-border);
    }
    .logo-area { display: flex; align-items: center; gap: 12px; }
    .logo-badge {
      background: linear-gradient(135deg, #ef4444, #f59e0b);
      color: white;
      font-weight: 700;
      padding: 6px 12px;
      border-radius: 8px;
      font-size: 14px;
      letter-spacing: 0.5px;
    }
    h1 { font-size: 24px; font-weight: 700; }
    .btn {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      background: var(--primary);
      color: white;
      border: none;
      padding: 8px 16px;
      border-radius: 8px;
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.2s;
      text-decoration: none;
    }
    .btn:hover { background: var(--primary-hover); transform: translateY(-1px); }
    .btn-secondary { background: #334155; }
    .btn-secondary:hover { background: #475569; }
    .btn-success { background: var(--success); }
    .btn-success:hover { background: #059669; }
    .btn-danger { background: var(--danger); padding: 4px 10px; font-size: 12px; }
    .btn-danger:hover { background: #dc2626; }
    
    /* Stats */
    .stats-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 16px;
      margin-bottom: 24px;
    }
    .stat-card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 16px;
    }
    .stat-title { font-size: 13px; color: var(--text-muted); font-weight: 500; }
    .stat-value { font-size: 26px; font-weight: 700; margin-top: 4px; }
    
    /* Tabs */
    .tabs {
      display: flex;
      gap: 8px;
      margin-bottom: 20px;
      border-bottom: 1px solid var(--card-border);
      padding-bottom: 8px;
    }
    .tab-btn {
      background: transparent;
      color: var(--text-muted);
      border: none;
      padding: 8px 16px;
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
      border-radius: 6px;
      transition: all 0.2s;
    }
    .tab-btn.active {
      background: var(--card-bg);
      color: var(--text);
      border: 1px solid var(--card-border);
    }
    .tab-content { display: none; }
    .tab-content.active { display: block; }

    /* Filter Bar */
    .filter-bar {
      display: flex;
      gap: 12px;
      margin-bottom: 20px;
      flex-wrap: wrap;
    }
    .input-search, .select-filter {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      color: var(--text);
      padding: 8px 14px;
      border-radius: 8px;
      font-size: 14px;
      outline: none;
    }
    .input-search { flex: 1; min-width: 250px; }
    .input-search:focus, .select-filter:focus { border-color: var(--primary); }

    /* Product Grid */
    .product-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(290px, 1fr));
      gap: 20px;
    }
    .product-card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      transition: transform 0.2s, border-color 0.2s;
    }
    .product-card:hover {
      transform: translateY(-2px);
      border-color: #475569;
    }
    .product-img-wrapper {
      width: 100%;
      height: 190px;
      background: #090d16;
      display: flex;
      align-items: center;
      justify-content: center;
      overflow: hidden;
    }
    .product-img {
      max-width: 90%;
      max-height: 90%;
      object-fit: contain;
      transition: transform 0.3s;
    }
    .product-card:hover .product-img { transform: scale(1.05); }
    .product-content {
      padding: 16px;
      display: flex;
      flex-direction: column;
      flex: 1;
    }
    .badges {
      display: flex;
      gap: 6px;
      flex-wrap: wrap;
      margin-bottom: 10px;
    }
    .badge {
      font-size: 11px;
      font-weight: 600;
      padding: 3px 8px;
      border-radius: 6px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }
    .badge-status-vorbestellbar { background: rgba(245, 158, 11, 0.15); color: #f59e0b; border: 1px solid rgba(245, 158, 11, 0.3); }
    .badge-status-verfügbar { background: rgba(16, 185, 129, 0.15); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.3); }
    .badge-status-ausverkauft { background: rgba(239, 68, 68, 0.15); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.3); }
    .badge-status-unbekannt { background: rgba(148, 163, 184, 0.15); color: #94a3b8; border: 1px solid rgba(148, 163, 184, 0.3); }
    .badge-lang { background: #334155; color: #cbd5e1; }
    .badge-shop { background: #1e3a8a; color: #93c5fd; }
    .product-title {
      font-size: 14px;
      font-weight: 600;
      color: var(--text);
      line-height: 1.4;
      margin-bottom: 12px;
      flex: 1;
    }
    .product-footer {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-top: auto;
      padding-top: 12px;
      border-top: 1px solid var(--card-border);
    }
    .product-price { font-size: 18px; font-weight: 700; color: #38bdf8; }
    .product-link {
      font-size: 13px;
      color: var(--primary);
      text-decoration: none;
      font-weight: 600;
      display: inline-flex;
      align-items: center;
      gap: 4px;
    }
    .product-link:hover { text-decoration: underline; }

    /* Tables */
    table { width: 100%; border-collapse: collapse; margin-top: 12px; }
    th, td {
      padding: 12px;
      text-align: left;
      border-bottom: 1px solid var(--card-border);
      font-size: 14px;
    }
    th { color: var(--text-muted); font-weight: 600; }
    tr:hover { background: rgba(255, 255, 255, 0.02); }
    .table-container {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      overflow: hidden;
      padding: 8px 16px;
    }
    
    /* Forms */
    .form-box {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 20px;
      margin-bottom: 24px;
    }
    .form-row {
      display: flex;
      gap: 12px;
      margin-top: 12px;
      flex-wrap: wrap;
    }
    .toast {
      position: fixed;
      bottom: 24px;
      right: 24px;
      background: var(--card-bg);
      border: 1px solid var(--primary);
      color: var(--text);
      padding: 12px 20px;
      border-radius: 8px;
      box-shadow: 0 10px 25px rgba(0,0,0,0.5);
      display: none;
      z-index: 1000;
    }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div class="logo-area">
        <span class="logo-badge">POKÉMON TCG</span>
        <h1>Satella Wächter Dashboard</h1>
      </div>
      <div style="display: flex; gap: 10px;">
        <button class="btn btn-secondary" onclick="triggerTest()">🧪 Test-Alert</button>
        <button class="btn" onclick="triggerScan()">🔄 Jetzt scannen</button>
      </div>
    </header>

    <!-- Stats -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-title">Systemstatus</div>
        <div class="stat-value" style="color: var(--success); font-size: 20px; margin-top: 8px;">● Online & Aktiv</div>
      </div>
      <div class="stat-card">
        <div class="stat-title">Überwachte Produkte</div>
        <div class="stat-value" id="stat-products">0</div>
      </div>
      <div class="stat-card">
        <div class="stat-title">Aktive Shops</div>
        <div class="stat-value" id="stat-shops">0</div>
      </div>
      <div class="stat-card">
        <div class="stat-title">Letzte Überprüfung</div>
        <div class="stat-value" id="stat-last-check" style="font-size: 16px; margin-top: 10px;">-</div>
      </div>
    </div>

    <!-- Navigation Tabs -->
    <div class="tabs">
      <button class="tab-btn active" onclick="switchTab('tab-products', this)">📦 Produkte (<span id="tab-count">0</span>)</button>
      <button class="tab-btn" onclick="switchTab('tab-shops', this)">🏪 Shops verwalten</button>
      <button class="tab-btn" onclick="switchTab('tab-config', this)">⚙️ Konfiguration & Hilfe</button>
    </div>

    <!-- Tab 1: Products -->
    <div id="tab-products" class="tab-content active">
      <div class="filter-bar">
        <input type="text" id="searchInput" class="input-search" placeholder="🔍 Nach Titel, Set oder Shop suchen..." oninput="renderProducts()">
        <select id="statusFilter" class="select-filter" onchange="renderProducts()">
          <option value="all">Alle Statuswerte</option>
          <option value="vorbestellbar">🟡 Nur Vorbestellbar</option>
          <option value="verfügbar">🟢 Nur Verfügbar</option>
          <option value="ausverkauft">🔴 Ausverkauft</option>
        </select>
        <select id="langFilter" class="select-filter" onchange="renderProducts()">
          <option value="all">Alle Sprachen</option>
          <option value="Deutsch">🇩🇪 Deutsch</option>
          <option value="Englisch">🇬🇧 Englisch</option>
          <option value="Japanisch">🇯🇵 Japanisch</option>
        </select>
      </div>

      <div class="product-grid" id="productGrid">
        <p style="color: var(--text-muted); padding: 20px;">Lade Produkte...</p>
      </div>
    </div>

    <!-- Tab 2: Shops -->
    <div id="tab-shops" class="tab-content">
      <div class="form-box">
        <h3>➕ Neuen Shop oder Kategorie hinzufügen</h3>
        <p style="color: var(--text-muted); font-size: 13px; margin-top: 4px;">Trage die URL einer Pokémon-Kategorie- oder Suchseite ein.</p>
        <div class="form-row">
          <input type="text" id="newShopName" class="input-search" placeholder="Shop- oder Kategoriename (z. B. Gate to the Games Displays)">
          <input type="text" id="newShopUrl" class="input-search" placeholder="https://www.shop.de/pokemon-karten/">
          <button class="btn btn-success" onclick="addShop()">Hinzufügen</button>
        </div>
      </div>

      <div class="table-container">
        <table>
          <thead>
            <tr>
              <th>Status</th>
              <th>Shop-Name</th>
              <th>Überwachte URL</th>
              <th>Aktionen</th>
            </tr>
          </thead>
          <tbody id="shopsTableBody"></tbody>
        </table>
      </div>
    </div>

    <!-- Tab 3: Config -->
    <div id="tab-config" class="tab-content">
      <div class="form-box">
        <h3>ℹ️ Push-Benachrichtigungskanäle</h3>
        <p style="color: var(--text-muted); font-size: 14px; margin-top: 8px;">
          Aktive Kanäle werden aus der Datei <code>.env</code> im Projektordner geladen:
        </p>
        <div style="margin-top: 16px; display: grid; gap: 12px; font-size: 14px;">
          <div style="background: #090d16; padding: 12px; border-radius: 8px;">
            <b>🤖 Telegram Bot:</b> Befehle direkt im Chat: <code>/check</code>, <code>/status</code>, <code>/shops</code>, <code>/addshop</code>
          </div>
          <div style="background: #090d16; padding: 12px; border-radius: 8px;">
            <b>💬 Discord Webhook:</b> Formatiert Push-Meldungen mit Farb-Embeds & Bildern
          </div>
          <div style="background: #090d16; padding: 12px; border-radius: 8px;">
            <b>📱 ntfy.sh:</b> Kostenlose Smartphone-App (iOS & Android) ohne Account
          </div>
        </div>
      </div>
    </div>
  </div>

  <div id="toast" class="toast"></div>

  <script>
    let appData = { products: {}, shops: [], stats: {}, last_check: "" };

    async function loadData() {
      try {
        const res = await fetch('/api/data');
        appData = await res.json();
        updateUI();
      } catch (e) {
        console.error('Fehler beim Laden:', e);
      }
    }

    function updateUI() {
      const prodKeys = Object.keys(appData.products || {});
      document.getElementById('stat-products').innerText = prodKeys.length;
      document.getElementById('tab-count').innerText = prodKeys.length;
      
      const enabledShops = (appData.shops || []).filter(s => s.enabled !== false).length;
      document.getElementById('stat-shops').innerText = `${enabledShops} / ${(appData.shops || []).length}`;
      document.getElementById('stat-last-check').innerText = appData.last_check || 'Wird gerade initialisiert...';

      renderProducts();
      renderShops();
    }

    function renderProducts() {
      const grid = document.getElementById('productGrid');
      const search = document.getElementById('searchInput').value.toLowerCase();
      const statusFilter = document.getElementById('statusFilter').value;
      const langFilter = document.getElementById('langFilter').value;

      const items = Object.values(appData.products || {});
      const filtered = items.filter(p => {
        const text = `${p.title || ''} ${p.shop || ''}`.toLowerCase();
        if (search && !text.includes(search)) return false;
        if (statusFilter !== 'all' && (p.status || 'unbekannt') !== statusFilter) return false;
        if (langFilter !== 'all' && (p.language || 'unbekannt') !== langFilter) return false;
        return true;
      });

      if (filtered.length === 0) {
        grid.innerHTML = '<p style="color: var(--text-muted); padding: 40px; grid-column: 1/-1; text-align: center;">Keine passenden Pokémon-Produkte gefunden.</p>';
        return;
      }

      grid.innerHTML = filtered.map(p => {
        const statusClass = `badge-status-${p.status || 'unbekannt'}`;
        const statusText = p.status === 'vorbestellbar' ? '🟡 Vorbestellbar' :
                           p.status === 'verfügbar' ? '🟢 Verfügbar' :
                           p.status === 'ausverkauft' ? '🔴 Ausverkauft' : '⚪ Gelistet';
        const img = p.image || 'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/poke-ball.png';
        const price = p.price || 'Preis prüfen';

        return `
          <div class="product-card">
            <div class="product-img-wrapper">
              <img src="${img}" alt="${p.title}" class="product-img" onerror="this.src='https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/poke-ball.png'">
            </div>
            <div class="product-content">
              <div class="badges">
                <span class="badge ${statusClass}">${statusText}</span>
                <span class="badge badge-shop">${p.shop || 'Shop'}</span>
                <span class="badge badge-lang">${p.language || 'Unbekannt'}</span>
              </div>
              <div class="product-title" title="${p.title}">${p.title}</div>
              <div class="product-footer">
                <span class="product-price">${price}</span>
                <a href="${p.url}" target="_blank" rel="noopener" class="product-link">Zum Shop ↗</a>
              </div>
            </div>
          </div>
        `;
      }).join('');
    }

    function renderShops() {
      const tbody = document.getElementById('shopsTableBody');
      const shops = appData.shops || [];

      tbody.innerHTML = shops.map(s => {
        const active = s.enabled !== false;
        return `
          <tr>
            <td><span class="badge ${active ? 'badge-status-verfügbar' : 'badge-status-ausverkauft'}">${active ? 'Aktiv' : 'Pausiert'}</span></td>
            <td><b>${s.name}</b></td>
            <td><a href="${s.url}" target="_blank" style="color: var(--primary); text-decoration: none; word-break: break-all;">${s.url}</a></td>
            <td>
              <div style="display: flex; gap: 6px;">
                <button class="btn btn-secondary" style="padding: 4px 10px; font-size: 12px;" onclick="toggleShop('${s.name}')">${active ? 'Pausieren' : 'Aktivieren'}</button>
                <button class="btn btn-danger" onclick="deleteShop('${s.name}')">Löschen</button>
              </div>
            </td>
          </tr>
        `;
      }).join('');
    }

    function switchTab(tabId, el) {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
      el.classList.add('active');
      document.getElementById(tabId).classList.add('active');
    }

    function showToast(msg) {
      const t = document.getElementById('toast');
      t.innerText = msg;
      t.style.display = 'block';
      setTimeout(() => { t.style.display = 'none'; }, 3000);
    }

    async function triggerScan() {
      showToast('🔄 Scan gestartet...');
      await fetch('/api/check', { method: 'POST' });
      setTimeout(loadData, 2000);
    }

    async function triggerTest() {
      showToast('🧪 Test-Alarm gesendet!');
      await fetch('/api/test', { method: 'POST' });
    }

    async function addShop() {
      const name = document.getElementById('newShopName').value.trim();
      const url = document.getElementById('newShopUrl').value.trim();
      if (!name || !url) return alert('Bitte Name und URL angeben!');
      await fetch('/api/shops/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, url })
      });
      document.getElementById('newShopName').value = '';
      document.getElementById('newShopUrl').value = '';
      showToast('✅ Shop hinzugefügt!');
      loadData();
    }

    async function toggleShop(name) {
      await fetch('/api/shops/toggle', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name })
      });
      loadData();
    }

    async function deleteShop(name) {
      if (!confirm(`Shop "${name}" wirklich löschen?`)) return;
      await fetch('/api/shops/delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name })
      });
      loadData();
    }

    // Auto-refresh alle 15 Sekunden
    loadData();
    setInterval(loadData, 15000);
  </script>
</body>
</html>
"""


class DashboardRequestHandler(BaseHTTPRequestHandler):
    state_manager = None
    watcher = None

    def log_message(self, format, *args):
        # Ruhige Logs
        return

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path in ("/", "/index.html"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode("utf-8"))

        elif parsed.path == "/api/data":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            data = {
                "products": self.state_manager.products if self.state_manager else {},
                "shops": self.state_manager.load_shops() if self.state_manager else [],
                "stats": self.state_manager.state.get("stats", {}) if self.state_manager else {},
                "last_check": self.state_manager.state.get("last_check") if self.state_manager else "",
            }
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)
        content_length = int(self.headers.get("Content-Length", 0))
        post_body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else ""

        payload = {}
        if post_body:
            try:
                payload = json.loads(post_body)
            except Exception:
                pass

        if parsed.path == "/api/check":
            if self.watcher:
                threading.Thread(target=self.watcher.run_manual_check, daemon=True).start()
            self._send_json({"ok": True, "message": "Check gestartet"})

        elif parsed.path == "/api/test":
            notifier.notify_admin(
                "Pokémon-TCG-Wächter Test",
                "✅ Web-Dashboard Verbindung erfolgreich!\nDer Bot läuft und überwacht aktiv Shops."
            )
            self._send_json({"ok": True, "message": "Test gesendet"})

        elif parsed.path == "/api/shops/add":
            name = payload.get("name", "").strip()
            url = payload.get("url", "").strip()
            if name and url and self.state_manager:
                self.state_manager.add_shop(name, url)
                self._send_json({"ok": True})
            else:
                self._send_json({"ok": False, "error": "Fehlende Angaben"}, status=400)

        elif parsed.path == "/api/shops/toggle":
            name = payload.get("name", "").strip()
            if name and self.state_manager:
                new_state = self.state_manager.toggle_shop(name)
                self._send_json({"ok": True, "enabled": new_state})
            else:
                self._send_json({"ok": False}, status=400)

        elif parsed.path == "/api/shops/delete":
            name = payload.get("name", "").strip()
            if name and self.state_manager:
                self.state_manager.remove_shop(name)
                self._send_json({"ok": True})
            else:
                self._send_json({"ok": False}, status=400)

        else:
            self.send_response(404)
            self.end_headers()

    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))


def start_web_server(state_manager, watcher, host="0.0.0.0", port=5000):
    """Startet den Web-Server im Hintergrund."""
    DashboardRequestHandler.state_manager = state_manager
    DashboardRequestHandler.watcher = watcher

    server = ThreadingHTTPServer((host, port), DashboardRequestHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True, name="WebServer")
    thread.start()
    log.info("🌐 Web-Dashboard gestartet unter: http://localhost:%d", port)
    return server
