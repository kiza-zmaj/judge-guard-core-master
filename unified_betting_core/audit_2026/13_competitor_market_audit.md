# 13. Audit Konkurencije i Tržišta (Competitor & Market Audit)

**Datum audita:** 22. septembar 2026.  
**Klasifikacija tržišne pozicije:**
```text
CATEGORY DEMAND    = DEMONSTRATED (Kategorija vredi milijarde)
SHARPBET DEMAND    = UNPROVEN (Nema korisnika)
PRODUCT-MARKET FIT = UNPROVEN (Nema dokazanog angažovanja)
```

---

## 1. Uporedna Tabela Direktnih Konkurenata

| Konkurent | URL / Sedište | Cene i Planovi | Broj Kladionica | Prediktivni ML Model | Real-time Odds Feed | CLV Tracking | Automatska Egzekucija | Status na Tržištu |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **OddsJam** | [oddsjam.com](https://oddsjam.com) (SAD) | $99 – $499 / mo | 200+ globalno | **NE** (Čist benchmark skener) | **DA** (API WebSocket < 1s) | **DA** (Pinnacle closing) | Delimično (One-click extension) | Tržišni lider u SAD, akvizicija $160M |
| **RebelBetting** | [rebelbetting.com](https://rebelbetting.com) (Švedska) | €89 – €219 / mo | 90+ evropskih | **NE** (Arb/Value scraper) | **DA** (Desktop/Web sync) | **DA** (Prosečan CLV prikazan) | **DA** (Auto-stake / One-click) | 200k+ registrovanih, profitabilan 10+ god. |
| **BetBurger** | [betburger.com](https://betburger.com) (Kipar) | €130 – €450 / mo | 250+ bookija | **NE** (Brzi arb skener) | **DA** (Live & Pre-match) | **NE** (Fokus na arbitražu) | **DA** (Direct bet helper) | Glavni alat balkanskih i istočnoevropskih arbitražera |
| **Action Network** | [actionnetwork.com](https://actionnetwork.com) (SAD) | $9.99 – $29.99 / mo | Sve legalne US | Osnovni (Consensus picks) | **DA** (Live odds) | **NE** (Nema CLV fokus) | **NE** (Media / Affiliate model) | Prodat za $240M kompaniji Better Collective |
| **SharpBet (Naš sistem)** | Lokalni prototip | Planirano €29 – €199 | Samo Mozzart (trenutno) | **DA (Dixon-Coles Poason)** | **NE** (Statički JSON/PDF) | **DA** (Empirical Gate v18) | **DA (Mozzart Parser v2.0)** | **Pre-revenue prototip u razvoju** |

---

## 2. Šta SharpBet Radi Bolje od Konkurencije

1. **Pravi Matematički Prediktivni Model (Dixon-Coles):**
   * OddsJam i RebelBetting **uopšte ne modeliraju sport**. Oni su obični "skrejperi" koji pretpostavljaju da je kvota na Pinnacle-u savršena, pa traže greške na mekim kladionicama (tzv. *Market-Maker Discrepancy*).
   * Ako Pinnacle nema likvidnost na specifičnom marketu (npr. golovi u prvom poluvremenu u ligi Srbije ili Rumunije), OddsJam i RebelBetting su beskorisni.
   * SharpBet može samostalno da izračuna fer verovatnoću iz golova timova, nezavisno od toga šta radi Pinnacle.
2. **Specijalizacija za Izvedene Markete (Derivatives):**
   * Konkurenti se uglavnom bave 1X2 i hendikepima. SharpBet ima matematički rešene specijale (`I1+`, `I2+`, `I 0-1`, `1&I1+`) koji su omiljeni među balkanskim i evropskim igračima.
3. **Lokalna Egzekucija (Mozzart v2.0 Parser):**
   * Integracija sa regionalnim tiketima koja direktno prevodi predikciju u gotov format za uplatu.

---

## 3. Gde SharpBet Drastično Zaostaje za Konkurencijom

1. **Odsustvo Live Odds Feed-a:**
   * Konkurencija troši **$20,000 – $50,000 mesečno** na brze live API feedove (Betradar, The-Odds-API, privatni skrejperi). SharpBet trenutno radi na statičkim JSON snimcima.
2. **Nula Tržišne Validacije:**
   * Imati dobar kod ne znači imati biznis. Bez korisnika koji plaćaju pretplatu, SharpBet je u ovom trenutku samo istraživački softver.
3. **Limitiranje Naloga (Account Limiting Risk):**
   * Ako korisnik na Mozzartu ili Bet365 konstantno uplaćuje +EV selekcije na poluvremenima, kladionica će mu limitirati nalog na uplate od 100 dinara za manje od 2 do 3 nedelje. Konkurenti (RebelBetting) imaju čitave vodiče kako izbeći limite, dok SharpBet Business Case taj rizik potpuno ignoriše.

---

## 4. Zaključak

Postoji jasna potražnja na tržištu za kvantitativnim alatima (Category Demand = Demonstrated).  
Međutim, SharpBet još uvek nije konkurentan na tržištu gotovih proizvoda dok ne izgradi:
a) Live skrejper kvota;  
b) Web interfejs za korisnike;  
c) Provereni tromesečni trag na pravim kvotama.
