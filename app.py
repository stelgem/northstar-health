import datetime as dt
import os
import json
import threading
import uuid

from dash import ALL, MATCH, Dash, Input, Output, State, ctx, dcc, html, no_update

import agents
from agents import CRITERIA_LABELS, LANES, ROOT

JOBS = {}   # scan jobs run in background threads; the page polls them


def initials(name):
    return "".join(word[0] for word in name.split()[:2]).upper() or "?"


def rec_class(rec):
    return {"Prioritize outreach": "rec rec-go", "Watch": "rec rec-watch"}.get(rec, "rec rec-pass")


# ---------------------------------------------------------------- components

def score_bars(card):
    rows = []
    for key, label in CRITERIA_LABELS.items():
        crit = card.get(key, {})
        s = max(1, min(5, int(crit.get("score", 1))))
        rows.append(html.Details([
            html.Summary([html.Span(label, className="crit-label"),
                          html.Span(className="crit-bar", children=html.Span(style={"width": f"{s * 20}%"}, className=f"crit-fill s{s}")),
                          html.Span(f"{s}/5", className="crit-score")]),
            html.P(crit.get("rationale", ""), className="crit-rationale"),
        ], className="crit-row"))
    return html.Div(rows, className="crit-grid")


def candidate_card(s, saved=False, show_save=True):
    card = s.get("scorecard", {})
    srcs = s.get("source_notes") or [{"url": u, "supports": ""} for u in s.get("sources", [])]
    return html.Div([
        html.Div([html.Div(initials(s["name"]), className="logo-mark"), html.H3(s["name"], className="card-title"),
                  html.Div([html.Div(f'{s.get("score", "–")}', className="score-num"), html.Div("/100", className="score-den")], className="score-badge")],
                 className="card-heading"),
        html.Div([html.Span(s.get("recommendation", "Not scored"), className=rec_class(s.get("recommendation"))),
                  html.Span(f'{s["stage"]}{" · " + s["round_amount"] if s.get("round_amount") and s["round_amount"] != "Unknown" else ""}', className="pill"),
                  html.Span(card.get("segment", s.get("category", "")), className="pill pill-seg")], className="tag-row"),
        html.P(f'{card.get("subcategory", s.get("subcategory", ""))} · {s["location"]}', className="muted"),
        html.P(card.get("headline", s.get("description", "")), className="headline"),
        html.P(s.get("description", ""), className="desc"),
        score_bars(card) if card else None,
        html.Div([html.Strong("Portfolio conflict: "), card.get("portfolio_conflict", "Not checked")], className="freshness"),
        html.Div([html.Strong("RED FLAGS  "), "; ".join(card.get("red_flags", [])) or "None noted"], className="unknowns") if card else None,
        html.Div([html.Strong("UNKNOWN / VERIFY  "), "; ".join(card.get("unknowns", [])) or "—"], className="unknowns") if card else None,
        html.Details([html.Summary(f"Verified sources ({len(srcs)})"),
                      html.Ul([html.Li([html.A(src["url"][:70], href=src["url"], target="_blank", className="source-link"),
                                        html.Span(f' — {src.get("supports", "")}', className="muted")]) for src in srcs])], className="sources-box"),
        html.Button("✓ Saved to watchlist" if saved else "Save to watchlist", id={"type": "live-add", "index": s["id"]},
                    className="secondary-button" if saved else "primary-button", disabled=saved) if show_save else None,
    ], className="startup-card candidate")


def run_cost_panel(summary):
    if not summary:
        return None
    t = summary["total"]
    rows = [html.Tr([html.Th(h) for h in ["Agent", "Calls", "Input tokens", "Cached", "Output", "Web searches", "Cost (USD)"]])]
    for agent, a in summary["by_agent"].items():
        rows.append(html.Tr([html.Td(agent.title()), html.Td(a["calls"]), html.Td(f'{a["input_tokens"]:,}'), html.Td(f'{a["cached_tokens"]:,}'),
                             html.Td(f'{a["output_tokens"]:,}'), html.Td(a["web_search_calls"]), html.Td(f'${a["cost_usd"]:.4f}')]))
    rows.append(html.Tr([html.Td(html.Strong("Total")), html.Td(t["calls"]), html.Td(f'{t["input_tokens"]:,}'), html.Td(f'{t["cached_tokens"]:,}'),
                         html.Td(f'{t["output_tokens"]:,}'), html.Td(t["web_search_calls"]), html.Td(html.Strong(f'${t["cost_usd"]:.4f}'))], className="total-row"))
    return html.Div([
        html.Div([html.Span("THIS SCAN", className="dock-label"),
                  html.Span(f'{summary.get("elapsed_s", 0):.0f}s · ${t["cost_usd"]:.4f} · {t["input_tokens"] + t["output_tokens"]:,} tokens', className="cost-headline")], className="cost-top"),
        html.Table(rows, className="usage-table"),
    ], className="cost-panel")


