# Master Submission Checklist — Amazon Developer Hackathon 2026

> **Projekat:** JudgeGuard Autonomous AI Governance & Alexa+ MCP Bridge  
> **Primarni Track:** Alexa+ (Plan A: Self-hosted MCP Server 2025-11-25+ preko Streamable HTTP; Plan B: Alexa+ Experience Web Simulator)  
> **Mini-Challenges:** AWS Builder Challenge (Bedrock Runtime) + Open Source Challenge (MIT Samostalni Repo)  
> **Autoritativni izvor istine:** [Official Rules](https://amazonappdev2026.devpost.com/rules) & NotebookLM (UUID: `82440dea-0a12-40a7-a249-0ba460f69611`)  
> **AWS Credits Rok:** 21. oktobar 2026. u 21:00 CEST (12:00 PM PT)  
> **Finalni Submission Rok:** **23. oktobar 2026. u 21:00 CEST** (12:00 PM PT)

---

## 📊 Tabela Realnog Statusa (Audit Stanja)

| Stavka / Kriterijum | Lokalni Kod / Fajl | Javno Stanje (GitHub) | Devpost Submission Forma | Konačni Status |
| :--- | :---: | :---: | :---: | :---: |
| **Devpost nalog & registracija** | — | — | Registrovan & Join kliknut | ✅ SPREMNO |
| **Podobnost Srbije & punoletstvo** | Pravila verifikovana | — | Potvrđeno učešće po pravilima | 🟡 Verifikovano po formulaciji |
| **Alexa+ Track (Plan A: MCP / Plan B: Sim)** | ✅ Implementirano | 🟡 Čeka push / novi repo | Čeka unos | 🟡 Spreman kod, čeka objavu |
| **MCP 2025-11-25+ Streamable HTTP** | ✅ Implementirano | 🟡 Čeka push / novi repo | Čeka unos URL-a | 🟡 Testiran lokalno |
| **AWS Builder (Bedrock Runtime)** | ✅ Implementirano | 🟡 Čeka push / novi repo | Čeka kopiranje u polje | 🟡 Spreman tekst i kod |
| **Open Source mini-challenge** | ✅ MIT paket spreman | ❌ Nema javnog repo-a još | Čeka URL repo-a | 🟡/❌ U toku kreiranje repoa |
| **GitHub repozitorijum** | ✅ Lokalno kompletno | ❌ Nema root LICENSE; README star | Čeka ispravan javni URL | ❌ U toku sanacija |
| **Root README sa uputstvima** | ✅ Napisan u paketu | ❌ Root README je Auth0 | Čeka postavljanje | 🟡 U toku sanacija |
| **MIT Licenca** | ✅ U paketu | ❌ GitHub vraća `license: null` | — | ❌ Rešava se root licencom |
| **Automatizovani testovi** | ✅ 10/10 passed | 🟡 Nema GH Actions linka | — | 🟡 Dokazivo komandom |
| **Demo Video (< 3:00 min)** | ✅ Skripta gotova (2:45) | — | 🟡 Nije snimljen / postavljen | 🟡 Čeka snimanje |
| **Video Platforma (YouTube/Vimeo Public)** | Pravila usvojena | — | — | 🟡 Usvojeno: samo YT/Vimeo |
| **AWS Product Feedback** | ✅ Fajl postoji | 🟡 Čeka push | 🟡 Čeka unos u Devpost formu | 🟡 Spreman za unos |
| **Hackathon Friction Log (10% bonus)** | ✅ Fajl postoji | 🟡 Čeka push | 🟡 Čeka unos u Devpost formu | 🟡 Spreman za unos |
| **AWS Krediti (rok: 21. oktobar u 21:00 CEST)**| — | — | Opciono poslati pre roka | ✅ Rok preračunat |
| **Finalna prijava pre roka (23. oktobar)** | — | — | Čeka završetak svih koraka | 🟡 U toku priprema |

---

## 1. Pre razvoja (Pre-Development)

- [x] **Registrovan Devpost nalog i kliknut Join Hackathon.**  
  *Status:* Korisnik poseduje nalog na Devpost-u i registrovan je na takmičenje [amazonappdev2026.devpost.com](https://amazonappdev2026.devpost.com/).
- [x] **Proveren status podobnosti i punoletstva.**  
  *Tačna pravna formulacija:*  
  > Srbija nije eksplicitno navedena među isključenim jurisdikcijama u Official Rules. Učešće zavisi od statusa punoletstva (dostizanja *age of majority in country of residence*), lokalnih propisa, važećih sankcija/izvoznih kontrola i nepostojanja konflikta interesa (pravila ne garantuju univerzalni „18+ whitelist“ već zahtevaju usklađenost sa zakonima zemlje prebivališta).
- [x] **Izabran primarni track: Alexa+ (Jasno razdvojena dva puta).**  
  *Plan A (Pravi MCP server — Primarni):* Self-hosted MCP server koji implementira MCP specifikaciju **2025-11-25+** preko **Streamable HTTP transporta**, sa stvarnim runtime pozivom u kodu (`judgeguard_evaluate`, `judgeguard_audit_log`, `judgeguard_check_permission`).  
  *Plan B (Simulirano Alexa+ iskustvo — Fallback/Vizuelni demo):* Sopstvena demonstraciona web aplikacija (**Alexa+ Experience Web Simulator** na `/` i `/simulator`).  
  *Važna napomena za sudije:* Naš web simulator je **sopstvena demonstraciona web aplikacija** koja vizualizuje agentic workflow i audit HUD, a **nije** zvanični Amazonov interni Alexa+ simulator.
- [x] **Odlučeno o učešću u mini-izazovima (AWS Builder & Open Source).**  
  *AWS Builder:* Implementiran `bedrock_client.py` koji koristi AWS Bedrock Runtime (`anthropic.claude-3-5-sonnet-20241022-v2:0` i `amazon.titan-text-express-v1`) za dubinsko rasuđivanje i bezbednosnu analizu.  
  *Open Source:* Kreiranje zasebnog, čistog javnog repozitorijuma `judgeguard-alexa-mcp` pod MIT licencom na GitHub-u, razvijenog u potpunosti tokom hackathon perioda.
- [x] **Pročitani track docs i starter repo.**  
  *Status:* Proučena dokumentacija za Alexa+ MCP integraciju, Streamable HTTP specifikacija (2025-11-25) i zvanična pravila.
- [x] **Odabran minimalni korisnički scenario.**  
  *Scenario:* Autonomno upravljanje pametnim domom i osetljivim operacijama (npr. otključavanje ulaznih vrata, pokretanje transakcija) gde Alexa+ agent poziva JudgeGuard MCP alate pre izvršenja, uz blokiranje neovlašćenih radnji i RAG pretragu pravila i rokova iz Google NotebookLM-a sa tačnim citatima.

---

## 2. Tokom razvoja (During Development)

- [x] **Amazon tehnologija pozvana u runtime-u.**  
  - *MCP Streamable HTTP Server:* Implementiran u `server.py` (FastAPI / Uvicorn, JSON-RPC 2.0 endpoint, `initialize` sa `protocolVersion: 2025-11-25`, `tools/list`, `tools/call`).  
  - *AWS Bedrock Runtime:* Pozvan u runtime-u u `bedrock_client.py` (Boto3 klijent sa podrškom za Claude 3.5 i Titan).
- [x] **Git commit istorija i changelog.**  
  *Status:* Uredna atomička git istorija sa kontrolnim tačkama verifikovanim kroz `judge_guard.py`.
- [x] **Secrets van repo-a.**  
  *Status:* Koristi se `.env` konfiguracija uključena u `.gitignore`. Nijedan privatni API ključ ili AWS credential se ne čuva u git istoriji.
- [x] **Automatizovani testovi i verifikacija iz čistog okruženja.**  
  *Tačni podaci o testovima:*  
  - **Komanda:** `python3 -m unittest test_server.py` (ili `pytest -q`)  
  - **Rezultat:** `Ran 10 tests in 0.051s - OK` (10 passed, 0 failures, 0 errors)  
  - **Okruženje:** Python 3.12.3 na Linux x86_64 (`Linux 6.8.0-101-generic`)  
  - **Commit:** Lokalni hash `b130ada` (prenosi se u javni repo).  
  *Napomena:* Sama brzina testova ne dokazuje mrežnu otpornost niti AWS Bedrock odziv, pa je priložen i E2E protokolarni test sa živim HTTP POST i SSE zahtevima.
- [x] **AWS integracija dokumentovana.**  
  *Status:* Dokument `AWS_PRODUCT_FEEDBACK.md` sadrži tačnu arhitekturu poziva, merenja latencije (Bedrock Claude 3.5 Sonnet vs Titan) i konkretne preporuke za AWS tim.
- [x] **Open Source doprinos tokom hackathon prozora.**  
  *Status:* Kompletan kod servera, simulatora, testova i specifikacija razvijen od nule unutar hackathon prozora (septembar - oktobar 2026).
- [x] **Vođen realan friction log.**  
  *Status:* Dokumentovan `HACKATHON_FRICTION_LOG.md` sa 3 stvarna inženjerska problema (MCP Streamable HTTP spec 2025-11-25 format zaglavlja, Bedrock Converse API token streaming unutar MCP tool poziva, i SSE broadcast sinhronizacija sa web simulatorom).

---

## 3. Pre slanja (Pre-Submission & Sanitization)

- [ ] **README ima kompletna uputstva za pokretanje i reprodukciju (Javno).**  
  *Status:* Pripremljen detaljan `README.md` sa instrukcijama:
  ```bash
  git clone https://github.com/kizabgd123/judgeguard-alexa-mcp.git
  cd judgeguard-alexa-mcp
  python3 -m venv .venv
  source .venv/bin/activate
  pip install -e .
  # Pokretanje servera i web simulatora na http://127.0.0.1:8765
  python3 server.py
  # Pokretanje verifikacionih testova
  python3 -m unittest test_server.py
  ```
  *Akcija:* Postaje ✅ čim se kod publikuje na GitHub.
- [ ] **Repozitorijum je javno dostupan sa prepoznatom MIT licencom.**  
  *Trenutni problem:* Postojeći `judge-guard-core-master` nema root `LICENSE` fajl na GitHub-u (GitHub API vraća `license: null`), a root `README.md` opisuje Auth0 projekat.  
  *Rešenje:* Kreiranje čistog, posebnog repozitorijuma **`judgeguard-alexa-mcp`** pod MIT licencom gde je root nivo 100% posvećen ovom hackathonu, uz dodavanje MIT licence i na postojeći repo.
- [ ] **Demo Video je kraći od 3 minuta, na engleskom i JAVAN.**  
  *Kritična pravila:*  
  - **Dozvoljene platforme:** Isključivo **YouTube** ili **Vimeo** (Loom **NIJE** dozvoljen zvaničnim pravilima!).  
  - **Vidljivost:** Isključivo **Public** (Pravila zahtevaju javno dostupan video; ne planirati „Unlisted“).  
  - **Dužina:** Strogo **ispod 3:00 minuta** (skripta je tempirana na 2:45, a finalni mp4 se meri u sekundu sa uvodom i odjavom).  
  - **Jezik:** Engleski jezik.  
  - **Sadržaj videa:** Prikaz korisničkog upita, Alexa+ agenta koji poziva JudgeGuard MCP Streamable HTTP endpoint (`tools/call`), evaluacije rizika uz pomoć AWS Bedrock / NotebookLM RAG-a, blokiranja opasne komande i real-time prikaza na simulatoru / terminalu.
- [ ] **Popunjena polja na Devpost submission formi.**  
  *Razlika između fajla i prijave:*  
  - `AWS_PRODUCT_FEEDBACK.md` postoji u repo-u ✅ -> **Mora biti kopiran u polje "Product Feedback" na Devpostu** 🟡  
  - `HACKATHON_FRICTION_LOG.md` postoji u repo-u ✅ -> **Mora biti unet u polje "Friction Log" za 10% bonus** 🟡  
  - Opis projekta iz `README.md` -> **Mora biti unet u "Project Story / Inspiration / What it does"** 🟡  
  - URL javnog GitHub repozitorijuma -> **Mora biti unet u polje za kod i Open Source mini-challenge** 🟡  
  - URL YouTube/Vimeo videa -> **Mora biti unet u polje "Demo Video"** 🟡
- [ ] **AWS Krediti — podnet zahtev ako je potrebno.**  
  *Rok:* **21. oktobar 2026. u 21:00 CEST** (12:00 PM PT).
- [ ] **Konačno slanje pre krajnjeg roka.**  
  *Interni rok:* 22. oktobar 2026.  
  *Zvanični krajnji rok:* **23. oktobar 2026. u 21:00 CEST**.
