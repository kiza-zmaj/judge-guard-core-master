# 06 — Ograničenja audita (Limitations & Caveats)

> **Princip integriteta:** Svako ograničenje mora biti eksplicitno navedeno bez ulepšavanja ili prikrivanja.  
> Ovaj dokument definiše granice onoga što podaci i metodologija mogu, a šta **ne mogu** da dokažu.  

---

## L0 — Odsustvo vremenskih serija kvota (Nemogućnost empirijske dekompozicije)

**Činjenica:**
Mozzart istorijski dataset (Kaggle v2, 344.005 zapisa) ekstrahovan je iz periodičnih štampanih PDF biltena (Web lista). Svaki meč sadrži tačno jedan zabeležen skup kvota u trenutku objave biltena.

**Implikacija:**
- Dataset **ne poseduje parove otvarajućih i zatvarajućih kvota** (open vs. close timestamps) za isti meč.
- Zbog toga je **egzaktna dekompozicija CLV-a na "udeo marže" i "udeo modelske greške" empirijski nemoguća** na ovom datasetu.
- Bilo kakav raniji pokušaj procentualnog razdvajanja (npr. 80% / 20%) predstavljao je teoretsku ilustraciju zasnovanu na pretpostavljenoj marži, a ne naučno izmereni podatak.

---

## L1 — Dataset je PRIVATE na Kaggle platformi

**Činjenica:**
Kaggle dataset [`mozzart-historical-odds`](https://www.kaggle.com/datasets/kiza123123/mozzart-historical-odds) je u privatnom statusu (status: PRIVATE).

**Implikacija:**
- Iako je kernel v8 uspešno izvršen i verifikovan, nezavisna treća strana ne može samostalno da reprodukuje rezultate bez odobrenog pristupa datasetu.
- Sve metrike (344k mečeva, 18.79% marža, ECE 3.78%, CLV −9.82%) verifikovane su unutar kontrolisanog okruženja autora i logova.

---

## L2 — Gate C je statistički potkapacitiran (Underpowered)

**Činjenica:**
U Gate C backtestu realizovano je svega **$N = 89$ opklada** iz holdout skupa.

**Implikacija:**
- Formalna power analiza pokazuje da je za detekciju realnog edge-a od 2% ROI potreban uzorak od **$N = 27.374$ opklada** ($SE = 12.52\%$, $SD = 118.09\%$).
- Čak i prema umerenijim procenama iz literature (Kaunitz et al. 2017), minimum je 1.500 do 3.000 opklada.
- Interval poverenja na $N=89$ iznosi $[−23.31\%; +25.76\%]$.
- **Zaključak:** Rezultat od $+€5.90$ i ROI $+0.66\%$ predstavlja **čist statistički šum** i ne sme se tumačiti kao dokaz profitabilnosti.

---

## L3 — Odsustvo infrastrukture za realno izvršavanje (Execution Gap)

**Činjenica:**
Sistem je u fazi offline audita i ne poseduje:
1. Live WebSocket tick feed za praćenje promena kvota u milisekundama.
2. Automatski execution bridge prema kladionici ili berzi.
3. Empirijsko merenje slippage-a (klizanja kvote između signala i uplate).
4. Modelovanje limita uloga (retail kladionice agresivno limitiraju naloge koji pobeđuju closing linije).

**Implikacija:**
Čak i kada bi model teoretski imao pozitivan CLV, sistem **nije spreman za produkciju (not product-ready)** bez rešavanja execution infrastrukture.

---

## L4 — Dixon-Coles model nije state-of-the-art za moderna tržišta

**Činjenica:**
Dixon-Coles (1997) bivariate Poisson MLE model koristi isključivo istorijske rezultate i proseke postignutih i primljenih golova.

**Implikacija:**
- Model uspeva da postigne dobru kalibraciju verovatnoća (Gate A: ECE 3.78%), ali nema rezoluciju (sharpness) niti mikro-informacije (sastavi, povrede, kretanje tržišnog volumena, xG).
- Na tržištima gde je marža 18.79%, model bez specifičnog informacionog monopola gubi novac.

---

## L5 — Negativan CLV je empirijska granica, a ne univerzalna teorema

**Činjenica:**
Audit dokazuje da na testiranom uzorku (Mozzart HT 1X2, Dixon-Coles model, 2021–2026) model ostvaruje $-9.82\%$ CLV uz $t = -18.90$.

**Implikacija:**
- Ovo dokazuje da **ovaj model na ovom tržištu sa ovim kvotama nema prednost**.
- To **ne dokazuje** da je profit nemoguć generalno:
  * Na berzama kvota (Betfair) gde je provizija 2–5%.
  * Preko line shopping-a (poređenje soft kvota sa sharp Pinnacle closing linijom).
  * Korišćenjem in-play strategija ili tržišta izvedenih hendikepa.
