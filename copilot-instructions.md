# Copilot Instructions for `mae-upcoming`

## Project Purpose
- **This repository is a proof of concept**, presented to campus partners who are evaluating how to ingest department events from Princeton sites. Public-facing language must say so: the landing pages, the README and the repo description all read "MAE Upcoming (Proof of concept)". Do not quietly promote it to production wording -- no "canonical production feed", no stability promises about endpoints or field names. `tests/test_pipeline_contract.py` pins the labelling on both landing pages.
- Generate a normalized JSON events feed (`events.json`) from an upstream ICS calendar, with optional web-scraping enrichment for titles, content, and raw details.
- Intended for automation (GitHub Actions) and manual CLI use; schema compliance enforced via `schema/events.schema.json`.
- Canonical development and publishing both happen in `jaddo/mae-upcoming`. Legacy-repository mirroring is retired; `src/mirror_release.py` is retained, unwired, for possible reintroduction.
- `jaddo/mae-upcoming` is public so its release assets are directly shareable. Production refreshes run on a native every-30-minutes GitHub Actions schedule, a heartbeat workflow creates a tiny keepalive commit after 35 idle days so public-repo schedules do not age out, and the latest production payload is also deployed to GitHub Pages.
- **Upstream is `pu-orfe/upcoming`, and MAE reads inverted from ORFE.** MAE's ICS `SUMMARY` carries the talk title and its event page carries the speaker; ORFE is the other way round. Both validate against the same schema, so a swapped mapping produces schema-valid nonsense rather than an error. `transform_config.json` maps `name` -> `title`, `ENRICH_TARGET_FIELD=speaker` sends the scraped value to `speaker`, and `tests/test_mae_shape.py` pins the direction. Read the README's "How MAE differs from ORFE" before touching titles, speakers or locations.
- `mae.princeton.edu` sits behind a Cloudflare managed challenge that 403s every non-browser client. Enrichment only works with the `x-wdsoit-bot-bypass` header (`BOT_BYPASS_HEADER_VALUE`); without it every pass "succeeds" while populating nothing.
- The newsletter variant and deadline watch are **present but unwired** for MAE: the modules and their tests are kept and passing, but no workflow invokes them and no `newsletter_config.json` is committed. `tests/test_pipeline_contract.py` pins that, so enabling the feature is a deliberate change.

## Architecture Overview
- `src/main.py`: CLI entry point. Fetches ICS (`fetch_ics`), instantiates `ics.Calendar`, calls `transform_calendar`, and writes JSON. Handles optional enrichment based on CLI flags/env vars, then optionally writes the newsletter variant (`_write_newsletter_variant`) after the primary output.
- `src/transform.py`: Defines `TransformConfig` dataclass and transformation helpers. Maps ICS event fields to output keys, normalizes dates with `arrow`, shapes location data, and inserts configured placeholders/copies. Two location strategies: `dash` for ORFE's `101 - Sherrerd Hall`, `building-room` for MAE's `Bowen Hall 222`. `escape_name_commas` controls whether the `SUMMARY`-derived field gets ICS comma escaping re-applied -- right for a speaker, wrong for a title.
- `src/enrich.py`: Networking + parsing layer for enrichment. Statically caches headers, applies optional Markdown conversion, and offers:
  - `enrich_titles`, `fill_title_fallback`. `enrich_titles` takes a `target_field` and a `selector`; the selector may be a comma-separated list, tried **left to right** rather than handed to one `select_one` call, because CSS would resolve the group in document order instead of priority order. Title provenance is only stamped when the target is `title` -- marking a scraped speaker as an `enriched` title would report a still-`TBD` title as real.
  - `enrich_content`
  - `enrich_raw_details`, `enrich_raw_extracts`, plus extraction helpers. The abstract/bio extractors handle four markup shapes MAE editors produce (label inline, label alone in its own block, label wrapped in `<strong>`, `&nbsp;`-padded). They walk to siblings when the label block holds no body, climb to the nearest block ancestor first, and stop at the next section label -- these bodies carry no heading between `Abstract:` and `Bio:`, so without that an abstract swallows the bio.
- `src/placeholders.py`: shared title-provenance vocabulary (`TitleSource`, `is_missing_title`, `mark_title_source`). Imports nothing from the package, so both `transform` and `enrich` can depend on it without a cycle.
- `src/newsletter.py`: newsletter publication schedule and coverage windows. **Stdlib-only on purpose** -- the `Check ICS change` step in `ics_to_json.yml` runs it before `pip install`. Do not add third-party imports here, `arrow` included.
- `src/notify_missing_titles.py`: the deadline watch. Also stdlib-only; does its own GitHub HTTP via `urllib`, matching `verify_published_feed.py` / `mirror_release.py`.
- `site/feed-simulator.js`: the landing pages' feed view simulator. Reimplements the coverage-window arithmetic in browser JS; keep it in step with `src/newsletter.py` (`tests/test_feed_simulator.py` cross-checks them). Compares feed timestamps as plain strings on purpose, so results do not depend on the viewer's timezone. Shared by both pages and copied to the Pages root by the composite action. Never point it at events-newsletter.json: that file holds one edition, so simulating any other returns an empty list that reads as 'nothing scheduled'.
- `tools/validate_json.py`: JSON Schema validator using `jsonschema.Draft7Validator`. Built with no `RefResolver`, so schemas must stay self-contained (no `$ref` across files).
- `examples/`: MAE-shaped reference ICS and expected JSON snapshot used in regression tests, plus `dev_test_payload.json` served as `/dev/test.json`.
- `tests/fixtures/orfe_shape.ics` + `transform_config.orfe.json`: the ORFE-shaped feed and mapping, kept so the `dash`/escape code paths and the shape-independent machinery (windowing, provenance, schema) stay covered. Tests that use it pin the config explicitly so the repo-root `transform_config.json` cannot change what they see.
- Tests in `tests/` cover transformation, enrichment behaviors, and CLI flows (pytest + monkeypatch stubbing).

