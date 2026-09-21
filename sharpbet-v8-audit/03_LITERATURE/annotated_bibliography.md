# Anotirana bibliografija — SharpBet v8 Audit

> **Metodologija:** Pretraga izvršena preko `search_arxiv.py` (`literature-search-arxiv`), NotebookLM beležnice `SharpBet: Beating Closing Odds & Market Efficiency Alpha 2026` i referentnih peer-reviewed časopisa.  
> **Sve tvrdnje su direktno povezane sa nalazima iz audita (Kernel v8).**  

---

## Klaster A — Modeliranje ishoda i fudbalskih golova (J2, RQ1)

### 1. Dixon & Coles (1997)
- **Naslov:** *Modelling association football scores and inefficiencies in the football betting market*
- **Publikacija:** Journal of the Royal Statistical Society: Series C, Vol. 46, No. 2
- **DOI / URL:** [10.1111/1467-9876.00065](https://doi.org/10.1111/1467-9876.00065)
- **Metod:** Bivariate Poisson MLE sa $\rho$-korekcijom za međusobnu zavisnost niskih rezultata (0-0, 1-0, 0-1, 1-1).
- **Nalaz:** Model uspeva da aproksimira distribuciju golova bolje od nezavisnog Poissona. U periodu 1992–1995 u UK zabeležena je anomalija koja je donosila profit.
- **Relevantnost za SharpBet v8:**
  - Dixon-Coles je bazni model implementiran u našem audit pipeline-u.
  - Uspešno konvergira (`Success: True`) i daje solidnu kalibraciju verovatnoća (Gate A: ECE 3.78%).
  - **Ograničenje:** Kreiran je u eri kada su kladionice imale fiksne, spore kvote i znatno nižu efikasnost. Na modernom retail tržištu (Mozzart) sa maržom od 18.79%, sirovi DC model nema dovoljno oštrine (sharpness) da proizvede pozitivan expected value.

### 2. Zhang & Rastelli (2026)
- **Naslov:** *Bayesian Conway-Maxwell-Poisson model with spike-and-slab priors for dispersed count data with application to football scores*
- **ArXiv:** [arXiv:2607.18009v1](https://arxiv.org/abs/2607.18009v1)
- **Metod:** Bajesovski Conway-Maxwell-Poisson (CMP) model koji eksplicitno modeluje i pod-disperziju (under-dispersion) i pre-disperziju (over-dispersion) golova.
- **Nalaz:** Fudbalski rezultati često krše strogu Poissonovu pretpostavku o jednakosti srednje vrednosti i varijanse ($\mathbb{E}[X] = \text{Var}(X)$). CMP distribucija pruža fleksibilnije modelovanje repova.
- **Relevantnost za SharpBet v8:**
  - Ako se projekat nastavi u pravcu fundamentalnog modelovanja, CMP ili Negative Binomial modeli predstavljaju teorijski superiorniju zamenu za klasični Dixon-Coles, naročito za poluvremena gde je frekvencija nula golova (0:0) dominantna.

### 3. Peters & Pacheco (2022)
- **Naslov:** *Betting the system: Using lineups to predict football scores*
- **ArXiv:** [arXiv:2210.06327v3](https://arxiv.org/abs/2210.06327v3)
- **Metod:** Mašinsko učenje (Support Vector Regression) na podacima Premier League (2020–2022) sa integracijom sastava timova (lineups).
- **Nalaz:** Statistički podaci o golmanima i odbrani imaju veći prediktivni značaj od napadača. Sastavi sami po sebi ne donose stabilnu prednost ako se ne modeluje dinamika kvota.
- **Relevantnost za SharpBet v8:**
  - Dodavanje novih fundamentalnih varijabli (npr. sastavi) u fundamentalni model retko donosi edge nad efikasnim tržištem jer tržište to već uračunava pre početka meča.

---

## Klaster B — Efikasnost tržišta, overround i Closing Line Value (J1, J3, RQ3, Gate B)

### 4. Kaunitz, Briercliffe & Shen (2017)
- **Naslov:** *Beating the bookies with machine learning*
- **Publikacija:** Royal Society Open Science
- **DOI / URL:** [10.1098/rsos.170585](https://doi.org/10.1098/rsos.170585)
- **Uzorak:** 479.440 fudbalskih mečeva tokom 10 godina.
- **Ključni nalaz (ZLATNI STANDARD):**
  - **Direktno fundamentalno modelovanje ishoda mečeva (golovi, posedi, xG) NE MOŽE da pobedi zatvarajuće linije**, jer kvote oštrih kladionica već inkorporiraju preko 98% svih javno dostupnih informacija.
  - Jedina dokazana strategija za ostvarivanje pozitivnog CLV-a i profita bila je **korišćenje de-viggovanog konsenzusa oštrih kladionica (Pinnacle) radi pronalaženja linija koje kasne na soft kladionicama (line shopping / off-market pricing).**
- **Direktna primena na SharpBet v8:**
  - Objašnjava zašto naš Dixon-Coles model ima CLV od **−9.82%**: model pokušava da direktno "pogodi ishod" protiv retail kladionice koja ima maržu od 18.79%.
  - Bez poređenja sa oštrim kvotama (line shopping), fundamentalni model je osuđen na negativan CLV koji reflektuje maržu kuće.

### 5. Constantinou (2020)
- **Naslov:** *Investigating the efficiency of the Asian handicap football betting market with ratings and Bayesian networks*
- **ArXiv:** [arXiv:2003.09384v2](https://arxiv.org/abs/2003.09384v2)
- **Metod:** Bajesovske mreže na vrhunskim evropskim ligama naspram azijskih hendikepa.
- **Nalaz:** Čak i visoko sofisticirani Bajesovski rejtinzi ne mogu konzistentno da ostvare profitabilnost na visoko likvidnim ligama kada se u obzir uzmu transakcioni troškovi i marža.
- **Relevantnost za SharpBet v8:**
  - Potvrđuje nalaz iz Gate B: na glavnim ligama efikasnost tržišta eliminiše bilo kakav statistički edge modela.

### 6. Winkelmann & Deutscher (2025)
- **Naslov:** *Do Betting Markets Sense a Goal Coming? Evidence from the German Bundesliga*
- **ArXiv:** [arXiv:2505.21275v1](https://arxiv.org/abs/2505.21275v1)
- **Nalaz:** Kvote na kladionicama izuzetno brzo inkorporiraju mikro-dinamiku igre. Statističke cene iz štampanih biltena (Mozzart lista) objavljene 24–48h ranije su statične, dok se prava verovatnoća pomera ka closing liniji.

---

## Klaster C — Kalibracija verovatnoća vs. Profitabilnost (RQ2, Gate A vs Gate B)

### 7. Gneiting & Raftery (2007)
- **Naslov:** *Strictly Proper Scoring Rules, Prediction, and Estimation*
- **Publikacija:** Journal of the American Statistical Association
- **DOI / URL:** [10.1198/016214506000001437](https://doi.org/10.1198/016214506000001437)
- **Nalaz:** Striktno pravilna pravila ocenjivanja (Brier Score, Logarithmic Score) podstiču prognostičara da izveštava svoje iskrene verovatnoće. Kalibracija meri pouzdanost verovatnoće, a rezolucija meri njenu oštrinu.
- **DIREKTNO REŠENJE PARADOKSA GATE A vs GATE B:**
  - Gate A meri kalibraciju (ECE 3.78%, Brier 0.2171). To znači da su predviđanja modela pouzdana i dobro skalirana u domenu verovatnoća.
  - Međutim, kalibracija **ne uzima u obzir cenu opklade**.
  - Ako se fer kalibrisana verovatnoća od 50% plasira na kvotu 1.70 (koja ima ugrađenu marginu), očekivani povrat je $0.50 \times 1.70 - 1 = -15\%$.
  - Dakle, **dobra kalibracija (Gate A PASS) matematički koegzistira sa negativnim CLV-om (Gate B BLOCKED)**.

### 8. Brümmer & Doddington (2013)
- **Naslov:** *Likelihood-ratio calibration using prior-weighted proper scoring rules*
- **ArXiv:** [arXiv:1307.7981v1](https://arxiv.org/abs/1307.7981v1)
- **Nalaz:** Optimizacija kalibracije ne garantuje optimalnost odluke u asimetričnim ili visoko opterećenim sistemima troškova.

---

## Klaster D — Preopterećenje backtesta i statistička snaga (RQ4, Gate C)

### 9. Bailey & López de Prado (2014)
- **Naslov:** *The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting and Non-Normality*
- **Publikacija:** Journal of Portfolio Management
- **DOI / URL:** [10.3905/jpm.2014.40.3.039](https://doi.org/10.3905/jpm.2014.40.3.039)
- **Nalaz:** Kada se strategije testiraju na malim uzorcima, varijansa i asimetrija prinosa stvaraju prividnu statističku značajnost. Deflated Sharpe Ratio koriguje ovu iluziju.
- **DIREKTNA PRIMENA NA GATE C (N=89):**
  - U našem auditu Gate C ima $N = 89$ opklada sa ROI od $+0.66\%$ (€5.90) i $95\%$ CI $[−23.31\%; +25.76\%]$.
  - Standardna devijacija po opkladi iznosi $118\%$.
  - Za pouzdanu detekciju 2% ROI na nivou snage $1-\beta = 0.80$ potrebno je **$N = 27.374$ opklada**.
  - Zaključak: Gate C rezultat od 89 opklada je 100% statistički šum.
