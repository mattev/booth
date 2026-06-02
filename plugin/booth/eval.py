"""The Booth eval harness — three wins in one run:

  1. Compare models (Haiku vs Sonnet): quality, latency, and estimated cost side by side.
  2. Regression-check: re-run after tweaking the persona prompt; watch the scores move.
  3. Catch silent failures: flags template fallbacks (the "same canned line" bug) and
     scenario/model combos that produce zero variation across repeats.

Usage:
    python3 -m booth.eval                       # both models, 2 repeats, with judge
    python3 -m booth.eval --models haiku         # one model
    python3 -m booth.eval --repeats 3            # more runs for variance
    python3 -m booth.eval --no-judge             # skip quality grading (cheaper/faster)

Writes a CSV to evals/ and prints a summary table. The judge is a model grading the
generated lines 1-5 on accuracy / persona / humor.
"""
import argparse
import csv
import json
import sys
import time
import urllib.request
from pathlib import Path

from . import commentary
from .eval_scenarios import SCENARIOS

MODELS = {"haiku": "claude-haiku-4-5", "sonnet": "claude-sonnet-4-6"}
JUDGE_MODEL = "claude-haiku-4-5"   # cheap; judging is relative across rows

# Approximate USD per million tokens — update if pricing changes. Used only for estimates.
PRICING = {
    "claude-haiku-4-5":  {"in": 1.00, "out": 5.00},
    "claude-sonnet-4-6": {"in": 3.00, "out": 15.00},
}

OUT_DIR = Path(__file__).resolve().parents[2] / "evals"


def _est_cost(model, in_tok, out_tok):
    p = PRICING.get(model)
    if not p:
        return 0.0
    return in_tok / 1e6 * p["in"] + out_tok / 1e6 * p["out"]


def _lines_text(lines):
    return " | ".join(f"{l['speaker']}: {l['text']}" for l in lines)