def scan_results_view(result):
    if not result:
        return [], None
    scored = result.get("scored", [])
    kids = [candidate_card(s) for s in scored] or [html.P("No startups passed verification this time. Try other sectors or keywords.", className="muted")]
    extra = []
    if result.get("excluded"):
        extra.append(html.Details([html.Summary(f'Filtered out by the code gate ({len(result["excluded"])})'),
                                   html.Ul([html.Li([html.Strong(e["name"]), f' — {e["reason"]}']) for e in result["excluded"]])], className="filtered-box"))
    if result.get("quarantined"):
        extra.append(html.Details([html.Summary(f'⚠ Quarantined headlines: possible prompt injection ({len(result["quarantined"])})'),
                                   html.Ul([html.Li(q["title"]) for q in result["quarantined"]])], className="filtered-box warn", open=True))
    meta = html.P(f'Run {result["run_id"]} · {len(result.get("leads", []))} headlines → {len(result.get("scout_candidates", []))} startups extracted → '
                  f'{len(scored)} verified US Pre-seed/Seed and scored · finished {result.get("finished", "")}', className="muted run-meta")
    return [html.Div([meta] + extra, className="full-width")] + kids, run_cost_panel(result.get("summary"))


def watchlist_card(s, meta):
    card = s.get("scorecard", {})
    questions = card.get("diligence_questions") or ["What measurable outcome does the product move?", "Who pays, and why do they keep paying?", "What is the regulatory pathway?"]
    return html.Div([
        html.Div([html.Div(initials(s["name"]), className="logo-mark"), html.H3(s["name"], className="card-title"),
                  html.Div([html.Div(f'{s.get("score", "–")}', className="score-num"), html.Div("/100", className="score-den")], className="score-badge")], className="card-heading"),
        html.Div([html.Span(s.get("recommendation", ""), className=rec_class(s.get("recommendation"))), html.Span(s["stage"], className="pill")], className="tag-row"),
        html.P(f'{card.get("segment", s.get("category", ""))} · {s["location"]}', className="muted"),
        html.P(card.get("headline", s.get("description", "")), className="headline"),
        html.Label("Status", className="field-label"),
        dcc.Dropdown(id={"type": "status", "index": s["id"]}, options=["New", "Researching", "Contacted", "Meeting scheduled", "Follow-up", "Passed"],
                     value=meta.get("status", "New"), clearable=False, className="status-dropdown"),
        html.Label("Next action", className="field-label"),
        dcc.Input(id={"type": "next-action", "index": s["id"]}, value=meta.get("next_action", ""), placeholder="e.g., Ask DTL for warm intro", className="text-input"),
        html.H4("Diligence questions from the Thesis Analyst", className="subheading"),
        html.Ul([html.Li(q) for q in questions], className="question-list"),
        html.Label("Your notes (used by the Outreach Writer)", className="field-label"),
        dcc.Textarea(id={"type": "notes", "index": s["id"]}, value=meta.get("notes", ""), placeholder="Why you like it, warm-intro path, what to ask...", className="notes-box"),
        html.Button("Draft outreach email", id={"type": "draft-email", "index": s["id"]}, className="primary-button"),
        dcc.Loading(dcc.Markdown(id={"type": "email-draft", "index": s["id"]}, className="email-draft"), type="dot"),
        html.Button("Remove from watchlist", id={"type": "watch-remove", "index": s["id"]}, className="secondary-button"),
    ], className="startup-card")


# ---------------------------------------------------------------- layout

