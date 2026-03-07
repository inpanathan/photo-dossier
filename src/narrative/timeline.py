"""Timeline builder — orders retrieval matches into a chronological timeline.

Groups photos by calendar day, clusters into scenes within each day,
and identifies gaps between active days.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta

import structlog

from src.models import (
    DateGap,
    DayGroup,
    LocationInfo,
    Match,
    Scene,
    SubjectType,
    Timeline,
    TimelineEntry,
)

logger = structlog.get_logger(__name__)

# Photos within this many minutes are grouped into the same scene
SCENE_GAP_MINUTES = 30


def build_timeline(matches: list[Match], subject_type: SubjectType) -> Timeline:
    """Build a chronological timeline from retrieval matches.

    Args:
        matches: List of Match objects from retrieval.
        subject_type: The subject being tracked.

    Returns:
        Timeline with days, scenes, and gap annotations.
    """
    entries = _matches_to_entries(matches)

    # Split into timestamped and unplaced
    timestamped = [e for e in entries if e.timestamp is not None]
    unplaced = [e for e in entries if e.timestamp is None]

    # Sort by timestamp (None already filtered out above)
    timestamped.sort(key=lambda e: e.timestamp or datetime.min)

    # Group by calendar day
    day_map: dict[date, list[TimelineEntry]] = defaultdict(list)
    for entry in timestamped:
        day_key = entry.timestamp.date()  # type: ignore[union-attr]
        day_map[day_key] = day_map.get(day_key, [])
        day_map[day_key].append(entry)

    # Build DayGroup objects with scene clustering
    sorted_dates = sorted(day_map.keys())
    days: list[DayGroup] = []

    for d in sorted_dates:
        day_entries = day_map[d]
        scenes = _cluster_scenes(day_entries)
        days.append(
            DayGroup(
                date=d.isoformat(),
                day_label=d.strftime("%A, %B %d, %Y"),
                entries=day_entries,
                scenes=scenes,
            )
        )

    # Detect gaps between active days
    gaps = _detect_gaps(sorted_dates)

    # Add unplaced entries to a special "undated" day group at the end
    if unplaced:
        days.append(
            DayGroup(
                date="undated",
                day_label="Undated photos",
                entries=unplaced,
                scenes=[],
            )
        )

    timeline = Timeline(
        subject_type=subject_type,
        date_range_start=sorted_dates[0].isoformat() if sorted_dates else None,
        date_range_end=sorted_dates[-1].isoformat() if sorted_dates else None,
        total_days_spanned=(
            (sorted_dates[-1] - sorted_dates[0]).days + 1
            if len(sorted_dates) > 1
            else len(sorted_dates)
        ),
        active_days=len(sorted_dates),
        days=days,
        gaps=gaps,
    )

    logger.info(
        "timeline_built",
        subject_type=subject_type,
        total_entries=len(entries),
        timestamped=len(timestamped),
        unplaced=len(unplaced),
        active_days=timeline.active_days,
        total_days_spanned=timeline.total_days_spanned,
        gaps=len(gaps),
    )

    return timeline


def _matches_to_entries(matches: list[Match]) -> list[TimelineEntry]:
    """Convert Match objects to TimelineEntry objects."""
    entries = []
    for m in matches:
        ts = m.metadata.timestamp if m.metadata else None
        loc = m.location

        # If metadata has GPS but no location info, create a minimal one
        if loc is None and m.metadata and m.metadata.has_gps:
            loc = LocationInfo(
                display_name=f"{m.metadata.latitude:.4f}, {m.metadata.longitude:.4f}"
            )

        entries.append(
            TimelineEntry(
                image_id=m.image_id,
                image_url=m.image_url,
                image_path=m.image_path,
                timestamp=ts,
                date=ts.strftime("%Y-%m-%d") if ts else None,
                time=ts.strftime("%H:%M:%S") if ts else None,
                location=loc,
                confidence=m.similarity_score,
            )
        )
    return entries


def _cluster_scenes(entries: list[TimelineEntry]) -> list[Scene]:
    """Cluster entries within a day into scenes based on time gaps."""
    if not entries:
        return []

    scenes: list[Scene] = []
    current_scene_entries: list[TimelineEntry] = [entries[0]]

    for entry in entries[1:]:
        prev = current_scene_entries[-1]
        if prev.timestamp and entry.timestamp:
            gap = (entry.timestamp - prev.timestamp).total_seconds() / 60
            if gap > SCENE_GAP_MINUTES:
                scenes.append(_make_scene(current_scene_entries))
                current_scene_entries = []
        current_scene_entries.append(entry)

    # Final scene
    if current_scene_entries:
        scenes.append(_make_scene(current_scene_entries))

    return scenes


def _make_scene(entries: list[TimelineEntry]) -> Scene:
    """Create a Scene from a cluster of entries."""
    start_ts = entries[0].timestamp
    end_ts = entries[-1].timestamp

    # Determine time-of-day label
    label = _time_of_day_label(start_ts) if start_ts else "unknown"

    # Pick the most common location
    location = None
    for e in entries:
        if e.location:
            location = e.location
            break

    return Scene(
        start_time=start_ts.strftime("%H:%M") if start_ts else None,
        end_time=end_ts.strftime("%H:%M") if end_ts else None,
        location=location,
        entries=entries,
        label=label,
    )


def _time_of_day_label(ts: datetime) -> str:
    """Map a timestamp to a human-readable time-of-day label."""
    hour = ts.hour
    if hour < 6:
        return "early morning"
    if hour < 12:
        return "morning"
    if hour < 14:
        return "midday"
    if hour < 17:
        return "afternoon"
    if hour < 20:
        return "evening"
    return "night"


def _detect_gaps(sorted_dates: list[date]) -> list[DateGap]:
    """Detect gaps of 2+ days between active dates."""
    gaps = []
    for i in range(1, len(sorted_dates)):
        delta = (sorted_dates[i] - sorted_dates[i - 1]).days
        if delta >= 2:
            gaps.append(
                DateGap(
                    start_date=(sorted_dates[i - 1] + timedelta(days=1)).isoformat(),
                    end_date=(sorted_dates[i] - timedelta(days=1)).isoformat(),
                    gap_days=delta - 1,
                )
            )
    return gaps
