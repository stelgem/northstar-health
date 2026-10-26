"""Cost-cutting experiment: Verifier with web_search context 'low' (production) vs 'medium'.
Same 4 startups, no cache. Records tokens, cost and whether the verdict changed."""
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import agents  # noqa: E402

COS = [("Collective X Health", "Collective X Health raises $3.2M pre-seed to close women's health data gap"),
       ("Allswell", "Allswell raises $7M seed for LGBTQ+ virtual behavioral health"),
       ("The American Baby Company", "The American Baby Company raises seed round"),
       ("Avni Wellness", "Avni Wellness raises funding for women's wellness")]

def run(args):
    (name, headline), size = args
    v, rec = agents.verifier_agent({"name": name, "headlines": [headline]}, f"exp-{size}", context_size=size)
    vd = v.model_dump()
    return {"name": name, "size": size, "us": vd["us_domiciled"], "hq": vd["headquarters"], "round": vd["latest_round"],
            "amount": vd["round_amount"], "sources": len(vd["sources"]), "gate": agents.gate(dict(vd)) or "PASS",
            "input": rec["input_tokens"], "output": rec["output_tokens"], "web": rec["web_search_calls"], "cost": rec["cost_usd"], "latency": rec["latency_s"]}

if __name__ == "__main__":
    jobs = [(c, s) for c in COS for s in ("low", "medium")]
    with ThreadPoolExecutor(8) as ex:
        rows = list(ex.map(run, jobs))
    for r in rows:
        print(r)
    summ = {s: {k: round(sum(r[k] for r in rows if r["size"] == s), 4) for k in ["input", "output", "web", "cost"]} for s in ("low", "medium")}
    agree = sum(1 for c, _ in COS if len({(r["gate"] == "PASS", r["round"]) for r in rows if r["name"] == c}) == 1)
    print(json.dumps(summ, indent=1), f"verdict agreement {agree}/{len(COS)}")
    Path("logs/experiment_context_size.json").write_text(json.dumps({"rows": rows, "summary": summ, "agreement": f"{agree}/{len(COS)}"}, indent=1))
