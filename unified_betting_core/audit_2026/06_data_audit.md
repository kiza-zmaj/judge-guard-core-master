# 06. Audit Podataka i Data Provenance (Data Audit)

**Datum:** 22. septembar 2026.  
**Predmet:** Analiza integriteta svih korišćenih datasetova u SharpBet sistemu  

---

## 1. Pregled Svih Korišćenih Datasetova

| Dataset | Izvor / Poreklo | Broj Redova / Mečeva | Vremenski Raspon | Integritet | Uočeni Problemi |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Mozzart JSON Snapshot** | Mozzart Web listing (lokalni JSON) | 75 mečeva / 224 validna ishoda | 23.09.2026 – 27.09.2026 | **100% VERIFIED** | 1 kvota nevalidna (1.01 <= 1.01). Nema xG polja. |
| **Mozzart Historical Odds** | Kaggle: `kiza123123/mozzart-historical-odds` | 394,088 redova (344,005 mečeva) | 02.06.2021 – 19.09.2026 | **DELIMIČAN** | 274,290 redova nema datum meča (legacy PDF bilteni). |
| **Football-Data Ground Truth** | `football-data.co.uk` (Top 5 liga) | 7,081 mečeva (4 sezone) | Sezone 2022/23 do 2025/26 | **VERIFIED** | Potpuno pokriveni FT i 1H rezultati i Pinnacle kvote. |

---

## 2. Detaljni Audit Mozzart JSON Fajla (75 Utakmica)

Verifikovan fajl: `/home/kizamladjanijebac/Downloads/mozzart_next_5_days_2026-09-23_to_2026-09-27.json`

* **Ukupno utakmica:** 75
* **Očekivano ishoda (1X2):** $75 \times 3 = 225$
* **Preskočeni ishodi:** Tačno 1 ishod:
  * **Match ID:** `1069401`
  * **Meč:** `Servette Geneve W vs Lion W`
  * **Ishod:** `away`
  * **Kvota:** `1.01`
  * **Razlog odbacivanja:** Pravilo minimalne kvote u sistemu (`val <= 1.01` je nevažeća kvota za modelovanje).
* **Ukupno evaluiranih ishoda:** **224**
* **Odsustvo xG podataka:** JSON sadrži samo osnovne podatke o kvotama i ligama. Ne sadrži `home_xg` i `away_xg`, zbog čega je sistem morao da upotrebi bazni fallback (1.4 / 1.1).

---

## 3. Forenzika Kaggle Dataseta `mozzart-historical-odds`

Dataset koji je autor postavio na Kaggle sadrži 394,088 zapisa, ali krije veliku manu u poreklu podataka koja je tek u verziji v18.3 formalno priznata:

1. **Problem datuma (274,290 redova bez datuma):**
   * Izvor podataka su delom bili štampani i PDF bilteni Mozzarta koji su izlazili utorkom i petkom.
   * U tim PDF-ovima utakmice su grupisane po danima ili ligama, ali mnogi pojedinačni redovi nisu imali eksplicitan timestamp.
   * Zbog toga čak 274,290 redova ne može pouzdano da se poređa u vremensku seriju bez rizika od preplitanja kola.
2. **Pokrivenost poluvremena:**
   * Od 344,005 mečeva, 333,507 ima poluvremenske 1X2 kvote (96.9%).
   * Međutim, specijali poput `I1+`, `I2+`, `I 0-1` nisu postojali u tabelarnom obliku u starijim godinama, već samo bazični `1X2` za prvo poluvreme.
   * To objašnjava zašto su u verzijama v12 i v18 korišćene **sintetičke kvote za markete golova**, umesto pravih Mozzartovih kvota za specijale!

---

## 4. Razdvajanje Trening i Test Skupova (Data Splits)

* **Train period:** Sezone 2022/23 i 2023/24 (Top 5 liga, 3,800 mečeva).
* **Development / Validation:** Sezona 2024/25 (1,751 meč).
* **Final Untouched Holdout:** Sezona 2025/26.
* **Temporalna separacija:** Podela je urađena isključivo hronološki, što sprečava curenje sezonskih formi u trening set.
