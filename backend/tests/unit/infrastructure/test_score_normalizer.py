"""Unit tests for min_max_normalize."""

import pytest

from app.infrastructure.retrieval.score_normalizer import min_max_normalize


def test_empty_list() -> None:
    assert min_max_normalize([]) == []


def test_single_element() -> None:
    assert min_max_normalize([0.5]) == [1.0]


def test_all_equal_scores() -> None:
    result = min_max_normalize([3.0, 3.0, 3.0])
    assert result == [1.0, 1.0, 1.0]


def test_zero_to_one_range() -> None:
    result = min_max_normalize([0.0, 0.5, 1.0])
    assert result == pytest.approx([0.0, 0.5, 1.0])


def test_arbitrary_scores() -> None:
    result = min_max_normalize([10.0, 20.0, 30.0])
    assert result == pytest.approx([0.0, 0.5, 1.0])


def test_negative_scores() -> None:
    result = min_max_normalize([-2.0, 0.0, 2.0])
    assert result == pytest.approx([0.0, 0.5, 1.0])


def test_preserves_order() -> None:
    scores = [5.0, 1.0, 3.0]
    result = min_max_normalize(scores)
    # 5 → 1.0, 1 → 0.0, 3 → 0.5
    assert result == pytest.approx([1.0, 0.0, 0.5])
