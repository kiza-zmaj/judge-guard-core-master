# Master Submission Checklist — Amazon Developer Hackathon 2026

> **Projekat:** JudgeGuard Autonomous AI Governance & Alexa+ MCP Bridge  
> **Primarni Track:** Alexa+ (Plan A: Self-hosted MCP Server 2025-11-25+ preko Streamable HTTP; Plan B: Alexa+ Experience Web Simulator)  
> **Mini-Challenges:** AWS Builder Challenge (Bedrock Claude 3.5 & Titan) + Open Source Challenge (Zaseban repo: `judgeguard-policy-schema`)  
> **Autoritativni izvor istine:** [Official Rules](https://amazonappdev2026.devpost.com/rules)  
> **AWS Credits Rok:** 21. oktobar 2026. u 21:00 CEST (12:00 PM PT)  
> **Finalni Submission Rok:** **23. oktobar 2026. u 21:00 CEST** (12:00 PM PT)

---

## 📊 Tabela Realnog Statusa (Pošteni Audit Stanja)

| Stavka / Kriterijum | Lokalni Kod / Fajl | Javno Stanje (GitHub) | Devpost Submission Forma | Konačni Status |
| :--- | :---: | :---: | :---: | :---: |
| **Primarni Hackathon Repo** | ✅ `server.py`, testovi | ✅ [kiza-zmaj/judgeguard-alexa-mcp](https://github.com/kiza-zmaj/judgeguard-alexa-mcp) | Čeka unos URL-a | ✅ **SPREMNO NA GITHUB-U** |
| **MIT Licenca (Primarni)** | ✅ `LICENSE` (MIT) | ✅ GitHub API: `license: MIT` | — | ✅ **SPREMNO** |
| **Clean-Clone & Pokretanje** | ✅ `REPO_ROOT` & `app` fix | ✅ Popravljen import i `pyproject.toml` | — | ✅ **VERIFIKOVANO** |
| **MCP 2025-11-25 Spec** | ✅ `test_protocol.py` | ✅ 10 protokolskih testova prolaze | Čeka unos | ✅ **VERIFIKOVANO TESTOM** |
| **Streamable HTTP Transport** | ✅ JSON-RPC POST + SSE | ✅ Razdvojen MCP POST od UI telemetry SSE | — | ✅ **VERIFIKOVANO** |
| **AWS Bedrock: Claude 3.5** | ✅ Implementiran payload & dispatch | ✅ `bedrock_client.py` live & fallback | Čeka unos teksta | ✅ **VERIFIKOVANO (Claude testiran)** |
| **AWS Bedrock: Titan podrška** | ✅ `inputText`/`textGenerationConfig` | ✅ Implementiran i testiran Titan dispatch | Čeka unos teksta | ✅ **VERIFIKOVANO (Titan testiran)** |
| **Policy Grounding (NotebookLM Lineage)** | ✅ Transparentan lokalni korpus | ✅ Pošteno opisano bez lažnih live tvrdnji | — | ✅ **TRANSPARENTNO** |
| **Open Source Mini-Challenge** | ✅ Zaseban dodatni repo sa JSON Schema | ✅ [kiza-zmaj/judgeguard-policy-schema](https://github.com/kiza-zmaj/judgeguard-policy-schema) | Čeka unos URL-a | ✅ **DODATNI REPO SPREMAN** |
| **Automatizovani testovi** | ✅ 21/21 passed (0.096s) | ✅ `test_server.py` + `test_protocol.py` | — | ✅ **VERIFIKOVANO** |
| **Demo Video skripta (< 3 min)** | ✅ Tempirana na 2:45 | ✅ `DEMO_VIDEO_SCRIPT.md` | 🟡 Čeka snimanje korisnika | 🟡 **Čeka snimanje** |
| **Video Platforma (YT/Vimeo Public)**| Pravila usvojena | — | Isključivo Public YouTube/Vimeo | 🟡 **Pravilo striktno usvojeno** |
| **Devpost Product Feedback** | ✅ `AWS_PRODUCT_FEEDBACK.md` | ✅ Live na GitHub-u | 🟡 Čeka kopiranje u formu | 🟡 **Spreman za unos** |
| **Devpost Friction Log (10% bonus)** | ✅ `HACKATHON_FRICTION_LOG.md` | ✅ Live na GitHub-u | 🟡 Čeka kopiranje u formu | 🟡 **Spreman za unos** |
| **AWS Krediti (rok: 21. oktobar)** | — | — | Opciono poslati pre roka | ✅ **Rok preračunat** |
| **Finalno slanje (rok: 23. oktobar)** | — | — | Čeka unos linkova i videa | 🟡 **Sve spremno za unos** |

---

## 1. Zvanični Linkovi za Devpost Formu

1. **Primarni projekat (Alexa+ Track):**  
   `https://github.com/kiza-zmaj/judgeguard-alexa-mcp`
2. **Open Source Mini-Challenge (Dodatni open-source repozitorijum):**  
   `https://github.com/kiza-zmaj/judgeguard-policy-schema`  
   - *GitHub username:* `kizabgd123` (author/committer javnog commita)  
   - *Project Organization:* `kiza-zmaj/judgeguard-policy-schema`  
   - *Opis:* Samostalna Pydantic v2 biblioteka i rule engine za definisanje bezbednosnih polisa, JSON Schema export i MCP granica za AI agente.
3. **AWS Builder Mini-Challenge dokaz:**  
   Implementiran `bedrock_client.py` sa eksplicitnom podrškom za **Anthropic Claude 3.5 Sonnet** i **Amazon Titan Text Express** (`inputText`/`textGenerationConfig`).

---

## 2. Uputstvo za Sudije (Čist Clone i Pokretanje)

```bash
git clone https://github.com/kiza-zmaj/judgeguard-alexa-mcp.git
cd judgeguard-alexa-mcp
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# Pokretanje servera i Alexa+ Web Simulatora na portu 8765
python3 server.py

# Pokretanje kompletne verifikacione baterije (21 test)
python3 -m unittest test_server.py test_protocol.py
```
