# 01 — JTBD Kanvas (Jobs-To-Be-Done Framework)

> **Metodologija:** CodyMaster JTBD Discovery & Opportunity Scoring  
> **Kontekst:** Evaluacija SharpBet v8 sistema nakon audita i odluka o investiranju resursa  
> **Datum revizije:** 2026-09-21  

---

## 1. Glavni "Job Statement"

```
Kada (SITUATION):
  se nađem pred odlukom da li da uložim dalji inženjerski i računarski napor u SharpBet sistem nakon što je audit vratio verdikt FAIL_CLOSED_BLOCKED,

Želim da (MOTIVATION):
  kroz rigoroznu i matematički neoborivu analizu razlučim da li je neuspeh posledica nepopravljive strukture tržišta (ogromna retail marža od 18.8%) ili rešive slabosti modela (Dixon-Coles fundamentalni pristup),

Kako bih (EXPECTED OUTCOME):
  mogao ili da preusmerim inženjerski rad na tržišta sa stvarnim edge-om (niska marža, exchange, brze linije), ili da čisto i bez žaljenja prekinem projekat bez pada u zamku nepovratnih troškova (sunk-cost fallacy).
```

---

## 2. Tri dimenzije posla (Three Job Dimensions)

| Dimenzija | Definicija u kontekstu SharpBet-a | Cilj posla |
|---|---|---|
| **Funkcionalna (Functional)** | Dobiti matematički egzaktan, podacima potkrepljen dokaz zašto strategija ima negativan CLV i koliki uzorak je potreban za statističku pouzdanost. | Eliminacija proizvoljnih pretpostavki; donošenje binarnog izbora: Stop ili Pivot. |
| **Socialna (Social)** | Biti prepoznat kao profesionalac i kvant koji odluke donosi na osnovu rigoroznih dokaza, a ne na osnovu nade, lažnih marketinških prikaza ili lažiranih backtestova. | Mogućnost da se audit prezentuje bilo kom iskusnom investitoru ili kvantu bez rupa u logici. |
| **Emocionalna (Emotional)** | Osećati sigurnost i mentalni mir znajući da je fail-closed sistem zaštitio kapital od realnog gubitka. | Oslobađanje od pritiska "šta ako ovo nekako radi" i "uložio sam previše truda da bih stao". |

---

## 3. Sile koje utiču na odluku (The Four Forces of Progress)

```
                       (+) PUSH OF PRESENT SITUATION
             - CLV je -9.82% uz t = -18.90 (katastrofalan pad).
             - Margina od 18.79% guta bilo kakvu modelsku prednost.
             - N=89 u Gate C je statistički šum (potrebno 27k opklada).
                                   │
                                   ▼
        [ STARI NAČIN ] ─────────────────────────► [ NOVO REŠENJE / NOVI STATUS ]
        Slepo forsiranje Dixon-                    Prekid (Stop) ili Pivot na
        Coles modela na retail                     Exchange/Arbitražu sa transparentnim
        Mozzart biltenima                          CLV benchmarkingom
                                   ▲
                                   │
                       (+) PULL OF NEW SOLUTION
             - Oslobađanje vremena i računarskih resursa za validne projekte.
             - Ako se pivotira: rad na likvidnim tržištima sa maržom < 2%.
             - Potpuna naučna i inženjerska čestitost.

──────────────────────────────────────────────────────────────────────────────────

                       (-) ANXIETY OF NEW SOLUTION
             - "Šta ako postoji niša liga u Mozzartu gde je kvota bila dobra?"
             - "Da li je sav dosadašnji rad na PDF parseru i bazi bio uzaludan?"
             - Prebacivanje na Exchange traži live API integracije i bankroll.
                                   │
                                   ▼
        [ OTPOR PROMENI ] ─────────────────────────► [ PREKID ILI PIVOT ]
                                   ▲
                                   │
                       (-) HABIT OF CURRENT SOLUTION
             - Navika da se uvek dodaje još jedan sloj koda, još jedan fit ili filter.
             - Emotivna vezanost za ideju da se može pobediti lokalna kladionica.
```

---

## 4. Konkurentska rešenja koja se trenutno unajmljuju (Competing Solutions)

1. **Direktno alternativno rešenje (Workaround):** Nastaviti fino podešavanje (fine-tuning) Dixon-Coles modela, filtriranje mečeva po ligama ili dodavanje složenih heuristika.
   - *Zašto ne uspeva:* Ako je prosečna marža 18.79%, a model koristi iste javne podatke, nikakvo filtriranje na malom holdoutu ne može promeniti fundamentalni nedostatak prednosti (Kaunitz et al. 2017).
2. **Indirektno rešenje (Pivot na drugu arhitekturu):** Prelazak na arbitražno klađenje ili "line shopping" (poređenje softbook kvota u odnosu na Pinnacle/Betfair fer kvote).
   - *Zašto ima potencijal:* Ovo je jedini pristup u literaturi koji dokazano generiše pozitivan CLV protiv retail kladionica.
3. **Opcija nečinjenja (Do-Nothing / Status Quo):** Zanemariti Gate B verdikt, fokusirati se na prividni Gate C ROI od 0.66% i pustiti live klađenje.
   - *Posledica:* Gotovo siguran gubitak kapitala usled negativnog CLV-a od -9.82%.

---

## 5. Metrike ishoda i bodovanje prilika (Outcome Metrics & Opportunity Scoring)

Formula:
$$\text{Opportunity Score} = \text{Importance} + \max(\text{Importance} - \text{Satisfaction}, 0)$$
*Skor $\ge 15$ označava kritične, nedovoljno pokrivene zahteve (najviši prioritet za rešavanje).*

| ID | Metrika ishoda (Outcome Metric) | Importance (1-10) | Satisfaction (1-10) | Opportunity Score | Prioritet |
|---|---|:---:|:---:|:---:|---|
| **M1** | **Zaštita kapitala od negativnog CLV-a** (Sistem nikada ne odobrava novac ako je CLV < 0) | **10** | **10** | **10** | Održano (Gate B radi) |
| **M2** | **Odsustvo lažnih pretpostavki u auditu** (Nema izmišljenih procenata ili fiktivnih closing margina) | **10** | **3** | **17** | **KRITIČAN (Score $\ge 15$)** |
| **M3** | **Statistička snaga procene** (Uzorak opklada dovoljno velik da razlikuje šum od realnog prinosa) | **9** | **2** | **16** | **KRITIČAN (Score $\ge 15$)** |
| **M4** | **Rešivost problema marže** (Trgovanje samo na tržištima gde je marža dovoljno niska da omogući +EV) | **9** | **2** | **16** | **KRITIČAN (Score $\ge 15$)** |
| **M5** | **Reproducibilnost za treća lica** (Mogućnost da eksterni revizor pokrene isti audit) | **8** | **4** | **12** | Srednji prioritet (Dataset private) |

---

## 6. Zaključak JTBD Analize

Glavni posao koji korisnik unajmljuje ovaj audit da uradi nije „ulepšavanje propalog modela“, već **isporuka nemilosrdne istine bez lažiranja (M2)** i **statistička diskvalifikacija iluzija (M3)**.

- **Rezultat bodovanja:** Metrike M2, M3 i M4 imaju Opportunity Score od 16 i 17.
- **Akcioni zaključak:** Audit mora odbaciti bilo kakve izmišljene dekompozicije, jasno predočiti nemogućnost pobede nad 18.8% maržom pomoću javnog Dixon-Coles modela i usmeriti pažnju na jedine racionalne ishode: **čist STOP** ili **strukturalni PIVOT na niske marže / line shopping**.
