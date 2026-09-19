"""
Root conftest.py — ensures the project root is on sys.path so that
`from src.xxx import yyy` works for all pytest tests without needing
`sys.path.append(os.getcwd())` inside every test file.
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))
