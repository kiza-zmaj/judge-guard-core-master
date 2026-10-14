#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KRITICAR Multi-Agent Orchestration Engine (STRICT MODE: gemini-3.5-flash-lite ONLY, NO FALLBACKS)

Pravila:
  1. Google modeli: ISKLJUČIVO 'gemini-3.5-flash-lite' za sve Google agente. Nijedan drugi model.
  2. NEMA FALLBACKA: Ako bilo koji čvor, model ili servis baci grešku, izvršavanje se ODMAH PREKIDA.
  3. Ako verifikacija ne prođe (REJECT nakon maksimalnog broja pokušaja), sesija se NE ZAVRŠAVA uspešno,
     već se podiže kritični izuzetak (RuntimeError).
"""

import os
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
# 0. RESOLUCIJA API KLJUČEVA I KONFIGURACIJE (Strogo Bez Hardkodovanja)
# -------------------------------------------------------------
def get_gemini_api_key() -> str:
    """Preuzima validan Gemini API ključ iz .env ili okruženja."""
    keys = os.getenv("GEMINI_API_KEYS", "")
    if keys:
        first_key = keys.split(",")[0].strip()
        if first_key:
            return first_key
    key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not key:
        raise ValueError("KRITIČNA GREŠKA: Nije pronađen validan API ključ u .env ili okruženju!")
    return key

resolved_key = get_gemini_api_key()
os.environ["GOOGLE_API_KEY"] = resolved_key

OLLAMA_BASE_URL = os.getenv("OPENAI_API_BASE", "http://localhost:11434/v1")
OPENAI_KEY = os.getenv("OPENAI_API_KEY", "ollama")

def extract_text(content: Any) -> str:
    """Pouzdan ekstraktor teksta bez obzira da li model vrati string ili listu blokova."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                parts.append(item.get("text", ""))
            elif hasattr(item, "text"):
                parts.append(str(item.text))
            else:
                parts.append(str(item))
        return "".join(parts)
    return str(content)

# -------------------------------------------------------------
# 1. PYDANTIC STRUKTUIRANI IZLAZI
# -------------------------------------------------------------
class AnalystOutput(BaseModel):
    intent: str = Field(
        description="Glavna namera korisnika prepoznata iz prompta."
    )
    key_entities: List[str] = Field(
        default_factory=list,
        description="Ključni entiteti i koncepti pomenuti u zahtevu."
    )
    subtasks: List[str] = Field(
        default_factory=list,
        description="Logički koraci koje Generator mora pokriti."
    )
    success_criteria: List[str] = Field(
        default_factory=list,
        description="Strogi uslovi koje finalni odgovor mora zadovoljiti."
    )

class QAOutput(BaseModel):
    alignment_summary: str = Field(
        description="Sažetak usklađenosti drafta sa planom i činjenicama iz pretrage."
    )
    minor_issues: List[str] = Field(
        default_factory=list,
        description="Manje stilske finesi koje ne utiču na faktičku tačnost."
    )
    critical_issues: List[str] = Field(
        default_factory=list,
        description="Faktičke neistine, kontradikcije ili halucinacije."
    )
    drift_score: int = Field(
        ge=0, le=10,
        description="Ocena odstupanja od 0 do 10 (0=savršeno, 10=potpuna neistina)."
    )

class EvaluatorOutput(BaseModel):
    decision: Literal["PASS", "REJECT"] = Field(
        description="Presuda: PASS ili REJECT."
    )
    reason: str = Field(
        description="Obrazloženje odluke."
    )

# -------------------------------------------------------------
# 2. DEFINICIJA STANJA APLIKACIJE
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
# 3. ISKLJUČIVO gemini-3.5-flash-lite I GEMMA (NEMA FALLBACK-A)
# -------------------------------------------------------------
# Google model: ISKLJUČIVO gemini-3.5-flash-lite za sve zadatke!
EXACT_GOOGLE_MODEL = "gemini-3.5-flash-lite"

