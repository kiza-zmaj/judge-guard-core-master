# 🏆 Mozzart Kvantitativni Tiketi — Unified Betting Core Pipeline

**Datum analize:** 21.09.2026. | **Izvor:** Mozzart Ponuda (45 mečeva, 405 tržišta)  
**Način pokretanja:** Nativna `unified_betting_core.main` aplikacija (`--run-pipeline --mozzart`)  
**Matematički engine:** Dixon-Coles Bivariate Poisson (`PoissonEngine`) + Power De-vigging (`DevigEngine`) + `EmpiricalDecisionGate` + `KellyCriterion`  

---

## 📊 Sažetak kreiranih tiketa (Generisano kroz `unified_betting_core`)

| # | Naziv tiketa | Strategija | Parova | Ukupna kvota | P(prolaz) | Preporučeni ulog | Potencijalni dobitak |
|---|---|---|:---:|:---:|:---:|:---:|:---:|
| 1 | **Tiket 1: SIGURICA / VALUE BANKERI** | Visoka verovatnoća prolaza (>75%), optimalne niske marže | 5 | **1.99** | 41.1% | €20.00 | **€39.80** |
| 2 | **Tiket 2: URAVNOTEŽENI VALUE TIKET** | Maksimalni kvalitet kvota u ligama sa najnižom maržom (Argentina 1), umeren rizik | 4 | **6.70** | 16.3% | €15.00 | **€100.50** |
| 3 | **Tiket 3: GOLOVI SPECIJAL (2+ / 0-2 / 3+)** | Poisson distribucija očekivanih golova: 2+ u efikasnim i 0-2 u taktičkim ligama | 4 | **2.01** | 38.7% | €15.00 | **€30.15** |
| 4 | **Tiket 4: NOĆNI EKSPRES (Južna i Srednja Amerika)** | Noćni mečevi (00:00 - 03:30), optimalna kombinacija favorita i golova | 4 | **2.14** | 40.1% | €15.00 | **€32.10** |
| 5 | **Tiket 5: SISTEM 4 OD 6 (Sa zaštitom)** | Sistem 4 od 6 — dobitan sa 4 pogođena para, maksimalan profit na 5 i 6 | 6 | **5.13** | 17.4% | €15.00 | **€76.95** |
| 6 | **Tiket 6: LOVAC NA KVOTE (Visoki prinos)** | Odabrani favoriti i golovi kvota 1.45 - 2.10 za veći dobitak | 5 | **8.38** | 10.4% | €10.00 | **€83.80** |

---

### 📋 Tiket 1: SIGURICA / VALUE BANKERI
**Strategija:** Visoka verovatnoća prolaza po paru (>80%), ukupna kvota ~2.00  
**Ukupna kvota:** `1.99` | **Zajednička verovatnoća:** `41.1%`  
**Ulog:** `€20.00` | **Potencijalni dobitak:** `€39.80`  

| Br. | Vreme | Meč | Takmičenje | Tip | Kvota | P(kalib.) | xG Prognoza |
|:---:|:---:|---|---|:---:|:---:|:---:|:---:|
| 1 | Uto 00:30 | **Criciuma vs Operario PR** | Brazil 2 | `1X` | **1.14** | 84.8% | Tačan rez: 1-0 |
| 2 | Pon 03:00 | **Malacateco vs Deportivo Mixco** | Gvatemala 1 - Apertura | `1X` | **1.14** | 84.6% | Tačan rez: 2-0 |
| 3 | Uto 07:00 | **Philippines M23 vs Kuwait M23** | Azijske igre | `X2` | **1.13** | 83.9% | Tačan rez: 0-2 |
| 4 | Pon 01:15 | **Olimpia Tegucigalpa vs Independiente Siguatepeque** | Honduras 1 - Apertura | `12` | **1.15** | 83.6% | Tačan rez: 2-0 |
| 5 | Pon 20:30 | **Trento vs Pro Vercelli** | Italija 3 A | `1X` | **1.18** | 81.8% | Tačan rez: 1-0 |

---

### 📋 Tiket 2: URAVNOTEŽENI VALUE TIKET
**Strategija:** Favoriti u ligama sa najnižom maržom kladionice, odličan odnos rizika i prinosa  
**Ukupna kvota:** `6.70` | **Zajednička verovatnoća:** `16.3%`  
**Ulog:** `€15.00` | **Potencijalni dobitak:** `€100.50`  

| Br. | Vreme | Meč | Takmičenje | Tip | Kvota | P(kalib.) | xG Prognoza |
|:---:|:---:|---|---|:---:|:---:|:---:|:---:|
| 1 | Pon 00:15 | **Belgrano vs Estudiantes Río Cuarto** | Argentina 1 - Klausura | `1` | **1.45** | 70.9% | Tačan rez: 2-0 |
| 2 | Pon 01:30 | **Luis Angel Firpo Usulutan vs Atletico Balboa** | El Salvador 1 - Apertura | `1` | **1.43** | 71.3% | Tačan rez: 2-0 |
| 3 | Pon 03:00 | **Malacateco vs Deportivo Mixco** | Gvatemala 1 - Apertura | `1` | **1.70** | 60.0% | Tačan rez: 2-0 |
| 4 | Pon 18:30 | **Montana vs Hebar** | Bugarska 2 | `1` | **1.90** | 53.6% | Tačan rez: 1-0 |

---

### 📋 Tiket 3: GOLOVI SPECIJAL (2+ / 0-2)
**Strategija:** Poisson raspodela efikasnosti: 2+ u otvorenim ligama  
**Ukupna kvota:** `2.01` | **Zajednička verovatnoća:** `38.7%`  
**Ulog:** `€15.00` | **Potencijalni dobitak:** `€30.15`  

