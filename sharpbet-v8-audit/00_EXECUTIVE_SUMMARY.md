# SharpBet v8 — Izvršni sažetak (Executive Summary)

> **Verdikt sistema:** `FAIL_CLOSED_BLOCKED`  
> **Predmet evaluacije:** Kernel v8 (`scriptVersionId=351589004`), offline audit halftime 1X2 modela  
> **Status:** Konačni audit zasnovan isključivo na verifikovanim brojevima i literaturi  

---

## 1. Činjenična baza (Potvrđeno iz Kernel v8 loga)

Sve brojke u ovoj tabeli potiču direktno iz izvršavanja Kernela v8 i Kaggle Dataset v2:

| Parametar / Metrika | Izmerena vrednost | Status / Značenje |
|---|---:|---|
| **Ukupno mečeva u datasetu** | **344.005** | Dataset v2 (43,53 MB, 19 kolona) |
| **Direktne poluvreme (HT) 1X2 kvote** | **333.507** (96,9%) | Izvučeno iz Mozzart PDF biltena |
| **Broj liga** | **1.364** | Globalna pokrivenost |
| **Tržišni overround (poluvreme 1X2)** | Prosek: **18,79%** / Medijana: **18,48%** | Izmereno na $N = 77.043$ mečeva |
| **Dixon-Coles MLE optimizacija** | `Success: True` | Identifikacija parametara konvergirala |
| **Gate A — Kalibracija verovatnoća** | **Macro ECE 3,78%**, Brier **0,2171** | **PASSED** |
| **Gate B — Tržišna prednost (CLV)** | Mean CLV: **−9,82%** [95% CI: −10,91%; −8,79%] | **BLOCKED** ($t = -18,90, p < 10^{-10}$) |
| **Gate C — Simulirani PnL & ROI** | ROI: **+0,66%**, PnL: **+€5,90**, $N = 89$ | **STATISTIČKI ŠUM** [95% CI: −23,31%; +25,76%] |

---

## 2. Odgovor na ključno pitanje: Da li je problem u tržištu ili u modelu?

### Metodološka istina o dekompoziciji CLV-a
U prethodnim nacrtima pokušana je dekompozicija CLV-a na procente (npr. 80% tržište / 20% model) polazeći od pretpostavke da closing margina iznosi 10%. 
**Taj split je matematički neprihvatljiv kao empirijski nalaz jer počiva na nedokazanoj pretpostavci.**

**Stvarno stanje dataseta:**
- Mozzart istorijski dataset potiče iz PDF biltena (Web lista).
- Svaki zapis sadrži **samo jednu kvotu po meču** (kvotu u trenutku štampe/objave).
- Dataset **ne poseduje parove kvota** (open vs. closing timestamped linije).
- **Zaključak:** Bez parnih kvota za isti meč, **egzaktna numerička dekompozicija CLV-a na tržišnu i modelsku komponentu je NEIZMERLJIVA na ovim podacima.**

### Šta jeste nepobitno dokazano:
1. **Margina od 18,79% je ogromna prepreka:** U retail kladionicama (softbooks) poluvremeni 1X2 market ima ogroman overround (~18,8%). 
2. **CLV je fatalno negativan (−9,82%):** Sa Studentovim $t = -18,90$, nulta hipoteza ($H_0: \text{CLV} \ge 0$) se kategorički odbacuje. Kvote koje model selektuje u proseku gube 9,82% vrednosti u odnosu na fer cene.
3. **Akademski konsenzus (Kaunitz et al. 2017, NotebookLM konsenzus):** Fundamentalni modeli (kao što je Poisson / Dixon-Coles) koji koriste isključivo javne podatke (istorijski golovi) ne mogu samostalno da prevaziđu marginu veću od 15% bez linijskog šopinga (line shopping) ili eksploatacije kvota koje kasne (lagging odds).

---

## 3. Zašto je Gate A PASSED, a Gate B BLOCKED? (Razbijanje prividnog paradoksa)

To što je model dobro kalibrisan (Gate A PASS, ECE 3,78%), a istovremeno gubi novac (Gate B BLOCKED, CLV −9,82%) nije nikakav paradoks:
- **Kalibracija (Gate A)** meri **unutrašnju konzistentnost verovatnoća**: kada model kaže da je verovatnoća 40%, taj ishod se u stvarnosti dešava u približno 40% slučajeva (Gneiting & Raftery 2007, Brümmer et al. 2013).
- **Tržišna prednost (Gate B)** meri **odnos modela prema ponuđenoj ceni**: ako bukmejker naplaćuje 18,79% provizije, čak i savršeno kalibrisan model koji se kladi na fer verovatnoće imaće negativan očekivani prinos od oko $-8\%$ do $-10\%$!
- **Zaključak:** *Kalibracija je nužan, ali nikako dovoljan uslov za profitabilnost.* Model tačno procenjuje verovatnoće, ali nema informacioni monopol („alpha“) nad tržištem koje ima ogromnu maržu.

---

## 4. Zašto je Gate C "Technical Pass" statistički irelevantan?

U auditu Gate C beleži ROI od $+0,66\%$ i PnL od $+€5,90$ na $N = 89$ opklada. 
Formalna power analiza (dvostrani test, $\alpha=0,05, 1-\beta=0,80$ sa $SE = 12,52\%, SD = 118,09\%$):
- Za statistički pouzdanu detekciju prednosti od **2% ROI**: potreban je uzorak od **$N = 27.374$ opklada** (308 puta više od realizovanog).
- Za detekciju prednosti od **3% ROI**: potreban je uzorak od **$N = 12.166$ opklada**.
- Interval poverenja na $N=89$ iznosi $[−23,31\%; +25,76\%]$ i obuhvata nulu.

**Presuda za Gate C:** Rezultat od $+€5,90$ na 89 opklada je **čist statistički šum**. Tretiranje ovog rezultata kao bilo kakvog pozitivnog signala predstavljalo bi klasičan backtest overfitting (Bailey & López de Prado 2014).

---

## 5. Zaključna presuda i status

- **Finalni status:** `FAIL_CLOSED_BLOCKED` je **ispravan, rigorozan i trajan** za ovaj pipeline.
- **Kapital:** Zaštićen. Kočnica je obavila svoju primarnu funkciju i sprečila raspodelu realnih sredstava na strategiju sa negativnim CLV-om.
- **Sledeći koraci:** Dokumentovani u [`07_DECISION.md`](./07_DECISION.md) i [`01_JTBD.md`](./01_JTBD.md).
