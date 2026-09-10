# Ownership and handover

This file records who owns **MAE Upcoming**, what running it involves, and what
has to happen when ownership changes hands. It is the document to read before
accepting the transfer, and the document to update immediately after.

## A note to the new owner

Read this file, then the README's [How MAE differs from ORFE](README.md#how-mae-differs-from-orfe),
then `tests/test_mae_shape.py`. That is the whole orientation. Everything else in
the README is reference you can look up when you need it.

One trap is worth knowing before you touch anything. MAE and ORFE put the same
information in **opposite** fields, and both feeds validate against the same
schema — so a swapped mapping produces output that is schema-valid, raises no
error, and is useless: the talk title sitting in `speaker` and the speaker
sitting in `title`. Four config values hold the inversion in place and
`tests/test_mae_shape.py` pins the direction of all four. If that suite is
green, the mapping is right.

Three things to do in your first week:

1. Confirm `ICS to JSON` has run within the last 30 minutes, and that
   `Verify Published Feed` is reporting `match`.
2. **Watch the repository**, so the failure-streak issues actually reach you.
   They are the only alerting that exists — no email, no Slack, no pager.
3. Decide what you want this to be. The README and the landing page currently
   promise nothing: proof of concept, endpoints may change, not an official MAE
   service. Keeping that language is a legitimate choice. So is removing it —
   but then the endpoints have to be honoured, which means the custom domain,
   and a person who answers when the feed breaks.

**Retiring it is also a legitimate outcome.** This was built to show campus
partners what ingesting a department's events as JSON involves; if it has
already made that point, it does not need to keep running. To retire it
cleanly, rather than letting it rot into a stale feed nobody notices:

1. Disable the scheduled workflows (Actions → each workflow → Disable), which
   stops both publishing and the watchdog.
2. Say so at the top of `README.md` and in `site/index.html`, with the date the
   feed stopped refreshing, so anyone who finds a cached payload knows what
   they have.
3. Leave the `latest` release in place. It stays readable as a shape reference,
   which is what it was for.
4. Archive the repository. Nothing here needs to be deleted; the licence lets
   anyone pick it up.

The failure mode to avoid is the middle state: schedules quietly aged out, the
site still serving a payload from some indeterminate week, and no note anywhere
saying it stopped. That looks like a live service and behaves like a lie.

## Current status

| | |
|---|---|
| Repository | `pu-shd/mae-upcoming` (public) |
| Outgoing owner | Michael Bino — `bino@princeton.edu` |
| Incoming owner | Jeff Addo — `@jaddo`, `jaddo@princeton.edu` |
| Destination | `jaddo/mae-upcoming` — a **personal account**, not an organization |
| Licence | MIT, © The Trustees of Princeton University |
| Nature | **Proof of concept.** Not an official MAE service, and no endpoint here is promised to anyone. |

The feed is live and refreshes every 30 minutes, so the repository is not inert:
transferring it transfers a thing that publishes on a schedule. Whoever holds it
owns whatever it serves.

### Consequences of moving to a personal account

The destination is a personal account rather than a Princeton organization, and
three things follow:

- **Copyright does not move with the repository.** The licence is MIT, © The
  Trustees of Princeton University, and it stays that way wherever the code
  lives. MIT permits the hosting; it does not reassign authorship. Do not
  rewrite the `LICENSE` holder to a personal name.