| Br. | Vreme | Meč | Takmičenje | Tip | Kvota | P(kalib.) | xG Prognoza |
|:---:|:---:|---|---|:---:|:---:|:---:|:---:|
| 1 | Uto 00:00 | **Guabira vs SA Bulo Bulo** | Bolivija Liga Kup | `2+` | **1.18** | 80.1% | Tačan rez: 2-0 |
| 2 | Pon 20:45 | **Redditch vs Rc Warwick** | Engleska 7 - Central | `2+` | **1.20** | 78.7% | Tačan rez: 2-0 |
| 3 | Pon 19:00 | **HB Koge vs Hobro IK** | Danska 2 | `2+` | **1.20** | 78.4% | Tačan rez: 1-1 |
| 4 | Pon 01:15 | **Olimpia Tegucigalpa vs Independiente Siguatepeque** | Honduras 1 - Apertura | `2+` | **1.18** | 78.3% | Tačan rez: 2-0 |

---

### 📋 Tiket 4: NOĆNI EKSPRES (Južna i Srednja Amerika)
**Strategija:** Noćni mečevi (00:00 - 03:30), optimalna kombinacija favorita i golova  
**Ukupna kvota:** `2.14` | **Zajednička verovatnoća:** `40.1%`  
**Ulog:** `€15.00` | **Potencijalni dobitak:** `€32.10`  

| Br. | Vreme | Meč | Takmičenje | Tip | Kvota | P(kalib.) | xG Prognoza |
|:---:|:---:|---|---|:---:|:---:|:---:|:---:|
| 1 | Pon 01:30 | **Luis Angel Firpo Usulutan vs Atletico Balboa** | El Salvador 1 - Apertura | `12` | **1.19** | 80.9% | Tačan rez: 2-0 |
| 2 | Uto 00:00 | **Guabira vs SA Bulo Bulo** | Bolivija Liga Kup | `2+` | **1.18** | 80.1% | Tačan rez: 2-0 |
| 3 | Pon 00:15 | **Belgrano vs Estudiantes Río Cuarto** | Argentina 1 - Klausura | `12` | **1.25** | 78.8% | Tačan rez: 2-0 |
| 4 | Pon 00:00 | **Cibao vs Univ. Organizacion y Metodo** | Dominikanska Republika 1 | `12` | **1.22** | 78.6% | Tačan rez: 2-0 |

---

### 📋 Tiket 5: SISTEM 4 OD 6 (Sa zaštitom)
**Strategija:** Sistem 4 od 6 (15 kombinacija) — dobitan sa 4 pogođena para  
**Ukupna kvota (sve pogođeno):** `5.13` | **Zajednička verovatnoća:** `17.4%`  
**Ulog:** `€15.00` (€1.00 po kombinaciji) | **Maksimalni dobitak:** `€76.95`  

| Br. | Vreme | Meč | Takmičenje | Tip | Kvota | P(kalib.) | xG Prognoza |
|:---:|:---:|---|---|:---:|:---:|:---:|:---:|
| 1 | Pon 02:30 | **Velez Sarsfield vs Tigre** | Argentina 1 - Klausura | `1X` | **1.30** | 76.5% | Tačan rez: 1-0 |
| 2 | Pon 01:15 | **Olimpia Tegucigalpa vs Independiente Siguatepeque** | Honduras 1 - Apertura | `1` | **1.33** | 76.2% | Tačan rez: 2-0 |
| 3 | Uto 02:15 | **Lanus vs Estudiantes de La Plata** | Argentina 1 - Klausura | `1X` | **1.31** | 75.3% | Tačan rez: 1-0 |
| 4 | Pon 20:30 | **Dolomiti Bellunesi vs Lumezzane** | Italija 3 A | `1X` | **1.30** | 74.1% | Tačan rez: 1-0 |
| 5 | Pon 01:30 | **LDU Quito vs Universidad Catolica** | Ekvador 1 | `1X` | **1.32** | 73.2% | Tačan rez: 1-1 |
| 6 | Uto 00:00 | **Nueva Chicago vs Patronat** | Argentina 2 | `1X` | **1.32** | 72.9% | Tačan rez: 1-0 |

---

### 📋 Tiket 6: LOVAC NA KVOTE (Visoki prinos)
**Strategija:** Odabrani favoriti i golovi kvota 1.50 - 2.10 za veći dobitak  
**Ukupna kvota:** `8.38` | **Zajednička verovatnoća:** `10.4%`  
**Ulog:** `€10.00` | **Potencijalni dobitak:** `€83.80`  

| Br. | Vreme | Meč | Takmičenje | Tip | Kvota | P(kalib.) | xG Prognoza |
|:---:|:---:|---|---|:---:|:---:|:---:|:---:|
| 1 | Pon 16:00 | **Sportist Svoge vs Vihren Sandanski** | Bugarska 2 | `2` | **1.53** | 64.0% | Tačan rez: 0-1 |
| 2 | Pon 00:00 | **Cibao vs Univ. Organizacion y Metodo** | Dominikanska Republika 1 | `1` | **1.55** | 63.8% | Tačan rez: 2-0 |
| 3 | Pon 03:30 | **Juticalpa vs CD Marathon** | Honduras 1 - Apertura | `2` | **1.53** | 63.7% | Tačan rez: 0-1 |
| 4 | Pon 00:15 | **Belgrano vs Estudiantes Río Cuarto** | Argentina 1 - Klausura | `2+` | **1.50** | 63.6% | Tačan rez: 2-0 |
| 5 | Pon 19:30 | **Aldosivi vs Atletico Tucuman** | Argentina 1 - Klausura | `1X` | **1.54** | 63.2% | Tačan rez: 1-1 |
