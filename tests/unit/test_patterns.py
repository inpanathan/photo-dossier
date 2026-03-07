"""Unit tests for src/narrative/patterns.py — detect_patterns()."""

from __future__ import annotations

from datetime import datetime

import pytest

from src.models import DayGroup, LocationInfo, SubjectType, Timeline, TimelineEntry
from src.narrative.patterns import (
    MIN_RECURRING_VISITS,
    MIN_ROUTINE_OCCURRENCES,
    _detect_recurring_locations,
    _detect_time_routines,
    _detect_weekly_patterns,
    detect_patterns,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_day(date_str: str, entries: list[TimelineEntry]) -> DayGroup:
    return DayGroup(date=date_str, day_label=date_str, entries=entries)


def _make_entry(
    image_id: str,
    timestamp: datetime | None = None,
    location_name: str | None = None,
) -> TimelineEntry:
    loc = LocationInfo(display_name=location_name) if location_name else None
    return TimelineEntry(
        image_id=image_id,
        timestamp=timestamp,
        location=loc,
    )


def _make_timeline(days: list[DayGroup]) -> Timeline:
    return Timeline(subject_type=SubjectType.HUMAN, days=days)


# ---------------------------------------------------------------------------
# detect_patterns — top-level routing
# ---------------------------------------------------------------------------


def test_detect_patterns_empty_timeline_returns_empty() -> None:
    result = detect_patterns(_make_timeline([]))
    assert result == []


def test_detect_patterns_single_active_day_returns_empty() -> None:
    day = _make_day("2024-06-01", [_make_entry("img1")])
    result = detect_patterns(_make_timeline([day]))
    assert result == []


def test_detect_patterns_undated_only_returns_empty() -> None:
    day = DayGroup(date="undated", day_label="Undated photos", entries=[_make_entry("img1")])
    result = detect_patterns(_make_timeline([day]))
    assert result == []


def test_detect_patterns_returns_list_of_patterns() -> None:
    # Build enough data to get at least one recurring-location pattern
    days = []
    for i in range(MIN_RECURRING_VISITS):
        date_str = f"2024-06-{i + 1:02d}"
        entry = _make_entry(f"img{i}", location_name="Coffee Shop")
        days.append(_make_day(date_str, [entry]))
    result = detect_patterns(_make_timeline(days))
    assert len(result) >= 1
    assert all(hasattr(p, "pattern_type") for p in result)


# ---------------------------------------------------------------------------
# _detect_recurring_locations
# ---------------------------------------------------------------------------


def test_recurring_locations_no_locations_returns_empty() -> None:
    days = [_make_day(f"2024-06-{i + 1:02d}", [_make_entry(f"img{i}")]) for i in range(5)]
    result = _detect_recurring_locations(days)
    assert result == []


def test_recurring_locations_below_threshold_no_pattern() -> None:
    days = []
    for i in range(MIN_RECURRING_VISITS - 1):
        entry = _make_entry(f"img{i}", location_name="The Gym")
        days.append(_make_day(f"2024-06-{i + 1:02d}", [entry]))
    result = _detect_recurring_locations(days)
    assert result == []


def test_recurring_locations_at_threshold_returns_pattern() -> None:
    days = []
    for i in range(MIN_RECURRING_VISITS):
        entry = _make_entry(f"img{i}", location_name="The Gym")
        days.append(_make_day(f"2024-06-{i + 1:02d}", [entry]))
    result = _detect_recurring_locations(days)
    assert len(result) == 1
    assert result[0].pattern_type == "recurring_location"
    assert "The Gym" in result[0].description


def test_recurring_locations_evidence_contains_dates() -> None:
    days = []
    for i in range(MIN_RECURRING_VISITS):
        entry = _make_entry(f"img{i}", location_name="Park")
        days.append(_make_day(f"2024-06-{i + 1:02d}", [entry]))
    result = _detect_recurring_locations(days)
    assert len(result[0].evidence) == MIN_RECURRING_VISITS
    assert all("Park" in ev for ev in result[0].evidence)


def test_recurring_locations_unknown_location_excluded() -> None:
    """'Unknown location' (default display_name) must not be counted."""
    days = []
    for i in range(MIN_RECURRING_VISITS + 2):
        entry = _make_entry(f"img{i}")  # no location_name → display_name = "Unknown location"
        days.append(_make_day(f"2024-06-{i + 1:02d}", [entry]))
    result = _detect_recurring_locations(days)
    assert result == []


def test_recurring_locations_confidence_capped_at_1() -> None:
    # 10 visits → confidence = min(1.0, 10/5) = 1.0
    days = []
    for i in range(10):
        entry = _make_entry(f"img{i}", location_name="Mall")
        days.append(_make_day(f"2024-06-{i + 1:02d}", [entry]))
    result = _detect_recurring_locations(days)
    assert result[0].confidence == pytest.approx(1.0)


def test_recurring_locations_same_day_multiple_entries_counts_once() -> None:
    """Multiple entries at the same location on the same day count as one visit."""
    entries = [
        _make_entry("a", location_name="Café"),
        _make_entry("b", location_name="Café"),
        _make_entry("c", location_name="Café"),
    ]
    # Only 2 distinct days even though there are many entries
    day1 = _make_day("2024-06-01", entries)
    day2 = _make_day("2024-06-02", entries)
    result = _detect_recurring_locations([day1, day2])
    # 2 visits < MIN_RECURRING_VISITS (3) → no pattern
    assert result == []


def test_recurring_locations_multiple_distinct_locations() -> None:
    location_a = "Library"
    location_b = "Stadium"
    days = []
    for i in range(MIN_RECURRING_VISITS):
        days.append(
            _make_day(
                f"2024-06-{i + 1:02d}",
                [
                    _make_entry(f"a{i}", location_name=location_a),
                    _make_entry(f"b{i}", location_name=location_b),
                ],
            )
        )
    result = _detect_recurring_locations(days)
    pattern_types = {p.description for p in result}
    assert any(location_a in d for d in pattern_types)
    assert any(location_b in d for d in pattern_types)


# ---------------------------------------------------------------------------
# _detect_time_routines
# ---------------------------------------------------------------------------


def test_time_routines_no_timestamps_returns_empty() -> None:
    days = [_make_day(f"2024-06-{i + 1:02d}", [_make_entry(f"img{i}")]) for i in range(5)]
    result = _detect_time_routines(days)
    assert result == []


def test_time_routines_below_threshold_no_pattern() -> None:
    days = []
    for i in range(MIN_ROUTINE_OCCURRENCES - 1):
        ts = datetime(2024, 6, i + 1, 8, 30)  # all in the 08:00-10:00 bucket
        entry = _make_entry(f"img{i}", timestamp=ts)
        days.append(_make_day(f"2024-06-{i + 1:02d}", [entry]))
    result = _detect_time_routines(days)
    assert result == []


def test_time_routines_at_threshold_returns_pattern() -> None:
    days = []
    for i in range(MIN_ROUTINE_OCCURRENCES):
        ts = datetime(2024, 6, i + 1, 8, 15)  # bucket 4 (08:00-10:00)
        entry = _make_entry(f"img{i}", timestamp=ts)
        days.append(_make_day(f"2024-06-{i + 1:02d}", [entry]))
    result = _detect_time_routines(days)
    assert len(result) == 1
    assert result[0].pattern_type == "daily_routine"
    assert "08:00-10:00" in result[0].description


def test_time_routines_confidence_capped_at_1() -> None:
    days = []
    for i in range(10):
        ts = datetime(2024, 6, i + 1, 7, 0)
        entry = _make_entry(f"img{i}", timestamp=ts)
        days.append(_make_day(f"2024-06-{i + 1:02d}", [entry]))
    result = _detect_time_routines(days)
    assert all(p.confidence <= 1.0 for p in result)


def test_time_routines_same_day_multiple_entries_counts_once_per_bucket() -> None:
    """Two entries in the same 2-hour bucket on the same day should count as one."""
    ts1 = datetime(2024, 6, 1, 9, 0)
    ts2 = datetime(2024, 6, 1, 9, 45)
    entries = [_make_entry("a", ts1), _make_entry("b", ts2)]
    day = _make_day("2024-06-01", entries)
    # Only one day → cannot reach MIN_ROUTINE_OCCURRENCES for the bucket
    result = _detect_time_routines([day])
    assert result == []


def test_time_routines_evidence_lists_active_dates() -> None:
    days = []
    for i in range(MIN_ROUTINE_OCCURRENCES):
        ts = datetime(2024, 6, i + 1, 14, 0)  # afternoon bucket
        entry = _make_entry(f"img{i}", timestamp=ts)
        days.append(_make_day(f"2024-06-{i + 1:02d}", [entry]))
    result = _detect_time_routines(days)
    assert len(result) >= 1
    assert len(result[0].evidence) == MIN_ROUTINE_OCCURRENCES


# ---------------------------------------------------------------------------
# _detect_weekly_patterns
# ---------------------------------------------------------------------------


def test_weekly_patterns_empty_days_returns_empty() -> None:
    assert _detect_weekly_patterns([]) == []


def test_weekly_patterns_no_pattern_when_below_threshold() -> None:
    # 2 Mondays but MIN_ROUTINE_OCCURRENCES is 3
    days = [
        _make_day("2024-06-03", []),  # Monday
        _make_day("2024-06-10", []),  # Monday
    ]
    result = _detect_weekly_patterns(days)
    # 2 Mondays < 3 → no weekly pattern for Monday
    monday_patterns = [p for p in result if "Monday" in p.description]
    assert monday_patterns == []


def test_weekly_patterns_detects_repeated_weekday() -> None:
    # 3 Mondays across 3 weeks → should trigger
    days = [
        _make_day("2024-06-03", []),  # Monday
        _make_day("2024-06-10", []),  # Monday
        _make_day("2024-06-17", []),  # Monday
    ]
    result = _detect_weekly_patterns(days)
    monday_patterns = [p for p in result if "Monday" in p.description]
    assert len(monday_patterns) == 1
    assert monday_patterns[0].pattern_type == "weekly_pattern"


def test_weekly_patterns_skips_undated_entries() -> None:
    days = [
        DayGroup(date="undated", day_label="Undated photos", entries=[]),
        _make_day("2024-06-03", []),
        _make_day("2024-06-10", []),
        _make_day("2024-06-17", []),
    ]
    result = _detect_weekly_patterns(days)
    # Should still detect the Monday pattern from dated entries
    monday_patterns = [p for p in result if "Monday" in p.description]
    assert len(monday_patterns) == 1


def test_weekly_patterns_confidence_not_above_1() -> None:
    # Many Mondays
    days = [_make_day(f"2024-06-{3 + i * 7:02d}", []) for i in range(8)]
    result = _detect_weekly_patterns(days)
    assert all(p.confidence <= 1.0 for p in result)


def test_weekly_patterns_invalid_date_string_skipped() -> None:
    days = [
        _make_day("not-a-date", []),
        _make_day("2024-06-03", []),
        _make_day("2024-06-10", []),
        _make_day("2024-06-17", []),
    ]
    # Should not raise; invalid date is silently skipped
    result = _detect_weekly_patterns(days)
    assert isinstance(result, list)
