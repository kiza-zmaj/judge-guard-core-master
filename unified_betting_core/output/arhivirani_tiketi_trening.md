# 💾 Arhiva Uživo Tiketa i Dataset za Trening Modela

**Datum kreiranja arhive:** 21.09.2026.  
**Izvor:** Korisnički uplaćeni tiketi na kladionici **Mozzart Bet**  
**Svrha:** Kreiranje ground-truth skupa podataka, evaluacija kalibracije modela (Brier Score, Log Loss) i nadgledano dotreniravanje temperaturnog skaliranja modela (`TemperatureScaler`).

---

## 🎟️ Pregled uplaćenih tiketa sa slika

### 1. Tiket: SIGURICA / VALUE BANKERI (5 Parova)
- **Šifra tiketa:** `1137024777052893`
- **Vreme uplate:** 21.09.2026. u 00:39:15
- **Maksimalna isplata:** `99,28 RSD`
- **Ukupna kvota:** `1.9934` (~1.99)
- **Status:** ⏳ **U TOKU (PENDING)**

| # | Vreme | Meč | Takmičenje | Tip | Kvota | P(model) | Implied P | xG Prognoza | Status |
|:---:|:---:|---|---|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 | Uto 00:30 | **Criciuma vs Operario PR** | Brazil 2 | `1X` | **1.14** | 84.8% | 83.5% | Tačan rez: 1-0 | ⏳ Čeka |
| 2 | Pon 03:00 | **Malacateco vs Deportivo Mixco** | Gvatemala 1 - Apertura | `1X` | **1.14** | 84.5% | 83.4% | Tačan rez: 2-0 | ⏳ Čeka |
| 3 | Pon 01:15 | **Olimpia Tegucigalpa vs Siguatepeque** | Honduras 1 - Apertura | `12` | **1.15** | 83.6% | 82.5% | Tačan rez: 2-0 | ⏳ Čeka |
| 4 | Uto 07:00 | **Philippines M23 vs Kuwait M23** | Azijske igre | `X2` | **1.13** | 83.9% | 83.1% | Tačan rez: 0-2 | ⏳ Čeka |
| 5 | Pon 20:30 | **Trento vs Pro Vercelli** | Italija 3 A | `1X` | **1.18** | 81.8% | 80.5% | Tačan rez: 1-0 | ⏳ Čeka |

---

### 2. Tiket: MEGA KOMBO VALUE (12 Parova)
- **Šifra tiketa:** `1137024772928642`
- **Vreme uplate:** 21.09.2026. u 00:44:34
- **Maksimalna isplata:** `40.388,50 RSD`
- **Ukupna sirova kvota:** `42.43` (sa Mozzart bonus multiplikatorom na 12 parova)
- **Status:** ⏳ **U TOKU (PENDING)**

