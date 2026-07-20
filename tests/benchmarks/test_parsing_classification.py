from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import ParamSpec, Protocol, TypeVar

import pytest

from opportunities.config.rules import ClassificationRules
from opportunities.normalization.location import normalize_locations
from opportunities.pipeline.classification import Classifier
from opportunities.scrapers.linkedin import SearchPageResult, parse_search_page

P = ParamSpec("P")
R = TypeVar("R")


class Benchmark(Protocol):
    """Describe the callable interface exposed by pytest-benchmark."""

    def __call__(self, target: Callable[P, R], *args: P.args, **kwargs: P.kwargs) -> R:
        """Measure repeated calls and return the final result."""
        ...


pytestmark = pytest.mark.performance


def test_linkedin_search_page_parsing_performance(
    benchmark: Benchmark,
    fixture_html: Callable[[str], str],
) -> None:
    """Track search-card parsing throughput against representative fixture HTML."""
    html = fixture_html("linkedin_search_page_1.html")

    result: SearchPageResult = benchmark(parse_search_page, html)

    assert len(result.cards) == 2


def test_classification_performance(
    benchmark: Benchmark,
    rules: ClassificationRules,
) -> None:
    """Track the complete deterministic classification decision path."""
    classifier = Classifier(rules, target_cycle=2027)
    location = normalize_locations(["London, UK"])

    result = benchmark(
        classifier.classify,
        title="Backend Software Engineering Intern 2027",
        description="Build distributed systems during a Summer 2027 internship.",
        location=location,
        posted_at=datetime(2026, 7, 20, tzinfo=UTC),
    )

    assert result.include
