"""Pattern detection across multi-day timelines.

Identifies recurring locations, time-based routines, and
weekly patterns from chronological photo data.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime

import structlog

from src.models import DayGroup, Pattern, Timeline

logger = structlog.get_logger(__name__)

# Minimum occurrences to call something a "recurring" location
MIN_RECURRING_VISITS = 3

# GPS proximity threshold in decimal degrees (~100m at equator)
GPS_CLUSTER_THRESHOLD = 0.001

# Minimum occurrences at similar times to detect a routine
MIN_ROUTINE_OCCURRENCES = 3

# Time bucket size in hours for routine detection
ROUTINE_BUCKET_HOURS = 2


def detect_patterns(timeline: Timeline) -> list[Pattern]:
    """Detect cross-day patterns in a timeline.

    Args:
        timeline: Built timeline with day groups.

    Returns:
        List of detected patterns with evidence.
    """
    patterns: list[Pattern] = []

    active_days = [d for d in timeline.days if d.date != "undated"]
    if len(active_days) < 2:
        return patterns

    patterns.extend(_detect_recurring_locations(active_days))
    patterns.extend(_detect_time_routines(active_days))
    patterns.extend(_detect_weekly_patterns(active_days))

    logger.info(
        "patterns_detected",
        count=len(patterns),
        types=[p.pattern_type for p in patterns],
    )

    return patterns


def _detect_recurring_locations(days: list[DayGroup]) -> list[Pattern]:
    """Find locations visited on multiple different days."""
    # Collect (lat, lng) clusters across days
    location_days: dict[str, set[str]] = defaultdict(set)
    location_names: dict[str, str] = {}

    for day in days:
        for entry in day.entries:
            if entry.location and entry.location.display_name != "Unknown location":
                loc_key = entry.location.display_name
                location_days[loc_key].add(day.date)
                location_names[loc_key] = entry.location.display_name

    patterns = []
    for loc_key, visit_dates in location_days.items():
        if len(visit_dates) >= MIN_RECURRING_VISITS:
            sorted_dates = sorted(visit_dates)
            patterns.append(
                Pattern(
                    pattern_type="recurring_location",
                    description=(
                        f"Subject visited {location_names[loc_key]} "
                        f"on {len(visit_dates)} different days"
                    ),
                    confidence=min(1.0, len(visit_dates) / 5),
                    evidence=[f"Seen at {location_names[loc_key]} on {d}" for d in sorted_dates],
                )
            )

    return patterns


def _detect_time_routines(days: list[DayGroup]) -> list[Pattern]:
    """Detect activities at similar times across multiple days."""
    # Bucket timestamps into 2-hour windows and count occurrences
    time_buckets: dict[int, list[str]] = defaultdict(list)

    for day in days:
        day_buckets_seen: set[int] = set()
        for entry in day.entries:
            if entry.timestamp:
                bucket = entry.timestamp.hour // ROUTINE_BUCKET_HOURS
                if bucket not in day_buckets_seen:
                    time_buckets[bucket].append(day.date)
                    day_buckets_seen.add(bucket)

    patterns = []
    for bucket, dates in time_buckets.items():
        if len(dates) >= MIN_ROUTINE_OCCURRENCES:
            start_hour = bucket * ROUTINE_BUCKET_HOURS
            end_hour = start_hour + ROUTINE_BUCKET_HOURS
            time_label = f"{start_hour:02d}:00-{end_hour:02d}:00"

            patterns.append(
                Pattern(
                    pattern_type="daily_routine",
                    description=(
                        f"Subject regularly appears around {time_label} ({len(dates)} days)"
                    ),
                    confidence=min(1.0, len(dates) / 5),
                    evidence=[f"Active around {time_label} on {d}" for d in sorted(dates)],
                )
            )

    return patterns


def _detect_weekly_patterns(days: list[DayGroup]) -> list[Pattern]:
    """Detect patterns tied to specific days of the week."""
    weekday_counts: Counter[str] = Counter()

    for day in days:
        if day.date == "undated":
            continue
        try:
            dt = datetime.fromisoformat(day.date)
            weekday_counts[dt.strftime("%A")] += 1
        except ValueError:
            continue

    patterns = []
    total_weeks = max(1, len(days) // 7)

    for weekday, count in weekday_counts.items():
        # If a weekday appears consistently (most weeks), flag it
        if count >= MIN_ROUTINE_OCCURRENCES and count >= total_weeks * 0.5:
            patterns.append(
                Pattern(
                    pattern_type="weekly_pattern",
                    description=f"Subject frequently appears on {weekday}s ({count} times)",
                    confidence=min(1.0, count / (total_weeks + 1)),
                    evidence=[f"Active on {count} {weekday}s out of ~{total_weeks} weeks"],
                )
            )

    return patterns
