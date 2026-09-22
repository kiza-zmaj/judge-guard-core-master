# 10. Matematička Forenzika Sintetičkog Marketa (Synthetic Market Flaw)

**Datum:** 22. septembar 2026.  
**Predmet:** Analiza fatalne greške u generisanju kvota u Kaggle v12 (`generate_kaggle_v12.py`)  
**Status Klasifikacije:**
```text
PREDICTIVE MODEL = MAY BE VALID (Dixon-Coles & kalibracija)
MARKET ROI       = INVALID (Artefakt poda kvota)
SYNTHETIC EV     = INVALID (Kružno generisanje)
SYNTHETIC CLV    = INVALID (Multiplikator fiktivnog EV-a)
```

---

## 1. Izvorna Formula u Kodu

U `generate_kaggle_v12.py` (linije 488–490) nalazi se sledeći kod:

```python
# 1. Model izračunava sopstvenu verovatnoću
p_i1 = m_probs["I1+"]

# 2. Veštačko generisanje tržišne kvote sa podom od 1.25
market_odds_i1 = round(max((1.0 / p_i1) * 0.935, 1.25), 2)

# 3. Računanje Expected Value (EV)
ev_i1 = (p_i1 * market_odds_i1) - 1.0

# 4. Trgovinski prag za ulazak u opkladu
if ev_i1 > 0.025:
    ...
```

---

## 2. Egzaktna Matematička Analiza

### 2.1. Tačka aktivacije poda (Floor Threshold)
Pod od $1.25$ se aktivira kada je proračunata kvota sa maržom manja ili jednaka $1.25$:

$$\frac{1}{p_{i1}} \times 0.935 \le 1.25$$

$$p_{i1} \ge \frac{0.935}{1.25} = 0.748 \quad (74.8\%)$$

**Zaključak 1:** Za svaku utakmicu gde model proceni da je verovatnoća za gol u prvom poluvremenu veća od **74.8%**, tržišna kvota se fiksira na **1.25**, bez obzira na to koliko je verovatnoća visoka!

---

### 2.2. Tačka gde EV postaje automatski pozitivan (+EV)
Kada je pod aktivan (`odds = 1.25`), očekivana vrednost je:

$$\text{EV} = (p_{i1} \times 1.25) - 1.0$$

Da bi EV bio pozitivan ($\text{EV} > 0$):

$$p_{i1} \times 1.25 > 1.0 \implies p_{i1} > \frac{1.0}{1.25} = 0.800 \quad (80.0\%)$$

Da bi opklada prošla ugrađeni prag trgovanja ($\text{EV} > 0.025$):

$$p_{i1} \times 1.25 - 1.0 > 0.025 \implies p_{i1} > \frac{1.025}{1.25} = 0.820 \quad (82.0\%)$$

**Zaključak 2:** Čim model proceni da je verovatnoća za gol u prvom poluvremenu veća od **82.0%**, sistem **automatski generiše +EV veću od 2.5% i uvek plasira opkladu**.

---

## 3. Prikaz Tržišne Nelogičnosti (Tabela Fiktivne Arbitraže)

| Model Verovatnoća $p$ | Prava Fer Kvota ($1/p$) | Stvarna Ponuda Kladionice (sa 6.5% marže) | Formula iz v12 Koda (`max(..., 1.25)`) | Generisani Lažni EV | Šta bi se desilo na pravom tržištu? |
| :---: | :---: | :---: | :---: | :---: | :--- |
| **70.0%** | 1.43 | 1.34 | 1.34 | -6.20% (Nema opklade) | Realno |
| **74.8%** | 1.34 | 1.25 | 1.25 | -6.50% (Nema opklade) | Granična tačka |
| **80.0%** | 1.25 | 1.17 | **1.25 (Floor)** | **0.00%** | Početak veštačkog edge-a |
| **85.0%** | 1.18 | 1.10 | **1.25 (Floor)** | **+6.25% (OPKLADA)** | Kladionica nudi 1.10, kod laže da nudi 1.25! |
| **90.0%** | 1.11 | 1.04 | **1.25 (Floor)** | **+12.50% (OPKLADA)** | Kladionica nudi 1.04, kod laže da nudi 1.25! |
| **95.0%** | 1.05 | 1.01 | **1.25 (Floor)** | **+18.75% (OPKLADA)** | Kladionica nudi 1.01, kod laže da nudi 1.25! |

---

## 4. Kako je Nastao Lažni CLV i Lažni ROI

1. **Lažni CLV:**
   U liniji 513 koda stoji:
   `"clv_fair": round(ev_i1 * 0.85, 4)`
   Pošto je `ev_i1` bio lažno naduvan na opkladama gde je $p > 0.82$, CLV je postao pozitivan množenjem sa 0.85. Zatim je sistem izračunao: `mean_clv = df_wagers['clv_fair'].mean()` i prijavio da je Gate B (Market Alpha) položen!
2. **Lažni ROI:**
   Kada se na utakmice gde pada gol u 85% slučajeva stavi fiktivna kvota od 1.25, zakon velikih brojeva garantuje ogroman pozitivan PnL. Zato je backtest prijavio visoki yield.

---

## 5. Zaključak

Ovo nije slučajnost, već klasična programska zamka ("floor artifact"). Autor je verovatno stavio `max(..., 1.25)` misleći: *"kladionice u praksi retko nude kvote ispod 1.25 za golove u poluvremenu"*.  
Međutim, ako kladionica ne nudi ispod 1.25, ona to radi tako što **pomeri granicu na 1.5 golova**, a ne tako što poklanja kvotu 1.25 za događaj koji ima 90% verovatnoće!

**Ovaj ROI se ni pod kojim uslovima ne sme koristiti u poslovnim projekcijama.**