app = Dash(__name__, title="NorthStar Health")
lane_opts = [{"label": f" {k}", "value": k} for k in LANES]
app.layout = html.Div([
    dcc.Store(id="watchlist", data=[], storage_type="local"),
    dcc.Store(id="watchlist-meta", data={}, storage_type="local"),
    dcc.Store(id="startup-data", data=[], storage_type="local"),
    dcc.Store(id="scan-result", data=None, storage_type="session"),
    dcc.Store(id="scan-job"),
    dcc.Interval(id="scan-poll", interval=1500, disabled=True),
    html.Header([html.Div([html.Div("NORTHSTAR HEALTH", className="eyebrow"), html.H1("Find the signals worth following.")], className="hero-copy"),
                 html.Div("AI sourcing and first-pass screening for the Meng Impact Investment Fund healthcare deal team: US pre-seed and seed startups in women's health, biotech, and evidence-based wellness, scored against our written thesis.", className="hero-tagline")], className="hero"),
    html.Nav([html.Button("Discover", id="discover-nav", className="nav-button active"), html.Button("Watchlist", id="watchlist-nav", className="nav-button")], className="nav-tabs"),
    html.Main([html.Section([
        html.Div([
            html.Div([html.H3("Find thesis-fit startups"),
                      html.P("Scout reads recent funding news → Verifier checks each startup on the web → code keeps only US-domiciled Pre-seed/Seed → Thesis Analyst scores against the Meng healthcare thesis. A scan takes about 2–5 minutes.", className="muted")], className="live-search-copy"),
            dcc.Checklist(id="lanes", options=lane_opts, value=list(LANES), inline=True, className="lane-check"),
            html.Div([dcc.Input(id="keywords", placeholder="Optional focus keywords, e.g. menopause, postpartum, at-home diagnostics", className="live-query", maxLength=120),
                      html.Button("Find startups", id="live-scan", className="primary-button"),
                      html.Button("Load last run", id="load-last", className="secondary-button")], className="live-search-controls"),
            html.Div(id="scan-progress", className="scan-progress"),
            html.Div(id="run-cost"),
            html.Div(id="live-results", className="live-results"),
        ], className="live-search-panel"),
    ], className="panel")], id="discover-view", className="content"),
    html.Main([html.Section([
        html.Div([html.H2("Your watchlist"), html.P("Startups you saved. Add notes, then let the Outreach Writer draft a first email. NorthStar never sends anything.", className="muted"),
                  html.Button("Export watchlist brief", id="export-brief", className="secondary-button"), dcc.Download(id="brief-download")], className="section-heading watchlist-heading"),
        html.Div(id="watchlist-grid", className="startup-grid"),
    ], className="panel")], id="watchlist-view", className="content", style={"display": "none"}),
    html.Button("Ask NorthStar", id="ask-launcher", className="ask-launcher"),
    html.Div([
        html.Div([html.Div([html.Span("NORTHSTAR ASSIST", className="dock-label"), html.Span("Ask about your saved startups", className="dock-helper")], className="dock-heading"),
                  html.Button("×", id="ask-close", className="ask-close")], className="dock-topline"),
        dcc.Textarea(id="question", placeholder="e.g. Which saved company best meets the Wellness evidence bar?", className="question-box", maxLength=600),
        html.Button("Analyze", id="analyze", className="primary-button"),
        dcc.Loading(dcc.Markdown(id="answer", className="answer"), type="dot"),
    ], id="ask-dock", className="ask-dock", style={"display": "none"}),
    html.Footer("NorthStar Health is a research assistant, not an investment decision-maker. Every claim links to its source; verify before acting."),
], className="page")


# ---------------------------------------------------------------- navigation

@app.callback(Output("discover-view", "style"), Output("watchlist-view", "style"), Output("discover-nav", "className"), Output("watchlist-nav", "className"),
              Input("discover-nav", "n_clicks"), Input("watchlist-nav", "n_clicks"), prevent_initial_call=True)
def switch_view(*_):
    if ctx.triggered_id == "watchlist-nav":
        return {"display": "none"}, {"display": "block"}, "nav-button", "nav-button active"
    return {"display": "block"}, {"display": "none"}, "nav-button active", "nav-button"


@app.callback(Output("ask-dock", "style"), Output("ask-launcher", "style"), Input("ask-launcher", "n_clicks"), Input("ask-close", "n_clicks"), prevent_initial_call=True)
def toggle_ask_dock(_, __):
    if ctx.triggered_id == "ask-launcher":
        return {"display": "block"}, {"display": "none"}
    return {"display": "none"}, {"display": "block"}


# ---------------------------------------------------------------- scanning

def _job(job_id, lanes, keywords):
    def progress(msg):
        JOBS[job_id]["steps"].append(msg)
    try:
        JOBS[job_id]["result"] = agents.run_pipeline(lanes, keywords, progress)
        JOBS[job_id]["status"] = "done"
    except Exception as exc:   # surfaced to the user, never a crash
        JOBS[job_id]["status"] = "error"
        JOBS[job_id]["steps"].append(f"Stopped: {exc}")


