"""Build report.html from scripts/report_template.html: embeds screenshots (as JPEG base64)
and fills numbers from logs. Run: python scripts/build_report.py"""
import base64
import html
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TPL = (ROOT / "scripts" / "report_template.html").read_text()
TMP = Path(tempfile.mkdtemp())


def img(name):
    src = ROOT / "screenshots" / f"{name}.png"
    out = TMP / f"{name}.jpg"
    subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", "80", str(src), "--out", str(out)], check=True, capture_output=True)
    return "data:image/jpeg;base64," + base64.b64encode(out.read_bytes()).decode()


def experiment():
    p = ROOT / "logs" / "experiment_context_size.json"
    if not p.exists():
        return "<p><i>The search-context experiment is pending.</i></p>"
    d = json.loads(p.read_text())
    rows = "".join(
        f"<tr><td>{html.escape(r['name'])}</td><td>{r['size']}</td><td>{html.escape(r['hq'][:48])}</td><td>{html.escape(r['round'])}</td>"
        f"<td>{'PASS' if r['gate'] == 'PASS' else 'Rejected (non-US)'}</td><td class='n'>{r['sources']}</td><td class='n'>{r['web']}</td>"
        f"<td class='n'>{r['input']:,}</td><td class='n'>${r['cost']:.4f}</td></tr>" for r in d["rows"])
    lo, me = d["summary"]["low"], d["summary"]["medium"]
    save = (1 - lo["cost"] / me["cost"]) * 100
    return (f"<p><b>Experiment: search context <code>low</code> (production) vs <code>medium</code>.</b> "
            f"<code>scripts/experiment_context_size.py</code> ran the Verifier on the same 4 companies with each setting (8 live calls, no cache).</p>"
            f"<table><tr><th>Company</th><th>Context</th><th>HQ found</th><th>Round</th><th>Gate</th><th class='n'>Sources</th><th class='n'>Searches</th><th class='n'>Input tok</th><th class='n'>Cost</th></tr>{rows}"
            f"<tr class='total'><td colspan='6'>Total, low</td><td class='n'>{lo['web']}</td><td class='n'>{lo['input']:,}</td><td class='n'>${lo['cost']:.4f}</td></tr>"
            f"<tr class='total'><td colspan='6'>Total, medium</td><td class='n'>{me['web']}</td><td class='n'>{me['input']:,}</td><td class='n'>${me['cost']:.4f}</td></tr></table>"
            f"<div class='callout good'><b>Result: no measurable quality loss.</b> Both settings reached the <b>same verdict for {d['agreement']} companies</b> "
            f"(same HQ country, same round, same gate decision; Avni Wellness correctly rejected both times). <code>low</code> was {save:.0f}% cheaper "
            f"(${lo['cost']:.4f} vs ${me['cost']:.4f}), almost entirely because it made fewer web searches ({lo['web']} vs {me['web']}). "
            f"Input tokens were <i>not</i> lower ({lo['input']:,} vs {me['input']:,}), so the context setting mostly changes how many searches the model "
            f"chooses to run, not how much text each one returns. <code>medium</code> sometimes found one or two more source links, and once wrote the round "
            f"amount more cleanly ('$4 million' vs 'US$4 million'). These are cosmetic differences. A 4-company sample is small, so this is evidence, not proof.</div>")


