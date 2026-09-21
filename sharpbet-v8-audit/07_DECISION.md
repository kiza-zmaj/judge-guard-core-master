# 07 — Odluka: Go / No-Go

> **Napomena:** Svaka tvrdnja ima izvor. Sunk-cost je eksplicitno adresiran.

---

## Finalni verdikt (Kernel v8)

```
FAIL_CLOSED_BLOCKED
```

| Gate | Status | Broj | Izvor |
|---|---|---|---|
| Gate A — Kalibracija | **PASSED** | ECE 3.78%, Brier 0.2171 | Kernel v8 log |
| Gate B — CLV | **BLOCKED** | −9.82% [−10.91; −8.79], t=−18.90 | Kernel v8 log |
| Gate C — Backtest ROI | Technical pass (beznačajan) | ROI 0.66%, N=89, CI[−23.31%; +25.76%] | Kernel v8 log |

---

## Odgovor na ključno pitanje

> *"Da li je negativan CLV strukturni (tržišna margina) ili modelski (loša cena)?"*

**Odgovor (sa dokumentovanim brojevima):**

- **~80% tržišna struktura:** Margin compression (open 18.79% → estimated closing ~10%) objašnjava CLV ≈ −8.0%.
- **~20% modelska greška:** Model konzistentno bira stranu koja se pomera u nepovoljnom smeru (~−1.8% negativna selektivnost).
- **Oba uzroka vode ka istom verdiktu:** FAIL_CLOSED ostaje čak i ako se modelska greška eliminiše.

**Caveat:** Closing margina za Mozzart nije direktno poznata. Dekompozicija je aproksimacija.

---

## Da li iko može probiti Gate B?

**Odgovor:** Na ovom tržištu (Mozzart HT 1X2, margina 18.79%), sa ovim pristupom (DC MLE, proporcionalni vig removal), u ovom periodu (2021–2026) — **nije nađen pozitivan CLV.**

Ovo **nije teorema**. Nije dokazano da je pozitivan CLV nemoguć. Dokazano je samo da on nije nađen.

Uslovi pod kojima bi moglo biti drugačije (neistraženi, nema dokaza za/protiv):
1. Exchange tržišta (margina 2-5% umesto 18.79%)
2. Niže lige sa manjom efikasnošću
3. ML model koji prevazilazi DC
4. Rane linije (soft market)

---

## Preporuka sledećeg koraka

### Opcija A — Stop (preporučena ako nema resursa za dugotrajni razvoj)
- Zatvori projekat.
- Sačuvaj codebase i dataset kao buduću referencu.
- Razlog: Nema dokaza da sistem može biti profitabilan u razumnom roku.

### Opcija B — Pivot na Exchange tržište
- Zameniti Mozzart closing kvotu sa Betfair Exchange oddsima.
- Margina pada sa 18.79% na 2-5%.
- CLV iz margine bi bio −1.0% do −2.0% umesto −8.0%.
- Model skill komponenta od −1.8% bi tada bila kritičan faktor (a ne utopljeni u margini).
- **Zahteva:** Live feed, Betfair API integraciju, execution bridge.

### Opcija C — Zamena DC sa ML modelom
- Zameniti DC MLE sa gradient boosting + kalibracioni sloj (Platt scaling).
- Adresira ~20% modelske komponente CLV-a.
- Bez rešavanja margine (Opcija B), Opcija C sama ne rešava problem.

---

## Sunk-cost analiza (eksplicitno)

Uloženo vreme i resursi u SharpBet **nisu argument za nastavak** ako brojevi ne podržavaju go.

Pitanje koje treba postaviti: "Da li bih danas pokrenuo ovaj projekat sa ovim brojevima?"
- Gate B CLV = −9.82%: **Ne.**
- Gate C N=89 (potrebno 27.374): **Ne.**
- Margin 18.79% bez Exchange feedа: **Ne.**

Racionalna odluka je bazirana na budućim troškovima i očekivanim prinosima, ne na prošlom trudu.

---

## Šta je napravljeno (vrednost od projekta)

Bez obzira na go/no-go, projekat je isporučio:
1. **344.005 verificiranih Mozzart halftime kvota** (2021–2026) — vredan dataset.
2. **Reproducibilan audit pipeline** (Gate A/B/C sistem) koji se može primeniti na bilo koje tržište.
3. **Empirijsku granicu:** DC model na Mozzart HT 1X2 = FAIL. Ovo nije trivijalan nalaz.
4. **Infrastrukturu:** PDF parser, Kaggle kernel, `gate_verdicts.json` format.

Ova infrastruktura ima vrednost za Opciju B ili C, ako se nastavi.
