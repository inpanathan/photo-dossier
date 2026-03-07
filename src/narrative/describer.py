"""Photo describer using a Vision-Language Model (VLM).

Generates natural language descriptions of photos using
Qwen2.5-VL via vLLM's OpenAI-compatible API on the 7810 node.
"""

from __future__ import annotations

import base64
import time
from pathlib import Path

import httpx
import structlog

from src.models import ImageMetadata, SubjectType, TimelineEntry
from src.utils.config import settings

logger = structlog.get_logger(__name__)

_HUMAN_SYSTEM_PROMPT = (
    "You are analyzing a photo of a person. Describe what the person is doing, "
    "their approximate location/setting, their clothing, and any notable objects "
    "or people around them. Be factual and concise (2-3 sentences). "
    "Do not speculate about identity or make assumptions about private details."
)

_PET_SYSTEM_PROMPT = (
    "You are analyzing a photo of a pet (cat or dog). Describe what the animal "
    "is doing, the setting/environment, and any notable features or objects. "
    "Be factual and concise (2-3 sentences)."
)


class PhotoDescriber:
    """Describes photos using a Vision-Language Model."""

    def __init__(self, http_client: httpx.Client | None = None) -> None:
        self._client = http_client or httpx.Client(
            base_url=settings.narrative.vlm_base_url,
            timeout=60.0,
        )

    def describe(
        self,
        image_path: str | Path,
        subject_type: SubjectType,
        metadata: ImageMetadata | None = None,
    ) -> str:
        """Generate a text description of a photo.

        Args:
            image_path: Path to the image file.
            subject_type: Whether the subject is human or pet.
            metadata: Optional metadata for context hints.

        Returns:
            Natural language description of the photo.
        """
        start = time.monotonic()
        path = Path(image_path)

        if not path.exists():
            logger.warning("describe_image_not_found", path=str(path))
            return _fallback_description(metadata, subject_type)

        # Encode image to base64
        image_data = base64.b64encode(path.read_bytes()).decode("utf-8")
        suffix = path.suffix.lower().lstrip(".")
        mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png"}.get(
            suffix, "image/jpeg"
        )

        # Build context hint from metadata
        context = _build_context_hint(metadata)

        system_prompt = (
            _HUMAN_SYSTEM_PROMPT if subject_type == SubjectType.HUMAN else _PET_SYSTEM_PROMPT
        )

        user_content: list[dict] = []
        if context:
            user_content.append({"type": "text", "text": context})
        user_content.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:{mime};base64,{image_data}"},
            }
        )
        user_content.append({"type": "text", "text": "Describe what you see in this photo."})

        try:
            response = self._client.post(
                "/chat/completions",
                json={
                    "model": settings.narrative.vlm_model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content},
                    ],
                    "max_tokens": settings.narrative.vlm_max_tokens,
                    "temperature": settings.narrative.temperature,
                },
            )
            response.raise_for_status()
            result = response.json()
            description: str = result["choices"][0]["message"]["content"].strip()

            elapsed_ms = round((time.monotonic() - start) * 1000)
            usage = result.get("usage", {})
            logger.info(
                "photo_described",
                image=str(path.name),
                subject_type=subject_type,
                latency_ms=elapsed_ms,
                input_tokens=usage.get("prompt_tokens"),
                output_tokens=usage.get("completion_tokens"),
            )

            return description

        except httpx.HTTPStatusError as e:
            logger.error(
                "vlm_request_failed",
                status_code=e.response.status_code,
                image=str(path.name),
            )
            return _fallback_description(metadata, subject_type)

        except httpx.ConnectError:
            logger.error("vlm_unavailable", base_url=str(self._client.base_url))
            return _fallback_description(metadata, subject_type)

    def describe_batch(
        self,
        entries: list[TimelineEntry],
        subject_type: SubjectType,
        metadata_map: dict[str, ImageMetadata] | None = None,
    ) -> dict[str, str]:
        """Describe multiple photos, returning a map of image_id -> description.

        Args:
            entries: Timeline entries to describe.
            subject_type: Subject type for prompt context.
            metadata_map: Optional map of image_id to metadata.

        Returns:
            Dict mapping image_id to description text.
        """
        descriptions: dict[str, str] = {}
        meta_map = metadata_map or {}

        for entry in entries:
            meta = meta_map.get(entry.image_id)
            desc = self.describe(entry.image_path, subject_type, meta)
            descriptions[entry.image_id] = desc

        logger.info(
            "batch_description_completed",
            total=len(entries),
            described=len(descriptions),
        )

        return descriptions

    def close(self) -> None:
        self._client.close()


def _build_context_hint(metadata: ImageMetadata | None) -> str:
    """Build a contextual hint from metadata to guide the VLM."""
    if not metadata:
        return ""

    parts = []
    if metadata.has_timestamp and metadata.timestamp:
        parts.append(f"Taken at {metadata.timestamp.strftime('%Y-%m-%d %H:%M')}")
    if metadata.camera_make:
        parts.append(f"Camera: {metadata.camera_make} {metadata.camera_model or ''}")

    if not parts:
        return ""

    return "Context: " + ". ".join(parts) + "."


def _fallback_description(metadata: ImageMetadata | None, subject_type: SubjectType) -> str:
    """Generate a metadata-only description when VLM is unavailable."""
    subject = "person" if subject_type == SubjectType.HUMAN else "pet"
    parts = [f"Photo of a {subject}"]

    if metadata:
        if metadata.has_timestamp and metadata.timestamp:
            parts.append(f"taken on {metadata.timestamp.strftime('%B %d, %Y at %H:%M')}")
        if metadata.has_gps:
            parts.append(f"at coordinates ({metadata.latitude:.4f}, {metadata.longitude:.4f})")

    return ". ".join(parts) + "."
