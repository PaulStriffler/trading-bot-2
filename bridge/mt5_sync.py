"""MT5 → Dashboard live sync.

Polls every active MT5 terminal configured in bridge/accounts.yaml and
writes a single dashboard/live.json with the combined snapshot. The
dashboard reads this file every few seconds and displays balance, equity,
margin and open P&L per account.

Run this on the Windows machine where MT5 is installed:

    python -m bridge.mt5_sync

It loops forever, writing fresh data every 5 seconds.

Prerequisites:
  pip install MetaTrader5 pyyaml

bridge/accounts.yaml example (see accounts.example.yaml).
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    import MetaTrader5 as mt5
except ImportError:
    print("ERROR: MetaTrader5 package not installed.")
    print("On Windows: pip install MetaTrader5")
    print("On macOS/Linux this package is not available — run this script on Windows.")
    sys.exit(1)

import yaml

ROOT = Path(__file__).resolve().parent.parent
LIVE_FILE = ROOT / "dashboard" / "live.json"
CONFIG_FILE = Path(__file__).parent / "accounts.yaml"
POLL_INTERVAL = 5  # seconds


def load_accounts() -> list[dict]:
    if not CONFIG_FILE.exists():
        print(f"No config at {CONFIG_FILE} — copy accounts.example.yaml and fill in your details.")
        sys.exit(1)
    with CONFIG_FILE.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f).get("accounts", [])


def snapshot_one(acc: dict) -> dict:
    """Initialise MT5 for one account, return its snapshot, then shutdown."""
    init_args = {"path": acc.get("terminal_path")} if acc.get("terminal_path") else {}
    if not mt5.initialize(**init_args):
        return {"id": acc["id"], "label": acc["label"], "error": f"initialize failed: {mt5.last_error()}"}

    # Login if explicit credentials given (terminal might already be logged in)
    if acc.get("login") and acc.get("password") and acc.get("server"):
        ok = mt5.login(int(acc["login"]), password=acc["password"], server=acc["server"])
        if not ok:
            err = mt5.last_error()
            mt5.shutdown()
            return {"id": acc["id"], "label": acc["label"], "error": f"login failed: {err}"}

    info = mt5.account_info()
    positions = mt5.positions_get() or []
    open_pnl = float(sum(p.profit for p in positions))

    result = {
        "id": acc["id"],
        "label": acc["label"],
        "broker": acc.get("broker", ""),
        "login": info.login,
        "name": info.name,
        "server": info.server,
        "currency": info.currency,
        "balance": float(info.balance),
        "equity": float(info.equity),
        "margin": float(info.margin),
        "margin_free": float(info.margin_free),
        "margin_level": float(info.margin_level) if info.margin else 0,
        "leverage": int(info.leverage),
        "open_pnl": round(open_pnl, 2),
        "positions_count": len(positions),
        "positions": [
            {
                "symbol": p.symbol,
                "type": "long" if p.type == mt5.ORDER_TYPE_BUY else "short",
                "volume": float(p.volume),
                "price_open": float(p.price_open),
                "price_current": float(p.price_current),
                "sl": float(p.sl) if p.sl else None,
                "tp": float(p.tp) if p.tp else None,
                "profit": float(p.profit),
            } for p in positions
        ],
        "error": None,
    }
    mt5.shutdown()
    return result


def write_snapshot(snapshots: list[dict]) -> None:
    total_balance = sum(s.get("balance", 0) for s in snapshots if not s.get("error"))
    total_equity = sum(s.get("equity", 0) for s in snapshots if not s.get("error"))
    total_open_pnl = sum(s.get("open_pnl", 0) for s in snapshots if not s.get("error"))
    data = {
        "ts": datetime.utcnow().isoformat() + "Z",
        "accounts": snapshots,
        "totals": {
            "balance": round(total_balance, 2),
            "equity": round(total_equity, 2),
            "open_pnl": round(total_open_pnl, 2),
        }
    }
    LIVE_FILE.parent.mkdir(exist_ok=True)
    LIVE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    # Fallback for file:// dashboards (browsers block fetch of local JSON)
    (LIVE_FILE.parent / "live.js").write_text(
        "window.LIVE_DATA = " + json.dumps(data) + ";", encoding="utf-8"
    )
    print(f"[{datetime.now().strftime('%H:%M:%S')}] "
          f"{len(snapshots)} account(s) · total balance ${total_balance:,.2f} · "
          f"equity ${total_equity:,.2f} · open P&L ${total_open_pnl:+,.2f}")


def main():
    accounts = load_accounts()
    if not accounts:
        print("No accounts configured.")
        sys.exit(1)
    print(f"Syncing {len(accounts)} account(s) every {POLL_INTERVAL}s.")
    print(f"Writing to: {LIVE_FILE}")
    print("Press Ctrl+C to stop.\n")

    while True:
        try:
            snapshots = [snapshot_one(a) for a in accounts]
            write_snapshot(snapshots)
        except KeyboardInterrupt:
            print("\nStopped.")
            break
        except Exception as e:
            print(f"ERROR: {e}")
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
