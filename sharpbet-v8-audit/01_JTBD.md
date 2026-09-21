# 01 — JTBD Kanvas: SharpBet v8

> Okvir: Jobs-To-Be-Done | Verzija: 1.0 | Datum: 2026-09-21

---

## Kontekst ("When...")

Kada sam u situaciji da procenjujem da li da nastavim da ulažem vreme i novac u SharpBet nakon što je sistem vratio `FAIL_CLOSED_BLOCKED`...

---

## Glavni "Job"

> *"Želim da **nedvosmisleno znam** da li je negativan rezultat posledica **popravljive greške modela** ili **nepopravljive strukture tržišta** — da bih mogao ili da usmerim resurse ka popravci ili da čisto zatvorim projekat bez sunk-cost žaljenja."*

**Funkcionalni aspekt:** Dobiti jasnu go/no-go preporuku zasnovanu na brojevima.
**Emocionalni aspekt:** Eliminisati neizvesnost i osloboditi se od kognitivne tenzije "možda radi".
**Socijalni aspekt:** Moći da objasnim odluku trećoj strani bez sramote.

---

## Pod-jobovi i success kriterijumi

| ID | Job statement | Success kriterijum | Gate koji adresira |
|---|---|---|---|
| J1 | Razdvoji tržišni overround od modelske greške | Numerička dekompozicija CLV-a | Gate B |
| J2 | Utvrdi da li je model dobro kalibrisan | ECE/Brier stabilni po ligama i vremenu | Gate A |
| J3 | Dokaži ili obori da pozitivan CLV nije moguć | Empirijska granica + falsifikacioni test | Gate B |
| J4 | Diskvalifikuj ili validiraj Gate C statistički | Power analiza, N potreban | Gate C |
| J5 | Napravi reproduktivan, javan artefakt | Dataset PRIVATE → blokira J5 | Reproducibilnost |

---

## Anti-jobs (šta plan NE sme da uradi)

- ❌ Ne treba da "spašava" projekat pod svaku cenu (sunk-cost).
- ❌ Ne treba da tumači ROI 0,66% i PnL €5,90 kao prednost.
- ❌ Ne treba da tretira "successfully ran" kao "profitabilan".
- ❌ Ne treba da tvrdi "matematički nemoguće" bez formalne teoreme.

---

## Status posle analize

| Job | Status |
|---|---|
| J1 (CLV dekompozicija) | ✅ Urađeno — ~80% tržišna margina, ~20% model |
| J2 (kalibracija) | ✅ Gate A PASS (ECE 3.78%) — potvrđeno |
| J3 (granica profitabilnosti) | ⚠️ Nije formalno dokazano — empirijska granica, nije teorema |
| J4 (power analiza) | ✅ N=27.374 potrebno za 2% ROI detektovanje — Gate C je šum |
| J5 (reproducibilnost) | ❌ Dataset PRIVATE — audit nije nezavisno proverljiv |

---

## Competing solutions (alternativne strategije)

1. **Pivot na nižu marginu (Exchange/Betfair):** Eliminisati strukturni uzrok CLV < 0.
2. **Pivot na niša-tržišta:** Tražiti ligu/vreme gde je margina < 10% i tržište manje efikasno.
3. **Zamena DC sa ML modelom:** Adresirati ~20% modelsku komponentu.
4. **Stop projekta:** Ako ni jedna alternativa nije ekonomski izvodljiva.
