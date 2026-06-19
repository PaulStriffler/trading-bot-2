# Trading-Strategie · FINAL (v3)

**Account-Kontext:** FTMO Funded Swing $10.000 (aktuell Eval 1), 1 % Risk = $100/Trade, Hebel 1:30.

---

## 0. Wochenvorbereitung (Sonntagabend)

Ziel: Vor Wochenstart alle relevanten Levels markieren, damit am Montag nur noch Trigger abgewartet werden müssen.

**Markiert werden:**
- **Order Blocks** (OBs)
- **BPRs** (Balanced Price Ranges) und **inverse BPRs**
- **Fair Value Gaps** (FVGs)
- **Inverse FVGs**

### Definition: Inverse FVG
Eine inverse FVG entsteht, wenn:
1. Eine ursprüngliche FVG existiert.
2. Eine Kerze sie **in entgegengesetzte Richtung** durchbricht — **ohne Reaktion** in der ursprünglichen Gap-Zone (mindestens auf 1H).
3. Der Preis später **in diese Zone zurückkommt**.
4. Von dort aus zeigt sich die Reaktion.

→ Die ursprüngliche Gap-Zone wird zur neuen Wider­stands-/Unterstützungszone in der **Gegen­richtung** der ursprünglichen FVG.

### Definition: Normale FVG-Reaktion
Preis kommt in die FVG → reagiert von dort in die ursprüngliche FVG-Richtung (Long bei bullischer FVG, Short bei bearischer).

---

## 1. Bias-Bestimmung

> **Regel:** Immer mit der aktuellen Marktrichtung mitgehen, nie dagegen.

**Vorgehen:**
1. Letzten **Break of Structure (BOS)** identifizieren — wohin ging er?
2. Kerzen-Charakter davor und danach prüfen → **bullisch oder bearisch?**
3. Bias = Richtung des letzten BOS, solange keine Gegen­bewegung bricht.

**Bias bullish** → Long-Setups suchen, Sweeps unter Lows abwarten
**Bias bearish** → Short-Setups suchen, Sweeps über Highs abwarten

---

## 2. Daily Liquidity Sweep

Auf Daily warten, bis ein klarer Liquidity-Sweep gegen den Bias stattfindet:

- **Long-Setup (Bias bull):** Sweep einer Daily-Low-Zone (Pivot-Low wird kurz untertroffen)
- **Short-Setup (Bias bear):** Sweep einer Daily-High-Zone

→ Markiert die "Liquidity-Quelle" — institutionelle Player füllen hier ihre Positionen.

---

## 3. Order Block Identifikation

**Standard:** Der OB ist der **letzte gegensätzlich-farbige Move-Block vor dem Sweep**.

**Wenn die Liquidity öfter gesweept wird (mehrfacher Sweep):**
- **Alle drei OBs** vor den jeweiligen Sweeps markieren
- In jeden OB schauen, welcher die **besten Confluences** hat
- Den OB mit den besten Confluences wählen

---

## 4. Entry-Sequenz (KERN der Strategie)

Die **strikte Sequenz** nach dem Daily-Sweep:

```
Schritt 1: Preis muss AUS dem Order Block RAUSKOMMEN
   ↓
Schritt 2: Preis muss WIEDER REINKOMMEN in den Order Block
   ↓
Schritt 3: IM Order Block muss eine Confluence (FVG / inverse FVG / BPR) gefunden werden
           Die Confluence darf den OB überlappen — Hauptsache sie ist da
   ↓
Schritt 4: BOS RAUS aus der Confluence (nicht aus dem ganzen OB)
   ↓
Schritt 5: ENTRY
```

**Wichtige Klarstellung:**
- Es geht nicht nur darum, dass der Preis den OB berührt
- Der Preis muss tatsächlich **wegspringen, zurückkommen, und sich in der OB-Confluence einnisten**
- Der BOS muss aus dem inneren Confluence-Bereich erfolgen, nicht aus dem äußeren OB-Rand

---

## 5. Stop Loss

**Position:** Unter dem **Order Block** (Long) / über dem Order Block (Short)
**Puffer:** **0.5 × ATR(4H)**

**Beispiel:**
- ATR(4H) = 100 Punkte
- SL = OB-Low − 50 Punkte (bei Long)

→ Sicherheitsabstand für normales Marktrauschen ohne Stop-Out auf einem Wick.

---

## 6. Take Profits

### 6.1 Wenn Previous Areas of Liquidity (PAL) vorhanden sind

**TP1** = 1:1 RR (das Risiko in Punkten, in Gewinnrichtung gespiegelt)
**TP3** = Die nächste **Previous Area of Liquidity** in Gewinnrichtung
**TP2** = **Mitte** zwischen TP1 und TP3

**Plausibilitätsregel:**
- Wenn TP1 in % ausgedrückt = 2 %
- Dann sollte TP3 mindestens +1 % darüber liegen (also TP3 ≥ 3 %)
- TP2 = Mittelwert von TP1 und TP3

### 6.2 Wenn keine PAL vorhanden ist → Fibonacci Extension

**Aufbau (auf Daily):**
1. **Punkt A:** letztes Swing Low
2. **Punkt B:** letztes Swing High
3. **Punkt C:** Low vor dem Entry (bei Long-Setup)

→ Fib-Extension von A → B → C, Standard-Levels (1.272, 1.618, 2.0)

**TP-Zuordnung:**
- TP1: 1:1 RR (wie oben)
- TP3: an einem höheren Fib-Extension-Level (z. B. 1.618 oder 2.0)
- TP2: zwischen TP1 und TP3

---

## 7. Risk Management

| Parameter | Wert |
|---|---|
| Account | $10.000 (FTMO Swing Funded) |
| Risk pro Trade | 1 % = $100 |
| Hebel | 1:30 |
| Aktueller Status | Eval Phase 1 |

**Partial Closes** an den TPs: empfohlen 33 / 33 / 34 (final je nach FTMO-Vorgaben anpassbar).

---

## Zusammenfassung in einem Satz

> Sonntags Levels markieren → Bias aus letztem Weekly BOS → Daily Sweep abwarten → OB davor markieren → Preis raus-rein-Confluence-BOS → Entry → SL unter OB mit 0.5×ATR(4H) Puffer → TP1 bei 1R, TP3 zur PAL oder via Fib-Extension auf Daily, TP2 dazwischen.

---

## Implementierungs-Status

- [x] Strategie dokumentiert
- [ ] Code-Implementierung (`strategy_v3.py`)
- [ ] Backtest auf 1H (echte Strategie-Auflösung)
- [ ] Annotated 1H-Screenshots (TradingView-Style mit Fib, OB, Confluences)
- [ ] Dashboard-Integration
