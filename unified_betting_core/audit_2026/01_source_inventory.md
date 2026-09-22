# 01. Inventar Svih Izvora i Podataka

**Datum popisa:** 22. septembar 2026.  
**Obuhvat:** Lokalni repozitorijumi, Git/GitHub, Kaggle cloud okruženje, baze podataka i projektna dokumentacija.

---

## 1. Zbirna Tabela Izvora

| Izvor (Source) | Putanja / URL | Verzija | Datum | Dostupnost | SHA-256 Hash / ID | Korišćen u trenutnoj aplikaciji | Dokaz (Evidence) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Lokalno jezgro** | `.../unified_betting_core/main.py` | 1.0.0 | 2026-09-21 | VERIFIED | `ae9e7128a81a...` | DA (Glavni CLI) | Fajl postoji, parsira argumente |
| **Lokalni runner** | `.../scratch/run_json_pipeline.py` | v18.3 QA | 2026-09-22 | VERIFIED | `88d7dd897013...` | DA (QA verifikator) | Izvršen uspešno, 224 ishoda |
| **Dixon-Coles v12** | `.../unified_betting_core/generate_kaggle_v12.py` | v12.1 | 2026-09-21 | VERIFIED | `9bffa01022ac...` | NE (Kaggle generator) | Sadrži `max(..., 1.25)` bug |
| **Dixon-Coles v18** | `.../unified_betting_core/generate_kaggle_v18.py` | v18.3.0 | 2026-09-22 | VERIFIED | `46bc92cb8271...` | DA (Zadnji kernel) | Sadrži 2025/26 holdout kapiju |
| **Kaggle Kernel v12** | `kiza123123/sharpbet-v12-halftime-goals-audit` | v12 | 2026-09-21 | VERIFIED | `5c6e6b18166c...` | NE (Prethodna faza) | Log fajl: 76 redova |
| **Kaggle Kernel v18** | `kiza123123/sharpbet-v18-halftime-goals-production` | v15 (Kaggle) | 2026-09-22 | VERIFIED | scriptVersionId=351902188 | DA (Remote build) | `gate_verdicts.json` |
| **Mozzart Dataset** | Kaggle: `kiza123123/mozzart-historical-odds` | 2026 update | 2026-09-19 | VERIFIED | 394,088 redova | DA (Trening/Audit) | Kaggle metadata & kernel log |
| **Mozzart JSON** | `Downloads/mozzart_next_5_days_...json` | Snapshot | 2026-09-22 | VERIFIED | 75 utakmica | DA (Lokalni test) | `run_json_pipeline.log` |
| **Ground Truth DB** | `football-data.co.uk` (E0, SP1, I1, D1, F1) | 22/23–25/26 | 2026-09-22 | VERIFIED | 7,081 utakmica | DA (Validacioni skup) | Downloaded in Kaggle |
| **Business Case** | `.../business-case-sharpbet-2026-09-22.md` | v1.0 | 2026-09-22 | VERIFIED | `980de9e1608c...` | DA (Dokumentacija) | 326 linija teksta |
| **Market Analiza** | `.../market-opportunity-analysis-2026-09-22.md` | v1.0 | 2026-09-22 | VERIFIED | `304d974caf42...` | DA (Dokumentacija) | 277 linija teksta |

---

## 2. Lokalni Projekti i Kopije

1. **Glavno radno stablo (Master Repo):**
   * Putanja: `/home/kizamladjanijebac/Documents/jude guard/judge-guard-core-master`
   * Poddirektorijum modula: `unified_betting_core/`
   * Povezivanje: Simbolički link `unified_betting_core/unified_betting_core -> .` omogućen radi unakrsnog importovanja.

2. **Pomoćni i radni direktorijumi:**
   * `scratch/`: Sadrži `run_json_pipeline.py` (QA runner) i `pseudo_labeling_experiment.py`.
   * `exports/`: Sadrži eksportovane JSON/CSV izveštaje iz ranijih faza.
   * `kaggle_pulled_kernel/`: Sadrži preuzeta stanja kernela sa Kaggle API-ja.
   * `sharpbet-v8-audit/`: Arhiva rane verzije v8 (prethodna Poason arhitektura).

---

## 3. Git i GitHub Stanje

* **Lokalni Git:**
  * Branch: `master` (ahead of `origin/master` by 47 commits).
  * Poslednji commit na masteru: `eaf4b06` (*2026-09-22 17:51:45 +0200*).
  * Poruka: `checkpoint: SharpBet Core v18.3 Implementation & Kaggle Verification (JudgeGuard)`.
* **Remote Repository:**
  * URL: `https://github.com/kizabgd123/judge-guard-core-master.git`
  * Status pristupa GitHub API-ju: Blokirano za direktan push bez tokena, ali lokalna kopija sadrži kompletnu istoriju sa 47 nepoguranih commitova.
* **Uočene anomalije u Git konfiguraciji:**
  * Poddirektorijum `my-worker` prijavljuje `fatal: no submodule mapping found in .gitmodules for path 'my-worker'`. To je lokalni repozitorijum (Cloudflare Worker) unutar stabla koji nije formalno registrovan u `.gitmodules`.

---

## 4. Kaggle Okruženje i Artefakti

* **Korisnički nalog:** `kiza123123`
* **Glavni kernel metadata:** `kernel-metadata.json`
  * ID: `kiza123123/sharpbet-v12-halftime-goals-audit`
  * Skripta: `sharpbet-v12-halftime-goals-audit.ipynb`
  * Dataset: `kiza123123/mozzart-historical-odds`
* **Zadnji izvršeni cloud build:**
  * Script Version ID: `351902188` (odgovara verziji 15 na Kaggle-u, v18.1/v18.3).
  * Generisani izlaz: `gate_verdicts.json` (potvrđuje fail-closed mehanizam i disproporciju sintetičkih opklada).