- **There is no org to inherit it.** If `@jaddo` leaves Princeton or stops
  maintaining it, nothing automatically catches the repository — no org admin
  can reassign it and no team retains access. That is the argument for either
  transferring into a Princeton org later or [retiring it
  cleanly](#a-note-to-the-new-owner) rather than leaving it running unowned.
- **`.github/CODEOWNERS` names `@jaddo`**, which is only a valid owner once the
  transfer is accepted (or once `@jaddo` is a collaborator here). Requiring
  code-owner review additionally needs branch protection to be configured on
  the destination; it does not carry over.

## What the incoming owner is taking on

Deliberately small. There is no server, no database, no cloud account, and no
custom secret. Everything runs in GitHub Actions on the repository's own
`GITHUB_TOKEN`, and all configuration is repository variables with in-workflow
defaults. The ongoing obligations are:

1. **Watch for failures.** Two consecutive failed pipeline runs open a GitHub
   issue. Nothing else pages anyone.
2. **Keep the schedules alive.** GitHub disables scheduled workflows on public
   repositories after a long idle period; the heartbeat workflow exists to
   prevent that (see below). If the heartbeat stops, the pipeline eventually
   stops silently.
3. **Re-decide the disclaimer.** The README and landing page say this is a
   proof of concept whose URLs may change. If the new owner intends to make it
   dependable, that language has to change and the endpoints then have to be
   honoured.

## Transfer checklist

### Before

- [ ] Jeff Addo reads this file and the README's "How MAE differs from
      ORFE" section, and accepts the transfer.
- [ ] Confirm `@jaddo` accepts the transfer. GitHub requires the destination
      to accept an incoming repository; the transfer sits pending until they do.
- [x] Repository variable values recorded — see [Repository
      variables](#repository-variables). Only four are set; everything else
      runs on the workflows' inline defaults. Captured 2026-09-10, immediately
      before the transfer.
- [ ] Note the live endpoints so they can be compared after the move:
      `https://github.com/pu-shd/mae-upcoming/releases/download/latest/events.json`
      and `https://pu-shd.github.io/mae-upcoming/events.json`.

### During

- [ ] Transfer `pu-shd/mae-upcoming` → `@jaddo` (Settings → General →
      Transfer ownership). It becomes `jaddo/mae-upcoming`.
- [ ] Once accepted, `@jaddo` is the owner outright. Remove any collaborator
      access that should not carry over, and add `bino@princeton.edu` as a
      collaborator only if Jeff wants a fallback during the first weeks.

### After — verify, do not assume

A transfer does not carry every setting with it, and the parts that silently do
not carry over are the parts that fail quietly.

- [ ] **Repository variables.** Only four are set (table below). Confirm
      those four survived and re-create any that did not. The other eleven are
      *deliberately unset* and resolve to the workflows' inline defaults —
      absence is the intended state, not a gap to fill.
- [ ] **Actions enabled**, and scheduled workflows are not disabled. Check that
      `ICS to JSON` has run within the last 30 minutes.
- [ ] **GitHub Pages enabled**, source "GitHub Actions", and the
      `github-pages` environment exists. Dispatch `Publish Landing Pages` and
      confirm the site serves.
- [ ] **Releases and assets** survived: tags `latest` and `dev` still carry
      `events.json`, and the `latest` release body still carries its
      `ICS_SHA256` line — `Verify Published Feed` compares against it.
- [ ] **`SITE_BASE_URL`.** `Verify Published Feed` defaults to
      `https://pu-shd.github.io/mae-upcoming`. After the move that is the wrong
      host, and the verifier will report drift against the old site. Set the
      variable to `https://jaddo.github.io/mae-upcoming`, or update the
      default in the workflow.
- [ ] **Hardcoded old-owner URLs.** Update the references listed under
      [Old-owner references](#old-owner-references) below.
- [ ] Dispatch `ICS to JSON` with `force: true` and confirm a fresh
      `events.json` reaches both the release and Pages.
- [ ] Update this file: move Jeff Addo into "Outgoing owner" only once
      the next handover happens, and delete the placeholder banner.

GitHub redirects the old repository URL, and release-download URLs follow the
redirect, so existing consumers of the `latest` asset should keep working. The
`pu-shd.github.io/mae-upcoming` Pages URL does **not** redirect; it stops
serving, and the site moves to `jaddo.github.io/mae-upcoming`. Anyone who
wired up the Pages URL has to be told directly.

## What runs, and when

| Workflow | Trigger | Guard | Does |
|---|---|---|---|
| `ICS to JSON` | `*/30 * * * *`, manual | `main` only | Fetch ICS, transform, enrich, validate, publish `latest` release + Pages |
| `ICS to JSON (Development)` | manual only | any branch | Same, into the shared `dev` release; used to preview branches |
| `Verify Published Feed` | `10,40 * * * *`, manual | `main` only | Compare what Pages serves against the release asset, and the live ICS hash against the release body |
| `Publish Landing Pages` | manual only | `main` only | Rebuild the Pages artifact from `site/**` + existing release assets, without running the pipeline |
| `Public repo heartbeat` | `17 4 * * *`, manual | `main` only | Write a tiny keepalive commit **only** after 35 days with no `main` commit |
| `Tests` | push to `main`, PRs, manual | — | `pytest`, the Node simulator suite, and the containerized suite |

The verify schedule is offset from the pipeline's on purpose, so a fresh deploy
has time to land. It runs as its own workflow rather than as a step in the
publish job because a job that dies early leaves its later steps *skipped* —
and a check living there would be skipped alongside the deploy it was meant to
check.

## Configuration

### Secrets

Only `GITHUB_TOKEN`, which GitHub provides. **There are no custom secrets**, so
there is nothing to hand over out of band and nothing to rotate at transfer.

### Repository variables

Every one is optional: the workflows carry MAE's values as inline defaults so a
fresh clone reproduces MAE's behaviour, and a variable overrides the default.

**Actually set on `pu-shd/mae-upcoming` as of 2026-09-10** — these four, and
only these four:

| Variable | Value |
|---|---|
| `ICS_URL` | `https://mae.princeton.edu/feeds/events/ical.ics` |
| `OUTPUT_FILE` | `events.json` |
| `ENRICH_RAW_DETAILS` | `true` |
| `ENRICH_RAW_DETAILS_OVERWRITE` | `false` |

Everything below that is not in that table is running on its inline default.
Two of those defaults matter:

- **`SITE_BASE_URL` is unset**, so the verifier is using the workflow default
  `https://pu-shd.github.io/mae-upcoming`. That host stops serving at transfer,
  so `Verify Published Feed` will report `error` and — after two consecutive
  runs — file an issue about a site the new owner does not own. Setting this
  variable is the first thing to do after the transfer, not the last.
- **`BOT_BYPASS_HEADER_VALUE` is unset**, so the default `1` is what actually
  gets sent to `mae.princeton.edu`, and it works. There is no bypass token to
  hand over.

| Variable | Purpose if set |
|---|---|
| `ICS_URL` | Source feed. Default `https://mae.princeton.edu/feeds/events/ical.ics` |
| `OUTPUT_FILE` | Output filename |
| `SITE_BASE_URL` | Base URL the verifier checks. **Must be updated after transfer** |
| `PAGES_CNAME` | Custom domain. See the hazard below |
| `REPO_VARIABLE` | Legacy passthrough |
| `BOT_BYPASS_HEADER_VALUE` | Sent as `x-wdsoit-bot-bypass`. Default `1` |
| `ENRICH_TARGET_FIELD` | Where scraped text lands. MAE needs `speaker` |
| `ENRICH_SUBTITLE_SELECTOR` | Comma-separated selectors, tried left to right |
| `ENRICH_RAW_DETAILS` | Enable raw detail extraction |
| `ENRICH_RAW_DETAILS_OVERWRITE` | Overwrite existing extracted values |
| `EXCLUDE_SERIES` | Series to drop from the feed |
| `FPO_SERIES_NAME` | MAE spells this `Final Public Oral Exam`; `FPO` is ORFE's name |
| `FALLBACK_PREPEND_TEXT` | Synthesized-title template. Default `{a_an} {series} Talk by` |
| `FALLBACK_INCLUDE_SPEAKER` | Append the speaker to a synthesized title |

`BOT_BYPASS_HEADER_VALUE` is a variable rather than a secret because
`mae.princeton.edu` only requires the header to be *present* — the default
value is `1`. If OIT ever issues a per-consumer token, move it to a secret
first: variable values are not masked in Actions logs.

The full reference, including every field-mapping option, is in the README's
[Configuration reference](README.md#configuration-reference-env-vars-and-inputs).

### The custom-domain hazard

There is no CNAME today; Pages serves from the `github.io` URL. Setting
`PAGES_CNAME` to a host that does not resolve makes GitHub redirect the
`github.io` URL to it, which takes the **whole site down** rather than degrading
it. Order: DNS record first, `PAGES_CNAME` and `SITE_BASE_URL` second. Never the
other way round.

## When it breaks

| Symptom | Where to look |
|---|---|
| Issue filed about a failure streak | `.ci/failure-streak` holds the count; `actions/update-failure-streak` maintains it. Two consecutive failures alert; a reset commits `0` |
| Enrichment runs clean but populates nothing | The bypass header. `mae.princeton.edu` returns 403 to every non-browser client, and a 403 is not treated as a hard failure |
| Site serves an old payload | `Verify Published Feed`. A mismatch inside the 20-minute grace window after publication is `pending`, not a fault; Pages caches for 10 minutes per edge |
| Site and release are stale *together* | Generation stopped. The verifier's second check — live ICS hash vs `ICS_SHA256` in the release body — is the one that catches this |
| Nothing has run in weeks | Scheduled workflows aged out. Dispatch anything on `main`, and check the heartbeat workflow is enabled |
| Titles look wrong — speaker in `title` | Read the README's "How MAE differs from ORFE" and run `tests/test_mae_shape.py`. This is the standing trap in this repo |

## Deliberately unfinished

These are decisions, not omissions. Each is pinned by
`tests/test_pipeline_contract.py`, so switching one on is a visible change
rather than a side effect.

- **Newsletter variant** — `src/newsletter.py`, `src/notify_missing_titles.py`
  and the newsletter schema are present, tested and **unwired**. No
  `newsletter_config.json` is committed, because ORFE's encoded ORFE's
  Monday-noon schedule and recess exceptions, which MAE never agreed to. Turning
  it on needs MAE's actual publication schedule first; the five steps are in the
  README.
- **Legacy mirroring** — retired. `src/mirror_release.py` is kept, unwired.
- **Custom domain** — `upcoming.mae.princeton.edu` does not exist in DNS.

## Old-owner references

Update these when the repository moves. Nothing here breaks the pipeline, but
each one misdirects a reader or a server admin.

| File | What to change |
|---|---|
| `README.md` | 15 `pu-shd` references — release URLs, Pages URLs, the local verify command |
| `site/index.html` | 6 `pu-shd` references in the landing page's endpoint list |
| `.github/workflows/verify_published_feed.yml` | The `SITE_BASE_URL` default |
| `copilot-instructions.md` | The canonical-repository statements |
| `src/verify_published_feed.py`, `src/notify_missing_titles.py` | `USER_AGENT` — **fixed**: was advertising the upstream `pu-orfe/upcoming`, now names `pu-shd/mae-upcoming`. This is the string MAE's server admins see when tracing traffic, so re-point it at `jaddo/mae-upcoming` on transfer |
| `tests/test_verify_published_feed.py`, `tests/test_notify_missing_titles.py` | `REPO` / `BASE_URL` / `ICS_URL` fixtures — **fixed**: were ORFE's, now MAE's. Test-local, so cosmetic |

Keep `README.md`, `copilot-instructions.md` and this file in agreement — they
are the three places a newcomer looks, and a stale one of the three is worse
than none.
