"""ICS event transformation utilities.

Provides configurable mapping, masking, placeholder injection, and
time/location normalization for calendar events.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Set, Iterable, Any
import os
import re
import json
from pathlib import Path
import arrow  # type: ignore

from .placeholders import TitleSource, is_missing_title, mark_title_source


@dataclass
class TransformConfig:
    target_timezone: str = os.getenv("TARGET_TZ", "America/New_York")
    time_format: str = "YYYY-MM-DDTHH:mm:ss"
    field_mappings: Dict[str, str] = field(
        default_factory=lambda: {
            "uid": "guid",
            "begin": "startTime",
            "end": "endTime",
            "url": "urlRef",
            "categories": "series",
            "description": "content",
            "name": "speaker",
        }
    )
    masked_fields: Set[str] = field(
        default_factory=lambda: {"dtstamp", "sequence", "transp", "class"}
    )
    placeholders: Dict[str, str] = field(
        default_factory=lambda: {
            "title": "",
            "cancelled": "",
            "bannerImage": "",
            "itemType": "advertisement",
        }
    )
    copies: Dict[str, str] = field(default_factory=dict)
    # How to split LOCATION into name/detail. "dash" reads ORFE's
    # "125 - Sherrerd Hall"; "building-room" reads MAE's "Bowen Hall 222".
    # default_factory, not a bare os.getenv default: a dataclass field default is
    # evaluated once at class creation, which would bake in whatever the
    # environment held at import time and make the knob untestable.
    location_strategy: str = field(
        default_factory=lambda: os.getenv("LOCATION_STRATEGY", "dash")
    )
    # Re-escape commas in the SUMMARY-derived field. The ics library hands us
    # unescaped text; ORFE's downstream ingester expects the backslashes back,
    # which is right for a speaker ("Elynn Chen\, New York University") and
    # wrong for a title ("Winds\, Waves\, and Wakes"). Off where SUMMARY maps
    # to `title`.
    escape_name_commas: bool = True
    # New configuration knobs
    join_categories: bool = True
    categories_delimiter: str = ","
    preserve_description_escapes: bool = True  # keep / add backslashes before , ;
    collapse_whitespace_in_description: bool = True
    # Control newline / fold representation in DESCRIPTION: space | literal_r | newline
    represent_newlines_as: str = "space"
    # Record titleSource/titleIsPlaceholder when the feed itself supplies a title
    mark_title_provenance: bool = True


def clean_text(value: str, collapse: bool = True) -> str:
    if not value:
        return ""
    value = value.replace("\r", "\n")
    if collapse:
        value = re.sub(r"\n+", " ", value)
        value = re.sub(r"\s+", " ", value).strip()
    return value


def escape_commas(value: str) -> str:
    return re.sub(r"(?<!\\),", r"\\,", value)


def escape_semicolons(value: str) -> str:
    return re.sub(r"(?<!\\);", r"\\;", value)


#: A trailing room designator: "222", "J223", "A10B". Anchored to the last
#: whitespace-separated token so "Bowen Hall 222" splits but "Bowen Hall" does not.
_ROOM_TOKEN = re.compile(r"^(?P<name>.*\S)\s+(?P<detail>[A-Z]?\d+[A-Za-z]?)$")


def _parse_location_dash(raw: str) -> tuple[str, str]:
    """ORFE's shape: "125 - Sherrerd Hall" -> detail "125", name "Sherrerd Hall"."""
    parts = [p.strip() for p in raw.split("-", 1)]
    if len(parts) == 2:
        return parts[1], parts[0]
    return "", parts[0]


def _parse_location_building_room(raw: str) -> tuple[str, str]:
    """MAE's shape, which carries no separator at all.

    "Engineering Quad J Wing/J223" -> name "Engineering Quad J Wing", detail "J223"
    "Bowen Hall 222"               -> name "Bowen Hall",              detail "222"
    "Bowen Hall"                   -> name "Bowen Hall",              detail ""

    Anything that does not end in a room-shaped token becomes the name outright.
    Guessing a split would be worse than declining to: the schema calls `name`
    the venue, so an unsplittable venue belongs there whole rather than in
    `detail`, which is what the dash strategy does to these values.
    """
    if "/" in raw:
        name, _, detail = raw.rpartition("/")
        return name.strip(), detail.strip()
    match = _ROOM_TOKEN.match(raw)
    if match:
        return match.group("name"), match.group("detail")
    return raw, ""


