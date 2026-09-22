# 05. Detaljni Audit Koda (Code Audit)

**Datum:** 22. septembar 2026.  
**Obuhvaćeni moduli:** `unified_betting_core/` (`models/`, `decision_engine/`, `data_ingestion/`, `execution/`, `api/`, `scratch/`)

---

## 1. Analiza Ključnih Softverskih Komponenti

### 1.1. Data Ingestion & Preprocessing
* **Fajlovi:** `data_ingestion/real_data_provider.py`, `mozzart_parser.py`
* **Input:** CSV fajlovi (`football-data.co.uk`), Mozzart PDF/JSON bilteni.
* **Output:** Standardizovane strukture utakmica, kvota i golova.
* **Da li koristi buduće informacije:** NE. Datum i vreme se striktno poštuju.
* **Fallback:** Za nepoznate lige postoji `LEAGUE_MAP` fallback.
* **Testiranost:** Pokriveno u `tests/test_real_data_provider.py`.

### 1.2. Feature Engineering & Rolling Metrics
* **Fajlovi:** `features/feature_builder.py`, `generate_kaggle_v12.py` (Cell 5)
* **Input:** Istorija prethodnih utakmica za domaći i gostujući tim (poslednjih 15 mečeva).
* **Output:** Očekivani golovi (`lambda_h`, `lambda_a`, FT i 1H).
* **Zero Lookahead:** `team_history` se ažurira striktno **nakon** izračunavanja parametara za meč.
* **Ocena:** ✅ **Arhitektonski besprekorno.**

### 1.3. Poisson & Dixon-Coles Halftime Engine
* **Fajlovi:** `models/poisson_model.py`, `models/dixon_coles.py`, `generate_kaggle_v18.py`
* **Input:** `lambda` parametri, matrica rezultata $m \times n$, korelacioni faktor `rho`.
* **Output:** Združena raspodela verovatnoća za tačne rezultate i izvedene markete (`1X2`, `I1+`, `I2+`, `I 0-1`).
* **Treniranje:** U v14–v18 parametri ($\mu, \gamma, \rho, \alpha_i, \beta_j$) se optimizuju preko L-BFGS-B MLE algoritma po ligama, uz striktnu sum-to-zero identifikaciju.
* **Ocena:** ✅ **Matematički napredno i korektno.**

### 1.4. De-vigging Engine (Power & Multiplicative)
* **Fajlovi:** `decision_engine/devig_engine.py`
* **Input:** Sirove kvote kladionica (`home`, `draw`, `away`).
* **Output:** Očišćene (fair) verovatnoće sa uklonjenom maržom (Power metod rešava eksponent $k$ tako da $\sum (1/O_i)^k = 1$).
* **Ocena:** ✅ **Industrijski standard za de-vigovanje.**

### 1.5. Expected Value (EV) & Market Logic
* **Fajlovi:** `decision_engine/empirical_gate.py`, `generate_kaggle_v12.py`
* **Formula u lokalnom kodu:** `raw_ev = (p_model * best_odds) - 1.0`
* **Formula u Kaggle v12:** `market_odds = max((1.0 / p) * 0.935, 1.25)` -> **Kritičan propust!**
* **Nalaz:** U lokalnom kodu formula je poštena. U Kaggle v12 je kompromitovana veštačkim podom kvota.

### 1.6. Closing Line Value (CLV) Engine
* **Lokalni kod:** Poredi kvotu u trenutku uplate sa fer de-vigovanom kvotom na zatvaranju.
* **Kaggle v12:** `clv_fair = round(ev * 0.85, 4)` -> **Nedopustiv proksi.** CLV se ne sme izvoditi iz sopstvenog EV-a, već isključivo iz kretanja stvarnog tržišta.
* **Kaggle v14:** Pokazao pravi CLV od -9.82% i oborio sistem.

### 1.7. Kelly Criterion & Staking
* **Fajlovi:** `decision_engine/kelly_criterion.py`
* **Logika:** Fractional Kelly ($1/20$ ili $0.05$) sa `max_cap = 0.0075` (maksimalno 0.75% bankrola po tiketu).
* **Ocena:** ✅ **Konzervativno, profesionalno dimenzionisanje uloga.**

### 1.8. Empirical Decision Gate (Governance)
* **Fajlovi:** `decision_engine/empirical_gate.py`
* **Filteri:**
  * Provera marže (`p_devig vs best_odds`).
  * Provera statusa podataka (`DataQualityState.LIVE` zahtevan za uplate).
  * Provera out-of-sample kalibracije i istorijskog dokaza.
* **Klasifikacija selekcija:**
  * `NO_EDGE`: Model nema dovoljnu prednost.
  * `FAKE_EV`: Model prijavljuje prednost, ali de-vigovana kvota pokazuje da je to iluzija.
  * `MARGINAL_EV`: Edge je ispod minimalnog praga (`MIN_EDGE = 0.05`).
  * `EXECUTABLE_EV`: Jedini status koji dozvoljava opkladu.
* **Ocena:** ✅ **Vrhunski bezbednosni filter.**

---

## 2. Pretraga Kritičnih Termina i Flaw Patterns

1. **`home_xg` i `away_xg` fallback:**
   * U `scratch/run_json_pipeline.py` (linije 167-168) i `main.py` (linije 341-342):
     `h_xg = float(m.get("home_xg", 1.4))`
     `a_xg = float(m.get("away_xg", 1.1))`
   * **Nalaz:** Kada u ulaznom JSON-u nema xG polja, sistem koristi fiksne vrednosti (1.4 / 1.1). To znači da za sve takve utakmice model predviđa identične bazne parametre ako nema istoriju. Ovo je dozvoljeno samo kao testni fallback, ali je nedopustivo u produkciji.

2. **`DataQualityState` (LIVE vs STALE):**
   * U `run_json_pipeline.py` ispravno stoji `DATA_QUALITY = DataQualityState.STALE`.
   * Zahvaljujući ovome, kapija odbija da označi ijednu opkladu kao `EXECUTABLE_EV`.

3. **`floor = 1.25` u v12:**
   * Pronađeno u `unified_betting_core/generate_kaggle_v12.py:489` i `sharpbet_v12_kaggle_kernel.ipynb:480`.
   * **Status:** Fatalna greška u backtestu.