## Coding Guidelines
- Target Python 3.10+; keep type hints (`from __future__ import annotations`) and dataclasses consistent with current style.
- Avoid side effects in helpers. Functions like `transform_event`, `fetch_*`, and extractors should remain pure (depend only on args/env).
- For new enrichment logic, reuse the existing `requests.get` pattern (headers, `DEFAULT_TIMEOUT`) and make it monkeypatch-friendly (no global session state).
- Preserve JSON output formatting (indent=2). When writing files use UTF-8.
- ICS transformation: respect `TransformConfig` knobs. If adding new config fields, update defaults, loaders, and extend tests.
- Newsletter scheduling belongs in a config file, never in code or in a cron expression. The deadline moves between semesters; a cron that encodes it would drift from the config invisibly. MAE commits no live schedule -- `newsletter_config.example.json` is the template.
- New `TransformConfig` knobs that read the environment must use `field(default_factory=...)`, not a bare `os.getenv` default: a dataclass field default is evaluated once at class creation, which bakes in the value present at import and makes the knob untestable.
- New pipeline-steering env vars must be added to `_ISOLATED_ENV_NAMES` in `tests/conftest.py`, so a value exported in a developer's shell cannot leak into assertions and look like a code regression.
- Feed timestamps are naive local wall clock in `TARGET_TZ`. Lift them into an aware datetime with `newsletter.event_start_to_aware`; never strip tzinfo off a window bound, and never read a feed timestamp as UTC.
- Tests must point at `tests/fixtures/newsletter_config.test.json` or `newsletter_config.example.json`, never a live schedule.
- Anything published under `pages/` needs a matching `--check` in `verify_published_feed.yml`; `tests/test_pipeline_contract.py` enforces this.
- Keep fallback rules intact: `fill_title_fallback` only overwrite empty/`TBD` titles unless explicitly told and enforces the 128-char prefix cap.
- Handle environment switches via small helpers (`enrichment_*_enabled`). Extend them if new flags are introduced to stay testable.

## Configuration & Environment
- Core env vars: `ICS_URL`, `OUTPUT_FILE`, `REPO_VARIABLE`, `TARGET_TZ`, `LOCATION_STRATEGY`.
- MAE-specific and load-bearing: `ENRICH_TARGET_FIELD=speaker`, `ENRICH_SUBTITLE_SELECTOR`, `BOT_BYPASS_HEADER_VALUE`. The workflows carry these as inline defaults so a fresh clone reproduces MAE rather than ORFE; repo variables override.
- `PAGES_CNAME` is intentionally empty. Do not set it before `upcoming.mae.princeton.edu` exists in DNS: a `CNAME` file naming an unresolvable host redirects the `github.io` URL to it and takes the site down.
- Filtering: `EXCLUDE_SERIES` (comma-separated string or JSON array) removes events whose transformed `series` matches; CLI flag `--exclude-series` mirrors the env and can be repeated.
- Enrichment toggles: `ENRICH_TITLES`, `ENRICH_OVERWRITE`, `ENRICH_CONTENT`, `ENRICH_CONTENT_OVERWRITE`, `ENRICH_RAW_DETAILS`, `ENRICH_RAW_DETAILS_OVERWRITE`, `ENRICH_RAW_EXTRACTS`, `ENRICH_RAW_EXTRACTS_OVERWRITE`, `ENRICH_CONTENT_FORMAT`, `ENRICH_DEBUG`, `BOT_BYPASS_HEADER_VALUE`.
- Title fallback prefix via `FALLBACK_PREPEND_TEXT` (supports `{series}` etc., ignored when >=128 chars).
- CLI flags mirror env vars; prefer adding switches in `_parse_args` and associated env helpers together.

## Testing & Validation
- Use pytest: `pytest` or `pytest tests/test_transform.py::test_example_files_roundtrip -q` for focused checks.
- Tests expect network calls to be stubbed via `monkeypatch` and `DummyResp`; follow this pattern for new HTTP-dependent code.
- Validate JSON output against schema: `python tools/validate_json.py --schema schema/events.schema.json --data events.json`.
- Regression fixtures: update `examples/sample_output.expected.json` alongside logic changes; keep it small but representative.

## Development Workflow
- Install deps: `pip install -r requirements.txt` (see `Makefile install`).
- Common Make targets:
  - `make gen` / `make gen-enriched` / `make gen-raw` for local generation.
  - `make validate` / `make validate-enriched` for schema checks.
  - `make example-validate-enriched` for a quick sanity run using bundled fixtures.
- When adding CLI behavior, ensure `generate_events_json` and `main` stay aligned and update docs/README if user-facing semantics change.
- Keep GitHub Actions compatibility in mind (no interactive prompts, deterministic output ordering).

## Documentation & References
- README documents usage, env vars, and sample workflows; update it with any notable CLI or configuration changes.
- Schema updates should retain backward compatibility where possible and include validator test coverage.
- LICENSE: MIT. Honor existing contribution guidelines (see `CONTRIBUTING.md` if present).
