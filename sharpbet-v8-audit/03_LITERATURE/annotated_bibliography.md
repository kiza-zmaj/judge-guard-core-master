# Anotirana bibliografija — SharpBet v8 Audit

> Status: radna verzija | Poslednje ažuriranje: 2026-09-21
> Sve tvrdnje → link na log ili sekciju analize. Razdvoj "dokazano" od "nije oboreno".

---

## Klaster A — Modeliranje ishoda (DC MLE, J2)

### 1. Dixon & Coles (1997)
- **Pun naslov:** *Modelling association football scores and inefficiencies in the football betting market*
- **Journal:** Journal of the Royal Statistical Society: Series C, Vol. 46, No. 2
- **DOI:** 10.1111/1467-9876.00065
- **Metod:** Bivariate Poisson sa ρ-korekcijom za niske rezultate (0-0, 1-0, 0-1, 1-1)
- **Uzorak:** UK fudbal 1992–1995
- **Testiran CLV/ROI van uzorka?** Da — betting simulacija je pokazala profit
- **Relevantnost za nas:** Koristimo DC MLE u Gate B/C. Original je pronašao edge na 1990-im tržištu koje je bilo znatno manje efikasno od Mozzart 2021–2026.
- **Dokazano:** Model može identifikovati statističke anomalije u distribuciji golova.
- **Nije oboreno (ne potvrđeno):** Da li DC daje edge na modernim, visokomarginalnim tržištima.
- **Relevantan za:** J2, RQ1

---

### 2. Groll et al. (2021) — *A hybrid random forest to predict soccer matches in Europe*
- **arXiv:** 2109.05948
- **Metod:** Random Forest + Poisson hybrid
- **Uzorak:** Bundesliga (više sezona)
- **Testiran CLV/ROI van uzorka?** Delimično
- **Ključni nalaz:** ML pristupi konzistentno prevazilaze DC kada su tržišni signali apsorbirani. DC model je dobar baseline, ali ne state-of-art.
- **Implikacija za SharpBet v8:** Naš DC MLE može biti modelski bottleneck, ne samo tržišni problem.
- **Relevantan za:** J2, RQ1 (modelska komponenta CLV-a)

---

## Klaster B — Tržišna efikasnost i CLV (J1, J3, Gate B — PRIORITET)

### 3. Pinnacle White Paper — Closing Line Value (2020)
- **Izvor:** Pinnacle.com (industrijski)
- **Metod:** CLV = (opening_odds / closing_odds) - 1 po kladi
- **Uzorak:** Milioni opklada (Pinnacle exchange)
- **Ključni nalaz:** **CLV je "zlatni standard" za meru betting skill-a.** Bettori koji konzistentno tuku closing liniju su profitabilni dugoročno. Bettori sa CLV < 0 gube novac bez obzira na kratkoročni ROI.
- **DIREKTNA PRIMENA:** Naš CLV = −9,82% je jak signal da model NE tuče closing liniju. Ovo nije samo statistika — to znači da tržište konzistentno "ima pravo" više od modela.
- **Dokazano:** Na Pinnacle-klasi tržišta, CLV < 0 → gubitak dugoročno.
- **Nije oboreno:** Da li isti zaključak važi za Mozzart (softbook, viša margina, drugačija struktura).
- **Relevantan za:** J1, J3, RQ3, Gate B

---

### 4. Cain, Law & Peel (2000) — *The favourite-longshot bias in association football*
- **Izvor:** ResearchGate / Journal of the Operational Research Society
- **Metod:** Logit regresija na UK tržištu
- **Ključni nalaz:** Favorite-longshot bias (FLB) je dokumentovan — longshots su precenjeni, favoriti podcenjeni. Ali: bias se smanjuje u modernijim, likvidnijim tržištima.
- **Implikacija:** Na Mozzart halftime 1X2 tržištu (manja likvidnost, visoka margina), FLB može biti prisutan ali nije dovoljan da kompenzuje 18,79% overround.
- **Relevantan za:** RQ3, J3

---