gemini_core = ChatGoogleGenerativeAI(
    model=EXACT_GOOGLE_MODEL
)

gemini_search = ChatGoogleGenerativeAI(
    model=EXACT_GOOGLE_MODEL,
    model_kwargs={"tools": [{"google_search": {}}]}
)

# Gemma modeli na lokalnom Ollama endpoint-u - BEZ FALLBACK-A
gemma_generator = ChatOpenAI(
    model="gemma4:31b-cloud",
    api_key=OPENAI_KEY,
    base_url=OLLAMA_BASE_URL,
    temperature=0.7,
    request_timeout=60.0
)

gemma_critic = ChatOpenAI(
    model="gemma4:31b-cloud",
    api_key=OPENAI_KEY,
    base_url=OLLAMA_BASE_URL,
    temperature=0.2,
    request_timeout=60.0
)

# -------------------------------------------------------------
# 4. KREIRANJE AGENT ČVOROVA (BEZ FALLBACKA - FAIL HARD & FAST)
# -------------------------------------------------------------
async def run_analyst(state: AgentState) -> Dict[str, Any]:
    """[1] ANALYST (gemini-3.5-flash-lite)"""
    logger.info(f"--- [1] ANALYST ({EXACT_GOOGLE_MODEL}) ZAPOČINJE RAD ---")
    prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "Ti si Lead Systems Analyst. Rastavi korisnički zahtev na korake, ključne entitete i "
            "kriterijume uspeha. Odgovori strogo prateći zadatu JSON šemu."
        )),
        ("user", "{user_prompt}")
    ])
    structured_analyst = gemini_core.with_structured_output(AnalystOutput)
    chain = prompt | structured_analyst
    
    result: AnalystOutput = await chain.ainvoke({"user_prompt": state["user_prompt"]})
    return {
        "analyst_plan": result.model_dump(),
        "iteration_count": 0
    }

async def run_generator(state: AgentState) -> Dict[str, Any]:
    """[2] GENERATOR (Gemma 4 31B) - Nema fallback-a."""
    iteration = state.get("iteration_count", 0) + 1
    logger.info(f"--- [2] GENERATOR (gemma4:31b-cloud) ZAPOČINJE RAD (Iteracija {iteration}) ---")
    
    plan_str = str(state.get("analyst_plan", {}))
    
    if iteration == 1:
        system_prompt = (
            "Ti si Senior Technical Writer. Na osnovu plana i korisničkog zahteva, "
            "napiši jasan, detaljan i precizan odgovor na jeziku na kom je postavljen upit."
        )
        user_content = f"Plan: {plan_str}\n\nZahtev: {state['user_prompt']}"
    else:
        system_prompt = (
            "Ti si Senior Technical Writer. Tvoj prethodni nacrt je odbijen sa primedbama. "
            "Ispravi SVE navedene greške i uvaži primedbe kritičara i dokazane činjenice."
        )
        qa_data = state.get("qa_report", {})
        critical = qa_data.get("critical_issues", []) if isinstance(qa_data, dict) else []
        user_content = (
            f"Korisnički zahtev: {state['user_prompt']}\n\n"
            f"Prethodni draft:\n{state.get('current_draft', '')}\n\n"
            f"Kritika:\n{state.get('critic_feedback', '')}\n\n"
            f"Proverene činjenice:\n{state.get('research_facts', '')}\n\n"
            f"Kritični nedostaci: {critical}"
        )
        
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", "{user_content}")
    ])
    
    # Direktno pozivanje BEZ try/except fallback-a. Ako padne, neka padne!
    chain = prompt | gemma_generator
    result = await chain.ainvoke({"user_content": user_content})
    draft_content = extract_text(result.content)
        
    return {
        "current_draft": draft_content,
        "iteration_count": iteration
    }

