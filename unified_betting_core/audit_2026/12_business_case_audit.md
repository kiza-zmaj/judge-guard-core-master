# 12. Audit Biznis Plana i Finansijskih Projekcija (Business Case Audit)

**Datum:** 22. septembar 2026.  
**Analizirani dokument:** `unified_betting_core/business-case-sharpbet-2026-09-22.md`  
**Autor dokumenta:** SharpBet Executive Leadership (Interni dokument za investitore, $750K Ask)  

---

## 1. Klasifikacija Ključnih Tvrdnji Biznis Plana

| Tvrdnja iz Dokumenta | Prijavljena Vrednost | Klasifikacija Audita | Nalaz i Obrazloženje |
| :--- | :--- | :--- | :--- |
| **Model Validation** | "SharpBet Core v18.3 validated in remote Kaggle with paper-trading status" | **PARTIALLY VERIFIED / CONTRADICTED** | U v18.1 postojala je oznaka, ali na bazi 351/354 proksi kvota. U v18.3 status je `FAIL_CLOSED_BLOCKED`! |
| **Backtesting Corpus** | "1,140+ verified fixtures" | **VERIFIED** | Podaci sa football-data.co.uk postoje (380 mečeva x 3 sezone). |
| **Target Capital Ask** | "$750,000 via SAFE / Post-money cap $5.0M" | **ASSUMPTION** | Standardna pre-seed želja bez osnova u trenutnom MRR-u. |
| **Year 1 ARR** | "€1,180,000 SaaS ARR (1,800 pretplatnika)" | **PROJECTION** | Zahteva akviziciju 150 novih pretplatnika mesečno od nule. |
| **Blended ARPU** | "€57.12 mesečno" | **ASSUMPTION** | Ponderisani prosek paketa (€29, €69, €199). Nema empirijskih korisnika. |
| **CAC (Cost of Acquisition)** | "€135 po korisniku" | **UNVERIFIED** | Nema pokrenutih plaćenih kampanja (Google Ads, Meta, Twitter). |
| **Monthly Churn** | "3.8% mesečno (LTV = 26.3 meseca)" | **UNVERIFIED** | Nerealno optimistično za B2C betting alate gde je prosek industrije 8%–15%. |
| **Break-Even Milestone** | "Month 10-12: ~1,100 Paying Users \| €100K MRR" | **FALSE / CONTRADICTED** | **MATEMATIČKA GREŠKA:** $1,100 \times €57.12 = €62,832$ MRR. Nedostaje €37,168 mesečno! |
| **Syndicate Capital Yield** | "€180,000 u Y1, €420,000 u Y2, €950,000 u Y3" | **UNVERIFIED / SPECULATIVE** | Pretpostavlja profitabilan algoritam na sopstvenom bankrolu, što nije dokazano. |
| **OddsJam Akvizicija** | "Acquired for $160M (2025)" | **SOURCE-BACKED (Kao primer industrije)** | Tržišna transakcija postoji, ali OddsJam je arbitražni skener, a ne Poasonov model. |

---

## 2. Detaljna Forenzika Finansijske Nelogičnosti (€100K MRR na 1,100 Korisnika)

U sekciji 8.3 (Milestone Roadmap, linija 272) navodi se:
> `Month 10-12: Full Break-Even Milestone (~1,100 Paying Users | €100K MRR)`

U sekciji 6.1 (Unit Economics, linija 200) eksplicitno se definiše:
> `Blended Monthly ARPU: €57.12 in Year 1`

### Matematička Provera:
1. **Pravi prihod za 1,100 korisnika:**
   $$\text{Stvarni MRR} = 1{,}100 \times €57.12 = \mathbf{€62{,}832.00}$$
   **Deficit u odnosu na plan:**
   $$€100{,}000 - €62{,}832 = \mathbf{€37{,}168.00 \quad (Greška \ od \ 37.2\%)}$$

2. **Koliko je korisnika stvarno potrebno za €100,000 MRR:**
   $$\text{Potreban broj korisnika} = \frac{€100{,}000}{€57.12} = \mathbf{1{,}750.7 \approx 1{,}751 \ pretplatnik}$$

**Komentar:**  
Ovakva greška u pitch deck-u pred profesionalnim investitorom (Venture Capital ili Syndicate Angel) uništava kredibilitet finansijskog modela u prvih 5 minuta sastanka.

---

## 3. Zabluda o "Unit Economics" pre Postojanja Korisnika

Dokument koristi termin *"Observed Unit Economics"*, što je netačno:
* **CAC od €135:** Nije izmeren na tržištu, već je pretpostavljen.
* **Churn od 3.8%:** U industriji sportskog klađenja gde 95% kladioničara gubi novac, korisnici masovno otkazuju pretplate nakon 2 do 3 meseca ako nemaju trenutni profit. Churn od 3.8% bi značio prosečan vek pretplatnika od preko 2 godine, što je nerealno čak i za vodeće svetske B2B SaaS platforme.
* **LTV od €1,322:** Izveden je iz tog preniskog churn-a. Ako je stvarni churn 10% (industrijski prosek), LTV pada na samo:
  $$\text{Realni LTV} = 10 \times €57.12 \times 0.88 = \mathbf{€502.65}$$
  Pri CAC-u od €135, racio LTV/CAC pada sa prijavljenih $9.8\times$ na $3.7\times$.

---

## 4. Zaključak

Biznis plan predstavlja **ambicioznu i lepo napisanu projekciju**, ali ne poseduje empirijsku validaciju. Njegove finansijske projekcije se ne smeju predstavljati kao dokazane činjenice.
