# 16. Konačna GO / NO-GO Odluka i Preporuka za Nastavak

**Datum Odluke:** 22. septembar 2026.  
**Predmet:** Konačna evaluacija SharpBet / Unified Betting Core projekta  
**Nadzorni Organ:** Antigravity Independent Audit Board  

---

## 1. Zasebne Odluke po Domenima

### 1.1. Technical Decision: CONDITIONAL GO
* **Obrazloženje:**
  Arhitektura koda u `unified_betting_core/` je dobro struktuirana, modularna i poštuje principe separacije odgovornosti.
  Lokalni pipeline (`scratch/run_json_pipeline.py`) je 100% deterministički reprodukovan (224 evaluirana ishoda, fail-closed zaštita, prazan tiket). Nema kritičnog curenja podataka (leakage) u proračunu rolling proseka i parametara timova.
* **Uslov za GO:**
  Hitno rešiti Git divergenciju (47 commitova ispred origin/mastera) i popraviti mapiranje podmodula `my-worker`.

### 1.2. Predictive Decision: RESEARCH ONLY (Matematički Validno)
* **Obrazloženje:**
  Bivarijantni Dixon-Coles model za prvo poluvreme sa korekcijom niske korelacije ($\rho \approx -0.02$ do $-0.07$) je matematički stabilan. Kalibracija na out-of-sample mečevima je odlična (Macro ECE = 3.78%, Brier = 0.2171). Model je validan kao kalkulator verovatnoća.
* **Ograničenje:**
  Model ne poseduje spoljne eksogene signale (povrede, motivacija, postave, vremenski uslovi), pa samim tim ne može samostalno da nadmaši oštro svetsko tržište (Pinnacle closing line).

### 1.3. Betting Edge Decision: NO-GO / UNPROVEN (Nije Dokazano)
* **Obrazloženje:**
  Backtest profitabilnosti iz v12/v16 je poništen zbog matematičke greške u podu kvota (`floor = 1.25`) i pretpostavke da je CLV fiksni derivat EV-a. Kada su u v14 primenjene stvarne Mozzart kvote, sistem je zabeležio prosečan CLV od **-9.82%** (t = -18.90, p = 0.0000). Na netaknutom holdoutu sezone 2025/26 u v18.3, ekonomski yield je bio negativan (**-0.79%**), a status je postavljen na `FAIL_CLOSED_BLOCKED`.
* **Presuda:** Ne postoji empirijski dokaz da sistem dugoročno ostvaruje profit protiv kladionice.

### 1.4. Commercial Decision: STOP / HYPOTHESIS ONLY (Obustaviti Pitch)
* **Obrazloženje:**
  Projekat nema korisnike, nema prihode, nema live streaming infrastrukturu za kvote. Postojeći Business Case sadrži veliku računovodstvenu grešku ($1,100 \times €57.12 = €62,832$, a ne €100,000 MRR). Izlazak pred investitore sa zahtevom od $750,000 na valuaciji od $5M na bazi ovakvog backtesta predstavljao bi reputacioni rizik.

---

## 2. Standardizovani Format Odluke

```text
TECHNICAL DECISION    : CONDITIONAL GO
PREDICTIVE DECISION   : RESEARCH ONLY
BETTING EDGE DECISION : NO-GO / UNPROVEN
COMMERCIAL DECISION   : STOP / HYPOTHESIS ONLY
OVERALL DECISION      : CONTINUE RESEARCH / PAPER TRADING ONLY
```

---

## 3. Završne Preporuke i Akcioni Plan

### PREPORUKA:
**Nastaviti samo uz uslove (Continue Research / Paper Trading Only).**  
Zaustaviti sve komercijalne aktivnosti i investicione razgovore dok se tehnologija ne dokaže na pravom tržištu bez novca.

### USLOVI ZA NASTAVAK:
1. **Potpuna eliminacija sintetičkih kvota:** U svim budućim Kaggle sveskama i lokalnim testovima trajno ukloniti bilo kakvu simulaciju kvota formulom `1/p * 0.935`. Koristiti isključivo stvarne istorijske kvote (Pinnacle closing, Bet365 ili stvarni Mozzart JSON).
2. **Korekcija Business Case dokumenta:** Uskladiti brojeve u `business-case-sharpbet-2026-09-22.md` (za €100K MRR potrebno je 1,751 korisnik). Ukloniti tvrdnje o "dokazanom 53% ROI".
3. **Push na Git Remote:** Sinhronizovati lokalnih 47 commitova sa GitHubom radi zaštite intelektualne svojine.
4. **Izgradnja Live Odds Scrapera:** Razviti automatizovani parser koji skida stvarne Mozzart kvote 15 minuta pre početka meča.

### DOKAZ KOJI NEDOSTAJE:
* **Realni istorijski CLV protiv Pinnacle-a veći od +2.0%** na uzorku od najmanje 500 uzastopnih utakmica.
* **Dokazano prihvatanje uloga:** Potvrda da kladionice ne limitiraju uloge na nivo od nekoliko stotina dinara nakon serije dobitaka na poluvremenima.

### NAJVEĆI RIZIK:
* **Marža kladionice (18.5% overround na poluvremenima):** Čak i ako je model statistički savršen, marža od 18.5% stvara matematički ponor koji običan Poasonov model zasnovan na istoriji golova ne može dugoročno da premosti.

### NAJBRŽI EKSPERIMENT KOJI MOŽE PROMENITI ODLUKU:
* **30-dnevni Shadow Paper Trading:**
  Povezati lokalni `scratch/run_json_pipeline.py` sa skriptom koja svakog jutra skida live Mozzart kvote, beleži virtuelne opklade u `data/prediction_audit_trail.jsonl`, a zatim ih sutradan automatski poravnava sa stvarnim rezultatima i zatvarajućim kvotama.  
  Ako nakon 30 dana i 300 utakmica stvarni CLV bude **pozitivan**, projekat momentalno dobija status **LIMITED PILOT / GO**. Ako CLV ostane negativan, projekat se trajno preusmerava na B2C analitički softver bez tvrdnji o klađenju.
