"""Contract tests over the CI wiring.

These catch the class of bug unit tests structurally cannot: a workflow that
publishes a file nobody verifies, a caller that forgets a required action input,
or a Pages tree that publishes a file nobody verifies.

MAE does not ship the newsletter variant: src/newsletter.py and
src/notify_missing_titles.py are present and tested but deliberately unwired.
Several tests here pin that, so turning the feature on is a visible decision
rather than a side effect.
"""
import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = REPO_ROOT / ".github" / "workflows"
PAGES_ACTION = REPO_ROOT / "actions" / "prepare-pages-artifact" / "action.yml"
VERIFY_WORKFLOW = WORKFLOW_DIR / "verify_published_feed.yml"
ICS_WORKFLOW = WORKFLOW_DIR / "ics_to_json.yml"
DEV_WORKFLOW = WORKFLOW_DIR / "ics_to_json_dev.yml"

NEWSLETTER_ASSET = "events-newsletter.json"


def load_yaml(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def workflow_paths():
    return sorted(WORKFLOW_DIR.glob("*.yml"))


def iter_steps(workflow):
    for job in (workflow.get("jobs") or {}).values():
        for step in job.get("steps") or []:
            yield step


def pages_action_callers():
    """Every (workflow_path, step) that invokes the Pages composite action."""
    found = []
    for path in workflow_paths():
        for step in iter_steps(load_yaml(path)):
            if "prepare-pages-artifact" in str(step.get("uses") or ""):
                found.append((path, step))
    return found


# --------------------------------------------------------------------------
# All workflows parse
# --------------------------------------------------------------------------

def test_every_workflow_is_valid_yaml():
    paths = workflow_paths()
    assert len(paths) >= 6, "expected the full set of workflows"
    for path in paths:
        assert load_yaml(path) is not None, f"{path.name} parsed as empty"


def test_pages_action_is_valid_yaml():
    assert load_yaml(PAGES_ACTION)["inputs"]


# --------------------------------------------------------------------------
# The composite action and its callers
# --------------------------------------------------------------------------

def test_action_gates_the_newsletter_behind_an_opt_in_flag():
    inputs = load_yaml(PAGES_ACTION)["inputs"]
    assert "include-newsletter" in inputs
    assert str(inputs["include-newsletter"]["default"]) == "false"
    # The file inputs stay declared so enabling the flag is the only change needed.
    assert "prod-events-newsletter-file" in inputs
    assert "dev-events-newsletter-file" in inputs


def test_at_least_one_caller_uses_each_local_source():
    """Keeps the two tests below from passing vacuously."""
    sources = [
        (step.get("with") or {}).get("prod-events-source")
        for _, step in pages_action_callers()
    ]
    assert "local" in sources
    dev_sources = [
        (step.get("with") or {}).get("dev-events-source")
        for _, step in pages_action_callers()
    ]
    assert "local" in dev_sources


def test_no_caller_enables_the_newsletter():
    """The feature is out of scope for MAE; enabling it should be deliberate."""
    for path, step in pages_action_callers():
        with_ = step.get("with") or {}
        assert str(with_.get("include-newsletter", "false")).lower() != "true", (
            f"{path.name} turns the newsletter on; MAE does not publish it and no "
            "newsletter_config.json describes MAE's schedule"
        )


def test_local_callers_pass_the_files_the_action_actually_requires():
    """A caller that forgets a required input should hard-fail, not ship a partial tree."""
    for path, step in pages_action_callers():
        with_ = step.get("with") or {}
        if with_.get("prod-events-source") == "local":
            assert with_.get("prod-events-file"), f"{path.name}: no prod-events-file"
        if with_.get("dev-events-source") == "local":
            assert with_.get("dev-events-file"), f"{path.name}: no dev-events-file"
            assert with_.get("dev-events-nofpo-file"), f"{path.name}: no dev-events-nofpo-file"


def test_newsletter_downloads_are_guarded_by_the_flag():
    """Both release branches rebuild the tree from scratch on every deploy, so an
    unguarded download would 404-warn on every run while the feature is off."""
    script = PAGES_ACTION.read_text(encoding="utf-8")
    for line_no, line in enumerate(script.splitlines()):
        if "gh release download" in line and NEWSLETTER_ASSET in line:
            preceding = "\n".join(script.splitlines()[max(0, line_no - 3):line_no])
            assert 'INCLUDE_NEWSLETTER}" = "true"' in preceding, (
                f"unguarded newsletter download at line {line_no + 1}"
            )


def test_local_branches_require_their_files():
    script = PAGES_ACTION.read_text(encoding="utf-8")
    assert "prod-events-source=local requires prod-events-file" in script
    assert "dev-events-source=local requires dev-events-file and dev-events-nofpo-file" in script
    assert "include-newsletter=true requires prod-events-newsletter-file" in script


# --------------------------------------------------------------------------
# Published paths are verified
# --------------------------------------------------------------------------

def published_pages_paths():
    """Site-relative JSON paths the composite action writes under pages/.

    Two ways a file lands there: `cp <src> pages/<path>` in the local branches, and
    `gh release download --pattern <asset> --dir pages[/dev]` in the release ones.
    """
    script = PAGES_ACTION.read_text(encoding="utf-8")
    paths = set()

    for target in re.findall(r"^\s*cp \S+ (pages/\S+\.json)\s*$", script, re.MULTILINE):
        if NEWSLETTER_ASSET in target:
            continue
        paths.add(target[len("pages/"):])

    for line in script.splitlines():
        if "gh release download" not in line:
            continue
        # Guarded by include-newsletter, which no caller enables, so it is not
        # actually published and must not demand a verify check.
        if NEWSLETTER_ASSET in line:
            continue
        directory = re.search(r"--dir (\S+)", line)
        if not directory:
            continue
        prefix = directory.group(1)[len("pages"):].strip("/")
        for pattern in re.findall(r"--pattern '([^']+)'", line):
            paths.add(f"{prefix}/{pattern}" if prefix else pattern)

    assert paths, "found no published paths; the extraction is broken, not the wiring"
    # dev/test.json is a static fixture copied from examples/, not a release asset.
    return {p for p in paths if p.endswith(".json") and not p.endswith("test.json")}


def verify_checks():
    text = VERIFY_WORKFLOW.read_text(encoding="utf-8")
    return {m.split("=")[0] for m in re.findall(r'--check "([^"]+)"', text)}


def test_verify_workflow_declares_checks():
    checks = verify_checks()
    assert len(checks) >= 3, f"expected the full check list, got {checks}"


def test_every_published_pages_path_has_a_verify_check():
    """Publishing a file nobody verifies is how drift goes unnoticed."""
    missing = published_pages_paths() - verify_checks()
    assert not missing, f"published but never verified: {sorted(missing)}"


@pytest.mark.parametrize(
    "path", ["events.json", "dev/events.json", "dev/events-nofpo.json"],
)
def test_expected_paths_are_verified(path):
    assert path in verify_checks()


def test_the_verifier_does_not_check_a_path_nobody_publishes():
    """A check for the unpublished newsletter variant would report permanent drift."""
    assert NEWSLETTER_ASSET not in " ".join(verify_checks())


# --------------------------------------------------------------------------
# Static assets the pages reference
# --------------------------------------------------------------------------

SITE_DIR = REPO_ROOT / "site"


def referenced_assets():
    """Local script/style/anchor targets the two pages load, as site-relative paths."""
    wanted = set()
    for page, prefix in ((SITE_DIR / "index.html", ""), (SITE_DIR / "dev" / "index.html", "dev/")):
        html = page.read_text(encoding="utf-8")
        for src in re.findall(r'<script[^>]+src="([^"]+)"', html):
            if src.startswith(("http://", "https://", "//")):
                continue
            if src.startswith("../"):
                wanted.add(src[3:])
            else:
                wanted.add(prefix + src.lstrip("./"))
    return wanted


def test_pages_reference_the_simulator():
    """Keeps the deployment test below from passing because the tag was removed."""
    assert "feed-simulator.js" in referenced_assets()


def test_every_referenced_asset_is_deployed_by_the_action():
    script = PAGES_ACTION.read_text(encoding="utf-8")
    copied = set(re.findall(r"^\s*cp \S+ pages/(\S+)\s*$", script, re.MULTILINE))
    missing = referenced_assets() - copied
    assert not missing, (
        f"the pages load {sorted(missing)} but the Pages action never copies it, "
        "so the deployed site would 404 on it"
    )


def test_referenced_assets_exist_in_the_repo():
    for asset in referenced_assets():
        assert (SITE_DIR / asset).is_file(), f"site/{asset} is referenced but missing"


def test_simulator_markup_has_no_hardcoded_date_presets():
    """Dates are chosen with the pickers; a hardcoded preset would rot each year."""
    for page in (SITE_DIR / "index.html", SITE_DIR / "dev" / "index.html"):
        html = page.read_text(encoding="utf-8")
        assert "nfs-labor" not in html, f"{page.name} still has the Labor Day preset"
    js = (SITE_DIR / "feed-simulator.js").read_text(encoding="utf-8")
    assert "nfs-labor" not in js


def test_simulator_never_offers_the_newsletter_variant_as_a_source():
    """The variant is the finished artifact for one edition; the simulator previews
    editions that do not exist yet. Selecting it makes every other edition come back
    empty, which reads as 'nothing is scheduled'."""
    for page in (SITE_DIR / "index.html", SITE_DIR / "dev" / "index.html"):
        html = page.read_text(encoding="utf-8")
        block = re.search(r'<select id="nfs-source">(.*?)</select>', html, re.S)
        options = re.findall(r'value="([^"]+)"', block.group(1)) if block else []
        assert not any("events-newsletter" in o for o in options), (
            f"{page.name} offers the newsletter variant as a simulator source"
        )


def test_simulator_leads_with_the_target_publication_date():
    """The common case is one control; the rest are derived or live behind Advanced."""
    for page in (SITE_DIR / "index.html", SITE_DIR / "dev" / "index.html"):
        html = page.read_text(encoding="utf-8")
        primary = re.search(r'<div class="nfs-controls nfs-primary">(.*?)\n        </div>', html, re.S)
        assert primary, f"{page.name} has no primary control row"
        assert 'id="nfs-pubdate"' in primary.group(1), f"{page.name}: publication date is not primary"
        assert "Target publication date" in primary.group(1)
        # The derived and fiddly controls must not clutter the primary row.
        for field in ("nfs-pubtime", "nfs-deadlinedate", "nfs-deadlinetime", "nfs-now"):
            assert field not in primary.group(1), f"{page.name}: {field} should be behind Advanced"


def test_simulator_shows_the_derived_deadline_next_to_the_control():
    """The deadline is computed from the publication date, so it has to be visible
    where the date is chosen, not only inside a collapsed panel."""
    for page in (SITE_DIR / "index.html", SITE_DIR / "dev" / "index.html"):
        html = page.read_text(encoding="utf-8")
        assert 'id="nfs-derived"' in html, f"{page.name} has no derived readout"
        form = re.search(r'<form id="nfs-form".*?</form>', html, re.S).group(0)
        assert 'id="nfs-derived"' in form, f"{page.name}: the readout is outside the form"
        advanced = re.search(r'<details class="nfs-advanced".*?</details>', html, re.S).group(0)
        assert 'id="nfs-derived"' not in advanced, (
            f"{page.name}: the readout must not be hidden inside Advanced"
        )
    js = (SITE_DIR / "feed-simulator.js").read_text(encoding="utf-8")
    assert "renderDerived" in js and "nfs-derived" in js


def test_simulator_hides_exact_dates_behind_an_advanced_accordion():
    for page in (SITE_DIR / "index.html", SITE_DIR / "dev" / "index.html"):
        html = page.read_text(encoding="utf-8")
        advanced = re.search(r'<details class="nfs-advanced".*?</details>', html, re.S)
        assert advanced, f"{page.name} has no Advanced accordion"
        for field in ("nfs-pubtime", "nfs-deadlinedate", "nfs-deadlinetime", "nfs-now"):
            assert field in advanced.group(0), f"{page.name}: {field} is not inside Advanced"
        assert " open" not in advanced.group(0).split(">")[0], (
            f"{page.name}: Advanced should start collapsed"
        )


def test_simulator_never_force_opens_the_advanced_panel():
    """It stays collapsed until the reader opens it, even for a customised link."""
    js = (SITE_DIR / "feed-simulator.js").read_text(encoding="utf-8")
    assert ".open = true" not in js, "the simulator force-opens the Advanced panel"


def test_edition_details_collapse_by_default():
    """The headline figures stay visible; the derived dates fold away."""
    for page in (SITE_DIR / "index.html", SITE_DIR / "dev" / "index.html"):
        html = page.read_text(encoding="utf-8")
        block = re.search(r'<details class="nfs-details nfs-editiondetails"([^>]*)>', html)
        assert block, f"{page.name} has no edition-details accordion"
        assert "open" not in block.group(1), f"{page.name}: it should start collapsed"
        assert 'id="nfs-details-list"' in html


def test_home_page_leads_with_the_simulator():
    """It is the main tool, and #feed-simulator must stay a stable deep link."""
    html = (SITE_DIR / "index.html").read_text(encoding="utf-8")
    main = html[html.index("<main>"):]
    ids = re.findall(r'<(?:div|section)[^>]*\bid="([^"]+)"', main)
    assert ids and ids[0] == "feed-simulator", f"first block in <main> is {ids[:1]}"
    assert 'id="feed-simulator"' in html


def test_hero_leads_with_the_simulator_action():
    html = (SITE_DIR / "index.html").read_text(encoding="utf-8")
    actions = re.search(r'<div class="hero-actions">(.*?)</div>', html, re.S).group(1)
    buttons = re.findall(r'<a class="btn ([a-z-]+)" href="([^"]+)">', actions)
    assert buttons, "no hero actions found"
    assert buttons[0] == ("btn-primary", "#feed-simulator"), buttons[0]
    # Raw-asset links are de-emphasised, never primary.
    for cls, href in buttons[1:]:
        assert cls == "btn-quiet", f"{href} should be quiet, got {cls}"


def test_orange_buttons_keep_a_readable_hover_label():
    """The global a:hover rule would otherwise paint orange text on orange."""
    html = (SITE_DIR / "index.html").read_text(encoding="utf-8")
    rule = re.search(r'\.btn-primary:hover,\s*\.btn-primary:focus-visible \{(.*?)\}', html, re.S)
    assert rule, "no hover rule for .btn-primary"
    assert "color:" in rule.group(1)
    assert "var(--brand)" not in rule.group(1).split("color:")[1].split(";")[0]


def test_hero_links_are_not_the_dark_brand_colour():
    """--brand-dark on the near-black hero is close to unreadable."""
    html = (SITE_DIR / "index.html").read_text(encoding="utf-8")
    assert ".hero a:not(.btn) { color: var(--brand); }" in html


def test_collapsed_accordions_are_forced_hidden():
    """Author `display` on a <details> child outranks the UA hiding rule in Safari,
    which renders the panel contents while collapsed. A guard restores it."""
    for page in (SITE_DIR / "index.html", SITE_DIR / "dev" / "index.html"):
        html = page.read_text(encoding="utf-8")
        assert "#feed-simulator details:not([open]) > *:not(summary) { display: none; }" in html, (
            f"{page.name} lacks the collapsed-accordion guard"
        )


def test_hero_link_colour_does_not_capture_buttons():
    """`.hero a` outranks `.btn-primary`, so an unscoped rule paints the button
    label the same orange as its background."""
    html = (SITE_DIR / "index.html").read_text(encoding="utf-8")
    assert ".hero a:not(.btn) {" in html
    assert ".hero a:not(.btn):hover {" in html
    assert "\n    .hero a {" not in html, "the unscoped rule would capture buttons"


def test_simulator_declares_a_default_feed():
    """The production page has no selector, so it names its source on the element."""
    html = (SITE_DIR / "index.html").read_text(encoding="utf-8")
    assert 'id="feed-simulator" data-feed="./events.json"' in html
    assert 'id="nfs-source"' not in html, "production should have no feed selector"


def test_dev_simulator_offers_only_full_feeds():
    html = (SITE_DIR / "dev" / "index.html").read_text(encoding="utf-8")
    block = re.search(r'<select id="nfs-source">(.*?)</select>', html, re.S)
    assert block, "the dev page should keep its selector"
    options = re.findall(r'value="([^"]+)"', block.group(1))
    assert options == ["./events.json", "./events-nofpo.json", "./test.json"]


def test_simulator_asset_is_self_contained():
    """A strict-ish Pages deploy plus no bundler means no external imports."""
    js = (SITE_DIR / "feed-simulator.js").read_text(encoding="utf-8")
    assert "import(" not in js and "require(" not in js.replace("module.exports", "")
    assert "http://" not in js and "https://" not in js.replace("mae.princeton.edu", "")


# --------------------------------------------------------------------------
# The ICS pipeline
# --------------------------------------------------------------------------

def test_ics_skip_gate_is_the_ics_hash_alone():
    """ORFE additionally keyed the gate on the newsletter edition, which moves on
    the calendar. With no time-driven output left, the hash is the whole gate --
    and it must not call into the unwired newsletter module."""
    text = ICS_WORKFLOW.read_text(encoding="utf-8")
    assert "ICS_SHA256" in text
    assert "--print-edition-id" not in text
    assert "src.newsletter" not in text


def test_ics_workflow_publishes_and_validates_the_full_feed():
    text = ICS_WORKFLOW.read_text(encoding="utf-8")
    assert "events.schema.json" in text
    assert "$OUTPUT_ASSET" in text
    assert "events-newsletter.schema.json" not in text


def test_ics_workflow_commits_maes_inverted_enrichment_defaults():
    """The inversion is the one thing that fails silently: a swapped mapping
    yields schema-valid output with title and speaker transposed. Defaults live
    in the workflow so a fresh clone reproduces MAE rather than ORFE."""
    text = ICS_WORKFLOW.read_text(encoding="utf-8")
    assert "ENRICH_TARGET_FIELD" in text and "'speaker'" in text
    assert "ENRICH_SUBTITLE_SELECTOR" in text
    assert "field--name-field-ps-event-speaker-name" in text


def test_workflows_carry_the_cloudflare_bypass_header():
    """mae.princeton.edu 403s every non-browser client. Without the header the
    enrichment steps succeed while populating nothing at all."""
    for path in (ICS_WORKFLOW, DEV_WORKFLOW):
        assert "BOT_BYPASS_HEADER_VALUE" in path.read_text(encoding="utf-8"), (
            f"{path.name} would enrich nothing"
        )


def test_no_workflow_hardcodes_the_orfe_pages_domain():
    for path in workflow_paths():
        text = path.read_text(encoding="utf-8")
        assert "upcoming.orfe.princeton.edu" not in text, f"{path.name} still points at ORFE"


def test_dev_workflow_excludes_maes_spelling_of_the_fpo_series():
    """`FPO` is ORFE's name for it and matches nothing in MAE's CATEGORIES, which
    would make the filtered variant byte-identical to the full feed."""
    text = DEV_WORKFLOW.read_text(encoding="utf-8")
    assert "Final Public Oral Exam" in text
    assert '--exclude-series "FPO"' not in text


def test_no_workflow_pins_as_of_outside_manual_dispatch():
    """A pinned clock in production would freeze the edition forever."""
    for path in workflow_paths():
        text = path.read_text(encoding="utf-8")
        for line in text.splitlines():
            if "--as-of" not in line:
                continue
            assert "${AS_OF" in line or "inputs.as_of" in line, (
                f"{path.name} hard-codes --as-of: {line.strip()}"
            )
        assert "NEWSLETTER_AS_OF" not in text


# --------------------------------------------------------------------------
# The newsletter is present but unwired
# --------------------------------------------------------------------------

def test_no_workflow_invokes_the_newsletter_or_the_deadline_watch():
    """Both modules keep their unit tests, so this is the only thing standing
    between 'available' and 'running against a schedule nobody wrote'."""
    for path in workflow_paths():
        text = path.read_text(encoding="utf-8")
        assert "src.newsletter" not in text, f"{path.name} invokes the newsletter"
        assert "notify_missing_titles" not in text, f"{path.name} invokes the watch"
        assert "--newsletter-output" not in text, f"{path.name} writes the variant"


def test_the_newsletter_modules_are_still_importable():
    """Unwired, not deleted: turning the feature on should not mean rewriting it."""
    import importlib

    assert importlib.import_module("src.newsletter")
    assert importlib.import_module("src.notify_missing_titles")


def test_no_live_newsletter_schedule_is_committed():
    """ORFE's newsletter_config.json encoded ORFE's Monday-noon schedule and its
    Labor Day exceptions. Shipping it here would describe a schedule MAE never
    agreed to; the example file is the template for when MAE wants one."""
    assert not (REPO_ROOT / "newsletter_config.json").exists()
    assert (REPO_ROOT / "newsletter_config.example.json").exists()


def test_ics_workflow_does_use_the_failure_streak_action():
    used = [str(step.get("uses") or "") for step in iter_steps(load_yaml(ICS_WORKFLOW))]
    assert any("update-failure-streak" in u for u in used)


# --------------------------------------------------------------------------
# Pull-request test signal
# --------------------------------------------------------------------------

def test_a_workflow_runs_pytest_on_pull_requests():
    for path in workflow_paths():
        workflow = load_yaml(path)
        triggers = workflow.get("on") or workflow.get(True)
        if not isinstance(triggers, dict) or "pull_request" not in triggers:
            continue
        if "pytest" in path.read_text(encoding="utf-8"):
            return
    pytest.fail("no workflow runs pytest on pull requests")


def test_container_test_path_is_exercised_in_ci():
    text = (WORKFLOW_DIR / "tests.yml").read_text(encoding="utf-8")
    assert "docker compose" in text and "tests" in text


# --------------------------------------------------------------------------
# Proof-of-concept labelling
# --------------------------------------------------------------------------

POC_LABEL = "Proof of concept"


@pytest.mark.parametrize("page", ["index.html", "dev/index.html"])
def test_both_pages_are_labelled_a_proof_of_concept(page):
    """Partners are being shown this to evaluate an integration. If the label
    goes missing, a demo endpoint reads as a service someone can depend on."""
    html = (SITE_DIR / page).read_text(encoding="utf-8")
    title = re.search(r"<title>(.*?)</title>", html, re.S)
    assert title and POC_LABEL in title.group(1), f"{page}: title omits the label"
    h1 = re.search(r"<h1>(.*?)</h1>", html, re.S)
    assert h1 and POC_LABEL in h1.group(1), f"{page}: h1 omits the label"


def test_home_page_states_the_stability_caveat():
    html = (SITE_DIR / "index.html").read_text(encoding="utf-8")
    banner = re.search(r'<p class="poc-banner">(.*?)</p>', html, re.S)
    assert banner, "the home page has no proof-of-concept banner"
    assert "not a production service" in banner.group(1)


def test_no_page_promises_a_production_service():
    """Wording drifts back toward "production" every time a page is edited."""
    for page in ("index.html", "dev/index.html"):
        html = (SITE_DIR / page).read_text(encoding="utf-8")
        for phrase in ("canonical feed", "production feed", "Production release"):
            assert phrase not in html, f"{page} still advertises a {phrase!r}"


def test_readme_leads_with_the_proof_of_concept_label():
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    first_heading = next(l for l in readme.splitlines() if l.startswith("# "))
    assert POC_LABEL.lower() in first_heading.lower(), first_heading

