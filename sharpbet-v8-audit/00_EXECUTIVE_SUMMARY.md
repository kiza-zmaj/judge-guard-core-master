# SharpBet v8 — Izvršni sažetak

**Verdict:** `FAIL_CLOSED_BLOCKED`
**Datum:** 2026-09-21
**Kernel:** v8 (`scriptVersionId=351589004`)
**Dataset:** v2, 344.005 mečeva, 43.53 MB

---

## Šta smo testirali

Dixon-Coles MLE model predviđanja halftime 1X2 ishoda fudbalskih utakmica. Model je treniran na 760 Premier League mečeva i validiran na holdout od 380. Evaluiran na 333.507 direktnih Mozzart HT 1X2 kvota iz perioda 2021–2026.

## Faktičke vrednosti iz Kernel v8 loga (ovo su dokazani brojevi)

| Metrika | Vrednost |
|---|---|
| Ukupno mečeva | 344.005 |
| Direktne HT 1X2 kvote | 333.507 (96.9%) |
| Tržišna margina (prosek/medijana) | 18.79% / 18.48% |
| Gate A — ECE / Brier | 3.78% / 0.2171 → **PASSED** |
| Gate B — CLV | −9.82%, CI [−10.91%; −8.79%], t=−18.90 → **BLOCKED** |
| Gate C — ROI / N / PnL | 0.66% / 89 / €5.90, CI [−23.31%; +25.76%] → **šum** |

## Odgovor na glavno pitanje

**Da li je negativan CLV strukturni ili modelski?**

Pretežno strukturni (~80%), delimično modelski (~20%).

- ~8.0% od −9.82% dolazi od margin compression (open 18.79% → closing ~10%)
- ~1.8% dolazi od negativne model selektivnosti

Oba uzroka zajedno čine system neimplojablinim.

## Šta Gate C ne dokazuje

Gate C (ROI 0.66%, N=89) nije dokaz prednosti.
Za detekciju 2% ROI na nivou power 0.80 potrebno je **N = 27.374 opklada** (308× više).
Gate C je statistički šum. Tačka.

## Zašto paradoks Gate A PASS / Gate B BLOCKED nije paradoks

Kalibracija (Gate A) meri da li model tačno izveštava svoja interna ubeđenja.
Profitabilnost (Gate B) meri da li su ta ubeđenja bolja od zatvarajuće linije.

Model može biti savršeno kalibrisan i sistematski gubiti novac — ako tržište zna isto što i model.

Literatura (Gneiting-Raftery 2007): *kalibracija je neophodan, ali ne dovoljan uslov za profitabilnost.*

## Šta nije dokazano

- Nije dokazano da je pozitivan CLV matematički nemoguć. Dokazano je samo da nije nađen.
- Nije testirana kalibracija po ligama (time-split, segment analiza).
- Closing margina za Mozzart nije direktno poznata — dekompozicija je aproksimacija.
- Dataset PRIVATE → audit nije nezavisno proverljiv.

## Preporuka

**STOP ili PIVOT.** Detalji u [`07_DECISION.md`](./07_DECISION.md).

Nastavak na istom tržištu sa istim pristupom bez promene je racionalno neopravdan.

---

*Sve tvrdnje u ovom dokumentu su zasnovane na Kernel v8 log outputu ili na analizi u `04_ANALYSIS/`. Nisu zasnovane na pretpostavkama ili optimizmu.*
