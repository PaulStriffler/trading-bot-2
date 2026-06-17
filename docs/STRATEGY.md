# Strategie — Detailbeschreibung

Quelle: [`Trading_Strategie_Masterplan.docx`](../Trading_Strategie_Masterplan.docx)

## 0. News-Filter (Pre-Trade)
- Forex Factory Wirtschaftskalender prüfen.
- Trading-Stopp 30 min vor / 15 min nach High-Impact-News (CPI, NFP, FOMC, Zinsentscheidungen).

## 1. Weekly Bias
- **Bullish:** Weekly High gebrochen (Break of Structure nach oben).
- **Bearish:** Weekly Low gebrochen.
- **Alternativ:** 5 aufeinanderfolgende Weekly-Closes bullisch bzw. bearisch.

## 2. Daily Liquidity Sweep

**Long-Setup** (bei Bullish Bias):
1. Down-Candle + Up-Candle bilden ein Daily Low.
2. Spätere Candle macht ein **neues Tief** unter diesem Low → Liquidität gesweept.

**Short-Setup** (bei Bearish Bias): spiegelverkehrt mit Daily High.

## 3. 4H Confluences (mind. 2 von 4)

| Confluence | Definition |
|---|---|
| **Order Block** | Die Move-Candle, die den Sweep ausgelöst hat |
| **Fair Value Gap (FVG)** | 3-Candle-Imbalance: Gap zwischen Wick High[1] und Wick Low[3] |
| **Balanced Price Range (BPR)** | Überschneidung zweier gegensätzlicher FVGs |
| **Equilibrium** | 50 %-Level der jüngsten Range (Fib 0.5) |

**Regeln:**
- Min. **2 von 4** Confluences in der Zone.
- **Eine davon muss der BOS** sein.
- 3 Confluences = ideales Setup. Bei starken Market Conditions reichen 2.

## 4. 1H Entry

**Long:**
1. Preis kommt von oben in die Confluence-Zone.
2. Reaktion in der Zone (Rejection-Wick, Engulfing, …).
3. 1H Break of Structure nach oben → Entry.

**Short:** spiegelverkehrt.

## 5. Risk Management

**Stop Loss:**
- Unter (Long) bzw. über (Short) der gesweepten Liquidität
- Plus Puffer **0,5 × ATR(4H)**

**Take Profits (3 Stufen):**
| TP | Ziel |
|---|---|
| TP1 | 1:1 RR — sichert Break-even, Teilverkauf |
| TP2 | Mittelpunkt zwischen TP1 und TP3 |
| TP3 | Nächste Daily Liquidity oder Fib-Extension |

**Position Sizing:** `Lotgröße = (Balance × Risk%) / (Stop-Distanz × Pip-Value)`
→ Bei 10.000 € und 1 % Risk: maximal **100 € Verlust pro Trade**.

**Erwartung:** Typischer Gewinn pro gewonnenem Trade 4–8 % vom Account.
