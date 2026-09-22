# 09. Audit Tržišnog Edge-a i Profitabilnosti (Market Edge Audit)

**Datum:** 22. septembar 2026.  
**Klasifikacija Nalaza:** **MARKET_EDGE_BACKTEST = INVALID**  
**Zaključak o Profitabilnosti:** **PROFITABLE MARKET EDGE = UNPROVEN**

---

## 1. Zvanična Klasifikacija Prema Pravilima Audita

U analiziranim fazama razvoja identifikovano je prisustvo sledećih obrazaca:
```python
# Pronađeno u generate_kaggle_v12.py:489
market_odds_i1 = round(max((1.0 / p_i1) * 0.935, 1.25), 2)

# Pronađeno u generate_kaggle_v12.py:513
clv_fair = round(ev_i1 * 0.85, 4)
```

Prema obaveznim pravilima ovog audita (Sekcija H i Sekcija I):
> Ako se u kodu pojavljuje sintetičko generisanje kvota iz sopstvene verovatnoće sa podom, ili CLV kao multiplikator EV-a:
> **MARKET_EDGE_BACKTEST = INVALID**  
> **PROFITABLE MARKET EDGE = UNPROVEN**

---

## 2. Šta je Potrebno za Validnu Proveru Tržišnog Edge-a

Da bi se bilo koji kvantitativni sportski sistem proglasio profitabilnim, međunarodni institucionalni standardi (poput onih koje koriste Starlizard ili Pinnacle) zahtevaju:

1. **Stvarne istorijske kvote u trenutku uplate (Available-at-bet Odds):** Tačan timestamp kada je kvota bila dostupna na sajtu kladionice.
2. **Stvarne zatvarajuće kvote (Closing Odds):** Kvote na samom početku meča sa oštrog tržišta (Pinnacle ili Betfair Exchange).
3. **Pravilno de-vigovanje (De-vigging):** Uklanjanje stvarne marže kladionice preko Power ili Shin metode, a ne pretpostavljene marže od 6.5%.
4. **Likvidnost i limiti:** Da li je kladionica uopšte prihvatala uloge od €50 ili €100 na tom marketu, ili je limit bio €5?
5. **Realni Closing Line Value (CLV):**
   $$\text{CLV} = \frac{\text{Available Odds}}{\text{Fair Closing Odds}} - 1$$
   Pozitivan CLV u dužem roku je **jedini matematički dokaz** postojanja prednosti nad tržištem.

---

## 3. Šta se Desilo Kada su Upotrebljene Pravi Mozzart Podaci (Forenzika v14)

Kada je u verziji v14 konačno pokrenut test na 77,043 stvarnih Mozzart kvota za poluvreme:

```text
📊 Empirical Mozzart Halftime 1X2 Market Margin (N=77,043):
   Mean Overround   : 18.79%
   Median Overround : 18.48%

🛡️ GATE B AUDIT: MARKET ALPHA (VS BENCHMARK DE-VIGGED CLOSING)
   Mean CLV         : -9.82% (t = -18.90, p-value = 0.0000)
   Cluster 95% CI   : [-10.91%, -8.79%] (Match-Clustered)
GATE B STATUS       : 🛑 BLOCKED (Retail overround hurdle not cleared)
```

**Analiza ovog rezultata:**
* Prosečan CLV je bio **-9.82%**. To znači da je svaka opklada koju je model izabrao u proseku bila za skoro 10% gora od fer cene na zatvaranju.
* t-statistika od **-18.90** sa p-vrednošću $0.0000$ statistički dokazuje sa verovatnoćom od 99.999% da model na tom marketu **nema edge, već gubi novac protiv marže kladionice**.
* Zbog toga je Gate B ispravno blokirao sistem (`FAIL_CLOSED_BLOCKED`).

---

## 4. Zaključak Tržišnog Audita

Tvrdnje iz Business Case-a o "algoritamskom izvlačenju alfa prinosa" i "dokazanom ROI-ju" su neosnovane.  
Sistem je na pravim kvotama pokazao negativan CLV (-9.82%), a pozitivan prinos je postizao isključivo onda kada su mu kvote veštački servirane kroz pod od 1.25 ili kada su korišćene proksi kvote (351 od 354 opklade u v18.1).
