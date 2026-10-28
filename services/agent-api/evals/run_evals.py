"""Runs the golden sets through the production chat pipeline (run_turn) and scores them.

    python services/agent-api/evals/run_evals.py [--strict] [--limit N]

Real Gemini (LLM_MODE=vertex) is paid and never runs by accident: it needs --confirm-spend, is capped per run by
--run-cap-usd (default 0.50) on top of the hard cap in config/llm.yaml, and prints the ledger before and after.
    LLM_MODE=vertex GOOGLE_CLOUD_PROJECT=... make eval EVAL_ARGS="--confirm-spend --limit 3"

`adk eval` expects a module-level static `root_agent`; our agent is built per request around a verified tenant,
so this runner loads the same ADK EvalSet files and executes each case with the real tools, repositories and
callbacks. LLM_MODE=vertex uses Gemini (needs GOOGLE_CLOUD_PROJECT + ADC); default is the deterministic FakeLlm.

Metrics (thresholds in test_config.json):
  tool_trajectory_avg_score: expected tool names appear in order in the actual calls ([] = no tool call)
  response_match_score:      share of the reference answer's content stems found in the response
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from google.adk.evaluation.eval_set import EvalSet

from agent_api.chat import run_turn
from agent_api.deps import Deps
from agent_api.settings import Settings
from magaza_core.analytics import AnalyticsEmitter
from magaza_core.budget import BudgetGuard, get_budget_guard
from magaza_core.contracts import ChatRequest
from magaza_core.embedding import get_embedder
from magaza_core.repo import TenantRegistry, get_db
from magaza_core.tenancy import TenantContext
from magaza_core.text import tokens

HERE = Path(__file__).parent


def is_subsequence(expected: list[str], actual: list[str]) -> bool:
    it = iter(actual)
    return all(name in it for name in expected)


def response_match(reference: str, response: str) -> float:
    ref = {t[:5] for t in tokens(reference) if len(t) > 2}
    got = {t[:5] for t in tokens(response)}
    return len(ref & got) / len(ref) if ref else 1.0


async def run_set(deps: Deps, path: Path, limit: int | None) -> dict[str, object]:
    evalset = EvalSet.model_validate_json(path.read_text(encoding="utf-8"))
    tenant_id = path.name.split(".")[0]
    config = await deps.registry.get(tenant_id)
    if config is None:
        raise SystemExit(f"tenant {tenant_id} not seeded; run `make seed` first")
    ctx = TenantContext.of(config)
    rows = []
    for case in evalset.eval_cases[:limit]:
        invocation = case.conversation[0]  # type: ignore[index]
        question = "".join(p.text or "" for p in invocation.user_content.parts or [])
        reference = "".join(
            p.text or "" for p in (invocation.final_response.parts if invocation.final_response else []) or []
        )
        expected = [
            t.name or ""
            for t in (invocation.intermediate_data.tool_uses if invocation.intermediate_data else [])
        ]  # type: ignore[union-attr]
        start = len(deps.analytics.events)
        text = ""
        async for event in run_turn(
            deps, ctx, ChatRequest(message=question, visitor_id=f"v_eval_{case.eval_id[-12:]}")
        ):
            if event.type == "token":
                text += event.text
        calls = [e.payload["tool"] for e in deps.analytics.events[start:] if e.event_type == "tool_call"]
        trajectory = 1.0 if (is_subsequence(expected, calls) and (expected or not calls)) else 0.0
        rows.append(
            {
                "id": case.eval_id,
                "trajectory": trajectory,
                "response": round(response_match(reference, text), 2),
                "tools": calls,
            }
        )
    n = len(rows)
    return {
        "eval_set": evalset.eval_set_id,
        "cases": n,
        "tool_trajectory_avg_score": round(sum(r["trajectory"] for r in rows) / n, 3),  # type: ignore[misc]
        "response_match_score": round(sum(r["response"] for r in rows) / n, 3),  # type: ignore[misc]
        "failures": [r for r in rows if r["trajectory"] < 1 or r["response"] < 0.3],  # type: ignore[operator]
    }


def print_budget(label: str, guard: BudgetGuard) -> None:
    print(f"budget {label}:", json.dumps(guard.status(), ensure_ascii=False))


async def main_async(args: argparse.Namespace) -> int:
    settings = Settings()
    settings.configure_vertex_env()
    guard = None
    if settings.llm_mode == "vertex":
        if not args.confirm_spend:
            print("LLM_MODE=vertex calls paid Gemini: re-run with --confirm-spend (and ideally --limit N).")
            return 2
        guard = get_budget_guard(run_cap_usd=args.run_cap_usd)
        print_budget("before", guard)
    deps = Deps(
        settings=settings,
        db=get_db(),
        embedder=get_embedder(),
        analytics=AnalyticsEmitter(None, settings.llm),
        budget=guard,
    )
    criteria = json.loads((HERE / "test_config.json").read_text(encoding="utf-8"))["criteria"]
    ok = True
    print(f"LLM_MODE={settings.llm_mode} model={deps.model_name}")
    for path in sorted(HERE.glob("*.evalset.json")):
        result = await run_set(deps, path, args.limit)
        passed = all(float(result[k]) >= v for k, v in criteria.items())  # type: ignore[arg-type]
        ok &= passed
        print(
            json.dumps({k: v for k, v in result.items() if k != "failures"}, ensure_ascii=False),
            "PASS" if passed else "BELOW THRESHOLD",
        )
        for failure in result["failures"]:  # type: ignore[attr-defined]
            print("   -", json.dumps(failure, ensure_ascii=False))
    await TenantRegistry(deps.db).list()  # keeps the client alive until all writes finished
    if guard is not None:
        print_budget("after", guard)
    return 0 if ok or not args.strict else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true", help="exit 1 when a metric is below its threshold")
    parser.add_argument("--limit", type=int, default=None, help="run only the first N cases of each set")
    parser.add_argument(
        "--confirm-spend", action="store_true", help="allow paid Gemini calls (LLM_MODE=vertex)"
    )
    parser.add_argument("--run-cap-usd", type=float, default=0.50, help="max spend of this run (vertex only)")
    sys.exit(asyncio.run(main_async(parser.parse_args())))
