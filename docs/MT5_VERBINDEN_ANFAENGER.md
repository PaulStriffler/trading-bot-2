# Dein FTMO/MT5 Account mit dem Dashboard verbinden — Anfänger-Guide

> Wenn du noch nie etwas mit „Code" oder „Terminal" zu tun hattest, ist dieser Guide für dich.
> Jeder Schritt ist erklärt. Du brauchst nichts vorher zu wissen.

---

## Was wollen wir erreichen?

Im Dashboard soll oben ein **grünes Banner** stehen mit deiner **echten FTMO-Balance** und **Equity**, das sich automatisch alle 5 Sekunden aktualisiert — so wie es im MT5-Programm selbst aussieht.

Damit das funktioniert, braucht es ein kleines Hilfsprogramm (die **„Bridge"**), das im Hintergrund läuft, dein MT5 ausliest, und die Werte in eine Datei schreibt, die das Dashboard dann anzeigt.

```
[MT5 auf Windows] → [Bridge-Skript] → [live.json Datei] → [Dashboard im Browser]
```

---

## Was du brauchst (Checkliste)

- [ ] **Einen Windows-Rechner.** MT5 läuft NUR auf Windows. Wenn du nur einen Mac hast, siehe Abschnitt „Was wenn ich nur einen Mac habe?" am Ende.
- [ ] **Internet auf diesem Windows-Rechner.**
- [ ] **Deine FTMO-Zugangsdaten:** Login-Nummer, Passwort, Server-Name (z. B. `FTMO-Demo2`)
- [ ] **~30 Minuten Zeit** für die Erst-Einrichtung. Danach läuft alles von selbst.

---

## Begriffe die du im Guide siehst (kurze Erklärung)

| Begriff | Was es bedeutet |
|---|---|
| **MT5** | MetaTrader 5 — das Trading-Programm, das du wahrscheinlich schon kennst |
| **FTMO** | Dein Broker für den $10k Funded Account |
| **Python** | Eine Programmier-Sprache. Hier nur Werkzeug — du musst nichts programmieren |
| **Pip** | Installiert Python-Pakete (so wie der App Store für Apps) |
| **Terminal / CMD / Eingabeaufforderung** | Schwarzes Fenster, in das du Befehle tippst. Klingt scary, ist es nicht |
| **Bridge** | Unser kleines Skript, das MT5 ausliest und ans Dashboard schickt |
| **Repo / Repository** | Der Ordner mit unserem ganzen Code (auf GitHub) |
| **Klonen** | Den Repo-Ordner auf deinen Rechner laden |

---

## Schritt 1: Sachen installieren (einmalig, ~15 Minuten)

### 1.1 MetaTrader 5 installieren

Wenn du noch kein MT5 auf Windows hast:

1. Geh auf https://ftmo.com/de/dashboard
2. Login → **Download MT5**
3. Installier es ganz normal (Doppelklick auf die `.exe` → Weiter, Weiter, Fertig)
4. Öffne MT5 → **Datei → Bei Trade-Konto anmelden**
5. Trag deine **FTMO Login-Nummer**, **Passwort** und den **Server** (z. B. `FTMO-Demo2`) ein
6. Wenn du oben rechts deine Balance siehst → ✅ MT5 läuft

### 1.2 Python installieren

1. Geh auf https://www.python.org/downloads/
2. Klick **Download Python 3.12.x** (der gelbe Button)
3. Öffne die heruntergeladene Datei
4. **GANZ WICHTIG:** Setz den Haken bei **„Add python.exe to PATH"** ganz unten im Installer (sonst findet Windows Python später nicht)
5. **Install Now**
6. Warten bis fertig

**So testest du ob's geklappt hat:**
- Drücke `Windows-Taste + R`
- Tipp `cmd` und drücke Enter — ein schwarzes Fenster (die „Eingabeaufforderung") geht auf
- Tipp `python --version` und drücke Enter
- Du solltest sowas sehen: `Python 3.12.1`
- ✅ Python läuft

Falls Fehler: Python-Installation wiederholen und den Haken bei „Add to PATH" nicht vergessen.

### 1.3 Git installieren

Git lädt unseren Code von GitHub runter.

1. Geh auf https://git-scm.com/download/win
2. Download startet automatisch
3. Installer öffnen → einfach immer **Next** klicken (Defaults sind ok)

**Testen:**
- Im schwarzen Fenster (Eingabeaufforderung) tippen: `git --version`
- Du solltest sehen: `git version 2.x.x`
- ✅ Git läuft

---

## Schritt 2: Code runterladen (~2 Minuten)

1. Öffne die **Eingabeaufforderung** (Windows-Taste + R, dann `cmd`, Enter)
2. Tipp diese drei Befehle einer nach dem anderen (jeweils mit Enter):

```
cd Desktop
git clone https://github.com/PaulStriffler/trading-bot-2.git
cd trading-bot-2
```

Was passiert:
- `cd Desktop` → wechselt in deinen Desktop-Ordner
- `git clone …` → lädt unseren ganzen Code als Ordner `trading-bot-2` runter
- `cd trading-bot-2` → wechselt in diesen Ordner

✅ Du siehst jetzt auf deinem Desktop einen Ordner namens `trading-bot-2`.

---

## Schritt 3: Bridge-Pakete installieren (~3 Minuten)

Immer noch in der Eingabeaufforderung (sollte mit `…\trading-bot-2>` anfangen):

```
pip install MetaTrader5 pyyaml
```

Was passiert:
- Pip lädt zwei Helfer-Pakete runter (MetaTrader5 für die Verbindung, pyyaml zum Lesen der Config-Datei)
- Dauert ~30 Sekunden

Wenn du am Ende `Successfully installed …` siehst → ✅ alles gut.

**Falls ein Fehler kommt** wie „pip not recognized": Python-Installation wiederholen, Haken bei „Add to PATH" setzen.

---

## Schritt 4: Deine Zugangsdaten eintragen (~3 Minuten)

Jetzt sagen wir der Bridge, welcher Account ausgelesen werden soll.

1. Öffne den Datei-Explorer (Windows-Taste + E)
2. Geh in den Ordner `Desktop > trading-bot-2 > bridge`
3. Du siehst eine Datei `accounts.example.yaml`
4. **Rechtsklick → Kopieren → Einfügen** (es entsteht `accounts.example - Kopie.yaml`)
5. **Rechtsklick → Umbenennen → schreib `accounts.yaml`** (genau so, ohne `.example`)
6. **Rechtsklick auf accounts.yaml → Öffnen mit → Editor (Notepad)**

Du siehst Text wie:

```yaml
accounts:
  - id: ftmo-swing-10k
    label: FTMO Swing $10k
    broker: FTMO
    terminal_path: "C:/Program Files/MetaTrader 5 FTMO/terminal64.exe"
    login: 1234567
    password: "your-password"
    server: "FTMO-Demo2"
```

**Was du ändern musst:**

- **`terminal_path`** → der Pfad zu deinem MT5-Programm
  - Standardpfad ist meist `C:/Program Files/MetaTrader 5/terminal64.exe`
  - Wenn FTMO seine eigene MT5-Version installiert hat: `C:/Program Files/FTMO MetaTrader 5/terminal64.exe`
  - Um den Pfad zu finden: Rechtsklick auf das MT5-Icon auf deinem Desktop → **Eigenschaften** → der „Ziel"-Pfad zeigt's
  - WICHTIG: Schrägstriche müssen `/` sein (nicht `\`), genau wie im Beispiel
- **`login`** → deine FTMO Login-Nummer (die 7-stellige Zahl)
- **`password`** → dein FTMO-Passwort, in Anführungszeichen lassen
- **`server`** → der FTMO-Server, den du beim MT5-Login eingegeben hast (z. B. `FTMO-Demo2` oder `FTMO-Server`)

**Falls du nur einen Account hast:** Lösch den zweiten Block (`- id: personal-mt5 …`) komplett raus, oder lass ihn einfach mit erfundenen Daten — die Bridge ignoriert dann den fehlerhaften zweiten Account und zeigt nur den ersten.

Speichern (`Strg + S`) und Notepad schließen.

---

## Schritt 5: Bridge starten

In der **Eingabeaufforderung** (immer noch im `trading-bot-2` Ordner):

```
python -m bridge.mt5_sync
```

Was du sehen solltest:

```
Syncing 1 account(s) every 5s.
Writing to: C:\Users\...\trading-bot-2\dashboard\live.json
Press Ctrl+C to stop.

[15:32:10] 1 account(s) · total balance $10,000.00 · equity $10,000.00 · open P&L $+0.00
[15:32:15] 1 account(s) · total balance $10,000.00 · equity $10,000.00 · open P&L $+0.00
```

✅ **Wenn du das siehst, läuft die Bridge.**

**Lass dieses Fenster offen!** Solange es offen ist, läuft die Verbindung. Wenn du's schließt, hört die Aktualisierung auf.

**Tipp:** Du kannst das Fenster minimieren — es muss nicht im Vordergrund sein.

---

## Schritt 6: Dashboard öffnen

Jetzt das Dashboard anschauen, mit den echten Daten drin.

In **einem zweiten** Eingabeaufforderungs-Fenster (das erste mit der Bridge weiter offen lassen!):

```
cd Desktop\trading-bot-2\dashboard
python -m http.server 8080
```

Du siehst:
```
Serving HTTP on :: port 8080 (http://[::]:8080/) ...
```

✅ Das Dashboard läuft jetzt als kleine Website auf deinem Rechner.

Öffne deinen Browser (Chrome / Edge / Firefox) und gehe zu:

**http://localhost:8080**

Du solltest oben ein **grünes Banner** sehen: „1 Live Account verbunden" mit deiner echten FTMO-Balance und Equity. Alle 5 Sekunden aktualisiert sich's automatisch.

---

## Es funktioniert! Was tun?

### Wenn du fertig bist mit Trading

Schließ die beiden schwarzen Fenster (Bridge + Server). Dashboard kann nicht mehr aktualisiert werden, aber die letzten Werte bleiben sichtbar.

### Wenn du am nächsten Tag wieder schauen willst

Du musst die Bridge und den Server **erneut starten** (die zwei Befehle aus Schritt 5 und 6 wiederholen). Tipp: Schritt 5 + 6 lassen sich auch als **Doppelklick-Skript** machen — sag mir Bescheid, dann bau ich dir eine `start.bat`.

---

## Was wenn was nicht klappt?

### „Initialize failed" beim Start der Bridge

→ MT5 ist nicht offen, oder die Bridge findet das Programm nicht.
**Lösung:** MT5 starten, einloggen, dann Bridge nochmal starten.

### „Login failed: (-1, 'No connection')"

→ Falsche Login / Passwort / Server in der `accounts.yaml`.
**Lösung:** In MT5 selbst nochmal einloggen, überprüfen welcher Server angezeigt wird (oben links steht der Account), und das in die YAML eintragen.

### „No module named 'MetaTrader5'"

→ Das Paket wurde nicht installiert.
**Lösung:** Schritt 3 wiederholen: `pip install MetaTrader5 pyyaml`

### Dashboard zeigt immer noch „Offline"

→ Drei mögliche Gründe:
1. Die Bridge läuft nicht (schwarzes Fenster geschlossen?)
2. Du hast das Dashboard direkt mit Doppelklick statt via `http://localhost:8080` geöffnet
3. Browser-Cache: drück `Strg + F5` für Hard-Refresh

### „python is not recognized"

→ Python-Installation hat den PATH-Haken nicht gesetzt.
**Lösung:** Python deinstallieren, neu installieren, beim Installer „Add to PATH" anhaken.

---

## Was wenn ich nur einen Mac habe?

Drei Möglichkeiten:

### Option A — Windows-VPS (Profi-Lösung, ~10 €/Monat)
Ein Anbieter wie **ForexVPS** oder **BeeksFX** stellt dir einen Windows-Rechner in der Cloud bereit, der 24/7 läuft. MT5 ist meist schon vorinstalliert. Du machst die Schritte 1–6 dort einmal, und es läuft für immer — auch wenn dein Mac aus ist.

→ Empfohlen, sobald du echtes Live-Trading machst.

### Option B — Parallels Desktop / VMware Fusion (~100 €/Jahr + Windows-Lizenz)
Damit läuft Windows als „virtueller PC" auf deinem Mac. MT5 und Bridge laufen drin, Dashboard im Mac-Browser über die VM-IP.

### Option C — Bootcamp (gratis, älter als 2020 Mac)
Du installierst Windows direkt auf deinem Mac neben macOS. Du musst zwischen den beiden Systemen umstarten. Geht aber NICHT mehr auf neueren Apple-Silicon-Macs (M1, M2, M3).

### Option D — Bei einem Freund / Familie / Büro-PC
Wenn du irgendwo Zugang zu einem Windows-Rechner hast, kannst du die Schritte 1–6 dort machen. Die Bridge schreibt einfach in eine Datei — solange der Rechner läuft, sieht das Dashboard die Daten.

---

## Sicherheits-Hinweise

- **Deine FTMO-Daten** stehen in der `accounts.yaml` Datei. Diese Datei ist im `.gitignore` ausgeschlossen — sie wird **nie** zu GitHub hochgeladen.
- **Die Bridge ist nur lesend** — sie führt KEINE Trades aus, schließt keine Positionen, ändert nichts an deinem Account. Sie liest nur Balance/Equity/offene Positionen.
- **FTMO Compliance:** Read-only Zugriff ist erlaubt ohne Anmeldung. Wenn du später Auto-Trading (Orders platzieren) willst, brauchst du eine schriftliche FTMO-Approval.

---

## Was als nächstes?

Wenn alles läuft und du Live-Daten siehst:
- **Lass die Bridge im Hintergrund laufen** während du tradest
- **Trag deine Trades ins Journal ein** — das funktioniert sofort, ohne extra Setup
- **Wenn du eine Demo willst ohne MT5:** auf Mac `python -m bridge.mock_sync` für simulierte Daten

Falls irgendwo ein Schritt nicht klappt — schreib mir an welcher Stelle es scheitert, dann gehen wir das gemeinsam durch.
