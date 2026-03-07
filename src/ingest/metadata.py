"""EXIF metadata extraction from image files.

Extracts timestamps, GPS coordinates, camera info, and orientation
from JPEG, PNG, and HEIC images. Handles missing or corrupt EXIF
gracefully by returning None fields.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import structlog
from PIL import Image
from PIL.ExifTags import GPS as GPS_TAGS
from PIL.ExifTags import TAGS

from src.models import ImageMetadata

logger = structlog.get_logger(__name__)


def extract_metadata(image_path: str | Path, corpus_root: str | Path) -> ImageMetadata:
    """Extract EXIF metadata from an image file.

    Args:
        image_path: Absolute path to the image.
        corpus_root: Root corpus directory (for computing relative path).

    Returns:
        ImageMetadata with all available fields populated.
    """
    path = Path(image_path)
    root = Path(corpus_root)
    rel_path = str(path.relative_to(root))
    image_id = rel_path  # use relative path as image ID

    try:
        stat = path.stat()
    except OSError:
        logger.warning("image_stat_failed", path=rel_path)
        return ImageMetadata(
            image_id=image_id,
            path=rel_path,
            format=path.suffix.lower().lstrip("."),
            size_bytes=0,
        )

    base = ImageMetadata(
        image_id=image_id,
        path=rel_path,
        format=path.suffix.lower().lstrip("."),
        size_bytes=stat.st_size,
    )

    try:
        img = Image.open(path)
        exif_data = img._getexif()  # noqa: SLF001
    except Exception:
        logger.debug("exif_extraction_failed", path=rel_path)
        return base

    if not exif_data:
        return base

    decoded = _decode_exif(exif_data)

    timestamp = _parse_datetime(decoded.get("DateTimeOriginal") or decoded.get("DateTime"))
    lat, lng = _parse_gps(decoded.get("GPSInfo"))
    orientation = decoded.get("Orientation")
    camera_make = decoded.get("Make")
    camera_model = decoded.get("Model")

    base.timestamp = timestamp
    base.latitude = lat
    base.longitude = lng
    base.orientation = orientation
    base.camera_make = str(camera_make).strip() if camera_make else None
    base.camera_model = str(camera_model).strip() if camera_model else None
    base.has_gps = lat is not None and lng is not None
    base.has_timestamp = timestamp is not None

    return base


def _decode_exif(exif_data: dict) -> dict:
    """Decode numeric EXIF tags to human-readable names."""
    decoded = {}
    for tag_id, value in exif_data.items():
        tag_name = TAGS.get(tag_id, str(tag_id))
        decoded[tag_name] = value
    return decoded


def _parse_datetime(dt_str: str | None) -> datetime | None:
    """Parse EXIF datetime string to Python datetime."""
    if not dt_str or not isinstance(dt_str, str):
        return None

    for fmt in [
        "%Y:%m:%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y:%m:%d %H:%M:%S%z",
    ]:
        try:
            return datetime.strptime(dt_str.strip(), fmt)
        except ValueError:
            continue

    return None


def _parse_gps(gps_info: dict | None) -> tuple[float | None, float | None]:
    """Parse EXIF GPS info to decimal latitude and longitude."""
    if not gps_info or not isinstance(gps_info, dict):
        return None, None

    # Decode GPS tag IDs to names
    decoded_gps = {}
    for key, val in gps_info.items():
        tag_name = GPS_TAGS.get(key, str(key))
        decoded_gps[tag_name] = val

    try:
        lat = _dms_to_decimal(
            decoded_gps.get("GPSLatitude"),
            decoded_gps.get("GPSLatitudeRef", "N"),
        )
        lng = _dms_to_decimal(
            decoded_gps.get("GPSLongitude"),
            decoded_gps.get("GPSLongitudeRef", "E"),
        )
        return lat, lng
    except (TypeError, ValueError, ZeroDivisionError):
        return None, None


def _dms_to_decimal(
    dms: tuple | None,
    ref: str,
) -> float | None:
    """Convert degrees/minutes/seconds to decimal degrees."""
    if dms is None or len(dms) != 3:
        return None

    degrees = float(dms[0])
    minutes = float(dms[1])
    seconds = float(dms[2])

    decimal = degrees + minutes / 60.0 + seconds / 3600.0

    if ref in ("S", "W"):
        decimal = -decimal

    return round(decimal, 6)
