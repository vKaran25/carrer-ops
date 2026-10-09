"""Golden-set evaluation. Mock mode is a smoke test, not a model benchmark."""

import argparse
import asyncio
import importlib
import inspect
import json
import math
from pathlib import Path
import sys
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field, model_validator

# Support `python3 tests/eval_harness.py` from any working directory.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import Settings
from app.query_parser import QuerySpec, parse_query


class GoldenCase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1)
    query: str = Field(min_length=1)
    expected_query_spec: QuerySpec
    expected_top_job_ids: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def grounded(self):
        if not self.query.strip():
            raise ValueError("Query must not be blank")
        prefs = self.expected_query_spec.soft_preferences
        if any(p.evidence not in self.query for p in prefs):
            raise ValueError("Expected preference evidence is not in query")
        if len({p.factor for p in prefs}) != len(prefs):
            raise ValueError("Duplicate expected preference factors")
        if len(set(self.expected_top_job_ids)) != len(self.expected_top_job_ids):
            raise ValueError("Duplicate expected job IDs")
        return self


class GoldenDataset(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: int
    description: str
    as_of: str
    top_k: int = Field(ge=1)
    profile: dict[str, Any]
    jobs: list[dict[str, Any]] = Field(min_length=1)
    cases: list[GoldenCase] = Field(min_length=1)

    @model_validator(mode="after")
    def consistent(self):
        if self.schema_version != 1:
            raise ValueError("Unsupported schema_version")
        ids = [job.get("job_id") for job in self.jobs]
        if any(not isinstance(i, str) or not i for i in ids):
            raise ValueError("Every job needs a non-empty job_id")
        if len(set(ids)) != len(ids):
            raise ValueError("Duplicate candidate job IDs")
        if len({case.id for case in self.cases}) != len(self.cases):
            raise ValueError("Duplicate case IDs")
        if any(set(case.expected_top_job_ids) - set(ids) for case in self.cases):
            raise ValueError("Expected job IDs must exist in candidate pool")
        return self


def load_dataset(path: Path) -> GoldenDataset:
    return GoldenDataset.model_validate_json(path.read_text())


def compare_specs(actual: QuerySpec, expected: QuerySpec) -> tuple[bool, bool]:
    def hard(spec):
        return {key: sorted(value) if isinstance(value, list) else value
                for key, value in spec.hard_filters.model_dump().items()}

    def soft(spec):
        # Evidence phrasing may differ; parse_query separately validates grounding.
        return sorted((p.factor, round(p.weight, 2), tuple(sorted(t.lower() for t in p.targets)))
                      for p in spec.soft_preferences)

    return hard(actual) == hard(expected), soft(actual) == soft(expected)


def ranking_metrics(ranked: list[str], expected: list[str], k: int) -> dict[str, float]:
    """Ordered labels have descending relevance grades, not outcome probabilities."""
    hits = len(set(ranked[:k]) & set(expected))
    grades = {job_id: len(expected) - index for index, job_id in enumerate(expected)}

    def dcg(ids):
        return sum((2 ** grades.get(job_id, 0) - 1) / math.log2(index + 2)
                   for index, job_id in enumerate(ids[:k]))

    return {"precision": hits / k, "recall": hits / len(expected),
            "ndcg": dcg(ranked) / dcg(expected)}


async def evaluate(dataset: GoldenDataset, parser, scorer) -> list[dict]:
    """Injected adapters cannot see golden labels; errors remain in denominators."""
    results = []
    for case in dataset.cases:
        row = dict(id=case.id, tool_valid=False, hard=False, soft=False,
                   precision=0.0, recall=0.0, ndcg=0.0, error=None)
        stage = "parser"
        try:
            spec = await parser(case)
            if not isinstance(spec, QuerySpec):
                raise TypeError("Parser must return QuerySpec")
            row["tool_valid"] = True
            row["hard"], row["soft"] = compare_specs(spec, case.expected_query_spec)
            stage = "scorer"
            # Copy inputs so an adapter cannot mutate the golden set across cases.
            ranked = scorer(query_spec=spec, jobs=json.loads(json.dumps(dataset.jobs)),
                            profile=json.loads(json.dumps(dataset.profile)),
                            as_of=dataset.as_of)
            if inspect.isawaitable(ranked):
                ranked = await ranked
            if not isinstance(ranked, list) or any(not isinstance(i, str) for i in ranked):
                raise TypeError("Scorer must return an ordered list of job ID strings")
            if len(set(ranked)) != len(ranked):
                raise ValueError("Duplicate ranked job IDs")
            if set(ranked) - {job["job_id"] for job in dataset.jobs}:
                raise ValueError("Unknown ranked job IDs")
            row.update(ranking_metrics(ranked, case.expected_top_job_ids, dataset.top_k))
        except Exception as exc:
            # Avoid printing API bodies or potentially private upstream exception text.
            row["error"] = f"{stage}: {type(exc).__name__} ({exc})"
        results.append(row)
    return results


def mock_scorer(*, query_spec, jobs, profile, as_of):
    """TEST DOUBLE ONLY: synthetic scalar signals, no semantic/profile reasoning."""
    hard = query_spec.hard_filters

    def eligible(job):
        return (
            (hard.recency_days is None or job["age_days"] <= hard.recency_days)
            and set(hard.tech_stack_keywords) <= set(job["tech_stack"])
            and (not hard.role_keywords or job["role"] in hard.role_keywords)
            and (not hard.industries or job["industry"] in hard.industries)
            and (not hard.company_names or job["company"] in hard.company_names)
        )

    def score(job):
        total = 0.0
        for pref in query_spec.soft_preferences:
            if pref.factor in ("company_tier", "seniority"):
                signal = float(job[pref.factor] in pref.targets)
            else:
                signal = job["signals"].get(pref.factor, 0.0)
            total += pref.weight * signal
        # Deterministic synthetic tie-break; NOT the production Layer 1 algorithm.
        return total, job["signals"].get("resume_match", 0.0)

    return [job["job_id"] for job in sorted(filter(eligible, jobs), key=score, reverse=True)]


def mock_parser(outputs):
    async def run(case):
        def handler(request):
            payload = json.loads(request.content)
            if payload["messages"][1]["content"] != case.query:
                raise ValueError("Incorrect query sent")
            if payload["tool_choice"]["function"]["name"] != "emit_query_spec":
                raise ValueError("Incorrect forced tool")
            return httpx.Response(200, json={"choices": [{"message": {"tool_calls": [{
                "type": "function", "function": {
                    "name": "emit_query_spec", "arguments": json.dumps(outputs[case.id]),
                },
            }]}}]})

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await parse_query(case.query, client=client, settings=Settings(
                openrouter_api_key="mock-only", openrouter_model="mock/tool-model"))
    return run


async def live_parser(case):
    return await parse_query(case.query)


def load_scorer(adapter: str):
    module_name, separator, function_name = adapter.partition(":")
    if not separator:
        raise ValueError("Use --scorer module:function")
    scorer = getattr(importlib.import_module(module_name), function_name)
    if not callable(scorer):
        raise TypeError("Scorer adapter is not callable")
    return scorer


def print_report(results, k, mode):
    print(f"Golden evaluation — {mode}")
    print(f"{'Case':<26} {'Tool':>5} {'Hard':>5} {'Soft':>5} {'P@'+str(k):>7} {'R@'+str(k):>7} {'NDCG@'+str(k):>8}")
    for row in results:
        print(f"{row['id']:<26} {int(row['tool_valid']):>5} {int(row['hard']):>5} "
              f"{int(row['soft']):>5} {row['precision']:>7.3f} {row['recall']:>7.3f} {row['ndcg']:>8.3f}")
        if row["error"]:
            print(f"  ERROR: {row['error']}")
        elif not (row["hard"] and row["soft"]):
            if not row["hard"]:
                print(f"  [mismatch: hard filters differ]")
            if not row["soft"]:
                print(f"  [mismatch: soft preferences differ]")
    means = {key: sum(row[key] for row in results) / len(results)
             for key in ("tool_valid", "hard", "soft", "precision", "recall", "ndcg")}
    exact = sum(row["hard"] and row["soft"] for row in results) / len(results)
    print(f"\nCases: {len(results)} | Tool-valid: {means['tool_valid']:.1%} | Spec accuracy: {exact:.1%}")
    print(f"Mean P@{k}: {means['precision']:.3f} | R@{k}: {means['recall']:.3f} | NDCG@{k}: {means['ndcg']:.3f}")
    return means


def main(argv=None):
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--dataset", type=Path, default=ROOT / "tests/golden_dataset.json")
    cli.add_argument("--mock", action="store_true", help="Offline smoke test; not real engine evaluation")
    cli.add_argument("--mock-outputs", type=Path, default=ROOT / "tests/eval_mock_parser_outputs.json")
    cli.add_argument("--scorer", help="Production scoring adapter as module:function")
    cli.add_argument("--case", help="Run only this case ID")
    cli.add_argument("--min-ndcg", type=float, default=0.0)
    args = cli.parse_args(argv)
    if not 0 <= args.min_ndcg <= 1:
        cli.error("--min-ndcg must be between 0 and 1")
    if args.mock and args.scorer:
        cli.error("--mock and --scorer are mutually exclusive")
    try:
        dataset = load_dataset(args.dataset)
        if args.case:
            dataset.cases = [case for case in dataset.cases if case.id == args.case]
            if not dataset.cases:
                raise ValueError("Unknown --case ID")
        if args.mock:
            parser = mock_parser(json.loads(args.mock_outputs.read_text()))
            scorer = mock_scorer
            mode = "MOCK smoke test (replayed parser + synthetic scorer; NOT a benchmark)"
        else:
            settings = Settings()
            if not settings.openrouter_configured:
                raise ValueError(
                    "OpenRouter is not configured. Configure OPENROUTER_API_KEY and OPENROUTER_MODEL "
                    "in .env or environment variables, or pass --mock for offline smoke testing."
                )
            parser = live_parser
            if args.scorer:
                scorer = load_scorer(args.scorer)
                mode = f"LIVE OpenRouter ({settings.openrouter_model}) + custom scorer ({args.scorer})"
            else:
                scorer = mock_scorer
                mode = f"LIVE OpenRouter ({settings.openrouter_model}) + baseline candidate scorer"
        results = asyncio.run(evaluate(dataset, parser, scorer))
        means = print_report(results, dataset.top_k, mode)
        return int(any(row["error"] or not (row["hard"] and row["soft"]) for row in results)
                   or means["ndcg"] < args.min_ndcg)
    except (OSError, ValueError, ImportError, AttributeError, TypeError) as exc:
        print(f"Evaluation setup failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