def judge(scenario, lines):
    """Grade generated commentary 1-5 on accuracy/persona/humor. Returns {} on failure."""
    if not lines:
        return {"accuracy": 0, "persona": 0, "humor": 0, "overall": 0}
    key = commentary._resolve_key()
    if not key:
        return {}
    prompt = (
        "You are grading sports-style broadcast commentary written for a live coding session.\n"
        f"SCENARIO: {scenario['desc']}\n"
        f"EVENTS: {json.dumps(scenario['events'])}\n"
        f"GENERATED COMMENTARY: {_lines_text(lines)}\n\n"
        "Score 1-5 (integers):\n"
        "- accuracy: does it reference the ACTUAL events/work, not generic filler?\n"
        "- persona: do the announcers fit (miller=play-by-play, kuiper=dry color, flemming=earnest)?\n"
        "- humor: is it charming, funny, and concise (not rambling)?\n"
        "- overall: holistic 1-5.\n"
        'Return ONLY JSON: {"accuracy":n,"persona":n,"humor":n,"overall":n}'
    )
    body = {"model": JUDGE_MODEL, "max_tokens": 100,
            "messages": [{"role": "user", "content": prompt}]}
    req = urllib.request.Request(
        commentary.API_URL, data=json.dumps(body).encode(),
        headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                 "content-type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read())
        text = "".join(b.get("text", "") for b in data.get("content", []))
        import re
        m = re.search(r"\{.*\}", text, re.DOTALL)
        return json.loads(m.group(0)) if m else {}
    except Exception:
        return {}


def run(models, repeats, do_judge):
    rows = []
    print(f"Running {len(SCENARIOS)} scenarios × {len(models)} models × {repeats} repeats"
          f"{' + judge' if do_judge else ''}...\n")
    for scen in SCENARIOS:
        expect_silent = scen.get("expect_silent", False)
        for mname, mid in models.items():
            outs = []
            for _ in range(repeats):
                res = commentary.generate(scen["events"], big_moment=scen.get("big_moment", False),
                                          model=mid)
                outs.append(res)
            # variation across repeats (a fallback or degenerate prompt yields identical text)
            distinct = len({_lines_text(r["lines"]) for r in outs})
            # silence-by-design: pass if it stayed quiet, fail loudly if it didn't
            silent_ok = expect_silent and all(not r["lines"] for r in outs)
            silent_bad = expect_silent and not silent_ok
            no_variation = distinct == 1 and repeats > 1 and not expect_silent
            for r_i, res in enumerate(outs):
                # don't quality-judge scenarios that are supposed to be silent
                scores = judge(scen, res["lines"]) if (do_judge and not res["fallback"] and not expect_silent) else {}
                rows.append({
                    "scenario": scen["name"],
                    "model": mname,
                    "run": r_i + 1,
                    "fallback": res["fallback"],
                    "expect_silent": expect_silent,
                    "silent_ok": silent_ok if expect_silent else "",
                    "error": res["error"] or "",
                    "n_lines": len(res["lines"]),
                    "distinct_of_repeats": distinct,
                    "no_variation": no_variation,
                    "accuracy": scores.get("accuracy", ""),
                    "persona": scores.get("persona", ""),
                    "humor": scores.get("humor", ""),
                    "overall": scores.get("overall", ""),
                    "latency_s": round(res["latency_s"], 2),
                    "in_tok": res["input_tokens"],
                    "out_tok": res["output_tokens"],
                    "est_cost_usd": round(_est_cost(mid, res["input_tokens"], res["output_tokens"]), 6),
                    "first_line": _lines_text(res["lines"])[:200],
                })
            if res["fallback"]:
                flag = "⚠️ FALLBACK"
            elif silent_bad:
                flag = "⚠️ SHOULD BE SILENT"
            elif silent_ok:
                flag = "✓ silent"
            elif no_variation:
                flag = "⚠️ NO VARIATION"
            else:
                flag = "ok"
            print(f"  {scen['name']:22} {mname:7} {flag:20} {_lines_text(outs[0]['lines'])[:76]}")
    return rows


def write_csv(rows):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"eval-{int(time.time())}.csv"
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    return path


def summarize(rows, models):
    print("\n" + "=" * 64)
    print(f"{'model':8} {'avg overall':12} {'avg lat':9} {'fallbacks':10} {'no-var':7} {'total $':9}")
    print("-" * 64)
    for mname in models:
        mr = [r for r in rows if r["model"] == mname]
        overalls = [float(r["overall"]) for r in mr if str(r["overall"]) not in ("", "0")]
        avg_overall = round(sum(overalls) / len(overalls), 2) if overalls else "n/a"
        avg_lat = round(sum(r["latency_s"] for r in mr) / len(mr), 2) if mr else 0
        fallbacks = sum(1 for r in mr if r["fallback"])
        novar = len({r["scenario"] for r in mr if r["no_variation"]})
        total_cost = round(sum(r["est_cost_usd"] for r in mr), 5)
        print(f"{mname:8} {str(avg_overall):12} {str(avg_lat)+'s':9} {fallbacks:<10} {novar:<7} ${total_cost}")
    # silence-by-design correctness (shared across models)
    silent_scen = {r["scenario"] for r in rows if r["expect_silent"]}
    bad_silent = {r["scenario"] for r in rows if r["expect_silent"] and r["silent_ok"] is False}
    print("-" * 64)
    print(f"silence-by-design: {len(silent_scen) - len(bad_silent)}/{len(silent_scen)} scenarios "
          f"correctly stayed quiet" + (f" — FAILED: {sorted(bad_silent)}" if bad_silent else ""))
    print("=" * 64)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="haiku,sonnet", help="comma list: haiku,sonnet")
    ap.add_argument("--repeats", type=int, default=2)
    ap.add_argument("--no-judge", action="store_true")
    args = ap.parse_args()

    models = {m: MODELS[m] for m in args.models.split(",") if m in MODELS}
    if not models:
        print(f"no valid models in {args.models!r}; choices: {list(MODELS)}")
        return 2

    rows = run(models, args.repeats, do_judge=not args.no_judge)
    summarize(rows, models)
    path = write_csv(rows)
    print(f"\nCSV: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
