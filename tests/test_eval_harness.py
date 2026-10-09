import asyncio
import json
from pathlib import Path
import subprocess
import sys

import pytest
from pydantic import ValidationError

from eval_harness import (
    GoldenDataset, compare_specs, evaluate, load_dataset, mock_parser,
    mock_scorer, ranking_metrics,
)
from app.query_parser import QuerySpec


TESTS = Path(__file__).resolve().parent


@pytest.fixture
def dataset():
    return load_dataset(TESTS / "golden_dataset.json")


@pytest.fixture
def parser():
    return mock_parser(json.loads((TESTS / "eval_mock_parser_outputs.json").read_text()))


def test_all_mock_cases(dataset, parser):
    rows = asyncio.run(evaluate(dataset, parser, mock_scorer))
    assert len(rows) == 5
    assert all(row["tool_valid"] and row["hard"] and row["soft"] for row in rows)
    assert all(row["error"] is None and row["ndcg"] == 1 for row in rows)


def test_metrics():
    assert ranking_metrics(["a", "b"], ["a", "b"], 2) == {
        "precision": 1, "recall": 1, "ndcg": 1}
    reversed_rank = ranking_metrics(["b", "a"], ["a", "b"], 2)
    assert reversed_rank["precision"] == reversed_rank["recall"] == 1
    assert 0 < reversed_rank["ndcg"] < 1
    assert ranking_metrics([], ["a", "b"], 2) == {
        "precision": 0, "recall": 0, "ndcg": 0}
    partial = ranking_metrics(["a", "irrelevant"], ["a", "b"], 2)
    assert partial["precision"] == partial["recall"] == 0.5
    assert 0 < partial["ndcg"] < 1


def test_spec_comparison(dataset):
    expected = dataset.cases[1].expected_query_spec
    data = expected.model_dump()
    data["soft_preferences"].reverse()
    data["soft_preferences"][1]["targets"].reverse()
    data["soft_preferences"][1]["evidence"] = "another grounded quote"
    assert compare_specs(QuerySpec.model_validate(data), expected) == (True, True)
    data["hard_filters"]["recency_days"] = 7
    data["soft_preferences"][1]["weight"] = 0.25
    assert compare_specs(QuerySpec.model_validate(data), expected) == (False, False)


def test_mock_does_not_read_expected_labels(dataset, parser):
    dataset.cases[0].expected_top_job_ids = ["java-retail"]
    dataset.cases[0].expected_query_spec.hard_filters.recency_days = 99
    row = asyncio.run(evaluate(dataset, parser, mock_scorer))[0]
    assert not row["hard"]
    assert row["precision"] == 0
    assert row["ndcg"] == 0


@pytest.mark.parametrize("ranked", [["unknown"], ["java-payments"] * 2, {"job_id": "java-payments"}])
def test_bad_scorer_output(dataset, parser, ranked):
    rows = asyncio.run(evaluate(dataset, parser, lambda **kwargs: ranked))
    assert all(row["error"].startswith("scorer:") and row["ndcg"] == 0 for row in rows)
    assert all(row["tool_valid"] for row in rows)


def test_parser_failure_is_recorded(dataset):
    async def broken(case):
        raise RuntimeError("private upstream data")

    rows = asyncio.run(evaluate(dataset, broken, mock_scorer))
    assert len(rows) == 5
    assert all(row["error"].startswith("parser: RuntimeError") for row in rows)
    assert all(not row["tool_valid"] and row["ndcg"] == 0 for row in rows)


def test_async_scorer(dataset, parser):
    async def scorer(**kwargs):
        return mock_scorer(**kwargs)

    assert all(row["ndcg"] == 1 for row in asyncio.run(evaluate(dataset, parser, scorer)))


@pytest.mark.parametrize("change", ["unknown_id", "duplicate_job", "duplicate_case", "version", "ungrounded"])
def test_invalid_dataset(dataset, change):
    data = dataset.model_dump()
    if change == "unknown_id":
        data["cases"][0]["expected_top_job_ids"] = ["missing"]
    elif change == "duplicate_job":
        data["jobs"].append(data["jobs"][0])
    elif change == "duplicate_case":
        data["cases"].append(data["cases"][0])
    elif change == "version":
        data["schema_version"] = 2
    else:
        data["cases"][0]["expected_query_spec"]["soft_preferences"][0]["evidence"] = "invented"
    with pytest.raises(ValidationError):
        GoldenDataset.model_validate(data)


def test_cli_single_mock_case_from_other_directory(tmp_path):
    result = subprocess.run(
        [sys.executable, str(TESTS / "eval_harness.py"), "--mock", "--case", "resume-week"],
        cwd=tmp_path, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "NOT a benchmark" in result.stdout
    assert "Cases: 1" in result.stdout
    assert "Spec accuracy: 100.0%" in result.stdout


def test_cli_unconfigured_fails_cleanly():
    result = subprocess.run([sys.executable, str(TESTS / "eval_harness.py")],
                            capture_output=True, text=True)
    assert result.returncode == 2
    assert "OpenRouter is not configured" in result.stderr
