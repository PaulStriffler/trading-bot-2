"""Mock data generator — for previewing the live UI without MT5.

Writes plausible fake account data to dashboard/live.json every 5 seconds.
Run on Mac / Linux to see how the dashboard looks with live data.

    python -m bridge.mock_sync
"""
from __future__ import annotations

import json
import random
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIVE_FILE = ROOT / "dashboard" / "live.json"
INTERVAL = 5


def jitter(base: float, pct: float) -> float:
    return base * (1 + random.uniform(-pct, pct))


def snapshot():
    ftmo_balance = 10245.50
    ftmo_open_pnl = round(random.uniform(-80, 220), 2)
    personal_balance = 4980.00
    personal_open_pnl = round(random.uniform(-50, 80), 2)
    accounts = [
        {
            "id": "ftmo-swing-10k",
            "label": "FTMO Swing $10k",
            "broker": "FTMO",
            "login": 1234567,
            "name": "Paul Striffler",
            "server": "FTMO-Demo2",
            "currency": "USD",
            "balance": ftmo_balance,
            "equity": round(ftmo_balance + ftmo_open_pnl, 2),
            "margin": round(jitter(312.40, 0.01), 2),
            "margin_free": round(ftmo_balance + ftmo_open_pnl - 312, 2),
            "margin_level": round(jitter(3340, 0.01), 2),
            "leverage": 30,
            "open_pnl": ftmo_open_pnl,
            "positions_count": 1 if abs(ftmo_open_pnl) > 0 else 0,
            "positions": [
                {
                    "symbol": "US500",
                    "type": "long",
                    "volume": 0.30,
                    "price_open": 5439.20,
                    "price_current": round(jitter(5462.10, 0.0005), 2),
                    "sl": 5413.50,
                    "tp": 5510.40,
                    "profit": ftmo_open_pnl,
                }
            ] if abs(ftmo_open_pnl) > 0 else [],
            "error": None,
        },
        {
            "id": "personal-mt5",
            "label": "Personal MT5",
            "broker": "IC Markets",
            "login": 7891234,
            "name": "Paul Striffler",
            "server": "ICMarkets-Live01",
            "currency": "USD",
            "balance": personal_balance,
            "equity": round(personal_balance + personal_open_pnl, 2),
            "margin": round(jitter(180.0, 0.01), 2),
            "margin_free": round(personal_balance + personal_open_pnl - 180, 2),
            "margin_level": round(jitter(2780, 0.01), 2),
            "leverage": 30,
            "open_pnl": personal_open_pnl,
            "positions_count": 1 if abs(personal_open_pnl) > 0 else 0,
            "positions": [],
            "error": None,
        },
    ]
    total_balance = sum(a["balance"] for a in accounts)
    total_equity = sum(a["equity"] for a in accounts)
    total_open_pnl = sum(a["open_pnl"] for a in accounts)
    return {
        "ts": datetime.utcnow().isoformat() + "Z",
        "accounts": accounts,
        "totals": {
            "balance": round(total_balance, 2),
            "equity": round(total_equity, 2),
            "open_pnl": round(total_open_pnl, 2),
        }
    }


def main():
    LIVE_FILE.parent.mkdir(exist_ok=True)
    print(f"Mock sync writing to: {LIVE_FILE}")
    print(f"Update interval: {INTERVAL}s · Ctrl+C to stop\n")
    while True:
        try:
            data = snapshot()
            LIVE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
            # Also write live.js for file:// fallback (browsers block fetch of local JSON)
            (LIVE_FILE.parent / "live.js").write_text(
                "window.LIVE_DATA = " + json.dumps(data) + ";", encoding="utf-8"
            )
            print(f"[{datetime.now().strftime('%H:%M:%S')}] "
                  f"FTMO equity ${data['accounts'][0]['equity']:,.2f} · "
                  f"Personal equity ${data['accounts'][1]['equity']:,.2f} · "
                  f"total open P&L ${data['totals']['open_pnl']:+,.2f}")
        except KeyboardInterrupt:
            print("\nStopped.")
            break
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
