#!/usr/bin/env python3
import sys
import time
from src.pyodide_optimizer.pipeline import PyodideSmallModelPipeline

TEST_INDEX = [
    {"id": "health_check", "text": "System operational check passed successfully."}
]

def run_health_check():
    start = time.perf_counter()
    pipeline = PyodideSmallModelPipeline(TEST_INDEX)
    res = pipeline.run("operational check", top_k=1)
    duration_ms = (time.perf_counter() - start) * 1000
    
    assert "passed" in res["answer"], "Health check failed!"
    print(f"✅ System Health Check PASSED in {duration_ms:.2f} ms")

if __name__ == "__main__":
    run_health_check()