def progress_view(job):
    steps = job["steps"]
    items = []
    for i, step in enumerate(steps):
        last = i == len(steps) - 1
        icon = "✕" if step.startswith("Stopped") else ("⏳" if last and job["status"] == "running" else "✓")
        items.append(html.Li([html.Span(icon, className="step-icon"), step], className="step"))
    return html.Ul(items, className="steps")


@app.callback(Output("scan-job", "data"), Output("scan-poll", "disabled"), Output("scan-progress", "children"),
              Input("live-scan", "n_clicks"), State("lanes", "value"), State("keywords", "value"), prevent_initial_call=True)
def start_scan(_, lanes, keywords):
    if not lanes:
        return no_update, True, html.P("Pick at least one sector.", className="refresh-error")
    ok, msg = agents.validate_user_text(keywords, "keywords", 120)
    if not ok:
        return no_update, True, html.Div(msg, className="guard-alert")
    if any(j["status"] == "running" for j in JOBS.values()):
        return no_update, True, html.P("A scan is already running. Wait for it to finish.", className="refresh-error")
    job_id = uuid.uuid4().hex[:8]
    JOBS[job_id] = {"status": "running", "steps": ["Starting scan…"], "result": None}
    threading.Thread(target=_job, args=(job_id, lanes, (keywords or "").strip()), daemon=True).start()
    return job_id, False, progress_view(JOBS[job_id])


@app.callback(Output("scan-progress", "children", allow_duplicate=True), Output("scan-poll", "disabled", allow_duplicate=True),
              Output("scan-result", "data"), Input("scan-poll", "n_intervals"), State("scan-job", "data"), prevent_initial_call=True)
def poll_scan(_, job_id):
    job = JOBS.get(job_id)
    if not job:
        return no_update, True, no_update
    if job["status"] == "running":
        return progress_view(job), False, no_update
    return progress_view(job), True, (job["result"] if job["status"] == "done" else no_update)


@app.callback(Output("scan-result", "data", allow_duplicate=True), Output("scan-progress", "children", allow_duplicate=True),
              Input("load-last", "n_clicks"), prevent_initial_call=True)
def load_last(_):
    path = ROOT / "runs" / "latest.json"
    if not path.exists():
        path = ROOT / "data" / "sample_run.json"
    if not path.exists():
        return no_update, html.P("No saved run yet. Click Find startups.", className="muted")
    return json.loads(path.read_text()), html.P(f"Loaded saved run from {path.name} (no tokens spent).", className="muted")


@app.callback(Output("live-results", "children"), Output("run-cost", "children"), Input("scan-result", "data"), Input("watchlist", "data"))
def render_results(result, watchlist):
    kids, cost = scan_results_view(result)
    if result:
        saved = set(watchlist or [])
        kids = kids[:1] + [candidate_card(s, s["id"] in saved) for s in result.get("scored", [])] if result.get("scored") else kids
    return kids, cost


@app.callback(Output("startup-data", "data"), Output("watchlist", "data"), Input({"type": "live-add", "index": ALL}, "n_clicks"),
              State("scan-result", "data"), State("startup-data", "data"), State("watchlist", "data"), prevent_initial_call=True)
def save_candidate(clicks, result, dataset, watchlist):
    if not ctx.triggered_id or not any(clicks):
        return no_update, no_update
    cid = ctx.triggered_id["index"]
    cand = next((x for x in (result or {}).get("scored", []) if x["id"] == cid), None)
    if not cand:
        return no_update, no_update
    data = [x for x in (dataset or []) if x["id"] != cid] + [cand]
    return data, list(dict.fromkeys((watchlist or []) + [cid]))


# ---------------------------------------------------------------- watchlist

@app.callback(Output("watchlist", "data", allow_duplicate=True), Input({"type": "watch-remove", "index": ALL}, "n_clicks"), State("watchlist", "data"), prevent_initial_call=True)
def remove_saved(clicks, watchlist):
    if not ctx.triggered_id or not any(clicks):
        return no_update
    return [x for x in (watchlist or []) if x != ctx.triggered_id["index"]]