async def run_critic(state: AgentState) -> Dict[str, Any]:
    """[3a] CRITIC (Gemma 4 31B) - Nema fallback-a."""
    logger.info("--- [3a] CRITIC (gemma4:31b-cloud) ANALIZIRA DRAFT (PARALELNO) ---")
    prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "Ti si Advokat đavola i Senior Peer Reviewer. Pronađi sve logičke rupe, neproverene pretpostavke "
            "i pristrasnosti u draftu. Budi direktan i precizan."
        )),
        ("user", "Draft za analizu:\n{draft}")
    ])
    
    # Direktno pozivanje BEZ fallback-a
    chain = prompt | gemma_critic
    result = await chain.ainvoke({"draft": state["current_draft"]})
    feedback = extract_text(result.content)
        
    return {"critic_feedback": feedback}

async def run_research(state: AgentState) -> Dict[str, Any]:
    """[3b] RESEARCH (gemini-3.5-flash-lite + Google Search) - Nema fallback-a."""
    logger.info(f"--- [3b] RESEARCH ({EXACT_GOOGLE_MODEL} + Google Search) VERIFIKUJE ČINJENICE (PARALELNO) ---")
    prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "Ti si Fact-Checker. Koristi Google Search alat da proveriš tačnost ključnih tvrdnji iz teksta. "
            "Sumiraj samo dokazane činjenice sa referencama."
        )),
        ("user", "Tekst za proveru činjenica:\n{draft}")
    ])
    
    # Direktno pozivanje BEZ fallback-a
    chain = prompt | gemini_search
    result = await chain.ainvoke({"draft": state["current_draft"]})
    facts = extract_text(result.content)
        
    return {"research_facts": facts}

async def run_qa_auditor(state: AgentState) -> Dict[str, Any]:
    """[4] QA AUDITOR (gemini-3.5-flash-lite)"""
    logger.info(f"--- [4] QA AUDITOR ({EXACT_GOOGLE_MODEL}) OCENJUJE MATRICU ---")
    prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "Ti si Glavni QA Auditor za AI sisteme.\n"
            "Uporedi draft sa planom, kritikama i proverenim činjenicama.\n"
            "- MINOR ISSUES (drift_score 0-2): Stilske finese i opštepoznate činjenice.\n"
            "- CRITICAL ISSUES (drift_score > 3): Faktičke neistine, kontradikcije, halucinacije.\n"
            "Ako je odgovor tačan i odgovara na zahtev, drift_score je 0-2."
        )),
        ("user", (
            "Plan analitičara:\n{plan}\n\n"
            "Nacrt (Draft):\n{draft}\n\n"
            "Kritika (Critic):\n{critic}\n\n"
            "Činjenice iz pretrage (Research):\n{research}"
        ))
    ])
    
    structured_qa = gemini_core.with_structured_output(QAOutput)
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
    """[5] EVALUATOR (gemini-3.5-flash-lite)"""
    logger.info(f"--- [5] EVALUATOR ({EXACT_GOOGLE_MODEL}) DONOSI ODLUKU ---")
    prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "Ti si Vrhovni Sudija (Evaluator).\n"
            "- Ako nema kritičnih grešaka i drift_score <= 3, donesi PASS.\n"
            "- U suprotnom, ako postoje faktičke greške ili je drift_score > 3, donesi REJECT."
        )),
        ("user", "QA Izveštaj: {qa_report}\nDrift Score: {drift_score}")
    ])
    
    structured_evaluator = gemini_core.with_structured_output(EvaluatorOutput)
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
    """[6] SECURITY GUARD (gemini-3.5-flash-lite)"""
    logger.info(f"--- [6] SECURITY GUARD ({EXACT_GOOGLE_MODEL}) PROVERA BEZBEDNOSTI ---")
    prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "Ti si bezbednosni filter (SecurityGuard). Proveri da li tekst sadrži PII podatke, "
            "govor mržnje ili opasne instrukcije. Ako je potpuno bezbedan, vrati ga nepromenjenog."
        )),
        ("user", "{draft}")
    ])
    
    chain = prompt | gemini_core
    result = await chain.ainvoke({"draft": state["current_draft"]})
    return {"final_output": extract_text(result.content)}

