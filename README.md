# MAE Upcoming (Proof of concept)

Automated pipeline that fetches the Princeton [Mechanical and Aerospace Engineering](https://mae.princeton.edu/events) events ICS feed, applies configurable transformation, and publishes a stable JSON file as a GitHub Release asset and on GitHub Pages.

> **This is a proof of concept, not a production service.** It exists to show campus partners what it takes to ingest a Princeton department's events as JSON, and to let them evaluate the record shape against their own site before committing to an integration. The feed is real and refreshes every 30 minutes, but endpoints, field names and hosting may change without notice, and nothing here is an official MAE service. Read it as a reference implementation to copy, not a URL to depend on.
>
> The demonstration is deliberately a *second* department rather than a rewrite: it shows which parts of an ingest pipeline transfer between two sites on the same platform and which parts do not. That distinction is the substance of the demo — see [How MAE differs from ORFE](#how-mae-differs-from-orfe).

Forked from [`pu-orfe/upcoming`](https://github.com/pu-orfe/upcoming), which does the same job for ORFE. Both departments run on Princeton's `princeton-site-builder` platform and emit structurally identical ICS, so the pipeline, schema and tooling carry over unchanged. **What does not carry over is which field means what** — see [How MAE differs from ORFE](#how-mae-differs-from-orfe) before changing anything about titles, speakers or locations.

Canonical development and publishing both happen in this repository. Scheduled refreshes run on a native GitHub Actions schedule, a small heartbeat workflow keeps the schedules from aging out, and the latest payload is deployed to GitHub Pages.

## Ownership

**Ownership is being transferred to Jeff Addo (`@jaddo`, `jaddo@princeton.edu`).** The repository has left the `pu-shd` organization and is briefly at `pubino/mae-upcoming` while the transfer to `jaddo/mae-upcoming` is pending Jeff's acceptance; the URLs below name the destination, so they resolve once that lands. Until then, `bino@princeton.edu` maintains it.

[`HANDOVER.md`](HANDOVER.md) is the ownership record and the operations runbook: what runs on what schedule, every repository variable, how to respond when the feed goes stale, and the transfer checklist. Read it before relying on anything here — and before accepting the transfer.

This remains a proof of concept. Nothing in a transfer of ownership makes it an official MAE service.

## How MAE differs from ORFE

This is the important section. MAE and ORFE put the *same information in opposite places*, and because both feeds validate against the same schema, getting it wrong produces output that is schema-valid, error-free and useless — the talk title sitting in `speaker` and the speaker sitting in `title`.

| | ORFE | MAE |
|---|---|---|
| ICS `SUMMARY` | speaker + affiliation (`Xihong Lin, Harvard University`) | **the talk title** (`Local Maps Are All You Need!`) |
| Event page | the talk title, in `.event-subtitle` | the speaker: `.field--name-field-ps-event-speaker-name`, or `.event-subtitle` on seminar pages |
| `LOCATION` | `101 - Sherrerd Hall` | `Bowen Hall 222`, `Engineering Quad J Wing/J223` |
| `CATEGORIES` | seven named series plus `FPO` | `MAE Departmental Seminars`, `Final Public Oral Exam` |
| HTML pages | fetchable | behind a Cloudflare managed challenge |

Four things follow from that, and all four are configuration:

1. **`SUMMARY` maps to `title`, not `speaker`.** `transform_config.json` at the repo root does this. It also turns off comma re-escaping, which is right for a speaker name (`Elynn Chen\, New York University`, as ORFE's downstream ingester wants it) and wrong for a title (`Winds\, Waves\, and Wakes`).
2. **Enrichment writes to `speaker`.** `ENRICH_TARGET_FIELD=speaker` and `ENRICH_SUBTITLE_SELECTOR` name the element. The selector is a comma-separated list tried **left to right**, because MAE's FPO pages carry only the speaker field while its seminar pages carry only `.event-subtitle`.
3. **Locations need a different split.** `location_strategy: "building-room"` reads `Bowen Hall 222` as name `Bowen Hall` / detail `222`. ORFE's `dash` strategy finds no separator in MAE's values and leaves `location.name` empty on every event.
4. **Enrichment needs the bot-bypass header.** `mae.princeton.edu` returns HTTP 403 to every non-browser client, including its own home page. `BOT_BYPASS_HEADER_VALUE` is sent as `x-wdsoit-bot-bypass` and gets through. Without it every enrichment pass succeeds while populating nothing.

The workflows carry MAE's values as inline defaults rather than relying only on repo variables, so a fresh clone reproduces MAE's behavior; a repo variable still overrides. `tests/test_mae_shape.py` pins the direction of all four.

One thing that transfers unchanged and is worth keeping: MAE publishes `SUMMARY:TBD` while waiting on a speaker to supply a title, and `TBD` is already a recognised missing-title sentinel. So [title provenance](#title-provenance) flags those events exactly as it flagged ORFE's untitled ones.

## Features

* Every-30-minutes + manual workflow (cron + `workflow_dispatch`)
* Daily heartbeat check that writes a tiny keepalive commit only after 35 days without a `main` branch commit
* GitHub Pages deployment of the latest production `events.json`
* ICS fetching with SHA256 change detection
* Configurable field mapping and transformation, including two location strategies
* Speaker enrichment from event pages, past Cloudflare's bot challenge
* Content enrichment (optional)
* Raw details extraction (optional), with abstract/bio pulled out of the detail panel
* Failure streak tracking with issue creation
* JSON schema validation
* Title provenance (`titleSource` / `titleIsPlaceholder`) so consumers can tell a real title from a synthesized one
* An inline feed view simulator for planning an editorial window
* Unit tests and regression testing, runnable locally or in a container

## Usage

### Release Assets

**Demonstration feed** (`latest`)
- Canonical public URL: `https://github.com/jaddo/mae-upcoming/releases/download/latest/events.json`
- Pages URL: `https://jaddo.github.io/mae-upcoming/events.json`
- Landing page: `https://jaddo.github.io/mae-upcoming/`
- Published from `jaddo/mae-upcoming`
- Triggers: Scheduled (every 30 minutes via native GitHub Actions cron), manual
- Purpose: the feed to read when evaluating the format. Stable in shape, not promised as an endpoint.

**Development** (`dev`)
- Canonical public URL: `https://github.com/jaddo/mae-upcoming/releases/download/dev/events.json`
- Pages URLs:
  - `https://jaddo.github.io/mae-upcoming/dev/events.json`
  - `https://jaddo.github.io/mae-upcoming/dev/events-nofpo.json` — the full feed minus the `Final Public Oral Exam` series
  - `https://jaddo.github.io/mae-upcoming/dev/test.json`
- Triggers: Manual (`workflow_dispatch` on the development branch you want to test)
- Purpose: Testing environment

**Development test fixture** (`test.json`)
- Contents: a static snapshot of a fully enriched MAE payload
- Intended use: remote ingest and downstream integration testing when the live production or development feeds are empty or otherwise unsuitable as test input

### A custom domain

There is no CNAME yet, so Pages serves from `jaddo.github.io/mae-upcoming`. To move to `upcoming.mae.princeton.edu`:

1. Have MAE/OIT create the DNS record pointing at `jaddo.github.io`.
2. **Only then** set the `PAGES_CNAME` repo variable to `upcoming.mae.princeton.edu` and the `SITE_BASE_URL` variable to `https://upcoming.mae.princeton.edu`.

The order matters. A `CNAME` file naming a host that does not resolve makes GitHub redirect the `github.io` URL to it, which takes the whole site down rather than degrading it. `actions/prepare-pages-artifact` writes no `CNAME` at all when the variable is empty.

### Landing pages

The Pages site has two hand-written HTML pages:

| Path | Edit this file |
|------|----------------|
| `/` | `site/index.html` |
| `/dev/` | `site/dev/index.html` |

How to ship a change:

- **`site/index.html`** (production landing): merge to `main`, then dispatch **`Publish Landing Pages`**. This workflow only rebuilds the Pages artifact (no ICS fetch, no JSON regeneration) and reuses the current `latest`/`dev` release assets for the JSON endpoints. Restricted to `main`.
- **`site/dev/index.html`** (dev landing): dispatch **`ICS to JSON (Development)`** from the branch with your edits, with `force: true`. The dev workflow publishes `site/index.html` from the branch too, so you can preview both landing pages together.

The Pages tree is assembled by the local composite action `actions/prepare-pages-artifact`, which all three workflows share.

### Publish verification

**`Verify Published Feed`** (`.github/workflows/verify_published_feed.yml`) runs every 30 minutes and answers two questions the pipeline cannot answer about itself:

| Check | Catches |
|-------|---------|
| Served bytes vs the release asset, per path | A release was published but Pages never deployed, so the site serves an older payload |
| Live ICS hash vs `ICS_SHA256` in the `latest` release body | Generation stopped, so the site and the release are stale *together* and agree with each other |

It runs on its own schedule rather than as a step in the publish job on purpose. When the publish job fails early, its remaining steps are *skipped*, not failed — a check living there would be skipped alongside the deploy it was meant to verify.

Both checks tolerate normal transients rather than paging on them:

- Pages sits behind a CDN with `max-age=600` and per-edge caches, and neither a query string nor `Cache-Control: no-cache` forces revalidation. A mismatch within a 20-minute grace window after publication is `pending`, not a fault.
- Each path is sampled several times, likely landing on different edges. **Any one matching sample passes** — it proves the deploy reached the origin, so a stale sibling edge is just serving out its TTL.
- An unreachable host is reported as `error`, never as a content problem.
- Alerting requires two consecutive failing runs, so a single blip is never actionable.

`tests/test_pipeline_contract.py` asserts that every path the Pages action publishes has a matching verify check, and that the verifier does *not* check a path nobody publishes — a stray check for the unpublished newsletter variant would report permanent drift.

Run it locally with:
```bash
GITHUB_TOKEN=$(gh auth token) python -m src.verify_published_feed \
  --base-url https://jaddo.github.io/mae-upcoming \
  --repo jaddo/mae-upcoming \
  --check "events.json=latest:events.json" \
  --ics-url https://mae.princeton.edu/feeds/events/ical.ics
```

### Local Development

Generate JSON locally. The MAE mapping comes from `transform_config.json`, which `src.main` picks up from the working directory automatically:

```bash
python -m src.main \
  --ics-url "https://mae.princeton.edu/feeds/events/ical.ics" \
  --output events.json
```

With speaker enrichment — note all three settings, since MAE needs the inverted target *and* the bypass header:

```bash
ENRICH_TARGET_FIELD=speaker \
ENRICH_SUBTITLE_SELECTOR='.field--name-field-ps-event-speaker-name, div.event-subtitle' \
BOT_BYPASS_HEADER_VALUE=1 \
python -m src.main --ics-url "$ICS_URL" --enrich-titles --enrich-raw-details --enrich-raw-extracts \
  --output events.json
```

Validate output:
```bash
python tools/validate_json.py --schema schema/events.schema.json --data events.json
```

Update the committed example after a mapping change:
```bash
python -m src.main --ics-url "file://$PWD/examples/sample_input.example.ics" --print-only > /tmp/new.json
mv /tmp/new.json examples/sample_output.expected.json
pytest tests/test_transform.py::test_example_files_roundtrip -q
```

One-liners:
- Generate and validate from your `ICS_URL`
	```bash
	make install
	ICS_URL="https://mae.princeton.edu/feeds/events/ical.ics" make gen-enriched validate
	```
- Validate a previously generated file
	```bash
	make validate
	```
- Use the example ICS and validate (with enrichment and fallback applied)
	```bash
	make example-validate-enriched
	```

### Fixtures

| File | Shape | Used by |
|------|-------|---------|
| `examples/sample_input.example.ics` | MAE's live feed, 9 events | the roundtrip test, `make example-*` |
| `examples/sample_output.expected.json` | MAE, via `transform_config.json` | `test_example_files_roundtrip` |
| `examples/dev_test_payload.json` | MAE, fully enriched | served as `/dev/test.json` |
| `tests/fixtures/orfe_shape.ics` | ORFE's shape, 14 events | provenance, windowing and `dash`/escape coverage |
| `tests/fixtures/transform_config.orfe.json` | ORFE's mapping | the tests above, pinned so the repo-root config cannot change what they see |

The ORFE-shaped fixture is kept deliberately. The code now supports both shapes, so both need covering, and the tests that use it exercise machinery (edition windowing, provenance plumbing, schema) rather than anything ORFE-specific.

## Title provenance

Every event carries two extra fields:

| Field | Meaning |
|-------|---------|
| `titleSource` | `enriched` (scraped) · `ics` (supplied by the feed — the normal case for MAE) · `fallback-speaker` · `fallback-template` · `fallback-series` |
| `titleIsPlaceholder` | `true` for the three `fallback-*` sources — the title was synthesized here, not written by a person |

The pipeline guarantees a non-empty `title` (`minLength: 1` in the schema), so an event awaiting a title still ships as something like `An MAE Departmental Seminars Talk by Dr. Maruthi Akella, UT Austin`. These fields are what let a consumer tell that apart from a real title and filter it out. Disable with `TITLE_PROVENANCE=0` or `--no-title-provenance`.

Because MAE's titles come from the feed rather than from scraping, `ics` is the normal source here and `enriched` should not appear at all: enrichment writes to `speaker`, and deliberately does **not** stamp title provenance when its target is not `title`. Tagging a scraped speaker as an `enriched` title would report a still-`TBD` title as real, which is exactly the case provenance exists to catch.

## Feed view simulator

The landing pages embed a simulator so an editor can see a window before it arrives. Pick a **target publication date** and it filters the live feed in the browser, rendering the events in the window, which of them still carry a synthesised title, how long remains before the deadline, what falls outside the window and why, and the resulting JSON.

It leads the home page and is linkable at `/#feed-simulator`.

Everything else follows the standard schedule — deadline the Tuesday of the week before at noon, coverage from publication day through that week's Sunday — and the derived deadline and coverage window are shown immediately beneath the date, so the consequence of a change is visible without opening anything. An **Advanced** panel holds the publication time, an overridable deadline date/time, and an as-of clock.

For MAE this is a planning view over `events.json`, not a preview of a separate published file — the [newsletter variant](#newsletter-variant-present-but-unwired) is not published here.

Two properties matter for trusting what it shows:

- **It filters the way the pipeline does.** Feed timestamps are naive Eastern wall clock, and because every timestamp shares one format and one zone, the simulator compares them as plain strings. That is not a shortcut — it is what makes the result independent of the viewer's own timezone. `tests/test_feed_simulator.py` asserts the JavaScript and `src/newsletter.py` agree on the window bounds and on which events fall inside them.
- **It never writes anything.** It fetches a published feed and computes in the page.

The view is deep-linkable, so a specific window can be sent to someone:

```
https://jaddo.github.io/mae-upcoming/?pub=2026-09-21&deadline=2026-09-15&now=2026-09-14T13:00#feed-simulator
```

Query parameters: `pub`, `pubtime`, `deadline`, `deadlinetime`, `now` (and `feed` on `/dev/`, which offers a choice of dev feeds).

The logic lives in `site/feed-simulator.js`, shared by both pages and deployed to the Pages root by `actions/prepare-pages-artifact`. Its core is exercised by `tests/js/` under `node --test`; `tests/test_pipeline_contract.py` asserts that any asset the pages reference is actually deployed, so the page cannot ship a 404.

## Newsletter variant (present but unwired)

ORFE publishes a second feed scoped to one newsletter edition, plus an hourly deadline watch that files a GitHub issue listing events still awaiting a title. **MAE publishes neither.** `src/newsletter.py`, `src/notify_missing_titles.py`, `schema/events-newsletter.schema.json` and all of their tests are kept and passing, but nothing in CI invokes them, and no `newsletter_config.json` is committed — ORFE's encoded ORFE's Monday-noon schedule and its Labor Day exceptions, which would be describing a schedule MAE never agreed to.

`tests/test_pipeline_contract.py` pins that state, so switching it on is a visible decision rather than a side effect.

To turn it on:

1. Copy `newsletter_config.example.json` to `newsletter_config.json` and edit it to MAE's actual publication schedule and recess blackouts.
2. Pass `--newsletter-output events-newsletter.json` and `--newsletter-config newsletter_config.json` in `ics_to_json.yml`, and restore the newsletter schema validation step.
3. Set `include-newsletter: 'true'` on the `prepare-pages-artifact` calls and pass the newsletter file inputs.
4. Re-add the edition to the skip gate. The coverage window is time-driven, not ICS-driven: it moves every publication day whether or not upstream changed. Keying the gate on the ICS hash alone would leave the variant on a stale edition through a quiet week, with no error anywhere.
5. Add `--check "events-newsletter.json=latest:events-newsletter.json"` to `verify_published_feed.yml`, and update the contract tests that currently assert the feature is off.

Experiment with it first without touching CI:

```bash
make newsletter-example     # runs against tests/fixtures/orfe_shape.ics at a pinned clock
make newsletter-validate    # the above, then validate against both schemas
python -m src.newsletter --config newsletter_config.example.json --json
```

The demo targets the ORFE-shaped fixture on purpose: its event dates straddle the pinned `--as-of`, whereas MAE's sample feed is dated 2026 and would select an empty edition.

## Legacy mirror

Mirroring to another repository is **retired** and was never wired up here. `src/mirror_release.py` and its tests are kept but unwired, so reintroduction is a workflow change rather than a rewrite. The module resolves a target repository's canonical name before mutating it and follows redirects on all HTTP methods, which matters because a renamed target otherwise fails `DELETE` with HTTP 307.

To reintroduce it, add a step like this *after* the canonical release is published, and keep `continue-on-error` so a mirror problem can never block the Pages deploy:

```yaml
- name: Mirror to legacy repository
  if: steps.check_change.outputs.skip != 'true'
  continue-on-error: true
  env:
    TARGET_GITHUB_TOKEN: ${{ secrets.LEGACY_REPOSITORY_TOKEN }}
  run: |
    python -m src.mirror_release \
      --target-repo "<owner>/<name>" --target-commitish main \
      --tag latest --title "Latest Events" --notes "..." \
      --asset events.json --latest
```

## Tests

```bash
make test                 # pytest locally
make docker-test          # the same suite in a container
make test-js              # the simulator's node suite on its own
make newsletter-validate  # the unwired variant, end to end against the ORFE-shaped fixture
make serve-site           # preview the landing pages and simulator locally
```

`tests/test_mae_shape.py` is the file to read first. It covers the ORFE→MAE inversion end to end: both location strategies (including what the wrong one does to MAE input, so nobody "simplifies" the strategy away), the `SUMMARY`→`title` mapping and its comma convention, the enrichment target and its selector priority, and abstract/bio extraction across all four markup shapes MAE editors actually produce.

`tests/test_pipeline_contract.py` covers the CI wiring — that every published path is verified, that the workflows carry MAE's inverted defaults and the bypass header, that no workflow still points at ORFE's Pages domain, and that the newsletter stays unwired.

The simulator's JavaScript is covered twice: `tests/js/feed-simulator.test.js` runs under `node --test`, and `tests/test_feed_simulator.py` runs that suite from pytest *and* cross-checks the JavaScript against `src/newsletter.py` on the same editions. Those pytest cases skip when `node` is absent (the slim container has none) but run on CI's Ubuntu runners; `test_simulator_asset_exists` fails rather than skips if the files go missing, so a deletion cannot hide behind a skip.

`docker-compose` builds from `Dockerfile` and bind-mounts the working tree, so iterating needs no rebuild. `requirements.txt` carries `tzdata` as a `zoneinfo` fallback: the schedule arithmetic needs an IANA time zone database, Windows ships none, and a slim base image is not guaranteed to keep one across revisions. A test asserts the `America/New_York` lookup resolves, so a base image that drops it fails loudly.

Tests never read a live schedule — `tests/fixtures/newsletter_config.test.json` and `newsletter_config.example.json` are the only configs they touch, so an editor changing a deadline cannot break CI in a way that looks like a code regression. `tests/conftest.py` also clears every pipeline-steering environment variable per test, including `ENRICH_TARGET_FIELD` and `LOCATION_STRATEGY`, so a value exported in your shell cannot leak into assertions.

### Abstract and bio extraction

MAE editors produce four different markup shapes for the same labelled sections, and only the first was handled before this fork:

```html
<p>Abstract:<br/>Body follows the label.</p>          <!-- label and body in one block -->
<p>Abstract: </p><p>Body in the next sibling.</p>      <!-- Enter, not Shift+Enter -->
<p><strong>Abstract:</strong></p><p>Body.</p>          <!-- label wrapped for emphasis -->
<p>Abstract:&nbsp; </p><p>Body.</p>                    <!-- non-breaking space padding -->
```

The extractor walks on to siblings when the label's own block holds no body, climbing to the nearest block-level ancestor first so an emphasis wrapper does not strand the walk. Because these bodies carry no heading between `Abstract:` and `Bio:`, the walk also stops at the next section label — otherwise an abstract swallows the bio that follows it. On MAE's live feed this took abstract extraction from 1 event out of 7 to 6 out of 6 that carry the label at all.

## Configuration reference (env vars and inputs)

These environment variables and workflow inputs control behavior at runtime.

### Core runtime

| Name | Scope | Type | Default | Purpose |
|------|-------|------|---------|---------|
| `ICS_URL` | CLI/CI | string | `https://mae.princeton.edu/feeds/events/ical.ics` in CI | Upstream ICS feed URL. Supports http(s), `file://`, or local paths. |
| `OUTPUT_FILE` | CLI/CI | string | `events.json` | Output JSON filename. |
| `REPO_VARIABLE` | CLI/CI | string | `default` | Arbitrary variable passed to `manipulate_data` (currently unused). |
| `PAGES_CNAME` | CI | string | — (empty) | Custom domain written to `pages/CNAME`. Leave unset until DNS exists; see [A custom domain](#a-custom-domain). |
| `SITE_BASE_URL` | CI | string | `https://jaddo.github.io/mae-upcoming` | Base URL the publish verifier samples. |

### Enrichment and fallback

| Name | Scope | Type | Default | Purpose |
|------|-------|------|---------|---------|
| `ENRICH_TITLES` | CLI/CI | bool | `false` (manual CLI), `true` (scheduled CI) | Enable page scraping. |
| `ENRICH_TARGET_FIELD` | CLI/CI | string | `title`; **`speaker` in CI** | Event field the scraped value is written to. MAE's page carries the speaker, so CI sets `speaker`. Title provenance is only recorded when this is `title`. |
| `ENRICH_SUBTITLE_SELECTOR` | CLI/CI | string | `div.event-subtitle`; **`.field--name-field-ps-event-speaker-name, div.event-subtitle` in CI** | CSS selector(s) to read. Comma-separated selectors are tried **left to right**, not resolved as one CSS group, so priority is explicit. |
| `ENRICH_OVERWRITE` | CLI/CI | bool | `false` | When enriching, overwrite non-empty values instead of only filling blanks. |
| `ENRICH_DEBUG` | CLI/CI | bool | `false` | Verbose enrichment logging (fetch/skip/overwrite decisions, with the selector and target field). |
| `BOT_BYPASS_HEADER_VALUE` | CLI/CI | string | `1` | Value sent as `x-wdsoit-bot-bypass`. **Required for MAE** — the site 403s every other client. |
| `FALLBACK_PREPEND_TEXT` | CLI/CI | string | `{a_an} {series} Talk by` in CI | Prefix template for titles filled from `speaker`. Supports `{series}` and `{a_an}` for automatic A/An selection based on how the next word is *pronounced*; missing keys render empty and whitespace is collapsed. Max length: 128 chars. |
| `FALLBACK_INCLUDE_SPEAKER` | CLI/CI | bool | `true` | Include speaker name in fallback titles. MAE wants this on: a `TBD` title is far more useful as `An MAE Departmental Seminars Talk by <speaker>`. CLI: `--no-fallback-speaker`. |
| `ENRICH_CONTENT` | CLI/CI | bool | `false` | Enable content scraping from the event page into `content` (fallback stays as ICS `DESCRIPTION` if not overwritten). |
| `ENRICH_CONTENT_OVERWRITE` | CLI/CI | bool | `false` | Overwrite non-empty `content` when enriching. |
| `ENRICH_CONTENT_FORMAT` | CLI/CI | enum | `text` | Output format for scraped content: `text`, `markdown` (requires `markdownify`), or `html`. |
| `ENRICH_RAW_DETAILS` | CLI/CI | bool | `false` | Enable raw HTML scraping into `rawEventDetails` (inner HTML of `.events-detail-main`). |
| `ENRICH_RAW_DETAILS_OVERWRITE` | CLI/CI | bool | `false` | Overwrite non-empty `rawEventDetails` when enriching. |
| `ENRICH_RAW_EXTRACTS` | CLI/CI | bool | `true` | Extract `rawExtractAbstract` and `rawExtractBio` from `rawEventDetails` (requires raw details enrichment). |
| `ENRICH_RAW_EXTRACTS_OVERWRITE` | CLI/CI | bool | `false` | Overwrite existing extract values. |

Boolean envs accept: `1,true,yes,on` (case-insensitive) for true.

Titles are guaranteed non-empty (enforced by `minLength: 1` in the schema). The fill order is: the feed's own `SUMMARY` → `FALLBACK_PREPEND_TEXT` template (+ speaker unless disabled) → a series-derived last resort such as `An MAE Departmental Seminars Talk` (`A Seminar Talk` when the event has no series). The fallback pass runs even when enrichment is disabled.

### Transform parameters

Set these in `transform_config.json` (the repo root file, loaded automatically) or via `--config`. Template: `transform_config.example.json`.

| Name | Type | MAE value | Purpose |
|------|------|-----------|---------|
| `field_mappings` | object | `name` → `title` | ICS attribute to output field. **This is the inversion.** |
| `placeholders` | object | seeds `speaker` | Fields seeded before enrichment. MAE seeds `speaker`; ORFE seeded `title`. |
| `location_strategy` | enum | `building-room` | `dash` reads `101 - Sherrerd Hall`; `building-room` reads `Bowen Hall 222` and `Engineering Quad J Wing/J223`. An unknown value falls back to `dash` rather than raising, so a typo degrades a location instead of stopping the feed. |
| `escape_name_commas` | bool | `false` | Re-escape commas in the `SUMMARY`-derived field. Right for a speaker, wrong for a title. |
| `target_timezone` | string | `America/New_York` | Datetime normalization target. Also `TARGET_TZ`. |
| `mark_title_provenance` | bool | `true` | Record `titleSource` when the feed itself supplies a title. |

| Name | Scope | Type | Default | Purpose |
|------|-------|------|---------|---------|
| `LOCATION_STRATEGY` | CLI/CI | enum | `dash` | Environment default for `location_strategy`; the config file wins. |
| `TARGET_TZ` | CLI/CI | string | `America/New_York` | Target timezone for datetime normalization. |
| `EXCLUDE_SERIES` | CLI/CI | string or JSON array | — | Comma-separated list or JSON array of series names to drop after transformation. |
| `FPO_SERIES_NAME` | CI | string | `Final Public Oral Exam` | Series excluded from the dev `events-nofpo.json` variant. ORFE's `FPO` matches nothing in MAE's `CATEGORIES`, which would make the filtered variant identical to the full feed. |

`EXCLUDE_SERIES` is deliberately left **unset** in production. ORFE drops its `FPO` events from the main feed; MAE's `Final Public Oral Exam` events carry real titles and are a meaningful fraction of a small feed (2 of 9 at the time of writing), so dropping them silently is an editorial decision for MAE to make rather than one to inherit. Set the repo variable to `Final Public Oral Exam` if MAE wants ORFE's behavior.

### Newsletter schedule and variant

Unwired here — see [Newsletter variant](#newsletter-variant-present-but-unwired). The knobs still work if you invoke the modules directly.

| Name | Scope | Type | Default | Purpose |
|------|-------|------|---------|---------|
| `NEWSLETTER_OUTPUT_FILE` | CLI/CI | string | — | Path for the newsletter variant. Unset means no variant is written. CLI: `--newsletter-output`. |
| `NEWSLETTER_CONFIG_FILE` | CLI/CI | string | `newsletter_config.json` | Schedule config consumed by `src.main`. CLI: `--newsletter-config`. |
| `NEWSLETTER_CONFIG` | CLI | string | `newsletter_config.json` | Schedule config consumed by `src.newsletter` and `src.notify_missing_titles`. |
| `NEWSLETTER_TZ` | CLI/CI | string | `TARGET_TZ`, else `America/New_York` | Timezone for all schedule arithmetic. |
| `NEWSLETTER_PUBLISH_WEEKDAY` | CLI/CI | `MON`..`SUN` or `0`..`6` | `MON` | Publication weekday. Monday is `0`; ISO `7` is rejected. |
| `NEWSLETTER_PUBLISH_TIME` | CLI/CI | `HH:MM[:SS]` | `12:00:00` | Publication time of day. |
| `NEWSLETTER_DEADLINE_WEEKDAY` | CLI/CI | `MON`..`SUN` or `0`..`6` | `TUE` (via offset −6) | Resolved to the most recent such weekday *strictly before* publication. |
| `NEWSLETTER_DEADLINE_OFFSET_DAYS` | CLI/CI | integer | `-6` | Raw offset from the week-start Monday. Wins over `NEWSLETTER_DEADLINE_WEEKDAY`. |
| `NEWSLETTER_DEADLINE_TIME` | CLI/CI | `HH:MM[:SS]` | `12:00:00` | Submission deadline time of day. |
| `NEWSLETTER_REMINDER_LEAD_HOURS` | CLI/CI | comma-separated numbers | `72,48,24,4` | Hours before the deadline at which the watch announces a milestone. |
| `TITLE_PROVENANCE` | CLI/CI | bool | `true` | Record `titleSource` / `titleIsPlaceholder`. CLI: `--no-title-provenance`. |

Environment wins over the config file. `--as-of` pins the clock for testing and backfill; it deliberately has **no** environment default, since a stray repo variable would freeze the edition indefinitely, and `src.main` emits a `::warning::` whenever it is used.

### GitHub Actions inputs (manual/scheduled)

| Name | Workflow | Type | Default | Purpose |
|------|----------|------|---------|---------|
| `force` | `ICS to JSON` | input | `false` | Force regeneration even if ICS content hash is unchanged. |
| `enrich_titles` | `ICS to JSON` | input | `true` | Toggle enrichment on manual runs (scheduled runs always enrich). |

CLI flags mirror the envs: `--enrich-titles`, `--enrich-overwrite`, `--enrich-content`, `--enrich-content-overwrite`, `--enrich-raw-details`, `--enrich-raw-details-overwrite`, `--enrich-raw-extracts`.
`--exclude-series` accepts comma-separated names and can be repeated; it mirrors `EXCLUDE_SERIES`.
`--no-fallback-speaker` disables including speaker in fallback titles; mirrors `FALLBACK_INCLUDE_SPEAKER=0`.
`--config` selects a transform config; `--no-title-provenance` mirrors `TITLE_PROVENANCE=0`.

### The `{a_an}` placeholder

`FALLBACK_PREPEND_TEXT` supports `{series}` and `{a_an}`, which auto-selects "A" or "An" following pronunciation rather than spelling, because spelling alone is wrong in both directions:

| Series starts with | Article | Why |
|---|---|---|
| `MAE Departmental Seminars` | **An** | Spelled out, "em" |
| `Final Public Oral Exam` | **A** | Ordinary word |
| `S. S. Wilks Memorial Seminar` | **An** | Spelled out, "ess" |
| `ORFE Department Colloquia` | **An** | Read as a word, "or-fee" |
| `University Seminar` | **A** | Vowel letter, "yoo" sound |
| `Hour-Long Seminar` | **An** | Consonant letter, vowel sound |
| `PDE Workshop` | **A** | Spelled out, "pee" |

A single letter, or an all-caps run, is treated as spelled out and judged by the name of its first letter. All-caps acronyms that are read as words instead live in `_WORD_ACRONYMS` in `src/enrich.py` — add to that set if a new one appears in the feed.