@app.callback(Output("watchlist-grid", "children"), Output("watchlist-nav", "children"), Input("watchlist", "data"), State("startup-data", "data"), State("watchlist-meta", "data"))
def render_watchlist(watchlist, dataset, meta):
    saved = [s for s in (dataset or []) if s["id"] in (watchlist or [])]
    label = f"Watchlist ({len(saved)})" if saved else "Watchlist"
    if not saved:
        return [html.P("Your watchlist is empty. Save a startup from Discover.", className="muted")], label
    return [watchlist_card(s, (meta or {}).get(s["id"], {})) for s in sorted(saved, key=lambda x: -x.get("score", 0))], label


@app.callback(Output("watchlist-meta", "data"), Input({"type": "status", "index": ALL}, "value"), Input({"type": "notes", "index": ALL}, "value"),
              Input({"type": "next-action", "index": ALL}, "value"), State({"type": "status", "index": ALL}, "id"), State("watchlist-meta", "data"), prevent_initial_call=True)
def save_meta(statuses, notes, actions, ids, meta):
    meta = dict(meta or {})
    for i, st, nt, ac in zip(ids, statuses, notes, actions):
        meta[i["index"]] = {"status": st or "New", "notes": nt or "", "next_action": ac or ""}
    return meta


@app.callback(Output({"type": "email-draft", "index": MATCH}, "children"), Input({"type": "draft-email", "index": MATCH}, "n_clicks"),
              State({"type": "draft-email", "index": MATCH}, "id"), State("watchlist-meta", "data"), State("startup-data", "data"), prevent_initial_call=True)
def draft_email(_, bid, meta, dataset):
    s = next((x for x in (dataset or []) if x["id"] == bid["index"]), None)
    if not s:
        return "This record is no longer available."
    notes = (meta or {}).get(s["id"], {})
    ok, msg = agents.validate_user_text(notes.get("notes", ""), "notes", 1500)
    if not ok:
        return f"**{msg}**"
    try:
        draft, rec = agents.outreach_agent(s, notes)
        return draft + f"\n\n*Outreach Writer · {rec['input_tokens']:,} in / {rec['output_tokens']:,} out tokens · ${rec['cost_usd']:.4f} · draft only, not sent*"
    except Exception as exc:
        return f"Could not draft the email: {exc}"


@app.callback(Output("brief-download", "data"), Input("export-brief", "n_clicks"), State("watchlist", "data"), State("watchlist-meta", "data"), State("startup-data", "data"), prevent_initial_call=True)
def export_brief(_, watchlist, meta, dataset):
    lines = ["NORTHSTAR HEALTH: WATCHLIST BRIEF", f"Generated {dt.date.today()}", "Human-review research brief; verify all claims before acting.", ""]
    for s in [x for x in (dataset or []) if x["id"] in (watchlist or [])]:
        m, card = (meta or {}).get(s["id"], {}), s.get("scorecard", {})
        lines += [f"## {s['name']}: {s.get('score', '–')}/100, {s.get('recommendation', '')} ({m.get('status', 'New')})",
                  f"{card.get('segment', '')} · {s['stage']} {s.get('round_amount', '')} · {s['location']}", card.get("headline", ""),
                  "Red flags: " + "; ".join(card.get("red_flags", [])), "Diligence questions: " + " | ".join(card.get("diligence_questions", [])),
                  "Sources: " + " ".join(s.get("sources", [])), f"Next action: {m.get('next_action', '')}", f"Notes: {m.get('notes', '')}", ""]
    return dcc.send_string("\n".join(lines), "northstar-watchlist-brief.md")


@app.callback(Output("answer", "children"), Input("analyze", "n_clicks"), State("question", "value"), State("watchlist", "data"), State("startup-data", "data"), prevent_initial_call=True)
def ask(_, question, watchlist, dataset):
    ok, msg = agents.validate_user_text(question, "your question", 600)
    if not ok or not (question or "").strip():
        return f"**{msg or 'Please type a question.'}**"
    records = [{k: v for k, v in s.items() if k != "news"} for s in (dataset or []) if s["id"] in (watchlist or [])]
    if not records:
        return "Save at least one startup to your watchlist first."
    try:
        answer, rec = agents.assistant_agent(question.strip(), records)
        return answer + f"\n\n*{rec['input_tokens']:,} in ({rec['cached_tokens']:,} cached) / {rec['output_tokens']:,} out · ${rec['cost_usd']:.4f}*"
    except Exception as exc:
        return f"Could not answer: {exc}"


if __name__ == "__main__":
    app.run(debug=False, port=int(os.getenv("PORT", "8050")))
