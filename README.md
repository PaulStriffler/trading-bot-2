# Trading Bot 2 — ICT/SMC Multi-Timeframe für US-Indizes

Automatisierter Bot, der die Smart-Money-Strategie aus [`Trading_Strategie_Masterplan.docx`](Trading_Strategie_Masterplan.docx) auf **US500, US30, US100, US2000** ausführt — via MetaTrader 5, 30× Hebel, 1 % Risk auf einem 10.000 € Account.

## Strategie auf einen Blick

Top-Down Multi-Timeframe Analyse:

| Schritt | Timeframe | Was passiert |
|---|---|---|
| 0 | — | News-Filter (Forex Factory, High-Impact-Events meiden) |
| 1 | Weekly | Bias bestimmen (BOS oder 5 Closes in Folge) |
| 2 | Daily | Liquidity Sweep abwarten |
| 3 | 4H | Min. 2 von 4 Confluences (OB, FVG, BPR, Equilibrium), eine davon BOS |
| 4 | 1H | Entry bei Reaktion + BOS |
| 5 | — | SL = Sweep ± 0,5 × ATR(4H); 3 TPs (1:1, mid, Daily Liq/Fib) |

Details: siehe [`docs/STRATEGY.md`](docs/STRATEGY.md) und [`configs/strategy.yaml`](configs/strategy.yaml).

## Projektstruktur

```
.
├── bot/              # Strategie-Bausteine + Live-Engine
├── backtest/         # Backtest-Engine + Reports
├── dashboard/        # FastAPI Backend + React Frontend
│   ├── backend/
│   └── frontend/
├── configs/          # strategy.yaml — zentrale Parameter
├── data/             # Marktdaten-Cache (gitignored)
├── docs/             # Strategie-Doku
└── tests/            # Unit-Tests
```

## Setup

```bash
# Python 3.11+ empfohlen
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

> **Hinweis:** `MetaTrader5` ist Windows-only. Auf macOS läuft der Bot im Backtest-Modus; für Live-Trading wird ein Windows-Host (Bootcamp, VM, VPS) benötigt.

## Roadmap (10 Phasen)

- [x] **Phase 1** — Repo-Setup & Architektur
- [ ] Phase 2 — Datenbeschaffung (MT5 + Fallback CSV, 10 Jahre History)
- [ ] Phase 3 — Strategie-Bausteine als testbare Pure Functions
- [ ] Phase 4 — Strategie-Engine (Orchestrierung + News-Filter)
- [ ] Phase 5 — Backtester
- [ ] Phase 6 — Tuning & Walk-Forward-Validierung
- [ ] Phase 7 — Browser-Dashboard
- [ ] Phase 8 — Paper-Trading auf MT5 Demo
- [ ] Phase 9 — Live-Trading (klein anfangen)
- [ ] Phase 10 — Monitoring & Wartung

## Account-Parameter

| | |
|---|---|
| Account | 10.000 € |
| Hebel | 30× |
| Risk pro Trade | 1 % (Phase 9: Start mit 0,25 %) |
| Daily Loss Limit | 3 % (Kill-Switch) |
| Märkte | US500, US30, US100, US2000 |

## Disclaimer

Dies ist Software für **persönliche Forschung und Paper-Trading**. Kein Anlageberatung. Live-Trading auf eigenes Risiko.