_LOCATION_STRATEGIES = {
    "dash": _parse_location_dash,
    "building-room": _parse_location_building_room,
}


def parse_location(raw: str | None, strategy: str = "dash") -> dict:
    """Split a raw ICS LOCATION into the schema's name/id/detail triple.

    Unknown strategy names fall back to "dash" rather than raising: a typo in a
    repo variable should degrade the location, not stop the feed.
    """
    if not raw:
        return {"name": "", "id": "", "detail": ""}
    parser = _LOCATION_STRATEGIES.get(strategy or "dash", _parse_location_dash)
    name, detail = parser(raw.strip())
    return {"name": name, "id": "", "detail": detail}


def format_time(arrow_dt, cfg: TransformConfig) -> str:
    if arrow_dt is None:
        return ""
    try:
        localized = arrow_dt.to(cfg.target_timezone)
    except Exception:
        localized = arrow_dt
    return localized.format(cfg.time_format)


def transform_event(event, cfg: TransformConfig) -> dict:
    out: Dict[str, object] = {}

    # Map core fields
    for attr, target in cfg.field_mappings.items():
        if attr in cfg.masked_fields:
            continue
        val = getattr(event, attr, None)
        if val is None:
            continue
        if attr in {"begin", "end"}:
            out[target] = format_time(val, cfg)
        elif attr == "description":
            desc = str(val)
            if cfg.preserve_description_escapes:
                desc = escape_commas(escape_semicolons(desc))
            rep_mode = (cfg.represent_newlines_as or "space").lower()
            collapse = cfg.collapse_whitespace_in_description and rep_mode == "space"
            desc = clean_text(desc, collapse=collapse)
            if rep_mode == "literal_r":
                desc = desc.replace("\n", "\\r")
            elif rep_mode == "newline":
                # keep newlines
                pass
            elif rep_mode == "space":
                pass
            else:
                desc = clean_text(desc, collapse=True)
            out[target] = desc
        elif attr == "name":
            text = str(val)
            out[target] = escape_commas(text) if cfg.escape_name_commas else text
        elif attr == "categories":
            if isinstance(val, (set, list, tuple)):
                if cfg.join_categories:
                    out[target] = cfg.categories_delimiter.join(sorted(map(str, val)))
                else:
                    out[target] = next(iter(val), "")
            else:  # single string
                out[target] = str(val)
        else:
            out[target] = str(val)

    # Location parsing
    out["location"] = parse_location(
        getattr(event, "location", None), cfg.location_strategy
    )

    # Placeholders
    for k, v in cfg.placeholders.items():
        out.setdefault(k, v)

    # Copy fields
    for new_field, source_field in cfg.copies.items():
        if source_field in out:
            out[new_field] = out[source_field]

    # Title provenance: only a title the feed actually supplied counts as 'ics'.
    # Checked after `copies` so a copies entry that fills `title` is caught too;
    # the empty placeholder title seeded above is correctly left untagged.
    if cfg.mark_title_provenance and not is_missing_title(out.get("title")):
        mark_title_source(out, TitleSource.ICS)

    return out


def transform_calendar(calendar, cfg: TransformConfig | None = None) -> List[dict]:
    cfg = cfg or TransformConfig()
    events = [transform_event(ev, cfg) for ev in sorted(calendar.events, key=lambda e: e.begin or "")]
    return events


def load_config(path: str | os.PathLike | None) -> TransformConfig:
    """Load a TransformConfig from a JSON file if it exists; else defaults."""
    if not path:
        return TransformConfig()
    p = Path(path)
    if not p.exists():
        return TransformConfig()
    data: Dict[str, Any] = json.loads(p.read_text(encoding="utf-8"))
    cfg = TransformConfig()
    for field_name in [
        "target_timezone",
        "time_format",
        "field_mappings",
        "masked_fields",
        "placeholders",
        "copies",
        "mark_title_provenance",
        "location_strategy",
        "escape_name_commas",
    ]:
        if field_name in data and data[field_name] is not None:
            setattr(cfg, field_name, data[field_name])
    if isinstance(cfg.masked_fields, list):  # type: ignore
        cfg.masked_fields = set(cfg.masked_fields)  # type: ignore
    return cfg