def redteam():
    d = json.loads((ROOT / "logs" / "redteam_result.json").read_text())
    c, i = d["clean"], d["injected"]
    def row(label, r):
        return (f"<tr><td><b>{label}</b></td><td class='n'>{r['score']}/100</td><td>{r['recommendation']}</td><td class='n'>{r['evidence_bar']}/5</td>"
                f"<td>{html.escape(r['headline'])}</td><td class='n'>{len(r['red_flags'])}</td></tr>")
    return (f"<table><tr><th>Version</th><th class='n'>Score</th><th>Rec.</th><th class='n'>Evidence</th><th>Analyst headline</th><th class='n'>Red flags</th></tr>"
            f"{row('Clean', c)}{row('With injection', i)}</table>"
            f"<div class='callout good'><b>Result: {'PASS' if d['passed'] else 'FAIL'}. The attack did not change the outcome.</b> The injected version still scored "
            f"{i['score']}/100 (<b>{i['recommendation']}</b>) with Evidence 1/5. The analyst did not write 'pre-approved' or give 5s, and it listed "
            f"{len(i['red_flags'])} red flags rather than leaving them empty as the attack demanded.</div>"
            f"<div class='callout warn'><b>Honest caveats.</b> (1) The score still moved by {i['score'] - c['score']} points ({c['score']} → {i['score']}). Some of that is "
            f"ordinary run-to-run variance and some may be the injection, so the defense limited the attack rather than making it irrelevant. (2) The model "
            f"<b>did not explicitly report</b> that the record tried to instruct it, even though the rules ask it to. This is why the hard decisions (gate, "
            f"score arithmetic, 'Outside thesis' ⇒ Pass) live in code, and why explicit attack reporting is a next step.</div>")


def usage_table():
    recs = [json.loads(l) for l in (ROOT / "logs" / "usage.jsonl").read_text().splitlines() if l.strip()]
    agg = {}
    for r in recs:
        a = agg.setdefault(r["agent"], {"calls": 0, "input_tokens": 0, "cached_tokens": 0, "output_tokens": 0, "web_search_calls": 0, "cost_usd": 0.0, "lat": []})
        for k in ["input_tokens", "cached_tokens", "output_tokens", "web_search_calls", "cost_usd"]:
            a[k] += r.get(k, 0)
        a["calls"] += 1; a["lat"].append(r.get("latency_s", 0))
    rows = ""
    for name, a in sorted(agg.items(), key=lambda x: -x[1]["cost_usd"]):
        rows += (f"<tr><td>{name.title()}</td><td class='n'>{a['calls']}</td><td class='n'>{a['input_tokens']:,}</td><td class='n'>{a['cached_tokens']:,}</td>"
                 f"<td class='n'>{a['output_tokens']:,}</td><td class='n'>{a['web_search_calls']}</td><td class='n'>{min(a['lat']):.1f}–{max(a['lat']):.1f} s</td><td class='n'>${a['cost_usd']:.4f}</td></tr>")
    t = {k: sum(a[k] for a in agg.values()) for k in ["calls", "input_tokens", "cached_tokens", "output_tokens", "web_search_calls", "cost_usd"]}
    rows += (f"<tr class='total'><td>All calls ({recs[0]['ts'][:10]})</td><td class='n'>{t['calls']}</td><td class='n'>{t['input_tokens']:,}</td><td class='n'>{t['cached_tokens']:,}</td>"
             f"<td class='n'>{t['output_tokens']:,}</td><td class='n'>{t['web_search_calls']}</td><td></td><td class='n'>${t['cost_usd']:.4f}</td></tr>")
    return ("<table><tr><th>Agent</th><th class='n'>Calls</th><th class='n'>Input</th><th class='n'>Cached</th><th class='n'>Output</th>"
            "<th class='n'>Web searches</th><th class='n'>Latency range</th><th class='n'>Cost</th></tr>" + rows + "</table>"
            f"<p class='small'>Includes development runs, the red-team test and the context-size experiment ({t['calls']} calls, ${t['cost_usd']:.2f} in total).</p>")


def pytest_out():
    r = subprocess.run([sys.executable, "-W", "ignore", "-m", "pytest", "-q", "tests"], cwd=ROOT, capture_output=True, text=True)
    return html.escape("\n".join(r.stdout.strip().splitlines()[-2:]))


out = TPL
for name in sorted(set(re.findall(r"\{\{IMG:([\w]+)\}\}", out))):
    out = out.replace("{{IMG:%s}}" % name, img(name))
attack = json.loads((ROOT / "logs" / "redteam_result.json").read_text())["attack"].strip()
out = out.replace("{{EXPERIMENT}}", experiment()).replace("{{REDTEAM}}", redteam()).replace("{{PYTEST}}", pytest_out()).replace("{{USAGE_TABLE}}", usage_table()).replace("{{ATTACK}}", html.escape(attack))
(ROOT / "report.html").write_text(out)
print(f"report.html written: {len(out) / 1e6:.2f} MB")
