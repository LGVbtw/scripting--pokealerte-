"""
Stock/pre-order availability watcher.
Reads public HTML of configured product pages, checks for availability
keywords, and pings a Discord webhook only on unavailable -> available
transitions. State persisted to state.json (committed back by the
GitHub Actions workflow between runs).
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

# --- Config: products to watch ---------------------------------------------
# name: display name used in Discord alert
# url: public product page URL
# keywords: any one of these found in the page HTML/text means "available"
PRODUCTS = {
    "guizette-family-etb": {
        "name": "ETB Règne Delta (Guizette Family)",
        "url": "https://www.guizettefamily.com/produit/etb-me06-regne-delta-pokemon/",
        "keywords": ["Ajouter au panier", "Précommander", "Acheter"],
    },
    "golden-poke-etb": {
        "name": "ETB Règne Delta (Golden Poke)",
        "url": "https://golden-poke.fr/produit/etb-me6-regne-delta/",
        "keywords": ["Ajouter au panier", "Précommander", "Acheter"],
    },
    "hikaru-distribution-etb": {
        "name": "ETB Delta Reign (Hikaru Distribution)",
        "url": "https://hikarudistribution.com/products/coffret-dresseur-d-elite-etb-pokemon-delta-reign-me06-francais",
        "keywords": ["Add to cart", "In stock", "Ajouter au panier"],
    },
}

STATE_FILE = Path(__file__).parent / "state.json"
REQUEST_TIMEOUT = 15
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
}

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")
DISCORD_USER_ID = os.environ.get("DISCORD_USER_ID", "").strip()


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def is_available(html: str, keywords: list[str]) -> bool:
    lowered = html.lower()
    return any(kw.lower() in lowered for kw in keywords)


def send_discord_alert(product_name: str, url: str) -> None:
    if not DISCORD_WEBHOOK_URL:
        print("DISCORD_WEBHOOK_URL not set, skipping notification.", file=sys.stderr)
        return

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    mention = f"<@{DISCORD_USER_ID}> " if DISCORD_USER_ID else ""
    payload = {
        "content": (
            f"{mention}**{product_name}** semble disponible !\n"
            f"{url}\n"
            f"Détecté le {timestamp}"
        ),
        "allowed_mentions": {"users": [DISCORD_USER_ID] if DISCORD_USER_ID else []},
    }
    resp = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()


def check_product(key: str, product: dict, state: dict) -> None:
    url = product["url"]
    name = product["name"]
    keywords = product["keywords"]

    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"[{key}] request failed: {exc}", file=sys.stderr)
        return

    available_now = is_available(resp.text, keywords)
    seen_before = key in state
    was_available = state.get(key, {}).get("available", False)

    if available_now and not was_available and seen_before:
        print(f"[{key}] became available -> sending Discord alert")
        try:
            send_discord_alert(name, url)
        except requests.RequestException as exc:
            print(f"[{key}] failed to send Discord alert: {exc}", file=sys.stderr)
            # keep previous state so we retry alerting on next run
            return
    else:
        print(f"[{key}] available={available_now} (was={was_available}, first_check={not seen_before})")

    state[key] = {
        "available": available_now,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


def main() -> None:
    state = load_state()
    for key, product in PRODUCTS.items():
        check_product(key, product, state)
    save_state(state)


if __name__ == "__main__":
    main()
