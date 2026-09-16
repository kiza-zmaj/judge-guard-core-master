"""
Central Settings & Configuration for SharpBet Core.
"""

import os
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
MODELS_STORE_DIR = BASE_DIR / "models_store"

# LLM & Local Reasoning Endpoints
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral:7b")
ANYTHING_LLM_URL = os.getenv("ANYTHING_LLM_URL", "http://localhost:39321/api/v1/openai")
ANYTHING_LLM_KEY = os.getenv("ANYTHING_LLM_KEY", "brx-WK1HN05-5R6M3VJ-N47XYR1-7G81ADB")

# Bookmaker & Odds Data
ODDS_API_KEY = os.getenv("ODDS_API_KEY", "49b9aea9c90630dd82c02f1b87f25c86")
ODDS_API_URL = f"https://api.the-odds-api.com/v4/sports/soccer_epl/odds?regions=eu&markets=h2h&apiKey={ODDS_API_KEY}"

# Telegram Alerts
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "7969018449:AAEag8E8J_cK9d_2Lh54b8b6v7r5q6_dummy")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "512345678")

# Risk & Decision Thresholds
MIN_EDGE = float(os.getenv("MIN_EDGE", "0.05"))         # 5% minimum expected value
KELLY_FRACTION = float(os.getenv("KELLY_FRACTION", "0.5")) # Half-Kelly for capital preservation
MAX_BANKROLL_PCT = float(os.getenv("MAX_BANKROLL_PCT", "0.10")) # Max 10% on any single bet
DEFAULT_BANKROLL = float(os.getenv("DEFAULT_BANKROLL", "1000.0"))

# Default League & Target Season
DEFAULT_LEAGUE = "EPL"
DEFAULT_SEASON = 2024
