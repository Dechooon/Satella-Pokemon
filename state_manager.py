"""
Zustandsverwaltung für den Pokémon-TCG-Wächter.
Speichert erkannte Produkte, Statusänderungen, Historie und verwaltet die Shop-Liste.
"""
import json
import logging
import os
import time
from pathlib import Path
import config

log = logging.getLogger("tcg.state")


class StateManager:
    def __init__(self, state_file=config.STATE_FILE, shops_file=config.SHOPS_FILE):
        self.state_file = Path(state_file)
        self.shops_file = Path(shops_file)
        self.state = self._load_state()

    def _load_state(self):
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Falls altes Format (flaches Dict von Key -> Produkt)
                    if isinstance(data, dict) and "products" not in data:
                        return {
                            "products": data,
                            "last_check": None,
                            "recent_alerts": [],
                            "stats": {"checks_total": 0, "alerts_sent": 0}
                        }
                    return data
            except Exception as e:
                log.error("Fehler beim Laden von %s: %s", self.state_file, e)

        return {
            "products": {},
            "last_check": None,
            "recent_alerts": [],
            "stats": {"checks_total": 0, "alerts_sent": 0}
        }

    def save(self):
        tmp_file = self.state_file.with_suffix(".tmp")
        try:
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(self.state, f, ensure_ascii=False, indent=2)
            if self.state_file.exists():
                os.replace(tmp_file, self.state_file)
            else:
                tmp_file.rename(self.state_file)
        except Exception as e:
            log.error("Fehler beim Speichern von %s: %s", self.state_file, e)

    @property
    def products(self):
        return self.state.setdefault("products", {})

    def get_product(self, key):
        return self.products.get(key)

    def set_product(self, key, product_data):
        self.products[key] = product_data

    def record_alert(self, alert_item):
        """Speichert einen Alert in der Historie (maximal die letzten 50)."""
        recent = self.state.setdefault("recent_alerts", [])
        recent.insert(0, {
            **alert_item,
            "timestamp": time.strftime("%d.%m.%Y %H:%M:%S")
        })
        self.state["recent_alerts"] = recent[:50]
        stats = self.state.setdefault("stats", {"checks_total": 0, "alerts_sent": 0})
        stats["alerts_sent"] = stats.get("alerts_sent", 0) + 1

    def get_recent_alerts(self, limit=5):
        return self.state.get("recent_alerts", [])[:limit]

    def record_check_finished(self):
        self.state["last_check"] = time.strftime("%d.%m.%Y %H:%M:%S")
        stats = self.state.setdefault("stats", {"checks_total": 0, "alerts_sent": 0})
        stats["checks_total"] = stats.get("checks_total", 0) + 1
        self.save()

    # ==================== SHOPS-VERWALTUNG ====================
    def load_shops(self):
        if self.shops_file.exists():
            try:
                with open(self.shops_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                log.error("Fehler beim Laden von %s: %s", self.shops_file, e)
        return []

    def save_shops(self, shops):
        try:
            with open(self.shops_file, "w", encoding="utf-8") as f:
                json.dump(shops, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            log.error("Fehler beim Speichern von %s: %s", self.shops_file, e)
            return False

    def add_shop(self, name, url):
        shops = self.load_shops()
        for s in shops:
            if s["name"].lower() == name.lower():
                s["url"] = url
                s["enabled"] = True
                self.save_shops(shops)
                return "updated"
        shops.append({"name": name, "url": url, "enabled": True})
        self.save_shops(shops)
        return "added"

    def remove_shop(self, name):
        shops = self.load_shops()
        new_shops = [s for s in shops if s["name"].lower() != name.lower()]
        if len(new_shops) != len(shops):
            self.save_shops(new_shops)
            return True
        return False

    def toggle_shop(self, name):
        shops = self.load_shops()
        for s in shops:
            if s["name"].lower() == name.lower():
                s["enabled"] = not s.get("enabled", True)
                self.save_shops(shops)
                return s["enabled"]
        return None
