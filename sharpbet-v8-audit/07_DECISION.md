# 07 — Odluka o daljem radu (Go / No-Go & Strategic Decision)

> **Konačni verdikt:** `FAIL_CLOSED_BLOCKED`  
> **Status kapitala:** Zaključan (Capital Protected)  
> **Autoritet:** MASTER_ORCHESTRATION.md & JudgeGuard Governance  

---

## 1. Zbirni faktički nalaz

Odluka o projektu SharpBet v8 počiva isključivo na matematički i empirijski potvrđenim podacima:

1. **Gate A je PASSED (ECE 3.78%, Brier 0.2171):**
   - Dixon-Coles model je dobro kalibrisan u prostoru verovatnoća.
   - Međutim, literatura (Gneiting & Raftery 2007) dokazuje da kalibracija ne meri ekonomsku prednost (edge), već samo unutrašnju iskrenost verovatnoća modela.
2. **Gate B je KATEGORIČKI BLOCKED (Mean CLV −9.82%, $t = -18.90, p < 10^{-10}$):**
   - Na holdout skupu model konzistentno bira kvote koje su u proseku 9.82% ispod fer vrednosti.
   - Hipoteza o nultom ili pozitivnom CLV-u je nepovratno oborena.
3. **Gate C je STATISTIČKI ŠUM (ROI +0.66%, PnL +€5.90, $N = 89$):**
   - Power analiza dokazuje da je za pouzdanu detekciju 2% ROI potrebno $N = 27.374$ opklada.
   - Uzorak od 89 opklada nema nikakvu statističku snagu ($< 5\%$) i rezultat je nerazlučiv od čiste slučajnosti.
4. **Dekompozicija marže:**
   - Mozzart HT 1X2 overround iznosi u proseku **18.79%** (medijana 18.48%).
   - Zbog odsustva parnih otvarajućih i zatvarajućih kvota u PDF biltenima, tačan udeo marže vs. modelske greške je empirijski neizmerljiv. Ali opšte pravilo iz literature (Kaunitz et al. 2017) potvrđuje: *fundamentalni modeli na javnim podacima ne mogu savladati retail maržu od 18.8%.*

---

## 2. Eksplicitna analiza nepovratnih troškova (Sunk-Cost Analysis)

Racionalno donošenje odluka u kvantitativnim finansijama zahteva potpuno ignorisanje prošlog truda:
- Vreme uloženo u parsiranje 344k mečeva, podešavanje OCR-a, PDF ekstrakciju i pisanje Dixon-Coles MLE optimizatora **ne sme biti razlog da se odobri strategija koja gubi novac**.
- Da li bi nezavisan investitor danas uložio 1 evro u sistem koji ima izmeren CLV od −9.82% i maržu od 18.8%? **Odgovor je kategoričko NE.**
- Odobriti produkciju ili nastaviti forsiranje istog pristupa samo zato što je uloženo vreme predstavljalo bi klasičnu psihološku zamku nepovratnih troškova (sunk-cost fallacy).

---

## 3. Stvorena vrednost (Šta je realna dobit ovog rada)

Iako je model na ovom tržištu pao, projekat nije bio uzaludan. Stvorena je trajna infrastruktura:
1. **Verifikovan dataset od 344.005 mečeva:** Najveća strukturisana baza domaćih kvota za poluvremena (2021–2026).
2. **Modularni JudgeGuard Gate sistem (A/B/C):** Potpuno operativan MLOps audit sistem koji sprečava postavljanje kapitala na strategije sa negativnim CLV-om.
3. **Akademska jasnoća:** Definitivan empirijski dokaz da klasičan Dixon-Coles model na retail poluvremenim kvotama ne poseduje prednost.

---

## 4. Strateške opcije za budućnost

### Opcija 1: ČISTI PREKID (STOP) — Preporučeno ako nema resursa za live feed
- **Šta znači:** Zatvaranje SharpBet HT 1X2 istraživanja sa verdiktom `FAIL_CLOSED_BLOCKED`.
- **Zašto:** Bez pristupa berzama kvota (Betfair) ili brzim podacima u milisekundama, nastavak rada na istom tržištu sa istim modelom garantuje isti negativan ishod.
- **Akcija:** Arhivirati kod, sačuvati bazu kao istraživački aset, preusmeriti inženjerske resurse na druge projekte.

### Opcija 2: STRUKTURALNI PIVOT NA "LINE SHOPPING" (Kaunitz 2017 metod)
- **Šta znači:** Prekid pokušaja da se pogodi ishod utakmice preko Dixon-Coles modela. Umesto toga, modelovati fer cenu na osnovu de-viggovanog konsenzusa oštrih kladionica (Pinnacle/Betfair), a zatim skenirati retail kladionice (Mozzart/MaxBet) u potrazi za linijama koje kasne.
- **Zahtevi:** Live API / scraping feed sa milisekundnim osvežavanjem, nalozi na više kladionica, upravljanje limitima.

### Opcija 3: PIVOT NA BERZE KVOTA (BETFAIR EXCHANGE)
- **Šta znači:** Prelazak sa retail tržišta (18.8% marža) na peer-to-peer exchange (2–5% provizija na neto dobitak).
- **Zahtevi:** Znatno fleksibilniji modeli (Conway-Maxwell-Poisson ili GBDT ansambli sa kalibrisanim verovatnoćama) i likvidnost na azijskim hendikepima i full-time tržištima.

---

## 5. Konačna direktiva

**Verdikt `FAIL_CLOSED_BLOCKED` ostaje trajan za SharpBet v8.**  
Nijedan evro realnog kapitala ne sme biti raspoređen na ovu strategiju.  
Sistem je demonstrirao svoju primarnu svrhu — **beskompromisnu zaštitu kapitala od matematički neodrživih pretpostavki.**
