# 04. Izveštaj o Reproducibilnosti (Reproducibility Report)

**Datum verifikacije:** 22. septembar 2026.  
**Izvršeno u:** Lokalnom Linux okruženju sa zatečenom Python 3.12 konfiguracijom  
**Verifikator:** Antigravity Deterministic Runtime Checker  

---

## 1. Sistemski Profil i Okruženje

```text
PROJECT_PATH        : /home/kizamladjanijebac/Documents/jude guard/judge-guard-core-master
REMOTE_URL          : https://github.com/kizabgd123/judge-guard-core-master.git
BRANCH              : master (ahead by 47 commits)
HEAD_COMMIT         : eaf4b061d96c82337e7b3b962d6a645dcf4ca5b1
COMMIT_DATE         : 2026-09-22 17:51:45 +0200
WORKTREE_STATUS     : Dirty (Untracked audit and business case files)
PYTHON_VERSION      : Python 3.12.3
DEPENDENCY_SNAPSHOT : audit_2026/environment.txt
ENTRYPOINT          : scratch/run_json_pipeline.py & unified_betting_core/main.py
CONFIG_PATH         : unified_betting_core/config.py
INPUT_PATH          : /home/kizamladjanijebac/Downloads/mozzart_next_5_days_2026-09-23_to_2026-09-27.json
OUTPUT_PATH         : unified_betting_core/audit_2026/reproduction_output.json
```

---

## 2. Rezultati Reproduktivnog Pokretanja (Reproduction Run)

Izvršeno je čisto, determinističko pokretanje lokalne pipeline komponente:
`python3 scratch/run_json_pipeline.py`

### 2.1. Izvršni parametri i kontrola
* **Broj utakmica u ulaznom skupu:** 75
* **Očekivan broj ishoda (1X2):** 225
* **Preskočeno:** 1 ishod (ID 1069401, kvota 1.01 <= 1.01 — automatsko odbacivanje)
* **Evaluiranih ishoda:** 224
* **Kvalitet podataka:** `DataQualityState.STALE` (ispravno markiran statički snapshot)
* **Status istorijskog dokaza:** `historical_proof = False` (prepoznato odsustvo dokazanog edge-a)

### 2.2. Izlazni status selekcija
* `NO_EDGE` : 127
* `FAKE_EV` : 77
* `MARGINAL_EV` : 16
* `CALIBRATION_FAILED` : 4
* **EXECUTABLE_EV (Odobrene opklade):** **0**
* **Finalni tiket:** **PRAZAN TIKET (FAIL-CLOSED)**

### 2.3. Integritet i Asercije
* Sve interne asercije (`assert len(all_results) == 224`, `assert len(executable_results) == 0`) su **PROŠLE bez greške (PASS)**.
* Izlazni JSON: `audit_2026/reproduction_output.json` kreiran sa returncode = 0.

---

## 3. Determinizam i Seme Slučajnosti (Seeds)

* U fajlovima `generate_kaggle_v12.py` do `v18.py` koristi se fiksno seme: `np.random.seed(42)`.
* Dixon-Coles L-BFGS-B optimizacija konvergira deterministički na istim podacima (iteracije: 29 do 34 po ligama).
* Generisani kontrolni zbir (SHA-256) ključnih fajlova je trajno zabeležen u `audit_2026/file_hashes.sha256`.

---

## 4. Konačna Ocena Reproducibilnosti

```text
LOKALNI KOD I ARHITEKTURA KOMPONENTI : REPRODUCIBILITY = PASS
FAIL-CLOSED BEZBEDNOSNI MEHANIZAM    : REPRODUCIBILITY = PASS
PRIJAVLJENI PROFITABILNI BACKTEST    : REPRODUCIBILITY = FAIL (Zavisi od sintetičkog poda)
```

**Objašnjenje:**  
Kod radi tačno ono što piše u njemu. Na pravim podacima i sa ispravnim postavkama, on pouzdano odbija da se kladi jer nema dokazan edge. Ono što **ne može** da se reprodukuje u realnom svetu jeste pozitivan ROI, jer je taj rezultat bio artefakt veštačke formule.
