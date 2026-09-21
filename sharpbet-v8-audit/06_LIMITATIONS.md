# 06 — Ograničenja (Limitations)

> Svako ograničenje je eksplicitno označeno. Ovo nije odbrana projekta — ovo je checklista onoga što analiza NE može da tvrdi.

---

## L1 — Dataset PRIVATE (kritično)

**Ograničenje:** `mozzart-historical-odds` dataset je `PRIVATE` na Kaggle-u.

**Implikacija:**
- Audit rezultati **nisu nezavisno reproducibilni** od strane treće strane.
- Ni Gate A, ni Gate B, ni Gate C ne mogu biti verifikovani bez pristupa datasetu.
- Svaka tvrdnja o "ECE 3.78%" ili "CLV −9.82%" je verifikovana samo od strane autora.

**Mitigacija:** Objaviti dataset ili generisati sintetički subset koji dokazuje pipeline.

---

## L2 — Nema live feed / WebSocket integracij

**Ograničenje:** Sistem nema live WebSocket tick feed ni execution bridge.

**Implikacija:**
- Gate C koristi historijske kvote, ne live/delayed kvote.
- Slippage, limitovanje uloga i likvidnost nisu modelirani.
- Čak i da Gate B postane pozitivan, sistem nije spreman za deployment.

---

## L3 — Closing kvote nisu direktno dostupne

**Ograničenje:** CLV dekompozicija u Fazi 1 pretpostavlja closing marginu od ~10% (standardno za Mozzart klasu).
Stvarna closing margina nije dostupna u datasetu.

**Implikacija:** CLV dekompozicija (80% tržišna / 20% model) je aproksimacija, ne tačan broj.

---

## L4 — Gate C uzorak je premali za statističke zaključke

**Ograničenje:** N=89 opklada u Gate C (od 380 holdout-a).

**Implikacija:**
- Za detekciju ROI od 2% sa power 0.80 potrebno je N=27.374.
- Gate C ROI 0.66% i PnL €5.90 su statistički nerazlučivi od šuma.
- CI [−23.31%; +25.76%] sadrži nulu — nema dokaza ni na jednu stranu.

---

## L5 — Dixon-Coles model nije state-of-art

**Ograničenje:** DC 1997 je bazni model. Novija literatura (Groll 2021) pokazuje da ML pristupi prevazilaze DC.

**Implikacija:** Deo negative modelske selektivnosti (~20% CLV-a) može biti zbog zastarelosti modela, ne samo tržišne efikasnosti.

---

## L6 — Nestacionarnost tržišta 2021–2026 nije testirana

**Ograničenje:** Model je treniram na 760 mečeva, validiran na 380. Nije urađena time-split analiza po godinama.

**Implikacija:** Nije poznato da li model degradira tokom vremena (drift) ili je stabilan.

---

## L7 — "Nemoguć pozitivan CLV" je preaka tvrdnja

**Eksplicitno:** Analiza pokazuje da na **ovom** datasetu, sa **ovim** modelom, na **ovom** tržištu, u **ovom** vremenskom periodu, nije pronađen pozitivan CLV.

To **ne dokazuje** da je pozitivan CLV matematički nemoguć na:
- Alternativnim tržištima (Exchange)
- Nižim ligama sa manjom efikasnošću
- Boljim modelima
- Drugačijim vremenima ulaska (rane linije)
