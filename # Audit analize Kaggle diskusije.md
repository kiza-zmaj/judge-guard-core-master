# Audit analize Kaggle diskusije

## 1. Cilj audita

Audit proverava:

- da li su zaključci zasnovani na stvarnim Kaggle objavama;
- da li su pravilno identifikovani “top Kagglers”;
- da li su odvojene činjenice od pretpostavki;
- koliko su taktike reproduktivne i korisne;
- koje tvrdnje nisu dovoljno dokazane;
- šta bi trebalo dodatno proveriti pre implementacije.

---

## 2. Obuhvat i korišćeni izvori

Analizirani su:

1. zvanični leaderboard;
2. diskusije kompeticije;
3. komentari autora i učesnika;
4. rang učesnika prikazan unutar Kaggle diskusija;
5. konkretne brojke koje su učesnici sami objavili.

Glavni izvori:

- [Leaderboard](https://www.kaggle.com/competitions/biohub-cell-tracking-during-development/leaderboard)
- [Tom — custom napari visualizer](https://www.kaggle.com/competitions/biohub-cell-tracking-during-development/discussion/724130)
- [Hikaggler — public plateau](https://www.kaggle.com/competitions/biohub-cell-tracking-during-development/discussion/741749)
- [Eric — leakage u javnim modelima](https://www.kaggle.com/competitions/biohub-cell-tracking-during-development/discussion/742064)
- [Model blending](https://www.kaggle.com/competitions/biohub-cell-tracking-during-development/discussion/742131)
- [Top-100 pitanja](https://www.kaggle.com/competitions/biohub-cell-tracking-during-development/discussion/742169)

---

# 3. Audit kriterijuma “top Kaggler”

## Korišćena definicija

Kao primarni kriterijum uzet je plasman u ovoj konkretnoj kompeticiji.

| Učesnik | Rang u kompeticiji | Status dokaza |
|---|---:|---|
| Ogurtsov | 6 | Top-10 |
| Tom | 19 | Top-20 |
| TWEAK | 28 | Top-30 |
| Eric | 80 | Top-100 |
| Joseph Adamski | 86 | Top-100 |
| Hikaggler | 257 | Sekundarni izvor |
| Mohammadjafar Zamani | 285 | Sekundarni izvor |
| Vaibhav Nakrani | 296 | Sekundarni izvor |
| Yunk-S | 299 | Sekundarni izvor |
| hengck23 | 988 | Nije top učesnik po ovom kriterijumu |
| Chris Deotte | 2633 | Nije top učesnik po ovom kriterijumu |

## Nalaz

Kriterijum je korektan za rangiranje učesnika **u ovoj kompeticiji**, ali ne dokazuje da su to globalno najbolji Kaggle takmičari.

Takođe, trenutni leaderboard je zasnovan na približno 29% test podataka. Rangovi mogu da se promene na private leaderboardu.

### Ocena

**Pouzdanost klasifikacije: visoka za trenutni public leaderboard.**  
**Pouzdanost za konačni plasman: srednja do niska.**

---

# 4. Audit pojedinačnih autora i tvrdnji

## 4.1 Ogurtsov — rang 6

### Šta je stvarno objavljeno

Ogurtsov je rekao da se iznad javnog plafona može napredovati, ali da je to rizično za private leaderboard.

### Šta nije objavljeno

Nije objavio:

- konkretnu arhitekturu;
- tačne težine;
- validacionu proceduru;
- post-processing recept;
- konačan pipeline;
- brojčani ablation.

### Audit zaključak

Ogurtsovljev komentar je validan kao **signal o riziku**, ali nije tehnički recept.

| Element | Ocena |
|---|---|
| Autentičnost komentara | Visoka |
| Tehnička detaljnost | Niska |
| Reproduktivnost | Niska |
| Korisnost za risk management | Visoka |
| Dokaz da je metoda najbolja | Nizak |

---

## 4.2 Tom — rang 19

### Šta je provereno

Tom je objavio repository:

[Celltrack Studio](https://github.com/tom99763/celltrack-studio)

Objavljena funkcionalnost uključuje:

- vizuelizaciju trajektorija;
- proveru frame-to-frame matching-a;
- pregled 3D grešaka;
- testiranje post-processinga.

### Audit zaključak

Ovo je najjači javno proverljiv doprinos iz top-20 grupe, ali nije direktan dokaz da je alat povećao leaderboard score.

Alat ima visoku vrednost za:

- dijagnostiku;
- otkrivanje ID switch-a;
- otkrivanje loših linkova;
- poređenje post-processing pravila.

Nema dovoljno dokaza da je sam alat doneo konkretan LB dobitak.

| Element | Ocena |
|---|---|
| Autentičnost | Visoka |
| Reproduktivnost | Srednje-visoka |
| Direktan LB dokaz | Nizak |
| Korisnost za debugging | Vrlo visoka |
| Dokaz da povećava score | Nizak |

---

## 4.3 Eric — rang 80

### Glavna tvrdnja

Eric je proverio manifest javnog modela i zaključio da su težine trenirane na svih 199 train videa.

Takođe je naveo konkretan kontra-primer:

- lokalno poboljšanje: `+0.0078`;
- public LB rezultat: `−0.002`;
- ponovljeno kroz dve submission-e.

### Audit zaključak

Ovo je metodološki najjači nalaz u analiziranim diskusijama.

Međutim, treba imati u vidu:

- manifest javnog modela nije isto što i potpuna verifikacija celog trenažnog procesa;
- nije nezavisno reprodukovan ceo Ericov eksperiment;
- rezultat se odnosi na njegov pipeline i konkretan refinement;
- ne znači da je svaki lokalni CV beskoristan.

Precizniji zaključak je:

> Lokalna validacija je nepouzdana kada koristi modele koji su trenirani na validation videima ili njihovim vrlo bliskim varijantama.

| Element | Ocena |
|---|---|
| Provera manifesta | Visoka |
| Eksperimentalni dokaz | Srednje-visok |
| Generalizacija na sve modele | Srednja |
| Važnost za metodologiju | Vrlo visoka |
| Reproduktivnost | Visoka, uz pristup istim težinama |

---

## 4.4 OmerZalman — Diskusija 742169 ("A few question for top 100 people?")

OmerZalman je postavio 8 ciljanih pitanja top-100 timovima:

- Da li je performans iz specifičnog modela ili celog pipeline-a?
- Koji modul donosi najveći skok: detekcija, linking, divizija ili post-processing?
- Da li su trenirali na svim video zapisima i kako dizajnirati validaciju bez overfittinga?
- Kako balansirati division recall naspram lažnih divizija?
- Kako lokalna validacija korelira sa Leaderboardom?
- Da li koriste ensembling, TTA ili globalnu optimizaciju grafa?
- Koji pristupi su propali?

### Odgovori top takmičara (Ogurtsov — rang 6):

Ogurtsov je odgovorio:
> *"I guess you have some room for improvement in all directions."*
> *"My primary concern is private LB."*

### Audit zaključak

- Pitanja savršeno mapiraju ključne tehničke dileme takmičenja.
- Ogurtsovljev odgovor potvrđuje da nijedna pojedinačna komponenta (samo veći model ili samo post-processing) nije dovoljna, već dobitak dolazi iz sinergije svih 4 faze uz rigoroznu zaštitu od Private LB shakeupa.

| Element | Ocena |
|---|---|
| Autentičnost (provereno Kaggle CLI-jem) | Visoka |
| Tehnička relevantnost pitanja | Vrlo visoka |
| Pouzdanost Ogurtsovljevog saveta | Visoka (upozorenje na Private LB) |
| Direktna reproduktivnost recepta | Srednja (zahteva sinergiju celog steka) |

---

## 4.5 Joseph Adamski — rang 86

Joseph je podržao Tomov vizuelizacioni pristup, ali nije objavio detaljan pipeline.

### Audit zaključak

Može se koristiti kao dodatna potvrda da je vizuelna analiza korisna, ali nije dokaz samostalne taktike ili score improvement-a.

---

# 5. Audit sekundarnih tehničkih tvrdnji

Najviše konkretnih brojki objavio je Hikaggler, koji je u trenutku čitanja bio rangiran 257. Njegove tvrdnje su korisne, ali ih ne treba predstavljati kao dokazane taktike top-10 timova.

## 5.1 Sintetičko pretreniranje

Hikaggler navodi:

- oko `+0.012–0.018` u odnosu na trening od nule;
- hold-out poboljšanje `0.9146 → 0.9269`;
- pretreniranje na 497 od 2.174 sekvence;
- korišćenje svih 2.174 sekvence je bilo oko `−0.005` lošije.

### Audit

Ovo je zanimljiv ablation, ali nije nezavisno potvrđen.

Moguća objašnjenja:

1. domain gap između sintetičkih i realnih podataka;
2. različit broj gradient steps;
3. promena distribucije sekvenci;
4. overfitting sintetičkom domenu;
5. slučajnost konkretnog hold-out split-a.

### Status

**Empirijski signal, ne univerzalno pravilo.**

Pre implementacije treba reprodukovati:

```text
0% synthetic
10%
25%
50%
100%
```

uz isti broj gradient steps i isti real-data fine-tuning.

---

## 5.2 Conditional fusion

Hikaggler tvrdi da obično prosečavanje modela nije pomoglo, dok je conditional fusion bio korisniji.

### Audit

Ovo je metodološki uverljivo, jer modeli mogu biti korelisani. Međutim, nema dovoljno javnih detalja o:

- kriterijumu neizvesnosti;
- threshold-u;
- načinu kombinovanja node/edge/division izlaza;
- tome da li je fusion podešen na hold-out ili LB.

### Status

**Visok potencijal, nedovoljno dokumentovan.**

---

## 5.3 Node-count calibration

Hikaggler navodi da je node-count kalibracija prediktivnija od čistog recall-a.

### Audit

Ovo je u skladu sa drugim delovima diskusije:

- veći recall može povećati broj lažnih detekcija;
- metrički rezultat ne prati nužno detekcioni recall;
- model koji predviđa previše ćelija može biti lošiji iako nalazi više stvarnih ćelija.

### Status

**Visoka teorijska i praktična verovatnoća.**

Ipak, ne postoji javni dokaz da je to dominantan faktor za top-1/top-3 timove.

---

## 5.4 Division head

Hikaggler navodi:

- division Jaccard približno `0.07 → 0.19`;
- mali LB dobitak;
- potpuno uklanjanje division komponente koštalo je oko `−0.022`.

### Audit

Ovo nije kontradikcija.

Moguće je da:

- division head poboljša lokalnu division metriku;
- ali ukupan LB score malo reaguje jer su detection i tracking dominantni;
- potpuno uklanjanje divizija ipak pravi veliku štetu.

### Zaključak

Division komponentu ne treba optimizovati izolovano. Treba je posmatrati kao deo kompletnog graph construction-a.

---

# 6. Audit kvaliteta dokaza

## Kategorija A — direktno provereni izvori

- leaderboard rangovi;
- javni tekst diskusija;
- rang autora prikazan na Kaggle-u;
- Tomov javni GitHub repository;
- Ericova tvrdnja o manifestu i javnim težinama;
- konkretne brojke navedene u komentarima.

## Kategorija B — verovatni, ali nepotpuno provereni zaključci

- conditional fusion je bolji od prostog proseka;
- node calibration je važnija od čistog recall-a;
- sintetičko pretreniranje ima optimalnu količinu;
- private leaderboard će kazniti agresivno overfittingovanje public LB-a.

## Kategorija C — nije dokazano

Nije dokazano da:

- trenutni top-1 koristi sintetičko pretreniranje;
- top-3 koristi HOCT;
- top-10 koristi conditional fusion;
- Tomov vizuelizator povećava score;
- javni plateau predstavlja stvarni limit kompeticije;
- Hikagglerov pipeline može dati top-100 rezultat;
- division head nije važan za top timove.

---

# 7. Kontradikcije i upozorenja

## 7.1 “Pretraining pomaže” naspram “public modeli su već leakage-ovani”

Ovo nisu nužno kontradiktorne tvrdnje.

- Sintetičko pretreniranje može pomoći modelu koji se trenira bez leakage-a.
- Javni modeli mogu imati prednost na lokalnom hold-outu zato što su videli validation videe.
- Zbog toga se ne sme porediti score sintetičkog modela i javnog modela bez identične validacione metodologije.

## 7.2 “Division head malo pomaže” naspram “gašenje division-a mnogo košta”

Division head može imati mali marginalni dobitak kada je već prisutan dobar pipeline, ali njegovo potpuno uklanjanje može oštetiti rezultat.

## 7.3 “Model architecture nije pomogla” ne znači da modeli nisu važni

Hikaggler je testirao određene promene arhitekture i nije dobio dobitak. To ne dokazuje da su sve arhitektonske promene beskorisne.

Precizniji zaključak:

> Na njegovom pipeline-u, u njegovom validacionom režimu, standardno povećanje modela nije bilo dovoljno.

---

# 8. Operativni audit: šta je bezbedno implementirati

## Visok prioritet

### 1. Leakage-free validation

- split po celim videima;
- izbaciti validation videe iz pretraining-a;
- ne koristiti javne all-train težine za lokalnu procenu;
- fiksirati validation set.

### 2. Node-count dashboard

Pratiti:

```text
N_pred
N_gt
N_pred / N_gt
false node rate
node recall
edge recall
division recall
```

### 3. Vizuelni tracker audit

Korisiti Tomov princip:

- 3D trajektorije;
- frame-to-frame matching;
- ID-switch;
- gaps;
- divizije;
- over-segmentation.

### 4. Controlled ablations

Menjati samo jednu stvar po eksperimentu:

```text
detector
linker
division
threshold
post-processing
fusion
```

---

## Srednji prioritet

- synthetic pretraining;
- conditional fusion;
- adaptive threshold;
- sub-voxel refinement;
- duži temporalni prozori;
- graph-level reranking.

---

## Nizak prioritet bez dodatnih dokaza

- veći U-Net samo zbog većeg kapaciteta;
- duže treniranje bez node-count kontrole;
- prosto prosečavanje više modela;
- optimizacija samo division Jaccard-a;
- agresivno podešavanje prema lokalnom CV-u;
- kopiranje javnih all-train težina kao validacione osnove.

---

# 9. Konačna audit ocena

## Ukupna pouzdanost prethodne analize

**7/10**

### Zašto nije 10/10

- nisu javno dostupni kompletni pipeline-i top-1/top-3 učesnika;
- diskusija ne sadrži sistematske postove svih top-100 učesnika;
- public leaderboard koristi samo deo test podataka;
- većina tehničkih tvrdnji dolazi iz samoprijavljenih eksperimenata;
- neki najdetaljniji nalazi potiču od učesnika koji nisu top-100;
- nema nezavisne reprodukcije njihovih rezultata.

### Šta je najpouzdanije

1. problem sa leakage-om u javnim all-train modelima;
2. značaj node-count kalibracije;
3. korisnost vizuelne analize trajektorija;
4. rizik public-to-private generalizacije;
5. ograničenja prostog blendinga.

### Šta je najneizvesnije

1. da li synthetic pretraining daje korist top modelima;
2. koji pipeline koriste top-1 do top-5;
3. da li conditional fusion zaista donosi stabilan private-LB dobitak;
4. koliko je division head dominantan u konačnom rezultatu;
5. da li se javni score 0.974 može reprodukovati iz objavljenih komponenti.

---

# Konačna preporuka

Ako bi se pravio takmičarski pipeline na osnovu ovog audita, redosled bi bio:

```text
1. Leakage-free split
2. Node-count calibration
3. 3D trajectory visualization
4. Baseline detector/linker ablation
5. Conditional fusion
6. Synthetic pretraining ablation
7. Division and graph optimization
8. Final LB risk test
```

Najveća greška bila bi da se zaključi da je rešenje samo “veći model”. Prema dostupnim dokazima, ključna prednost je verovatnije u **validaciji, kalibraciji broja ćelija, graph construction-u i kontroli grešaka trajektorija** nego u samom povećanju arhitekture.