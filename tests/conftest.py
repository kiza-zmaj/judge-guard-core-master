"""
Pytest configuration for JudgeGuard test suite.
Provides safe mock environment variables so tests run safely without hardcoded repository secrets.
"""
import os

# Set dummy environment variables for tests if not provided
os.environ.setdefault("GEMINI_API_KEY", "test-mock-gemini-key")
os.environ.setdefault("OLLAMA_API_KEY", "test-mock-ollama-key")
os.environ.setdefault("ODDS_API_KEY", "test-mock-odds-key")