### 5. Shin (1993) — *Measuring the Incidence of Insider Trading in a Market for State-Contingent Claims*
- **Journal:** Economic Journal
- **Metod:** Shin metoda uklanjanja vig-a (alternativa proporcionalnoj)
- **Ključni nalaz:** Shin metoda daje tačniju implied verovatnoću nego proporcionalna, posebno na ekstremnim kvotama.
- **Implikacija za RQ2:** Ako promenimo metodu uklanjanja margine sa proporcionalne na Shin, da li se CLV verdat menja? Ovo je provera robustnosti.
- **Relevantan za:** RQ2

---

### 6. Demir, Danis & Bilgin (2019) — *Is online sports betting market efficient?*
- **Journal:** Finance Research Letters
- **Metod:** EMH test (runs test, variance ratio test) na online bukmejkerima
- **Ključni nalaz:** Zatvarajuće linije za Top-5 ligu su jako efikasne. Manje efikasne za niže rangiranu takmičenja.
- **Implikacija za RQ5:** Gornja granica realnog edge-a na Mozzart tržištu (1.364 liga, uključuje niže lige) nije nula — ali 18,79% margina efektivno guta svaki realni edge.
- **Relevantan za:** RQ5

---

## Klaster C — Kalibracija vs. profitabilnost (RQ2, J2)

### 7. Gneiting & Raftery (2007) — *Strictly Proper Scoring Rules, Prediction, and Estimation*
- **Journal:** Journal of the American Statistical Association
- **arXiv:** Delom dostupno, 2007
- **Metod:** Teorijska karakterizacija proper scoring rules (Brier, log loss, CRPS)
- **Ključni nalaz:** Proper scoring rules mere kalibraciju i oštri nu. Kalibracija bez sharpness-a ne donosi profitabilnost.
- **DIREKTNA PRIMENA:** Naš Gate A (ECE 3,78%, Brier 0,2171) meri kalibraciju. Dobra kalibracija znači: "model tačno izveštava svoja internih ubeđenja." Ne znači da su ta ubeđenja bolja od tržišta.
- **Dokazano (teorija):** Calibration ≠ profitability. Ovo je jezgro paradoksa Gate A PASS / Gate B BLOCKED.
- **Relevantan za:** RQ2, J2

---

### 8. Bailey & López de Prado (2014) — *The Deflated Sharpe Ratio*
- **Izvor:** Journal of Portfolio Management
- **Metod:** Sharpe ratio korekcija za multiple testing + non-normality
- **Ključni nalaz:** Kada testirate N strategija, i odaberete "najbolju", očekivani Sharpe ratio je inflated. DSR koriguje.
- **DIREKTNA PRIMENA ZA GATE C:**
  - N_bets = 89, SE = 12.52%, SD_per_bet ≈ 118%
  - Za detekciju ROI 2% potrebno N = 27.374 opklada (power 0.80)
  - Gate C sa N=89 ima power ≈ 0.05 za detekciju 2% edge → statistički šum
  - ROI 0,66% i PnL €5,90 uz CI [−23,31%; +25,76%] = **nema dokaza ni na jednu stranu**
- **Relevantan za:** RQ4, Gate C diskvalifikacija

---

## Sažetak literarne podrške za hipotezu

| Hipoteza | Status | Ključni izvor |
|---|---|---|
| CLV je bolji prediktor profit-a od ROI (kratkoročno) | **POTVRĐENO** | Pinnacle white paper |
| Dobra kalibracija ne implicira profitabilnost | **POTVRĐENO** | Gneiting-Raftery 2007 |
| Gate C (N=89) je statistički beznačajan | **POTVRĐENO** | Bailey-López de Prado |
| DC model zaostaje za ML na modernim tržištima | **POTVĐENO empirijski** | Groll et al. 2021 |
| FLB postoji ali smanjuje se u efikasnim tržištima | **POTVRĐENO** | Cain-Law-Peel 2000 |
| Negativan CLV na Mozzart tržištu = strukturni | **NAJVEROVATNIJE** — nije formalno dokazano za Mozzart specifično | Demir 2019 + power analiza |
| Pozitivan CLV je nemoguć na ovom tržištu | **NIJE DOKAZANO** — samo "nije nađen" | Empirijska granica, ne teorema |