# -------------------------------------------------------------
# 5. RUTIRANJE I FORMIRANJE GRAFA (NEMA FALLBACK-A)
# -------------------------------------------------------------
def route_evaluator(state: AgentState) -> Literal["generator", "security_guard"]:
    """
    Ruter: Ako je PASS ide na Security Guard.
    Ako je REJECT i iteracija < 2, vraća na Generator.
    AKO JE REJECT I DOSTIGNUT LIMIT: NEMA FALLBACK-A -> Prekida se cela sesija sa izuzetkom!
    """
    decision = state.get("evaluation_decision", "REJECT")
    iter_count = state.get("iteration_count", 0)
    
    if decision == "PASS":
        return "security_guard"
    
    if iter_count < 2:
        logger.warning(f"Evaluator REJECT (iteracija {iter_count}/2) -> Vraćanje na Generator.")
        return "generator"
    
    # NEMA FALLBACKA - SISTEM MORA DA PREKINE IZVRŠAVANJE
    reason = state.get("evaluation_reason", "Nepoznat razlog")
    err_msg = (
        f"KRITIČNA GREŠKA: Verifikacija NIJE prošla nakon {iter_count} iteracije!\n"
        f"Razlog odbijanja od strane Evaluatora: {reason}\n"
        f"Zabranjen fallback: Celokupna sesija je OBUSTAVLJENA."
    )
    logger.error(err_msg)
    raise RuntimeError(err_msg)

def build_kritic_graph():
    """Kompajlira LangGraph bez ijedne fallback grane."""
    workflow = StateGraph(AgentState)
    
    workflow.add_node("analyst", run_analyst)
    workflow.add_node("generator", run_generator)
    workflow.add_node("critic", run_critic)
    workflow.add_node("research", run_research)
    workflow.add_node("qa_auditor", run_qa_auditor)
    workflow.add_node("evaluator", run_evaluator)
    workflow.add_node("security_guard", run_security_guard)
    
    workflow.add_edge(START, "analyst")
    workflow.add_edge("analyst", "generator")
    
    # Paralelni fan-out
    workflow.add_edge("generator", "critic")
    workflow.add_edge("generator", "research")
    
    # Fan-in u QA Auditor
    workflow.add_edge("critic", "qa_auditor")
    workflow.add_edge("research", "qa_auditor")
    
    workflow.add_edge("qa_auditor", "evaluator")
    
    # Uslovna grana: SAMO generator ili security_guard. Nema fallback grane.
    workflow.add_conditional_edges(
        "evaluator",
        route_evaluator,
        {
            "generator": "generator",
            "security_guard": "security_guard"
        }
    )
    
    workflow.add_edge("security_guard", END)
    return workflow.compile()

kritic_app = build_kritic_graph()

# -------------------------------------------------------------
# 6. GLAVNI IZVRŠNI TOK
# -------------------------------------------------------------
async def run_pipeline(prompt_text: str) -> Dict[str, Any]:
    """Pokreće striktni asinhroni tok sa gemini-3.5-flash-lite bez fallback-a."""
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
    print("🚀 POKRETANJE KRITICAR (STRICT: gemini-3.5-flash-lite, NO FALLBACK)")
    print("=======================================================")
    print(f"Zahtev: {prompt_text}\n")
    
    final_state = dict(initial_state)
    async for event in kritic_app.astream(initial_state):
        for node_name, state_update in event.items():
            print(f"  ✓ Završen čvor: [ {node_name} ]")
            final_state.update(state_update)
            
    print("\n================ FINALNI REZULTAT =================")
    print(final_state.get("final_output", ""))
    print("====================================================\n")
    return final_state

if __name__ == "__main__":
    test_query = (
        "Objasni ukratko ko je i koje godine konstruisao prvi funkcionalni kvantni procesor, "
        "koliko je kjubita imao i kakav je značaj za kriptografiju."
    )
    if len(sys.argv) > 1:
        test_query = " ".join(sys.argv[1:])
        
    asyncio.run(run_pipeline(test_query))
