"""
LLM Sharp Bettor Qualitative Reasoning Agent.
Queries local Ollama daemon (:11434) or local AnythingLLM runtime (:39321).
Provides disciplined contextual match analysis without external internet dependencies.
"""

import json
import logging
import requests
from typing import Dict, Any, Optional
from unified_betting_core.config import (
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    ANYTHING_LLM_URL,
    ANYTHING_LLM_KEY
)

logger = logging.getLogger("SharpBet.LLMSharpAgent")

class LLMSharpAgent:
    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or OLLAMA_MODEL

    def analyze_fixture(self, match_data: Dict[str, Any], edge_info: Dict[str, Any]) -> str:
        """
        Sends fixture details and mathematical model edge to local LLM for sharp confirmation.
        """
        prompt = f"""
Ti si profesionalni kvantitativni i sharp fudbalski analitičar.
Analiziraj sledeći meč i potvrdi da li identifikovana prednost (+EV) ima smisla u realnim uslovima:

Meč: {match_data.get('home_team')} vs {match_data.get('away_team')}
Liga: {match_data.get('league', 'EPL')}
xG: Domaćin {match_data.get('home_xg')}, Gost {match_data.get('away_xg')}
Tržišne Kvote: 1: {match_data.get('home_odds')}, X: {match_data.get('draw_odds')}, 2: {match_data.get('away_odds')}

Matematički Model:
- Preporučeni Tip: {edge_info.get('bet_on', 'None')}
- Verovatnoća: {edge_info.get('prob', 0)*100:.1f}%
- Izračunata Prednost (Edge): +{edge_info.get('edge', 0)*100:.1f}%
- Predloženi Kelly Ulog: €{edge_info.get('stake', 0):.2f}

Zadatak:
1. U jednoj do dve rečenice daj stručni taktički komentar (stil igre, tempo, zavisnost od forme).
2. Da li postoji skriveni rizik (rotacije, povrede, stilski mismatch)?
3. Konačna preporuka: [POTVRĐENO / OPREZ / PRESKOČI]
"""
        # Try local Ollama first
        ollama_res = self._query_ollama(prompt)
        if ollama_res:
            return ollama_res

        # Fallback to local AnythingLLM
        anything_res = self._query_anything_llm(prompt)
        if anything_res:
            return anything_res

        # Algorithmic synthetic commentary if local daemons are offline
        return self._algorithmic_commentary(match_data, edge_info)

    def _query_ollama(self, prompt: str) -> Optional[str]:
        try:
            url = f"{OLLAMA_BASE_URL}/api/generate"
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "num_predict": 180
                }
            }
            res = requests.post(url, json=payload, timeout=4)
            if res.status_code == 200:
                data = res.json()
                response_text = data.get("response", "").strip()
                if response_text:
                    logger.info("Generated sharp reasoning via local Ollama.")
                    return response_text
        except Exception as e:
            logger.debug(f"Ollama local query bypassed: {e}")
        return None

    def _query_anything_llm(self, prompt: str) -> Optional[str]:
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {ANYTHING_LLM_KEY}"
            }
            payload = {
                "model": "mistral",
                "messages": [
                    {"role": "system", "content": "You are a professional quantitative sports bettor."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 150
            }
            res = requests.post(ANYTHING_LLM_URL, json=payload, headers=headers, timeout=4)
            if res.status_code == 200:
                data = res.json()
                choices = data.get("choices", [])
                if choices:
                    return choices[0].get("message", {}).get("content", "").strip()
        except Exception as e:
            logger.debug(f"AnythingLLM local query bypassed: {e}")
        return None

    def _algorithmic_commentary(self, match_data: Dict[str, Any], edge_info: Dict[str, Any]) -> str:
        edge = edge_info.get("edge", 0) * 100
        pick = edge_info.get("bet_on", "N/A").upper()
        h_team = match_data.get("home_team")
        a_team = match_data.get("away_team")

        if edge > 10.0:
            return (f"[POTVRĐENO]: Značajan diskorak u kvoti za {pick}. xG diferencijal favorizuje "
                    f"ovu opciju sa izraženom matematičkom vrednošću (+{edge:.1f}% edge).")
        elif edge >= 5.0:
            return (f"[POTVRĐENO]: Umereni +EV (+{edge:.1f}%) na meču {h_team} vs {a_team}. "
                    f"Preporučuje se striktno poštovanje Half-Kelly uloga bez preteranog izlaganja.")
        else:
            return f"[OPREZ]: Margina je ispod standardnog praga sigurnosti. Preporučuje se posmatranje uživo."
