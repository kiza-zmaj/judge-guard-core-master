#!/usr/bin/env python3
"""
Stream Launcher proxy in research/kaggle_s6e9/.
Executes start_stream.py from project root.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

if __name__ == "__main__":
    from start_stream import main
    main()
