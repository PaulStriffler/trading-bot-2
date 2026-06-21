# Live Bridge — MT5 → Dashboard

Sync live account data (balance, equity, margin, open positions) from MetaTrader 5 into the dashboard.

## Setup (Windows — required for real MT5 connection)

1. **Install MT5 terminal(s)** and log into your FTMO / personal accounts.
   For multiple accounts, install MT5 into separate folders (e.g. `MetaTrader 5 FTMO/` and `MetaTrader 5 Personal/`).

2. **Python 3.10+** with packages:
   ```bash
   pip install MetaTrader5 pyyaml
   ```

3. **Configure accounts:**
   ```bash
   cp bridge/accounts.example.yaml bridge/accounts.yaml
   ```
   Edit `accounts.yaml` and set `terminal_path`, optionally `login`/`password`/`server`.

4. **Run the bridge:**
   ```bash
   python -m bridge.mt5_sync
   ```
   Writes to `dashboard/live.json` every 5 seconds. Leave it running while you trade.

5. **Open the dashboard** via a local HTTP server (so it can fetch `live.json`):
   ```bash
   cd dashboard
   python -m http.server 8080
   ```
   Then visit http://localhost:8080 in your browser.

## Mock mode (macOS / no MT5)

To preview the live UI without a real MT5 connection:

```bash
python -m bridge.mock_sync
```

Generates plausible fake data for two accounts (FTMO + Personal MT5) and writes to `dashboard/live.json` every 5s. You'll see the dashboard update with jittering equity/P&L values.

## FTMO compliance reminder

FTMO allows algorithmic trading **only with prior written approval**. This bridge is read-only — it polls account state and writes to disk, it does not place orders. Reading account data is generally allowed without approval. **Verify with FTMO support** before relying on any automation for your funded account.

## Architecture

```
MT5 Terminal (Windows) ──┐
                         ├──► bridge/mt5_sync.py ──► dashboard/live.json ──► Dashboard
MT5 Terminal #2 ─────────┘
```

The bridge is a one-way data pump. No orders are sent to the broker.
