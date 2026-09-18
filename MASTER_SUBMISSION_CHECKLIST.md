# Master Submission Checklist — Amazon Developer Hackathon 2026

> **Project:** JudgeGuard Autonomous AI Governance & Alexa+ MCP Bridge  
> **Primary Track:** Alexa+ (Self-Hosted Streamable HTTP MCP Server + Web Simulator)  
> **Mini-Challenges:** AWS Builder (Bedrock Runtime) + Open Source (MIT Package)  
> **Authoritative Master Source:** NotebookLM (UUID: `82440dea-0a12-40a7-a249-0ba460f69611`) & Official Rules  
> **Final Submission Deadline:** October 23, 2026 @ 8:00 AM GMT-11 (12:00 PM PDT)  
> **Belgrade Local Deadline:** **23. oktobar 2026. u 21:00 CEST** (MANDATORY)

---

## 1. Pre razvoja (Pre-Development)

- [x] **Registrovan Devpost nalog i kliknut Join Hackathon.**  
  *Status:* Korisnik poseduje nalog na Devpost-u i registrovan je na takmičenje [amazonappdev2026.devpost.com](https://amazonappdev2026.devpost.com/).
- [x] **Proveren status podobnosti i punoletstva.**  
  *Status:* Prema Official Rules Sekciji 3, učesnici iz Srbije su podobni uz status punoletstva (18+).
- [x] **Izabran primarni track.**  
  *Status:* Izabran **Alexa+ Track** sa samostalno hostovanim MCP serverom preko Streamable HTTP protokola i pratećim Web Simulatorom (eliminacija hardverskih zavisnosti).
- [x] **Odlučeno da li se ide na AWS Builder i/ili Open Source.**  
  *Status:* Potvrđeno učešće u **oba** mini-izazova:
  - *AWS Builder:* Integrisan AWS Bedrock Runtime (`bedrock_client.py`) i Claude 3.5 / Titan.
  - *Open Source:* Samostalni paket pod MIT licencom (`packages/judgeguard_mcp_server/`).
- [x] **Pročitani track docs i starter repo.**  
  *Status:* Analiziran zvanični vodič, MCP specifikacija 2025-11-25+ i NotebookLM priručnik.
- [x] **Odabran minimalni korisnički scenario.**  
  *Status:* Autonomno upravljanje pametnim uređajima sa zaštitom od opasnih komandi (otključavanje vrata, finansijske transakcije) i RAG pretraga pravila/rokova sa tačnim citiranjem.
- [x] **Proveren pristup uređaju/simulatoru/Bee podacima/Alexa path-u/Ring sandbox-u.**  
  *Status:* Kreiran i verifikovan interaktivni **Alexa+ Experience Web Simulator** (`static/index.html`) sa direktnim povezivanjem na `/mcp` SSE stream i JSON-RPC 2.0.

---

## 2. Tokom razvoja (During Development)

- [x] **Obavezna Amazon tehnologija pozvana u runtime-u tamo gde je zahtevana.**  
  *Dokaz:*
  - MCP Streamable HTTP transport implementiran u `packages/judgeguard_mcp_server/server.py`.
  - AWS Bedrock Runtime pozvan u `packages/judgeguard_mcp_server/bedrock_client.py`.
- [x] **Git commit istorija i changelog.**  
  *Dokaz:* Atomička git istorija sa kontrolnim tačkama i verifikacijom preko `judge_guard.py`.
- [x] **Secrets van repo-a.**  
  *Dokaz:* Koristi se `.env` koji se nalazi u `.gitignore`. Nijedan statički API ključ nije u repozitorijumu.
- [x] **Testirano na ciljanoj platformi.**  
  *Dokaz:* Svi testovi (`packages/judgeguard_mcp_server/test_server.py`) prolaze 10/10:
  ```bash
  python3 -m unittest packages/judgeguard_mcp_server/test_server.py
  # Ran 10 tests in 0.051s - OK
  ```
- [x] **Ako je postojeći projekat: jasno dokumentovane nove funkcije.**  
  *Dokaz:* Novi paket `packages/judgeguard_mcp_server/` razvijen je ciljano tokom hackathona kao nezavisan governance gateway za Alexa+.
- [x] **AWS integracija dokumentovana, ako postoji.**  
  *Dokaz:* Kompletan dokument `packages/judgeguard_mcp_server/AWS_PRODUCT_FEEDBACK.md` i sekcija u `README.md`.
- [x] **Open Source doprinos napravljen tokom hackathon prozora, ako se prijavljuje.**  
  *Dokaz:* Celokupan kod paketa, `pyproject.toml`, testovi i dokumentacija kreirani tokom hackathon prozora.
- [x] **Vođen realan friction log.**  
  *Dokaz:* Dokumentovan `packages/judgeguard_mcp_server/HACKATHON_FRICTION_LOG.md` i JSONL baza `research/friction_logs/hackathon_friction_logs.jsonl` (za bonus do 10%).

---

## 3. Pre slanja (Pre-Submission)

- [x] **README ima setup/run/test instrukcije.**  
  *Dokaz:* [`packages/judgeguard_mcp_server/README.md`](file:///home/kizamladjanijebac/Documents/jude%20guard/judge-guard-core-master/packages/judgeguard_mcp_server/README.md) sadrži kompletna uputstva za instalaciju, pokretanje, testiranje i primere `curl` poziva.
- [x] **Repo je public sa licencom ili privatno podeljen na ispravan način.**  
  *Dokaz:* Zvanična MIT licenca u [`packages/judgeguard_mcp_server/LICENSE`](file:///home/kizamladjanijebac/Documents/jude%20guard/judge-guard-core-master/packages/judgeguard_mcp_server/LICENSE).
- [ ] **Video je javno dostupan, na engleskom ili preveden, kraći od 3 minuta.**  
  *Akcija:* Skripta pripremljena na tačno 2:45 u [`packages/judgeguard_mcp_server/DEMO_VIDEO_SCRIPT.md`](file:///home/kizamladjanijebac/Documents/jude%20guard/judge-guard-core-master/packages/judgeguard_mcp_server/DEMO_VIDEO_SCRIPT.md). Korisnik snima video i postavlja ga na YouTube/Loom (unlisted ili public).
- [ ] **Video prikazuje rad na ciljanoj platformi.**  
  *Akcija:* Video treba direktno da snimi rad Alexa+ Simulatora na `http://localhost:8765/`, terminalski SSE stream i JudgeGuard HUD.
- [x] **Nema neovlašćene muzike, footage-a ili trademark materijala.**  
  *Status:* Koristi se isključivo originalni glasovni snimak i snimak ekrana našeg simulatora i koda.
- [x] **Tekstualni opis objašnjava šta i kako.**  
  *Dokaz:* Kompletiran opis u `openspec/changes/alexa-judgeguard-mcp/design.md` i `packages/judgeguard_mcp_server/README.md`.
- [x] **Product Feedback popunjen za svaki alat/API/SDK.**  
  *Dokaz:* Popunjeno u `packages/judgeguard_mcp_server/AWS_PRODUCT_FEEDBACK.md` i `HACKATHON_FRICTION_LOG.md`.
- [x] **Track i mini-challenge izbor tačno označeni.**  
  *Status:* Označiti na Devpost formi:
  - Track: **Alexa+**
  - Mini-challenges: **AWS Builder Challenge** i **Open Source Challenge**
- [x] **Open Source dodatna polja popunjena, ako se koristi.**  
  *Status:* Uneti link ka GitHub repozitorijumu sa MIT licencom.
- [x] **Feature Requests popunjeni, ako su korisni.**  
  *Dokaz:* Zahtev za standardizovani AWS Bedrock MCP adapter i standardizovanu taksonomiju grešaka definisan u Product Feedback-u.
- [x] **Friction Logs popunjeni sa dokazima.**  
  *Dokaz:* Tri opsežna unosa sa tačnim koracima, greškama i rešenjima u `HACKATHON_FRICTION_LOG.md`.
- [ ] **AWS credits zahtev poslat ranije, ako je potreban.**  
  *Akcija:* Rok za zahtev za AWS kredite je **21. oktobar 2026. u 21:00 CEST**. Poslati preko zvanične Devpost forme ako su potrebni dodatni resursi.
- [ ] **Sačuvan screenshot/izvoz finalne Devpost prijave.**  
  *Akcija:* Prilikom unosa na Devpost preporučuje se snimanje ekrana ili export PDF-a pre klika na Submit.
- [ ] **Submission poslat pre internog roka; proverena potvrda na Devpost-u.**  
  *Plan:*
  - Interni Code Freeze: **21. - 22. oktobar 2026.**
  - Konačni rok: **23. oktobar 2026. u 21:00 CEST**.
