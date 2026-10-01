# Time-Series Momentum Backtester

Eigenständiges Forschungsrepo. Python 3.10+, keine externen Abhängigkeiten.

## Schnellstart

```sh
python -m unittest discover -s tests -v
python demo.py
python backtest.py --data data/demo.csv --manifest data/demo_manifest.json --config configs/baseline.json --out results/demo
```

Demo-Daten sind synthetisch: Die Ergebnisse belegen keinerlei Profitabilität.

## Datenvertrag

CSV: `date,symbol,return`, tägliche einfache Renditen als Dezimalzahl, sortierte ISO-Daten. Alle Instrumente müssen denselben Kalender und vollständige Werte besitzen. Fehlende Werte werden nie mit Null ersetzt. Exzessrenditen aus tatsächlich gehaltenen Futures inklusive sauberer Rollverkettung sind nötig; keine prozentualen Renditen aus additiv rückadjustierten Futureskursen. Rollwechsel ohne künstliche Preissprünge, einheitliche USD-Basis, historische Verfügbarkeit und Publikationszeiten müssen vom Lieferanten geprüft werden. Eine Manifestdatei dokumentiert `kind`, `source`, `return_definition`, `roll_method`, `currency`, `reviewed`. `reviewed=true` ist eine Nutzerbestätigung, keine automatische Datenzertifizierung.

EODHD-ETF-Adapter: `python download_eodhd.py --symbols SPY.US TLT.US GLD.US --start 2000-01-01 --end 2025-12-31 --out data/etf.csv`. API-Schlüssel ausschließlich als Umgebungsvariable EODHD_API_TOKEN. Adapter verwendet Adjusted Close und gemeinsame vollständige Daten; Ausgabe ist **ETF-Proxy**, keine Futures-Replikation. Dividenden/Corporate Actions des Anbieters prüfen. Short-Leihe und Finanzierung fehlen in dieser ersten Forschungsfassung.

## Strategie und Timing

12 Kalender-Monate kumulierte eigene Rendite; monatliche Neugewichtung. EW-Varianz (COM=60, annualisiert mit 261), 40% Volatilitätsbudget je Instrument, gleiches Kapitalgewicht pro Instrument. Kein SL/TP. Monatsende ist erst mit dem nächsten Datentag erkennbar: Der erste Tag des neuen Monats bleibt mit alter Gewichtung, neue Gewichte wirken ab dem zweiten Datentag. Diese konservative Close-Ausführung vermeidet fiktive Ausführung zum schon verwendeten Schlusskurs. Das ist eine dokumentierte Abweichung von der akademischen Monatsrenditeberechnung.

Gewichte sind konstante Return-Exposures innerhalb eines Monats, keine simulierten ganzzahligen Futureskontrakte. Das entspricht einer Forschungsapproximation, nicht einer handelbaren Broker-Simulation. Kosten in bps auf absolute Gewichtsänderungen; zusätzliche tatsächliche Rollkosten, Finanzierung, Collateral-Zinsen, Margin, Kontraktmultiplikatoren und Intraday-Risiko sind nicht modelliert. 40% je Markt ist kein Portfolio-Volatilitätsziel und keine Verlustobergrenze. Optionaler Gross-Cap ist eine separate Variante.

## Auswertung

`daily.csv`, `weights.csv`, `yearly.csv`, `summary.json`, `run.json`: Netto-/Bruttorenditen, Kosten, Equity, Drawdown, Exposure, CAGR, Sharpe (Exzessrendite, risikofreier Satz 0), Sortino, Monats-Trefferquote, PF auf Monatsrenditen, Marktbeiträge. PF und Trefferquote beziehen sich auf Monate, nicht einzelne Trades. Eingabe-SHA256, Konfiguration und Git-Commit werden protokolliert. Nur aktive Auswertungsperiode zählt; mindestens 24 Monatswerte empfohlen. Bei Verlust >=100% bricht die Engine ab.

Varianten vorab festlegen: 1/3/6/12 Monate und Kosten 0/5/10/20 bps. Ergebnisse gleichwertig berichten, keine nachträgliche Bestparameter-Auswahl. Bewertung in getrennten Zeitabschnitten via evaluation_start/end; Warmup bleibt davor. Parameter nicht anhand des späteren Holdouts auswählen. Konfidenzintervalle/Bootstrap und Kontrakt-Ausführung sind nächste Ausbaustufen.

## Quellen / Status

- Moskowitz, Ooi, Pedersen (2012): https://pages.stern.nyu.edu/~lpederse/papers/TimeSeriesMomentum.pdf
- Originaldaten: https://www.aqr.com/Insights/Datasets/Time-Series-Momentum-Original-Paper-Data
- Erweiterte Faktoren: https://www.aqr.com/Insights/Datasets/Time-Series-Momentum-Factors-Monthly
- EODHD Commodity-Dokumentation: https://eodhd.com/financial-apis/commodities-api-historical-prices-for-oil-gas-metals-agriculture-beta

Keine verifizierten Futuresdaten enthalten, keine Profitabilitätsaussage. Originaluniversum/Originalergebnisse noch nicht repliziert. EODHD Commodity-Spotreihen sind dafür unzureichend.

## GitHub

Dieses Projekt getrennt als `tsmom-backtester` importieren. Nach Anlage eines leeren Repos:

```sh
git remote add origin https://github.com/martkling6/tsmom-backtester.git
git push -u origin main
```
