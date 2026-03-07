"""Dossier narrative generator using an LLM.

Takes photo descriptions, timeline structure, and patterns to
produce a multi-day narrative dossier via Qwen2.5-14B-Instruct-AWQ
running on local vLLM.
"""

from __future__ import annotations

import json
import time

import httpx
import structlog

from src.models import (
    Dossier,
    DossierDay,
    DossierEntry,
    Pattern,
    SubjectType,
    Timeline,
)
from src.utils.config import settings

logger = structlog.get_logger(__name__)


class DossierGenerator:
    """Generates narrative dossiers from photo timelines using an LLM."""

    def __init__(self, http_client: httpx.Client | None = None) -> None:
        self._client = http_client or httpx.Client(
            base_url=settings.narrative.llm_base_url,
            timeout=120.0,
        )

    def generate(
        self,
        session_id: str,
        timeline: Timeline,
        descriptions: dict[str, str],
        patterns: list[Pattern],
    ) -> Dossier:
        """Generate a complete dossier from timeline data and photo descriptions.

        Args:
            session_id: Query session ID this dossier is for.
            timeline: Chronological timeline with day groups.
            descriptions: Map of image_id -> VLM description text.
            patterns: Detected cross-day patterns.

        Returns:
            Complete Dossier with executive summary, per-day entries, and patterns.
        """
        start = time.monotonic()

        prompt = _build_prompt(timeline, descriptions, patterns)
        system_prompt = _system_prompt(timeline.subject_type)

        try:
            response = self._client.post(
                "/chat/completions",
                json={
                    "model": settings.narrative.llm_model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt},
                    ],
                    "max_tokens": settings.narrative.llm_max_tokens,
                    "temperature": settings.narrative.temperature,
                    "response_format": {"type": "json_object"},
                },
            )
            response.raise_for_status()
            result = response.json()
            content = result["choices"][0]["message"]["content"]

            elapsed_ms = round((time.monotonic() - start) * 1000)
            usage = result.get("usage", {})
            logger.info(
                "dossier_generated",
                session_id=session_id,
                latency_ms=elapsed_ms,
                model=settings.narrative.llm_model,
                input_tokens=usage.get("prompt_tokens"),
                output_tokens=usage.get("completion_tokens"),
            )

            return _parse_dossier(session_id, timeline, content, patterns)

        except httpx.HTTPStatusError as e:
            logger.error(
                "llm_request_failed",
                session_id=session_id,
                status_code=e.response.status_code,
            )
            return _fallback_dossier(session_id, timeline, descriptions, patterns)

        except httpx.ConnectError:
            logger.error("llm_unavailable", base_url=str(self._client.base_url))
            return _fallback_dossier(session_id, timeline, descriptions, patterns)

        except (json.JSONDecodeError, KeyError, IndexError) as e:
            logger.error("llm_response_parse_failed", error=str(e))
            return _fallback_dossier(session_id, timeline, descriptions, patterns)

    def close(self) -> None:
        self._client.close()


def _system_prompt(subject_type: SubjectType) -> str:
    """Build the system prompt based on subject type."""
    subject = "person" if subject_type == SubjectType.HUMAN else "pet (cat or dog)"
    return (
        f"You are an intelligence analyst creating a surveillance-style dossier "
        f"about a {subject} based on photo evidence. "
        f"Your output must be valid JSON matching the specified schema. "
        f"Be factual and objective. Use uncertainty language for low-confidence entries. "
        f"Group observations by day and provide a brief executive summary."
    )


def _build_prompt(
    timeline: Timeline,
    descriptions: dict[str, str],
    patterns: list[Pattern],
) -> str:
    """Build the user prompt with all evidence."""
    parts = []

    parts.append("Generate a narrative dossier from the following photo evidence.\n")
    parts.append(f"Subject type: {timeline.subject_type.value}")
    parts.append(
        f"Date range: {timeline.date_range_start or 'unknown'} to "
        f"{timeline.date_range_end or 'unknown'}"
    )
    parts.append(f"Total photos: {sum(len(d.entries) for d in timeline.days)}")
    parts.append(f"Active days: {timeline.active_days}\n")

    # Per-day evidence
    parts.append("## Photo Evidence by Day\n")
    for day in timeline.days:
        parts.append(f"### {day.day_label} ({day.date})")
        for entry in day.entries:
            desc = descriptions.get(entry.image_id, "No description available.")
            time_str = entry.time or "unknown time"
            loc_str = entry.location.display_name if entry.location else "unknown location"
            confidence = f"{entry.confidence:.0%}" if entry.confidence else "N/A"
            parts.append(f"- [{time_str}] at {loc_str} (match confidence: {confidence}): {desc}")
        parts.append("")

    # Detected patterns
    if patterns:
        parts.append("## Detected Patterns\n")
        for p in patterns:
            parts.append(f"- **{p.pattern_type}**: {p.description}")
        parts.append("")

    # Gaps
    if timeline.gaps:
        parts.append("## Gaps in Coverage\n")
        for g in timeline.gaps:
            parts.append(f"- No photos from {g.start_date} to {g.end_date} ({g.gap_days} days)")
        parts.append("")

    # Output schema
    parts.append("## Required JSON Output Schema\n")
    parts.append("""```json
{
  "executive_summary": "2-3 sentence overview of the subject's activities",
  "days": [
    {
      "date": "YYYY-MM-DD",
      "day_summary": "1-2 sentence summary of the day",
      "entries": [
        {
          "time": "HH:MM or null",
          "location": "location name or null",
          "description": "narrative description of this observation",
          "confidence_label": "high|medium|low"
        }
      ]
    }
  ],
  "confidence_notes": ["any caveats about data quality or gaps"]
}
```""")

    return "\n".join(parts)


