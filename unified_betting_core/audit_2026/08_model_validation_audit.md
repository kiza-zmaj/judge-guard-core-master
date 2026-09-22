# 08. Validacija Modela i Kalibracija (Model Validation Audit)

**Datum:** 22. septembar 2026.  
**Predmet:** Evaluacija prediktivne snage, kalibracije verovatnoća i stabilnosti Dixon-Coles modela  

---

## 1. Zbirna Tabela Validacionih Metrika

| Metrika | Trening Skup (22/23 – 23/24) | Dev Skup (2024/25) | Final Untouched Holdout (2025/26) | Institucionalni Prag (Gate) | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Uzorak (Mečevi)** | 3,800 mečeva | 1,751 meč | 1,530 mečeva | $\ge 1,000$ mečeva | **PASSED** |
| **Macro ECE (Expected Calibration Error)** | 2.81% | 3.78% – 3.79% | 4.12% | $\le 6.00\%$ | **PASSED (Gate A)** |
| **Macro Brier Score** | 0.2015 | 0.2171 – 0.2235 | 0.2289 | $\le 0.2300$ | **PASSED (Gate A)** |
| **Brier Score (Market I1+)** | 0.1650 | 0.1776 | 0.1810 | $\le 0.2000$ | **PASSED** |
| **Brier Score (Market I2+)** | 0.2190 | 0.2334 | 0.2395 | $\le 0.2500$ | **PASSED** |
| **Dixon-Coles Korelacija $\rho$** | -0.021 do -0.078 | Stabilna po ligama | Stabilna po ligama | $[-0.15, 0.00]$ | **PASSED (Gate 0)** |
| **Closing Market Benchmark (CLV)** | N/A | -9.82% (Prave Mozzart) | N/A | $> 0.00\%$ | **BLOCKED (Gate B)** |
| **Realizovani Yield (PnL %)** | N/A | +0.66% (95% CI [-23%, +25%]) | **-0.79%** (OOS) | $> +2.00\%$ | **BLOCKED (Gate C)** |

---

## 2. Analiza Prediktivne Kalibracije (Gate A)

### 2.1. Šta je ECE i šta znače ovi brojevi?
Expected Calibration Error meri odstupanje između predviđene verovatnoće i stvarne učestalosti događaja. Ako model kaže da 100 utakmica ima 70% šanse za gol u prvom poluvremenu, tačno oko 70 tih utakmica zaista mora imati gol.
* **Izmereni ECE od 3.78% na 1,751 meču:** Ovo je izvanredan rezultat za fudbalsko modelovanje. Model ne pati od overconfidence-a (prevelike samouverenosti) niti underconfidence-a.
* **Brier Score od 0.2171:** Znatno bolji od naivnog "flip coin" modela (0.2500).

### 2.2. Da li je kalibracija dovoljna za pobedu nad kladionicom?
**NE.**  
Biti dobro kalibrisan znači znati *tačnu* verovatnoću. Ali kladionica Mozzart uzima maržu (overround) od **18.48% do 18.79%** na poluvremenima!  
Da bi model pobedio toliku maržu, on ne sme biti samo "dobro kalibrisan", on mora imati **ogromnu asimetriju informacija u odnosu na kvotera kladionice**. Dixon-Coles model koji se oslanja samo na istoriju golova tu asimetriju jednostavno **nema**.

---

## 3. Zaključak Validacije Modela

1. **Kao statistički model verovatnoće:** Model je **RESEARCH VALID**. Radi stabilno, konvergira, dobro procenjuje verovatnoće.
2. **Kao kladioničarski alfa-generator:** Model je **INSUFFICIENT**. Njegova prediktivna preciznost nije dovoljna da savlada maržu kladionice od 18.5%.
