# Quick-Backtest (POC)

3-Wochen Proof-of-Concept des ICT/SMC-Setups auf US500, US30, US100, US2000.
Datenquelle: Yahoo Finance (gratis, kein MT5 nötig).

## Ausführen

```bash
python -m backtest.quick.run
```

## Vereinfachungen (gegenüber Phase 5)

- **News-Filter:** übersprungen.
- **Bias:** BOS-Regel (jüngster BOS in den letzten 8 Wochen) + Fallback „5 Closes in Folge".
- **Confluences:** Order Block + FVG + 4H-BOS. BPR/Equilibrium werden in Phase 3 nachgereicht. Mindestens 2 von 3 müssen vorliegen.
- **Spread/Slippage:** 0. SL-zuerst-Logik bei gleichzeitigem Touch (konservativ).
- **TPs:** TP1 = 1 R, TP3 = jüngste Daily Liquidity (Swing der letzten 30 1H-Bars), TP2 = Mittelwert.
- **Offene Trades:** am letzten Bar zum Close abgewickelt.

## Output

- Console-Log: Bias, gefundene Sweeps, Trades, P&L pro Symbol, Gesamtbilanz.
- CSV: `backtest/quick/results/trades.csv` (gitignored).
