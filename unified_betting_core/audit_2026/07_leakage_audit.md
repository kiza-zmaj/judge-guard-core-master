# 07. Audit Curenja Podataka (Leakage Audit)

**Datum:** 22. septembar 2026.  
**Cilj:** Verifikacija kauzalnog vremenskog uslova:  
$$\text{feature\_timestamp} \le \text{decision\_timestamp} < \text{outcome\_timestamp}$$

---

## 1. Tabela Klasifikacije Curenja Podataka po Komponentama

| Komponenta / Feature | Leakage Status | Dokaz / Inspekcija Koda | Objašnjenje |
| :--- | :--- | :--- | :--- |
| **1. Rolling Averages (poslednjih 15 mečeva)** | **PASS** | `generate_kaggle_v12.py:210-245` | `team_history` se ažurira tek nakon izračunavanja lambda parametara za tekući meč. |
| **2. Last N Matches** | **PASS** | `features/feature_builder.py` | Koriste se isključivo prethodno završeni mečevi. |
| **3. Halftime Features** | **PASS** | `generate_kaggle_v18.py:180` | Ishodi poluvremena se evaluiraju tek na kraju meča, nikada pre početka. |
| **4. Injuries / Povrede** | **NOT APPLICABLE** | Nema u bazi | Model ne koristi vesti i sastave timova. |
| **5. Standings / Tabele** | **PASS** | `data_ingestion/` | Tabele se računaju kumulativno do datuma meča. |
| **6. Closing Odds (Zatvarajuće kvote)** | **PASS (kao Benchmark)** | `generate_kaggle_v14.py:482` | Closing kvote se koriste isključivo za post-hoc CLV verifikaciju, ne za predikciju. |
| **7. Market-Implied Features** | **NOT APPLICABLE** | Nema | Model je "bottom-up" (polazi od golova, ne od kretanja kvota). |
| **8. Probability Calibration** | **PASS** | `audit_ece.py`, Gate A | Kalibracioni parametri se mere na OOS skupu, ne fittuju se na testu. |
| **9. Threshold Optimization** | **UNPROVEN** | `ev > 0.025` | Prag od 2.5% EV u v12 je izabran arbitrarno, bez dokazane unakrsne validacije. |
| **10. Feature Normalization** | **PASS** | `generate_kaggle_v18.py` | Min-max skaliranje se računa isključivo unutar trening prozora. |
| **11. Team History Update Order** | **PASS** | `models/walk_forward_engine.py` | Hronološki redosled mečeva je strogo očuvan (sortirano po `Date`). |
| **12. Duplicate Matches** | **PASS** | `data_ingestion/` | Uklanjanje duplikata po ključu `(date, home_team, away_team)`. |
| **13. Season Overlap** | **PASS** | Podela po ligama | Sezone se ne preklapaju unutar iste lige. |
| **14. Same-Game Leakage** | **PASS** | `models/poisson_model.py` | Bivarijantni model ne koristi poluvremenski rezultat tekućeg meča za predikciju tog istog meča. |
| **15. Train/Test Contamination** | **PASS** | Sezone 22/23 vs 24/25 vs 25/26 | Sezone su vremenski potpuno izolovane. |
| **16. Market Simulation (Sintetičke Kvote)** | **FAIL** | `v12 Cell 9, v18 Gate B` | **SINTETIČKI LEAKAGE:** Kvote se generišu iz same verovatnoće modela (`odds = 1/p * 0.935`), čime je buduća isplativost veštački zavisna od modela. |

---

## 2. Detaljna Analiza: Razlika Između Prediktivnog i Tržišnog Curenja

### 2.1. Zašto je Prediktivni Sloj Čist (PASS)
U mašinskom učenju, najveća opasnost je da model "vidi" golove pre nego što se utakmica odigra (npr. računanjem proseka golova u sezoni uključujući i meč koji se tek igra).  
Pregledom koda u `generate_kaggle_v12.py`:
```python
# 1. Prvo se računaju parametri iz dosadašnje istorije
lh_1h = calculate_lambda(team_history[home], ...)
la_1h = calculate_lambda(team_history[away], ...)

# 2. Tek na kraju petlje istorija se dopunjava rezultatom ovog meča
team_history[home].append(match['FTHG'])
team_history[away].append(match['FTAG'])
```
Ovo je školski primer ispravnog inkrementalnog ažuriranja. Nema "lookahead bias-a".

### 2.2. Zašto Tržišna Simulacija Pada (FAIL)
Tržišni backtest pati od fundamentalnog **kružnog curenja (circular feedback)**:
Tržište se ne ponaša kao nezavisni sudija, već kao lutka u rukama modela. Kada model ima visoku verovatnoću, on sam sebi kreira kvotu sa ugrađenom maržom, a zatim kroz pod od 1.25 sam sebi garantuje arbitražu. To je direktno kršenje principa nezavisnog tržišnog vrednovanja.