def _parse_dossier(
    session_id: str,
    timeline: Timeline,
    content: str,
    patterns: list[Pattern],
) -> Dossier:
    """Parse the LLM JSON response into a Dossier model."""
    data = json.loads(content)

    days = []
    # Build image_url map from timeline for cross-referencing
    entry_map: dict[str, dict] = {}
    for day in timeline.days:
        for entry in day.entries:
            entry_map[entry.image_id] = {
                "image_url": entry.image_url,
                "image_path": entry.image_path,
            }

    for day_data in data.get("days", []):
        entries = []
        day_date = day_data.get("date", "")

        # Match LLM entries back to timeline entries for image URLs
        timeline_day = next((d for d in timeline.days if d.date == day_date), None)
        timeline_entries = timeline_day.entries if timeline_day else []

        for i, entry_data in enumerate(day_data.get("entries", [])):
            # Try to pair with timeline entry by index
            tl_entry = timeline_entries[i] if i < len(timeline_entries) else None

            entries.append(
                DossierEntry(
                    time=entry_data.get("time"),
                    location=entry_data.get("location"),
                    description=entry_data.get("description", ""),
                    image_url=tl_entry.image_url if tl_entry else "",
                    image_path=tl_entry.image_path if tl_entry else "",
                    confidence=tl_entry.confidence if tl_entry else 0.0,
                    confidence_label=entry_data.get("confidence_label", "medium"),
                )
            )

        days.append(
            DossierDay(
                date=day_date,
                day_label=day_data.get("day_label", day_date),
                day_summary=day_data.get("day_summary", ""),
                entries=entries,
            )
        )

    total_photos = sum(len(d.entries) for d in timeline.days)

    return Dossier(
        session_id=session_id,
        subject_type=timeline.subject_type,
        executive_summary=data.get("executive_summary", ""),
        date_range=f"{timeline.date_range_start} to {timeline.date_range_end}",
        total_photos=total_photos,
        total_days=timeline.active_days,
        days=days,
        patterns=patterns,
        confidence_notes=data.get("confidence_notes", []),
    )


def _fallback_dossier(
    session_id: str,
    timeline: Timeline,
    descriptions: dict[str, str],
    patterns: list[Pattern],
) -> Dossier:
    """Build a basic dossier without LLM when the service is unavailable."""
    days = []
    for day in timeline.days:
        entries = []
        for entry in day.entries:
            desc = descriptions.get(entry.image_id, "Photo observation.")
            loc_str = entry.location.display_name if entry.location else None
            entries.append(
                DossierEntry(
                    time=entry.time,
                    location=loc_str,
                    description=desc,
                    image_url=entry.image_url,
                    image_path=entry.image_path,
                    confidence=entry.confidence,
                    confidence_label="medium",
                )
            )
        days.append(
            DossierDay(
                date=day.date,
                day_label=day.day_label,
                day_summary=f"{len(entries)} photos on this day.",
                entries=entries,
            )
        )

    total_photos = sum(len(d.entries) for d in timeline.days)

    return Dossier(
        session_id=session_id,
        subject_type=timeline.subject_type,
        executive_summary=(
            f"Dossier for {timeline.subject_type.value} subject spanning "
            f"{timeline.date_range_start or 'unknown'} to {timeline.date_range_end or 'unknown'}. "
            f"{total_photos} photos across {timeline.active_days} active days. "
            f"(Generated without LLM — descriptions only.)"
        ),
        date_range=f"{timeline.date_range_start} to {timeline.date_range_end}",
        total_photos=total_photos,
        total_days=timeline.active_days,
        days=days,
        patterns=patterns,
        confidence_notes=["Dossier generated without LLM. Descriptions are basic."],
    )
