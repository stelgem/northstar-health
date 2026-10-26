"""Command-line scan: python run_scan.py  (same pipeline the website runs)."""
import json, sys
from agents import LANES, run_pipeline

if __name__ == "__main__":
    lanes = sys.argv[1:] or list(LANES)
    result = run_pipeline(lanes, progress=lambda m: print("·", m, flush=True))
    for s in result["scored"]:
        print(f"{s['score']:>3}/100  {s['recommendation']:<20} {s['name']} ({s['stage']}, {s['location']})")
    for e in result["excluded"]:
        print(f"   filtered: {e['name']}: {e['reason']}")
    print(json.dumps(result["summary"], indent=1))
