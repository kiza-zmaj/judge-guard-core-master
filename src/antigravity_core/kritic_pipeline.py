#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KRITICAR Multi-Agent Orchestration Engine (LangGraph + Gemini + Gemma)

Arhitektura:
  1. Analyst (Gemini 2.5 Flash Lite) -> Dekodiranje namere, dekompozicija i kriterijumi uspeha
  2. Generator (Gemma 31B / Gemini 2.5 Flash fallback) -> Generisanje i iterativna popravka drafta
  3. Critic (Gemma 26B / Gemini fallback) -> Advokat đavola, traženje logičkih rupa i pretpostavki (Paralelno)
  4. Research (Gemini 2.5 Flash + Google Search Grounding) -> Verifikacija činjenica na internetu (Paralelno)
  5. QA Auditor (Gemini 2.5 Flash) -> Anti-drift evaluacija, matrica usklađenosti, drift_score (0-10)
  6. Evaluator (Gemini 2.5 Flash Lite) -> PASS/REJECT odluka sa max 2 iteracije dorade
  7. Security Guard (Gemini 2.5 Flash Lite) -> PII, toksičnost, jailbreak inspekcija
  8. NotebookLM Bridge (nlm CLI/MCP) -> Opciona sinhronizacija verifikovanih znanja
"""

import os
import re
import sys
import asyncio
import logging
from typing import TypedDict, List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field

# Učitavanje konfiguracije
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# LangGraph i LangChain
from langgraph.graph import StateGraph, START, END
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

logger = logging.getLogger("kritic_pipeline")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# -------------------------------------------------------------
# 0. RESOLUCIJA API KLJUČEVA I MODELA (Zero Hardcoded Keys)
# -------------------------------------------------------------
def get_gemini_api_key() -> str:
    """Preuzima validan Gemini API ključ iz .env ili okruženja bez hardkodovanja."""
    # Podrška za rotaciju iz GEMINI_API_KEYS ili pojedinačni GOOGLE_API_KEY / GEMINI_API_KEY
    keys = os.getenv("GEMINI_API_KEYS", "")
    if keys:
        first_key = keys.split(",")[0].strip()
        if first_key:
            return first_key
    key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not key:
        raise ValueError("Nije pronađen GEMINI_API_KEY / GOOGLE_API_KEY u okruženju ili .env fajlu!")
    return key

# Postavi GOOGLE_API_KEY u os.environ za google-genai klijente
resolved_key = get_gemini_api_key()
os.environ["GOOGLE_API_KEY"] = resolved_key

OLLAMA_BASE_URL = os.getenv("OPENAI_API_BASE", "http://localhost:11434/v1")
OPENAI_KEY = os.getenv("OPENAI_API_KEY", "ollama")

# -------------------------------------------------------------
# 1. PYDANTIC STRUKTUIRANI IZLAZI (Stroga Validacija)
# -------------------------------------------------------------
class AnalystOutput(BaseModel):
    intent: str = Field(
        description="Glavna namera korisnika prepoznata iz prompta (npr. tehničko rešenje, sinteza, analiza)."
    )
    key_entities: List[str] = Field(
        default_factory=list,
        description="Ključni entiteti, koncepti, teorije ili institucije pomenuti u zahtevu."
    )
    subtasks: List[str] = Field(
        default_factory=list,
        description="Konkretni logički koraci koje Generator mora pokriti."
    )
    success_criteria: List[str] = Field(
        default_factory=list,
        description="Marljivo definisani uslovi koje finalni odgovor mora zadovoljiti."
    )

class QAOutput(BaseModel):
    alignment_summary: str = Field(
        description="Sažetak usklađenosti drafta sa planom i činjenicama iz pretrage."
    )
    minor_issues: List[str] = Field(
        default_factory=list,
        description="Manje stilske ili sitne nepreciznosti koje ne obaraju verifikaciju."
    )
    critical_issues: List[str] = Field(
        default_factory=list,
        description="Faktičke greške, kontradikcije ili neosnovane pretpostavke koje zahtevaju doradu."
    )
    drift_score: int = Field(
        ge=0, le=10,
        description="Ocena odstupanja od 0 do 10 (0=savršeno usklađeno, 10=potpuni drift ili neistina)."
    )

class EvaluatorOutput(BaseModel):
    decision: Literal["PASS", "REJECT"] = Field(
        description="Konačna presuda: PASS (ako je drift_score <= 3 i nema kritičnih rupa) ili REJECT."
    )
    reason: str = Field(
        description="Obrazloženje odluke sa tačnim smernicama za popravku ukoliko je REJECT."
    )

# -------------------------------------------------------------
# 2. DEFINICIJA STANJA APLIKACIJE (LangGraph State)
# -------------------------------------------------------------
class AgentState(TypedDict):
    user_prompt: str
    analyst_plan: Dict[str, Any]
    current_draft: str
    critic_feedback: str
    research_facts: str
    qa_report: Dict[str, Any]
    drift_score: int
    iteration_count: int
    evaluation_decision: str
    evaluation_reason: str
    final_output: str

# -------------------------------------------------------------
# 3. FABRIKA MODELA (Model Router sa Graceful Fallback-om)
# -------------------------------------------------------------
# Brzi / Ekonomični ruteri i evaluatori
gemini_flash_lite = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash-lite",
    temperature=0.1
)

gemini_flash = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.2
)

# Gemini sa ugrađenom Google Search podrškom
gemini_flash_search = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.0,
    model_kwargs={"tools": [{"google_search": {}}]}
)

def create_gemma_client(model_name: str, temperature: float = 0.5):
    """Kreira klijenta za Gemma modele preko lokalnog Ollama servera uz Gemini fallback."""
    try:
        return ChatOpenAI(
            model=model_name,
            api_key=OPENAI_KEY,
            base_url=OLLAMA_BASE_URL,
            temperature=temperature,
            request_timeout=30.0
        )
    except Exception as e:
        logger.warning(f"Lokalni Gemma model '{model_name}' nije dostupan ({e}). Koristi se Gemini 2.5 Flash kao fallback.")
        return ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=temperature)

gemma_generator = create_gemma_client("gemma4:31b-cloud", temperature=0.7)
gemma_critic = create_gemma_client("gemma4:31b-cloud", temperature=0.2)

# -------------------------------------------------------------
# 4. KREIRANJE ASINHRONIH AGENT ČVOROVA (Nodes)
# -------------------------------------------------------------
async def run_analyst(state: AgentState) -> Dict[str, Any]:
    """[1] ANALYST: Rastavlja zahtev na subtask-ove i uslove uspeha."""
    logger.info("--- [1] ANALYST ZAPOČINJE RAD ---")
    prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "Ti si Lead Systems Analyst. Rastavi korisnički zahtev na jasne korake, ključne entitete i "
            "striktne kriterijume uspeha. Budi koncizan, profesionalan i temeljan."
        )),
        ("user", "{user_prompt}")
    ])
    structured_analyst = gemini_flash_lite.with_structured_output(AnalystOutput)
    chain = prompt | structured_analyst
    
    result: AnalystOutput = await chain.ainvoke({"user_prompt": state["user_prompt"]})
    return {
        "analyst_plan": result.model_dump(),
        "iteration_count": 0
    }

async def run_generator(state: AgentState) -> Dict[str, Any]:
    """[2] GENERATOR: Piše draft ili primenjuje korekcije na osnovu QA nalaza."""
    iteration = state.get("iteration_count", 0) + 1
    logger.info(f"--- [2] GENERATOR ZAPOČINJE RAD (Iteracija {iteration}) ---")
    
    plan_str = str(state.get("analyst_plan", {}))
    
    if iteration == 1:
        system_prompt = (
            "Ti si Senior Technical Writer & Subject Matter Expert. Na osnovu postavljenog plana i "
            "korisničkog zahteva, sastavi detaljan, precizan, stručan i dobro strukturisan odgovor."
        )
        user_content = f"Plan: {plan_str}\n\nZahtev: {state['user_prompt']}"
    else:
        system_prompt = (
            "Ti si Senior Technical Writer. Tvoj prethodni odgovor je prošao rigoroznu recenziju. "
            "Ispravi SVE uočene faktičke greške, adresiraj primedbe kritičara i ukloni nelogičnosti. "
            "Zadrži visok nivo jasnoće i preciznosti."
        )
        qa_data = state.get("qa_report", {})
        critical = qa_data.get("critical_issues", []) if isinstance(qa_data, dict) else []
        user_content = (
            f"Korisnički zahtev: {state['user_prompt']}\n\n"
            f"Prethodni draft:\n{state.get('current_draft', '')}\n\n"
            f"Kritika logike i pretpostavki:\n{state.get('critic_feedback', '')}\n\n"
            f"Verifikovane činjenice sa interneta:\n{state.get('research_facts', '')}\n\n"
            f"Kritični nedostaci koje MORAŠ ispraviti: {critical}"
        )
        
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", "{user_content}")
    ])
    
    try:
        chain = prompt | gemma_generator
        result = await chain.ainvoke({"user_content": user_content})
        draft_content = result.content
    except Exception as e:
        logger.warning(f"Generator fallback na Gemini zbog greške: {e}")
        chain = prompt | gemini_flash
        result = await chain.ainvoke({"user_content": user_content})
        draft_content = result.content
        
    return {
        "current_draft": draft_content,
        "iteration_count": iteration
    }

async def run_critic(state: AgentState) -> Dict[str, Any]:
    """[3a] CRITIC: Advokat đavola koji traži logičke greške i pristrasnosti (Paralelno)."""
    logger.info("--- [3a] CRITIC ANALIZIRA DRAFT (PARALELNO) ---")
    prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "Ti si Advokat đavola i Senior Peer Reviewer. Tvoj zadatak je nemilosrdno pronalaženje svih "
            "logičkih praznina, preuranjenih zaključaka, neproverenih pretpostavki i pristrasnosti u draftu. "
            "Budi direktan, konstruktivan i navedi tačno šta nedostaje da bi argument bio neoboriv."
        )),
        ("user", "Draft za analizu:\n{draft}")
    ])
    
    try:
        chain = prompt | gemma_critic
        result = await chain.ainvoke({"draft": state["current_draft"]})
        feedback = result.content
    except Exception as e:
        logger.warning(f"Critic fallback na Gemini zbog greške: {e}")
        chain = prompt | gemini_flash
        result = await chain.ainvoke({"draft": state["current_draft"]})
        feedback = result.content
        
    return {"critic_feedback": feedback}

async def run_research(state: AgentState) -> Dict[str, Any]:
    """[3b] RESEARCH: Proverava ključne tvrdnje pomoću Google Search Grounding-a (Paralelno)."""
    logger.info("--- [3b] RESEARCH VERIFIKUJE ČINJENICE PREKO GOOGLE SEARCH (PARALELNO) ---")
    prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "Ti si elitni Fact-Checker i istraživač. Koristi Google Search alat da proveriš tačnost "
            "ključnih tvrdnji, datuma, brojeva, imena i tehničkih specifikacija iz sledećeg teksta. "
            "Vrati sažet pregled proverenih činjenica sa referencama. Izbegavaj nepotrebne podatke."
        )),
        ("user", "Tekst za proveru činjenica:\n{draft}")
    ])
    
    chain = prompt | gemini_flash_search
    try:
        result = await chain.ainvoke({"draft": state["current_draft"]})
        facts = result.content
    except Exception as e:
        logger.warning(f"Research Google Search poziv neuspešan ({e}). Koristi se standardni Flash fact-checker.")
        fallback_chain = prompt | gemini_flash
        result = await fallback_chain.ainvoke({"draft": state["current_draft"]})
        facts = result.content
        
    return {"research_facts": facts}

async def run_qa_auditor(state: AgentState) -> Dict[str, Any]:
    """[4] QA AUDITOR: Spaja paralelne grane, ocenjuje odstupanje (drift_score)."""
    logger.info("--- [4] QA AUDITOR SPRAVLJA MATRICU USKLAĐENOSTI ---")
    prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "Ti si Glavni QA Auditor za AI sisteme sa uravnoteženim profesionalnim kriterijumima.\n"
            "Tvoj zadatak je da uporediš draft sa originalnim planom, nalazima kritičara i proverenim činjenicama.\n\n"
            "VAŽNA PRAVILA KALIBRACIJE (Anti Over-Critique):\n"
            "1. MINOR ISSUES (drift_score 0-2): Stilske varijacije, opisni pridevi, uobičajena znanja za koja "
            "nije nužan naučni citat (osim ako korisnik nije tražio akademski rad), sitne dopune.\n"
            "2. CRITICAL ISSUES (drift_score > 3): Direktne faktičke neistine, kontradikcije, halucinacije, "
            "promašena tema ili opasni saveti.\n"
            "3. Ako je odgovor tačan, direktan i koristan za korisnika, drift_score MORA biti u opsegu 0-2."
        )),
        ("user", (
            "Plan analitičara:\n{plan}\n\n"
            "Nacrt (Draft):\n{draft}\n\n"
            "Kritika (Critic):\n{critic}\n\n"
            "Činjenice iz pretrage (Research):\n{research}"
        ))
    ])
    
    structured_qa = gemini_flash.with_structured_output(QAOutput)
    chain = prompt | structured_qa
    
    result: QAOutput = await chain.ainvoke({
        "plan": str(state.get("analyst_plan", {})),
        "draft": state.get("current_draft", ""),
        "critic": state.get("critic_feedback", ""),
        "research": state.get("research_facts", "")
    })
    
    logger.info(f"QA Drift Score: {result.drift_score}/10 | Kritične greške: {len(result.critical_issues)}")
    return {
        "qa_report": result.model_dump(),
        "drift_score": result.drift_score
    }

async def run_evaluator(state: AgentState) -> Dict[str, Any]:
    """[5] EVALUATOR: Donosi presudu PASS ili REJECT."""
    logger.info("--- [5] EVALUATOR DONOSI ODLUKU ---")
    prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "Ti si vrhovni sudija kvaliteta (Evaluator).\n"
            "PRAVILO ODLUČIVANJA:\n"
            "- Ako nema kritičnih faktičkih grešaka (critical_issues je prazno) i drift_score <= 3, "
            "odluka MORA biti PASS.\n"
            "- Odbij (REJECT) SAMO ukoliko postoje stvarne faktičke neistine, nepopravljive logičke kontradikcije "
            "ili je drift_score >= 4. Nemoj blokirati odgovor zbog sitnih stilskih finesa."
        )),
        ("user", "QA Izveštaj: {qa_report}\nDrift Score: {drift_score}")
    ])
    
    structured_evaluator = gemini_flash_lite.with_structured_output(EvaluatorOutput)
    chain = prompt | structured_evaluator
    
    result: EvaluatorOutput = await chain.ainvoke({
        "qa_report": str(state.get("qa_report", {})),
        "drift_score": state.get("drift_score", 5)
    })
    
    logger.info(f"Presuda Evaluatora: {result.decision} | Obrazloženje: {result.reason}")
    return {
        "evaluation_decision": result.decision,
        "evaluation_reason": result.reason
    }

async def run_security_guard(state: AgentState) -> Dict[str, Any]:
    """[6] SECURITY GUARD: Završna bezbednosna provera (PII, toksičnost, jailbreak)."""
    logger.info("--- [6] SECURITY GUARD VRŠI ZAVRŠNU VERIFIKACIJU ---")
    prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "Ti si bezbednosni filter (SecurityGuard). Proveri da li tekst sadrži osetljive lične podatke (PII), "
            "maliciozne instrukcije, govor mržnje ili nebezbedan sadržaj. Ako je tekst potpuno bezbedan, "
            "vrati ga nepromenjenog od reči do reči. Ako nije, zameni ga bezbednom porukom upozorenja."
        )),
        ("user", "{draft}")
    ])
    
    chain = prompt | gemini_flash_lite
    result = await chain.ainvoke({"draft": state["current_draft"]})
    return {"final_output": result.content}

# -------------------------------------------------------------
# 5. GRAF I USLOVNO RUTIRANJE (LangGraph Workflow)
# -------------------------------------------------------------
def route_evaluator(state: AgentState) -> Literal["generator", "security_guard", "fallback"]:
    """Usmerava tok: ako je PASS ide na Security, ako je REJECT i ima pokušaja vraća na Generator."""
    decision = state.get("evaluation_decision", "REJECT")
    iter_count = state.get("iteration_count", 0)
    
    if decision == "PASS":
        logger.info("Evaluator status: PASS -> Nastavak na Security Guard.")
        return "security_guard"
    
    if iter_count < 2:
        logger.info(f"Evaluator status: REJECT (iteracija {iter_count}/2) -> Vraćanje na Generator radi korekcije.")
        return "generator"
    
    logger.warning("Evaluator status: REJECT -> Dostignut maksimalni broj iteracija (2). Prelazak na Fallback.")
    return "fallback"

def build_kritic_graph():
    """Kompajlira LangGraph multi-agent radni tok."""
    workflow = StateGraph(AgentState)
    
    # Dodavanje čvorova
    workflow.add_node("analyst", run_analyst)
    workflow.add_node("generator", run_generator)
    workflow.add_node("critic", run_critic)
    workflow.add_node("research", run_research)
    workflow.add_node("qa_auditor", run_qa_auditor)
    workflow.add_node("evaluator", run_evaluator)
    workflow.add_node("security_guard", run_security_guard)
    
    # Spajanje sekvence i paralelnih grana
    workflow.add_edge(START, "analyst")
    workflow.add_edge("analyst", "generator")
    
    # Fan-out: Generator istovremeno pokreće Critic i Research (Paralelno)
    workflow.add_edge("generator", "critic")
    workflow.add_edge("generator", "research")
    
    # Fan-in: Spajanje rezultata u QA Auditor
    workflow.add_edge("critic", "qa_auditor")
    workflow.add_edge("research", "qa_auditor")
    
    workflow.add_edge("qa_auditor", "evaluator")
    
    # Uslovna grana iz evaluatora
    workflow.add_conditional_edges(
        "evaluator",
        route_evaluator,
        {
            "generator": "generator",
            "security_guard": "security_guard",
            "fallback": END
        }
    )
    
    workflow.add_edge("security_guard", END)
    return workflow.compile()

# Singleton instanca aplikacije
kritic_app = build_kritic_graph()

# -------------------------------------------------------------
# 6. NOTEBOOKLM SINHRONIZACIJA (/nlm-skill Integracija)
# -------------------------------------------------------------
def sync_to_notebooklm(notebook_id: str, title: str, content: str) -> bool:
    """Šalje verifikovani sadržaj direktno u NotebookLM preko nlm CLI."""
    import subprocess
    try:
        cmd = [
            "nlm", "source", "add", notebook_id,
            "--text", content,
            "--title", title
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        logger.info(f"Uspešno sinhronizovano u NotebookLM [{notebook_id}]: {res.stdout.strip()}")
        return True
    except Exception as e:
        logger.error(f"Greška prilikom sinhronizacije u NotebookLM: {e}")
        return False

# -------------------------------------------------------------
# 7. GLAVNA IZVRŠNA RUTINA (CLI Test Runner)
# -------------------------------------------------------------
async def run_pipeline(prompt_text: str, nlm_notebook_id: Optional[str] = None) -> Dict[str, Any]:
    """Pokreće puni asinhroni tok sa praćenjem događaja u realnom vremenu."""
    initial_state: AgentState = {
        "user_prompt": prompt_text,
        "analyst_plan": {},
        "current_draft": "",
        "critic_feedback": "",
        "research_facts": "",
        "qa_report": {},
        "drift_score": 0,
        "iteration_count": 0,
        "evaluation_decision": "",
        "evaluation_reason": "",
        "final_output": ""
    }
    
    print("\n=======================================================")
    print("🚀 POKRETANJE KRITICAR MULTI-AGENT SISTEMA")
    print("=======================================================")
    print(f"Zahtev: {prompt_text}\n")
    
    final_state = dict(initial_state)
    async for event in kritic_app.astream(initial_state):
        for node_name, state_update in event.items():
            print(f"  ✓ Završen čvor: [ {node_name} ]")
            final_state.update(state_update)
            
    print("\n================ FINALNI REZULTAT =================")
    if final_state.get("evaluation_decision") == "REJECT" and final_state.get("iteration_count", 0) >= 2:
        print("⚠️ FALLBACK SISTEMSKA PORUKA:")
        print("Sistem nije uspeo da postigne drift_score <= 3 nakon maksimalnog broja pokušaja.")
        print(f"Poslednji QA razlog: {final_state.get('evaluation_reason')}")
        output = final_state.get("current_draft", "")
    else:
        output = final_state.get("final_output", "")
        print(output)
    print("====================================================\n")
    
    # Opciono NotebookLM skladištenje
    if nlm_notebook_id:
        print(f"📤 Sinhronizujem u NotebookLM ({nlm_notebook_id})...")
        sync_to_notebooklm(
            notebook_id=nlm_notebook_id,
            title=f"KRITICAR Verified: {prompt_text[:40]}...",
            content=output
        )
        
    return final_state

if __name__ == "__main__":
    test_query = (
        "Objasni ukratko ko je i koje godine konstruisao prvi funkcionalni kvantni procesor, "
        "koliko je kjubita imao i kakav je značaj za kriptografiju."
    )
    if len(sys.argv) > 1:
        test_query = " ".join(sys.argv[1:])
        
    asyncio.run(run_pipeline(test_query))
