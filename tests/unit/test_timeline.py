"""Unit tests for src/narrative/timeline.py — build_timeline()."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from src.models import (
    BoundingBox,
    ImageMetadata,
    LocationInfo,
    Match,
    SubjectType,
    Timeline,
)
from src.narrative.timeline import (
    SCENE_GAP_MINUTES,
    _cluster_scenes,
    _detect_gaps,
    _make_scene,
    _matches_to_entries,
    _time_of_day_label,
    build_timeline,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BBOX = BoundingBox(x=0.1, y=0.1, width=0.2, height=0.3)


def _make_match(
    image_id: str,
    timestamp: datetime | None = None,
    similarity: float = 0.9,
    lat: float | None = None,
    lon: float | None = None,
    location: LocationInfo | None = None,
    path: str = "",
) -> Match:
    meta = ImageMetadata(
        image_id=image_id,
        path=path or f"/photos/{image_id}.jpg",
        format="jpeg",
        size_bytes=100_000,
        timestamp=timestamp,
        latitude=lat,
        longitude=lon,
        has_gps=lat is not None and lon is not None,
        has_timestamp=timestamp is not None,
    )
    return Match(
        face_id=f"face_{image_id}",
        image_id=image_id,
        image_path=meta.path,
        image_url=f"http://localhost/{image_id}.jpg",
        similarity_score=similarity,
        subject_type=SubjectType.HUMAN,
        bbox=_BBOX,
        metadata=meta,
        location=location,
    )


# ---------------------------------------------------------------------------
# build_timeline — happy path
# ---------------------------------------------------------------------------


def test_build_timeline_returns_timeline_type() -> None:
    matches = [_make_match("img1", datetime(2024, 6, 1, 9, 0))]
    result = build_timeline(matches, SubjectType.HUMAN)
    assert isinstance(result, Timeline)
    assert result.subject_type == SubjectType.HUMAN


def test_build_timeline_single_day_one_active_day() -> None:
    ts = datetime(2024, 6, 1, 9, 0)
    matches = [_make_match("a", ts), _make_match("b", ts + timedelta(minutes=10))]
    result = build_timeline(matches, SubjectType.HUMAN)
    assert result.active_days == 1
    assert result.total_days_spanned == 1
    assert result.date_range_start == "2024-06-01"
    assert result.date_range_end == "2024-06-01"


def test_build_timeline_multiple_days_counts_correctly() -> None:
    matches = [
        _make_match("a", datetime(2024, 6, 1, 9, 0)),
        _make_match("b", datetime(2024, 6, 3, 14, 0)),
    ]
    result = build_timeline(matches, SubjectType.HUMAN)
    assert result.active_days == 2
    # spans 3 days: Jun 1, 2, 3
    assert result.total_days_spanned == 3


def test_build_timeline_day_label_format() -> None:
    matches = [_make_match("a", datetime(2024, 6, 3, 10, 0))]
    result = build_timeline(matches, SubjectType.HUMAN)
    day = result.days[0]
    assert day.date == "2024-06-03"
    assert "Monday" in day.day_label
    assert "June" in day.day_label
    assert "2024" in day.day_label


def test_build_timeline_scenes_created_per_day() -> None:
    # Two photos far apart in the same day → two scenes
    t_base = datetime(2024, 6, 1, 8, 0)
    matches = [
        _make_match("a", t_base),
        _make_match("b", t_base + timedelta(minutes=SCENE_GAP_MINUTES + 5)),
    ]
    result = build_timeline(matches, SubjectType.HUMAN)
    assert len(result.days) == 1
    assert len(result.days[0].scenes) == 2


def test_build_timeline_close_photos_same_scene() -> None:
    t_base = datetime(2024, 6, 1, 8, 0)
    matches = [
        _make_match("a", t_base),
        _make_match("b", t_base + timedelta(minutes=SCENE_GAP_MINUTES - 1)),
    ]
    result = build_timeline(matches, SubjectType.HUMAN)
    assert len(result.days[0].scenes) == 1


# ---------------------------------------------------------------------------
# build_timeline — unplaced (no-timestamp) photos
# ---------------------------------------------------------------------------


def test_build_timeline_no_timestamp_creates_undated_group() -> None:
    matches = [_make_match("no_ts")]
    result = build_timeline(matches, SubjectType.PET)
    undated = [d for d in result.days if d.date == "undated"]
    assert len(undated) == 1
    assert len(undated[0].entries) == 1
    assert undated[0].day_label == "Undated photos"


def test_build_timeline_mixed_dated_and_undated() -> None:
    matches = [
        _make_match("dated", datetime(2024, 6, 1, 10, 0)),
        _make_match("no_ts"),
    ]
    result = build_timeline(matches, SubjectType.HUMAN)
    dated_days = [d for d in result.days if d.date != "undated"]
    undated_days = [d for d in result.days if d.date == "undated"]
    assert len(dated_days) == 1
    assert len(undated_days) == 1


def test_build_timeline_only_undated_no_date_range() -> None:
    matches = [_make_match("no_ts")]
    result = build_timeline(matches, SubjectType.HUMAN)
    assert result.date_range_start is None
    assert result.date_range_end is None
    assert result.active_days == 0


# ---------------------------------------------------------------------------
# build_timeline — empty input
# ---------------------------------------------------------------------------


def test_build_timeline_empty_matches_returns_empty_timeline() -> None:
    result = build_timeline([], SubjectType.HUMAN)
    assert result.active_days == 0
    assert result.total_days_spanned == 0
    assert result.days == []
    assert result.gaps == []
    assert result.date_range_start is None
    assert result.date_range_end is None


# ---------------------------------------------------------------------------
# build_timeline — gaps detection
# ---------------------------------------------------------------------------


def test_build_timeline_gap_detected_between_distant_days() -> None:
    matches = [
        _make_match("a", datetime(2024, 6, 1, 10, 0)),
        _make_match("b", datetime(2024, 6, 5, 10, 0)),
    ]
    result = build_timeline(matches, SubjectType.HUMAN)
    assert len(result.gaps) == 1
    gap = result.gaps[0]
    assert gap.start_date == "2024-06-02"
    assert gap.end_date == "2024-06-04"
    assert gap.gap_days == 3


def test_build_timeline_no_gap_for_consecutive_days() -> None:
    matches = [
        _make_match("a", datetime(2024, 6, 1, 10, 0)),
        _make_match("b", datetime(2024, 6, 2, 10, 0)),
    ]
    result = build_timeline(matches, SubjectType.HUMAN)
    assert result.gaps == []


def test_build_timeline_no_gap_for_single_day() -> None:
    matches = [_make_match("a", datetime(2024, 6, 1, 10, 0))]
    result = build_timeline(matches, SubjectType.HUMAN)
    assert result.gaps == []


# ---------------------------------------------------------------------------
# build_timeline — GPS fallback location
# ---------------------------------------------------------------------------


def test_build_timeline_gps_fallback_creates_location() -> None:
    match = _make_match("gps_img", datetime(2024, 6, 1, 9, 0), lat=51.5074, lon=-0.1278)
    result = build_timeline([match], SubjectType.HUMAN)
    entry = result.days[0].entries[0]
    assert entry.location is not None
    assert "51.5074" in entry.location.display_name
    assert "-0.1278" in entry.location.display_name


def test_build_timeline_explicit_location_takes_precedence() -> None:
    loc = LocationInfo(city="London", display_name="London, UK")
    match = _make_match("loc_img", datetime(2024, 6, 1, 9, 0), lat=51.5, lon=-0.1, location=loc)
    result = build_timeline([match], SubjectType.HUMAN)
    entry = result.days[0].entries[0]
    assert entry.location is not None
    assert entry.location.display_name == "London, UK"


def test_build_timeline_no_gps_no_location_is_none() -> None:
    match = _make_match("plain", datetime(2024, 6, 1, 9, 0))
    result = build_timeline([match], SubjectType.HUMAN)
    entry = result.days[0].entries[0]
    assert entry.location is None


# ---------------------------------------------------------------------------
# _matches_to_entries
# ---------------------------------------------------------------------------


def test_matches_to_entries_sets_confidence_from_similarity() -> None:
    match = _make_match("img", datetime(2024, 1, 1, 8, 0), similarity=0.77)
    entries = _matches_to_entries([match])
    assert len(entries) == 1
    assert entries[0].confidence == pytest.approx(0.77)


def test_matches_to_entries_sets_date_and_time_strings() -> None:
    ts = datetime(2024, 3, 15, 14, 30, 45)
    entries = _matches_to_entries([_make_match("img", ts)])
    assert entries[0].date == "2024-03-15"
    assert entries[0].time == "14:30:45"


def test_matches_to_entries_no_metadata_no_timestamp() -> None:
    match = Match(
        face_id="f1",
        image_id="img1",
        image_path="/x.jpg",
        image_url="",
        similarity_score=0.8,
        subject_type=SubjectType.HUMAN,
        bbox=_BBOX,
        metadata=None,
        location=None,
    )
    entries = _matches_to_entries([match])
    assert entries[0].timestamp is None
    assert entries[0].date is None
    assert entries[0].time is None


# ---------------------------------------------------------------------------
# _cluster_scenes
# ---------------------------------------------------------------------------


def test_cluster_scenes_empty_returns_empty() -> None:
    assert _cluster_scenes([]) == []


def test_cluster_scenes_single_entry_returns_one_scene() -> None:
    from src.models import TimelineEntry

    entry = TimelineEntry(
        image_id="img1",
        timestamp=datetime(2024, 6, 1, 9, 0),
    )
    scenes = _cluster_scenes([entry])
    assert len(scenes) == 1
    assert len(scenes[0].entries) == 1


def test_cluster_scenes_all_no_timestamp_returns_one_scene() -> None:
    from src.models import TimelineEntry

    entries = [TimelineEntry(image_id=f"img{i}") for i in range(3)]
    scenes = _cluster_scenes(entries)
    # Without timestamps, no gap can be calculated — all stay in one scene
    assert len(scenes) == 1
    assert len(scenes[0].entries) == 3


# ---------------------------------------------------------------------------
# _make_scene — label
# ---------------------------------------------------------------------------


def test_make_scene_label_morning() -> None:
    from src.models import TimelineEntry

    entry = TimelineEntry(image_id="x", timestamp=datetime(2024, 1, 1, 9, 30))
    scene = _make_scene([entry])
    assert scene.label == "morning"


def test_make_scene_label_night() -> None:
    from src.models import TimelineEntry

    entry = TimelineEntry(image_id="x", timestamp=datetime(2024, 1, 1, 22, 0))
    scene = _make_scene([entry])
    assert scene.label == "night"


def test_make_scene_start_end_times() -> None:
    from src.models import TimelineEntry

    entries = [
        TimelineEntry(image_id="a", timestamp=datetime(2024, 1, 1, 8, 0)),
        TimelineEntry(image_id="b", timestamp=datetime(2024, 1, 1, 9, 30)),
    ]
    scene = _make_scene(entries)
    assert scene.start_time == "08:00"
    assert scene.end_time == "09:30"


# ---------------------------------------------------------------------------
# _time_of_day_label boundaries
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("hour", "expected"),
    [
        (0, "early morning"),
        (5, "early morning"),
        (6, "morning"),
        (11, "morning"),
        (12, "midday"),
        (13, "midday"),
        (14, "afternoon"),
        (16, "afternoon"),
        (17, "evening"),
        (19, "evening"),
        (20, "night"),
        (23, "night"),
    ],
)
def test_time_of_day_label_boundaries(hour: int, expected: str) -> None:
    ts = datetime(2024, 1, 1, hour, 0)
    assert _time_of_day_label(ts) == expected


# ---------------------------------------------------------------------------
# _detect_gaps
# ---------------------------------------------------------------------------


def test_detect_gaps_empty_list() -> None:

    assert _detect_gaps([]) == []


def test_detect_gaps_single_date() -> None:
    from datetime import date

    assert _detect_gaps([date(2024, 6, 1)]) == []


def test_detect_gaps_one_day_apart_no_gap() -> None:
    from datetime import date

    result = _detect_gaps([date(2024, 6, 1), date(2024, 6, 2)])
    assert result == []


def test_detect_gaps_exact_threshold() -> None:
    from datetime import date

    # 2-day gap means delta == 2 → gap_days == 1
    result = _detect_gaps([date(2024, 6, 1), date(2024, 6, 3)])
    assert len(result) == 1
    assert result[0].gap_days == 1
    assert result[0].start_date == "2024-06-02"
    assert result[0].end_date == "2024-06-02"


def test_detect_gaps_multiple_gaps() -> None:
    from datetime import date

    dates = [date(2024, 6, 1), date(2024, 6, 5), date(2024, 6, 10)]
    result = _detect_gaps(dates)
    assert len(result) == 2
    assert result[0].gap_days == 3
    assert result[1].gap_days == 4