| # | Vreme | Meč | Takmičenje | Tip | Kvota | P(model) | Implied P | xG Prognoza | Status |
|:---:|:---:|---|---|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 | Pon 18:30 | **Montana vs Hebar** | Bugarska 2 | `1` | **1.90** | 53.6% | 50.5% | Tačan rez: 1-0 | ⏳ Čeka |
| 2 | Pon 03:00 | **Malacateco vs Deportivo Mixco** | Gvatemala 1 - Apertura | `1` | **1.70** | 60.0% | 56.5% | Tačan rez: 2-0 | ⏳ Čeka |
| 3 | Uto 00:00 | **Guabira vs SA Bulo Bulo** | Bolivija Liga Kup | `2+` | **1.18** | 80.1% | 79.2% | Tačan rez: 2-0 | ⏳ Čeka |
| 4 | Pon 20:45 | **Redditch vs Rc Warwick** | Engleska 7 - Central | `2+` | **1.20** | 78.7% | 77.8% | Tačan rez: 2-0 | ⏳ Čeka |
| 5 | Pon 19:00 | **HB Koge vs Hobro IK** | Danska 2 | `2+` | **1.20** | 78.4% | 77.6% | Tačan rez: 1-1 | ⏳ Čeka |
| 6 | Pon 01:15 | **Olimpia Tegucigalpa vs Siguatepeque** | Honduras 1 - Apertura | `1` | **1.33** | 76.2% | 73.0% | Tačan rez: 2-0 | ⏳ Čeka |
| 7 | Pon 02:30 | **Velez Sarsfield vs Tigre** | Argentina 1 - Klausura | `1X` | **1.30** | 76.5% | 74.2% | Tačan rez: 1-0 | ⏳ Čeka |
| 8 | Uto 02:15 | **Lanus vs Estudiantes de La Plata** | Argentina 1 - Klausura | `1X` | **1.31** | 75.3% | 73.8% | Tačan rez: 1-0 | ⏳ Čeka |
| 9 | Pon 20:30 | **Dolomiti Bellunesi vs Lumezzane** | Italija 3 A | `1X` | **1.30** | 74.1% | 73.5% | Tačan rez: 1-0 | ⏳ Čeka |
| 10 | Pon 01:30 | **LDU Quito vs Universidad Catolica** | Ekvador 1 | `1X` | **1.30** | 73.2% | 72.9% | Tačan rez: 1-1 | ⏳ Čeka |
| 11 | Uto 00:00 | **Nueva Chicago vs Patronato** | Argentina 2 | `1X` | **1.32** | 72.9% | 72.1% | Tačan rez: 1-0 | ⏳ Čeka |
| 12 | Pon 16:00 | **Sportist Svoge vs Vihren Sandanski** | Bugarska 2 | `2` | **1.53** | 64.0% | 61.2% | Tačan rez: 0-1 | ⏳ Čeka |

---

## 🛠️ Arhivirani fajlovi i struktura u bazi

1. **Strukturirana JSON baza uplate:**  
   [`unified_betting_core/data/training/placed_tickets_archive.json`](file:///home/kizamladjanijebac/Documents/jude%20guard/judge-guard-core-master/unified_betting_core/data/training/placed_tickets_archive.json)  
   Čuva kompletne metapodatke tiketa, šifre, kvote, uloge, potencijalne isplate i stanja pojedinačnih parova.

2. **Tabelarni CSV skup za treniranje i evaluaciju:**  
   [`unified_betting_core/data/training/mozzart_training_dataset.csv`](file:///home/kizamladjanijebac/Documents/jude%20guard/judge-guard-core-master/unified_betting_core/data/training/mozzart_training_dataset.csv)  
   Sadrži 17 uzoraka sa izvučenim matematičkim atributima:
   - `xg_home`, `xg_away` (očekivani golovi iz Poisson PMF modela)
   - `p_model` (predviđena verovatnoća)
   - `implied_prob_devigged` (tržišna verovatnoća očišćena od marže kladionice)
   - `edge` (matematička prednost modela u odnosu na ponudu)
   - `outcome_win` (0 ili 1 — popunjava se po završetku meča)

3. **Trening & Evaluacioni Engine:**  
   [`unified_betting_core/training/model_trainer.py`](file:///home/kizamladjanijebac/Documents/jude%20guard/judge-guard-core-master/unified_betting_core/training/model_trainer.py)  
   Automatizovano ocenjivanje rezultata, računanje Brier skora, Log gubitka i kalibracije parametara modela.

---

## 🚀 Kako unositi rezultate mečeva i trenirati model

Kada se mečevi završe, rezultati se unose jednostavnom komandom:
```bash
python3 -m unified_betting_core.training.model_trainer --record-result "Montana vs Hebar" "1-0"
```
ili za golove:
```bash
python3 -m unified_betting_core.training.model_trainer --record-result "Guabira vs SA Bulo Bulo" "2-1"
```

Aplikacija će automatski:
1. Odrediti da li je tip dobitan (`WIN`) ili gubitan (`LOSS`) za sve povezane tikete.
2. Ažurirati Brier skill score ($BSS$) u odnosu na kladionicu.
3. Pokrenuti optimizaciju temperaturnog skaliranja ($T$) kako bi se model automatski re-kalibrisao za naredna kola.
