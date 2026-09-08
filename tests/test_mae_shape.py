"""MAE's feed shape, which is ORFE's inverted.

ORFE puts the speaker in the ICS SUMMARY and the talk title on the event page in
`.event-subtitle`. MAE puts the title in SUMMARY and the speaker on the page.
Both feeds come from `princeton-site-builder` and are byte-for-byte the same
*structure*, so nothing here fails loudly when it is wrong -- a swapped mapping
produces schema-valid output with the two fields transposed. These tests pin the
direction.
"""
import json
from pathlib import Path

import pytest
from ics import Calendar

from src import main as main_mod
from src.enrich import (
    enrich_titles,
    extract_abstract_from_raw_details,
    extract_bio_from_raw_details,
)
from src.placeholders import TITLE_PLACEHOLDER_FIELD, TITLE_SOURCE_FIELD
from src.transform import (
    TransformConfig,
    load_config,
    parse_location,
    transform_calendar,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
MAE_ICS = REPO_ROOT / "examples" / "sample_input.example.ics"
MAE_CONFIG = REPO_ROOT / "transform_config.json"


# --------------------------------------------------------------------------
# location strategies
# --------------------------------------------------------------------------


class TestLocationStrategies:
    """MAE's LOCATION carries no separator, so the dash split leaves it nameless."""

    @pytest.mark.parametrize(
        "raw,name,detail",
        [
            ("Bowen Hall 222", "Bowen Hall", "222"),
            ("Engineering Quad J Wing/J223", "Engineering Quad J Wing", "J223"),
            ("Bowen Hall", "Bowen Hall", ""),
            ("Friend Center 101", "Friend Center", "101"),
            ("Maeder Hall A10", "Maeder Hall", "A10"),
        ],
    )
    def test_building_room_splits_trailing_room_token(self, raw, name, detail):
        assert parse_location(raw, "building-room") == {
            "name": name,
            "id": "",
            "detail": detail,
        }

    def test_building_room_keeps_unsplittable_venue_as_the_name(self):
        """The schema calls `name` the venue, so an unsplittable venue goes there.

        This is the case the dash strategy gets backwards on MAE input: it would
        put the whole string in `detail` and leave `name` empty.
        """
        got = parse_location("Princeton Plasma Physics Laboratory", "building-room")
        assert got["name"] == "Princeton Plasma Physics Laboratory"
        assert got["detail"] == ""

    def test_dash_strategy_still_reads_the_orfe_shape(self):
        assert parse_location("101 - Sherrerd Hall", "dash") == {
            "name": "Sherrerd Hall",
            "id": "",
            "detail": "101",
        }

    def test_dash_is_the_default_so_orfe_behavior_is_unchanged(self):
        assert parse_location("101 - Sherrerd Hall") == parse_location(
            "101 - Sherrerd Hall", "dash"
        )

    def test_dash_strategy_mangles_mae_input(self):
        """Documents *why* the strategy exists, so nobody 'simplifies' it away."""
        got = parse_location("Bowen Hall 222", "dash")
        assert got["name"] == ""
        assert got["detail"] == "Bowen Hall 222"

    def test_unknown_strategy_falls_back_to_dash_rather_than_raising(self):
        """A typo in a repo variable should degrade a location, not stop the feed."""
        assert parse_location("101 - Sherrerd Hall", "no-such-strategy") == {
            "name": "Sherrerd Hall",
            "id": "",
            "detail": "101",
        }

    @pytest.mark.parametrize("raw", ["", None])
    def test_empty_location_is_the_empty_triple(self, raw):
        assert parse_location(raw, "building-room") == {
            "name": "",
            "id": "",
            "detail": "",
        }

    def test_strategy_is_read_from_the_environment_per_instance(self, monkeypatch):
        monkeypatch.setenv("LOCATION_STRATEGY", "building-room")
        assert TransformConfig().location_strategy == "building-room"


# --------------------------------------------------------------------------
# SUMMARY -> title, and the comma convention that goes with it
# --------------------------------------------------------------------------


class TestSummaryMapsToTitle:
    def test_mae_config_maps_summary_to_title_not_speaker(self):
        cfg = load_config(MAE_CONFIG)
        assert cfg.field_mappings["name"] == "title"

    def test_mae_config_leaves_speaker_for_enrichment(self):
        cfg = load_config(MAE_CONFIG)
        assert cfg.placeholders.get("speaker") == ""
        assert "title" not in cfg.placeholders

    def test_commas_are_not_re_escaped_in_a_title(self):
        """`Winds\\, Waves\\, and Wakes` is right for a speaker, wrong for a title."""
        cfg = load_config(MAE_CONFIG)
        cal = Calendar(MAE_ICS.read_text(encoding="utf-8"))
        events = transform_calendar(cal, cfg)
        titled = [e for e in events if "Winds" in e["title"]]
        assert titled, "fixture should carry the comma-bearing title"
        assert titled[0]["title"].startswith("Winds, Waves, and Wakes")
        assert "\\," not in titled[0]["title"]

    def test_escaping_stays_on_by_default_for_the_orfe_shape(self):
        cfg = TransformConfig()
        assert cfg.escape_name_commas is True

    def test_titles_from_the_feed_are_marked_ics_not_placeholder(self):
        cfg = load_config(MAE_CONFIG)
        cal = Calendar(MAE_ICS.read_text(encoding="utf-8"))
        events = transform_calendar(cal, cfg)
        real = [e for e in events if e["title"].lower() != "tbd"]
        assert real, "fixture should carry real titles"
        for ev in real:
            assert ev[TITLE_SOURCE_FIELD] == "ics"
            assert ev[TITLE_PLACEHOLDER_FIELD] is False

    def test_a_tbd_summary_is_not_mistaken_for_a_real_title(self):
        """MAE really does publish `SUMMARY:TBD` while awaiting a title."""
        cfg = load_config(MAE_CONFIG)
        cal = Calendar(MAE_ICS.read_text(encoding="utf-8"))
        events = transform_calendar(cal, cfg)
        tbd = [e for e in events if e["title"].lower() == "tbd"]
        assert tbd, "fixture should carry the TBD event"
        assert TITLE_SOURCE_FIELD not in tbd[0]


# --------------------------------------------------------------------------
# enrichment target
# --------------------------------------------------------------------------


class _Resp:
    def __init__(self, text, status_code=200):
        self.text = text
        self.status_code = status_code

    def raise_for_status(self):
        if not (200 <= self.status_code < 300):
            raise RuntimeError("http error")


@pytest.fixture
def stub_page(monkeypatch):
    """Serve one fixed HTML body for every enrichment fetch."""

    def _install(html):
        monkeypatch.setattr(
            "src.enrich.requests.get",
            lambda url, timeout=15, headers=None: _Resp(html),  # noqa: ARG005
        )

    return _install


MAE_SPEAKER_FIELD = (
    '<div class="field field--name-field-ps-event-speaker-name">'
    "Dr. Rebecca Ciez, Purdue University</div>"
)


class TestEnrichmentTarget:
    def test_scraped_value_lands_in_the_configured_field(self, stub_page):
        stub_page(f"<html><body>{MAE_SPEAKER_FIELD}</body></html>")
        events = [{"urlRef": "https://mae.princeton.edu/events/2026/x", "speaker": ""}]
        stats = enrich_titles(
            events,
            True,
            target_field="speaker",
            selector=".field--name-field-ps-event-speaker-name",
        )
        assert stats.updated == 1
        assert events[0]["speaker"] == "Dr. Rebecca Ciez, Purdue University"

    def test_a_title_from_the_feed_survives_speaker_enrichment(self, stub_page):
        stub_page(f"<html><body>{MAE_SPEAKER_FIELD}</body></html>")
        events = [
            {
                "urlRef": "https://mae.princeton.edu/events/2026/x",
                "title": "Industrial Electrification",
                "speaker": "",
            }
        ]
        enrich_titles(
            events,
            True,
            target_field="speaker",
            selector=".field--name-field-ps-event-speaker-name",
        )
        assert events[0]["title"] == "Industrial Electrification"

    def test_speaker_enrichment_does_not_claim_the_title_was_enriched(self, stub_page):
        """Tagging titleSource='enriched' here would report a TBD title as real."""
        stub_page(f"<html><body>{MAE_SPEAKER_FIELD}</body></html>")
        events = [{"urlRef": "https://mae.princeton.edu/events/2026/x", "speaker": ""}]
        enrich_titles(
            events,
            True,
            target_field="speaker",
            selector=".field--name-field-ps-event-speaker-name",
            mark_provenance=True,
        )
        assert TITLE_SOURCE_FIELD not in events[0]
        assert TITLE_PLACEHOLDER_FIELD not in events[0]

    def test_title_target_still_records_provenance(self, stub_page):
        """The ORFE path is unchanged: a scraped *title* is real, and says so."""
        stub_page('<html><body><div class="event-subtitle">A Real Title</div></body></html>')
        events = [{"urlRef": "https://orfe.princeton.edu/events/2026/x", "title": ""}]
        enrich_titles(events, True, target_field="title", selector="div.event-subtitle")
        assert events[0]["title"] == "A Real Title"
        assert events[0][TITLE_SOURCE_FIELD] == "enriched"
        assert events[0][TITLE_PLACEHOLDER_FIELD] is False

    def test_defaults_come_from_the_environment(self, stub_page, monkeypatch):
        monkeypatch.setenv("ENRICH_TARGET_FIELD", "speaker")
        monkeypatch.setenv(
            "ENRICH_SUBTITLE_SELECTOR", ".field--name-field-ps-event-speaker-name"
        )
        stub_page(f"<html><body>{MAE_SPEAKER_FIELD}</body></html>")
        events = [{"urlRef": "https://mae.princeton.edu/events/2026/x"}]
        enrich_titles(events, True)
        assert events[0]["speaker"] == "Dr. Rebecca Ciez, Purdue University"

    def test_selector_list_is_tried_in_listed_order_not_document_order(self, stub_page):
        """MAE seminar pages have only the subtitle; FPO pages only the speaker field.

        One `select_one` call with a comma group would return whichever comes
        first in the document, so priority has to be explicit.
        """
        html = (
            "<html><body>"
            '<div class="event-subtitle">SECOND CHOICE</div>'
            '<div class="field--name-field-ps-event-speaker-name">FIRST CHOICE</div>'
            "</body></html>"
        )
        stub_page(html)
        events = [{"urlRef": "https://mae.princeton.edu/events/2026/x"}]
        enrich_titles(
            events,
            True,
            target_field="speaker",
            selector=".field--name-field-ps-event-speaker-name, div.event-subtitle",
        )
        assert events[0]["speaker"] == "FIRST CHOICE"

    def test_selector_list_falls_through_to_the_next_choice(self, stub_page):
        stub_page(
            '<html><body><div class="event-subtitle">FALLBACK</div></body></html>'
        )
        events = [{"urlRef": "https://mae.princeton.edu/events/2026/x"}]
        enrich_titles(
            events,
            True,
            target_field="speaker",
            selector=".field--name-field-ps-event-speaker-name, div.event-subtitle",
        )
        assert events[0]["speaker"] == "FALLBACK"


# --------------------------------------------------------------------------
# abstract / bio extraction across MAE's markup shapes
# --------------------------------------------------------------------------


#: What MAE editors actually produce. The first is the only shape the original
#: extractor handled; the rest returned empty.
INLINE_BREAK = (
    '<div class="field__item"><p>Abstract:<br/>Inline abstract body.</p>'
    "<p>Bio:<br/>Inline bio body.</p></div>"
)
SIBLING_PARAGRAPH = (
    '<div class="field__item"><p>Abstract: </p><p>Sibling abstract body.</p>'
    "<p>Bio: </p><p>Sibling bio body.</p></div>"
)
STRONG_WRAPPED = (
    '<div class="field__item"><p><strong>Abstract:</strong></p>'
    "<p>Wrapped abstract body.</p>"
    "<p><strong>Bio:</strong></p><p>Wrapped bio body.</p></div>"
)
NBSP_MARKER = (
    '<div class="field__item"><p>Abstract:&nbsp; </p><p>Nbsp abstract body.</p>'
    "<p>Bio:&nbsp; </p><p>Nbsp bio body.</p></div>"
)


class TestAbstractAndBioMarkupShapes:
    @pytest.mark.parametrize(
        "html,expected",
        [
            (INLINE_BREAK, "Inline abstract body."),
            (SIBLING_PARAGRAPH, "Sibling abstract body."),
            (STRONG_WRAPPED, "Wrapped abstract body."),
            (NBSP_MARKER, "Nbsp abstract body."),
        ],
    )
    def test_abstract_extracted_from_every_shape(self, html, expected):
        assert extract_abstract_from_raw_details(html) == expected

    @pytest.mark.parametrize(
        "html,expected",
        [
            (INLINE_BREAK, "Inline bio body."),
            (SIBLING_PARAGRAPH, "Sibling bio body."),
            (STRONG_WRAPPED, "Wrapped bio body."),
            (NBSP_MARKER, "Nbsp bio body."),
        ],
    )
    def test_bio_extracted_from_every_shape(self, html, expected):
        assert extract_bio_from_raw_details(html) == expected

    @pytest.mark.parametrize(
        "html", [INLINE_BREAK, SIBLING_PARAGRAPH, STRONG_WRAPPED, NBSP_MARKER]
    )
    def test_abstract_never_swallows_the_bio(self, html):
        """These bodies carry no heading between the two sections to break on."""
        assert "bio body" not in extract_abstract_from_raw_details(html).lower()

    def test_abstract_walk_stops_at_a_multi_paragraph_boundary(self):
        html = (
            '<div class="field__item"><p>Abstract: </p>'
            "<p>First abstract paragraph.</p><p>Second abstract paragraph.</p>"
            "<p>Bio: </p><p>The bio.</p></div>"
        )
        result = extract_abstract_from_raw_details(html)
        assert "First abstract paragraph." in result
        assert "Second abstract paragraph." in result
        assert "The bio." not in result

    def test_a_body_with_no_labels_yields_nothing(self):
        """MAE publishes some descriptions with no Abstract label at all."""
        html = (
            '<div class="field__item"><p>How is it possible that a quarter of '
            "the Nobel Prizes went to astrophysics?</p></div>"
        )
        assert extract_abstract_from_raw_details(html) == ""
        assert extract_bio_from_raw_details(html) == ""


# --------------------------------------------------------------------------
# end to end, over the committed MAE fixture
# --------------------------------------------------------------------------


class TestMaePipelineEndToEnd:
    def test_pipeline_produces_titles_from_the_feed_and_validates(self, tmp_path):
        from jsonschema import Draft7Validator

        out = tmp_path / "events.json"
        rc = main_mod.main(
            ["--ics-url", str(MAE_ICS), "--output", str(out), "--config", str(MAE_CONFIG)]
        )
        assert rc == 0
        data = json.loads(out.read_text(encoding="utf-8"))
        assert len(data) == 9

        schema = json.loads(
            (REPO_ROOT / "schema" / "events.schema.json").read_text(encoding="utf-8")
        )
        assert not list(Draft7Validator(schema).iter_errors(data))

        by_source = {}
        for ev in data:
            by_source.setdefault(ev[TITLE_SOURCE_FIELD], []).append(ev)
        # Eight real titles straight from SUMMARY; the ninth is MAE's `TBD`.
        assert len(by_source["ics"]) == 8
        assert sum(1 for ev in data if ev[TITLE_PLACEHOLDER_FIELD]) == 1

    def test_every_location_gets_a_venue_name(self, tmp_path):
        """The regression the dash strategy would cause: name empty on all nine."""
        out = tmp_path / "events.json"
        main_mod.main(
            ["--ics-url", str(MAE_ICS), "--output", str(out), "--config", str(MAE_CONFIG)]
        )
        data = json.loads(out.read_text(encoding="utf-8"))
        assert all(ev["location"]["name"] for ev in data)

    def test_generate_events_json_honors_the_mae_config(self, tmp_path):
        """It used to hardcode ORFE's mapping regardless of the config file."""
        out = tmp_path / "events.json"
        main_mod.generate_events_json(
            ics_url=str(MAE_ICS), output_path=out, config_path=str(MAE_CONFIG)
        )
        data = json.loads(out.read_text(encoding="utf-8"))
        titles = {ev["title"] for ev in data}
        assert "Local Maps Are All You Need!" in titles
