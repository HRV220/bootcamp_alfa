"""Read-only audit of saved case artifacts; never accesses night or external services."""
import ast
import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def notebook(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8-sig"))


def stream(nb, cell):
    return "".join("".join(o.get("text", [])) for o in nb["cells"][cell].get("outputs", [])).strip()


def audit():
    ml = notebook("task/case2/smurf_pipeline_fixed_with_outputs_1__1.ipynb")
    syntax_errors = []
    for index, cell in enumerate(ml["cells"]):
        if cell["cell_type"] != "code":
            continue
        try:
            ast.parse("".join(cell["source"]))
        except SyntaxError as error:
            syntax_errors.append({"cell_zero_based": index, "line": error.lineno,
                                  "message": error.msg, "text": error.text.strip()})
    with (ROOT / "task/case2/smurf_players.csv").open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    llm = notebook("task/case3/case3.ipynb")
    source = json.loads(stream(llm, 1))["events"]
    described = json.loads(stream(llm, 2))["events"]
    source_ids = [e["event_id"] for e in source]
    result_ids = [e["event_id"] for e in described]
    mismatches = [{"position_zero_based": i, "source": a, "response": b}
                  for i, (a, b) in enumerate(zip(source, described))
                  if a["event_id"] != b["event_id"]]
    return {
        "scope": "Local saved artifacts only; no night, cluster, training or LLM requests",
        "case1": {"source": "task/case1/1.1.png; manually transcribed rounded display values",
                  "early_winrate": 0.544, "late_winrate": 0.4691,
                  "difference_pp": round((0.544 - 0.4691) * 100, 2),
                  "target_pp": 3, "displayed_target_reached": True,
                  "statistical_significance": "not assessed; underlying rows unavailable"},
        "case2": {"syntax_errors": syntax_errors,
                  "csv_rows": len(rows), "csv_accounts": len({r["account_id"] for r in rows}),
                  "csv_matches": len({r["match_id"] for r in rows}),
                  "csv_unique_keys": len({(r["match_id"], r["player_slot"]) for r in rows}),
                  "csv_labels": dict(Counter(r["smurf"] for r in rows)),
                  "baseline_ap_source": "Saved output, cell index 17; not retrained",
                  "baseline_ap": 0.387234, "test_positive_prevalence": 162 / 8336,
                  "ap_over_prevalence": 0.387234 / (162 / 8336),
                  "optuna_ap_difference": 0.387965 - 0.387234},
        "case3": {"match_id": json.loads(stream(llm, 1))["match_id"],
                  "source_count": len(source), "source_unique_ids": len(set(source_ids)),
                  "types": dict(Counter(e["type"] for e in source)),
                  "min_time_sec": min(e["time"] for e in source),
                  "max_time_sec": max(e["time"] for e in source),
                  "source_sorted": source == sorted(source, key=lambda e: (
                      e["time"] is None, e["time"] or 0, e["event_id"])),
                  "response_count": len(described), "response_unique_ids": len(set(result_ids)),
                  "missing_ids": sorted(set(source_ids) - set(result_ids)),
                  "extra_ids": sorted(set(result_ids) - set(source_ids)),
                  "duplicate_ids": [k for k, v in Counter(result_ids).items() if v > 1],
                  "id_position_mismatches": mismatches,
                  "note": "ID mismatches are not a measured factual-error rate of summary prose"}}


if __name__ == "__main__":
    print(json.dumps(audit(), ensure_ascii=False, indent=2))
