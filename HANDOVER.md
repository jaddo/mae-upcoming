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
| Repository | `pubino/mae-upcoming` (public) — **in transit**, see [Transfer checklist](#transfer-checklist) |
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
- **`.github/CODEOWNERS` names `@jaddo`**, who already has write access, so the
  rules resolve and route today. Actually *requiring* code-owner review needs
  branch protection, which is configured per repository and does not survive a
  transfer — so it has to be set up again on the destination if it is wanted.

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

The move is happening in **two hops**, because GitHub's REST API refuses to
transfer an organization's repository to anyone but the caller:

> `422` — "You can only transfer a repository from an organization to yourself
> at this time."

So `pu-shd` → `@jaddo` directly was not available. Hop 1 took it out of the
organization to the outgoing owner's account; hop 2 is a personal-to-personal
transfer, which is permitted and which Jeff accepts.

### Hop 1 — `pu-shd` → `pubino` (done, 2026-09-11)

- [x] Repository variable values recorded first — see [Repository
      variables](#repository-variables).
- [x] Transferred out of the organization.
- [x] Verified afterward: all four repository variables survived, there are
      still no secrets, all seven workflows are `active` and the scheduled
      `ICS to JSON` and `Verify Published Feed` runs are succeeding, both
      releases and their assets are intact, and Pages serves from
      `pubino.github.io/mae-upcoming` with `events.json` matching the release
      asset.
- [x] `SITE_BASE_URL` set, because it was unset and the workflow default named
      the `pu-shd` host that had just stopped serving. It now names the
      destination, `jaddo.github.io/mae-upcoming`.
- [x] URLs in this repository retargeted to `jaddo` ahead of hop 2, on purpose
      — see [Why the URLs were changed first](#why-the-urls-were-changed-first).

Two things hop 1 changed that are worth knowing before hop 2:

- **Collaborator permissions are normalised down.** `@jaddo` held `admin` as an
  invited collaborator and came out of the transfer with `write`. Write is
  enough for CODEOWNERS, not for settings.
- **Organization-derived access disappears.** `orfeit` had admin through the
  organization and has none now. Only direct collaborator grants survive.

### Hop 2 — `pubino` → `@jaddo` (pending)

- [ ] Jeff reads this file and the README's "How MAE differs from ORFE".
- [ ] Initiate the transfer. It sits pending until `@jaddo` accepts; GitHub
      requires the destination account to accept an incoming repository.
- [ ] Nothing to do about `SITE_BASE_URL`. The variable already names
      `https://jaddo.github.io/mae-upcoming`, which is also the workflow
      default, so the watchdog is correct the moment the destination's Pages
      site goes live — and no admin action is required of the new owner. The
      variable is redundant with the default and may be deleted at any time by
      whoever holds admin; if it is ever edited, remember it *overrides* the
      default rather than agreeing with it.
- [ ] Confirm the same list hop 1 verified: variables, workflow states,
      releases, Pages, and a `Verify Published Feed` run reporting `match`.
- [ ] Dispatch `ICS to JSON` with `force: true` and confirm a fresh
      `events.json` reaches both the release and Pages.
- [ ] Check the four repository settings under [Settings to check the moment
      the transfer is accepted](#settings-to-check-the-moment-the-transfer-is-accepted).
      The outgoing owner cannot do this; admin left with the transfer.
- [ ] Tell anyone consuming the **Pages** URL directly. See below — this is the
      one that does not fail loudly. It is also the only item on this list that
      no amount of configuration can cover: it is a person telling other people,
      and the outgoing owner is the one who knows who they are.
- [ ] Decide whether the outgoing owner keeps useful access. A transfer leaves
      them as a collaborator, apparently at `write`, which is enough to fix
      files through a pull request but not settings. Granting `admin` is a
      one-click choice for the new owner and makes the first weeks easier; so is
      declining to.
- [ ] Update this file's "Current status" table and move Jeff into "Outgoing
      owner" only when the *next* handover happens.

### What redirects, and what does not

Git operations and the repository's web URLs redirect after a transfer —
GitHub's documentation is explicit that `git clone`, `git fetch` and `git push`
against the old location follow through to the new one — and release-download
URLs ride on that, so consumers of the `latest` asset keep working.

**GitHub Pages does not redirect, and it does not fail cleanly either.** This
was observed directly during hop 1: for a window after the transfer the old
`pu-shd.github.io/mae-upcoming` kept serving its *last build*, so a consumer
pointed at it saw stale-but-plausible JSON rather than an error, and the
watchdog — still checking that host at the time — reported `match`. The host
began returning `404` later the same day.

That is the worst shape a failure can take here: no error anywhere, just frozen
data that looks current. It is also why anyone using the Pages URL has to be
told at transfer time rather than left to notice.

### Why the URLs were changed first

The outgoing owner is **retained as a collaborator** after a personal-to-personal
transfer, which GitHub documents:

> "The original owner of the repository is added as a collaborator on the
> transferred repository."

What it does not document is at which permission level, and hop 1's evidence is
that transfers normalise collaborators down to `write`. Write access can still
change files through a pull request; it cannot change repository settings —
variables, secrets, Pages configuration.

So every URL was retargeted to `jaddo` **before** hop 2, while admin was still
in hand, and the verifier's base URL was moved out of a repository variable and
into the workflow's inline default. Anything that has to be corrected later
now lives in a file, where retained write access is enough, rather than in a
settings field that needs admin. That is the same reasoning the rest of this
repository already follows: MAE's values are inline defaults so a fresh clone
reproduces MAE's behaviour.

The cost of that ordering is a window — while hop 2 is pending, the published
landing page links to `jaddo` URLs that do not resolve yet. That was the
accepted trade: a short spell of dead links, against the risk of not being able
to fix the URLs at all.

### Settings to check the moment the transfer is accepted

These are repository *settings*, not files. They were all correct immediately
before the transfer — the values below were read from the API during the
pending window — but settings are the part of a transfer that can be
re-evaluated against the new owner's account defaults, and only the new owner
can change them.

| Setting | Value before transfer | Symptom if it comes out wrong |
|---|---|---|
| Workflow token permissions | `write` | **The one that fails loudest and least obviously.** Every workflow here declares `permissions: contents: write` (plus `issues`, `pages`, `id-token`), but the repository setting is a *ceiling*, not a default. If it lands on read-only, the declared permissions are denied and the pipeline fails at the publish step with a `403` — after successfully fetching and transforming the feed. Settings → Actions → General → Workflow permissions |
| Actions enabled | `enabled`, `allowed_actions: all` | Nothing runs at all, which at least announces itself |
| `github-pages` environment | present | The Pages deploy job fails; the release still publishes, so the site silently stops updating while the feed keeps moving |
| Branch protection on `main` | none | No change in behaviour. `CODEOWNERS` suggests reviewers; nothing enforces them. Worth adding only if this stops being a one-maintainer project |

A read-only token ceiling is worth dwelling on because of *where* it breaks. The
ICS fetch, the transform, the enrichment and the schema validation all succeed;
the failure is at the end, publishing the release. So the symptom is a red run
whose logs look fine for ninety per cent of their length, and the site simply
stops updating.

### While hop 2 is pending

Two things are deliberately wrong until Jeff accepts, and both fix themselves:

- **The landing page links to `jaddo` URLs that do not resolve yet**, because
  the URLs were retargeted ahead of the transfer for the reason above.
- **`Verify Published Feed` reports `error` / `unreachable`**, because both the
  variable and the default now name a Pages site that does not exist yet. An
  `error` fails the step, and two consecutive failing runs file a `feed-drift`
  issue.

That issue is expected, and it closes itself: the workflow's "Close drift issue
once the feed matches" step runs on every successful check, so the first green
run after the destination's Pages site goes live comments and closes it. Do not
respond to it by editing the watchdog.

The one thing worth not doing is disabling `Verify Published Feed` to silence
the window. A disabled watchdog is how the original stale-site incident went
unnoticed, and re-enabling it is exactly the step that gets forgotten.

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

**Actually set, as of 2026-09-11** — four inherited from `pu-shd`, plus
`SITE_BASE_URL`, which hop 1 made necessary:

| Variable | Value |
|---|---|
| `ICS_URL` | `https://mae.princeton.edu/feeds/events/ical.ics` |
| `OUTPUT_FILE` | `events.json` |
| `ENRICH_RAW_DETAILS` | `true` |
| `ENRICH_RAW_DETAILS_OVERWRITE` | `false` |
| `SITE_BASE_URL` | `https://jaddo.github.io/mae-upcoming` — the destination, matching the workflow default |

Everything not in that table is running on its inline default, and two of those
defaults matter:

- **`SITE_BASE_URL`** was unset until hop 1, so the verifier was checking the
  workflow default — which named the `pu-shd` host that had just stopped
  serving. An unreachable base URL is reported as `error`, an `error` fails the
  step, and two consecutive failing runs file a `feed-drift` issue, so this was
  roughly an hour away from paging about a site nobody owned. It now names the
  destination, which means the watchdog is correct from the moment hop 2 lands
  and needs no admin action afterward. The trade is that it is wrong *until*
  then: see [While hop 2 is pending](#while-hop-2-is-pending).
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

## Owner references in the tree

All of these were retargeted to `jaddo` on 2026-09-11, before hop 2, for the
reason given under [Why the URLs were changed
first](#why-the-urls-were-changed-first). The table is kept as the list to walk
if ownership ever changes again — none of it breaks the pipeline, but each
entry misdirects a reader or a server admin.

| File | What it carries |
|---|---|
| `README.md` | Release URLs, Pages URLs, the custom-domain instructions, the local verify command, the `SITE_BASE_URL` row in the configuration reference |
| `site/index.html` | Six links in the landing page's endpoint list, including the visible repository name |
| `.github/workflows/verify_published_feed.yml` | The `SITE_BASE_URL` inline default — the one that decides what the watchdog checks when no variable is set |
| `copilot-instructions.md` | The canonical-repository statements |
| `src/verify_published_feed.py`, `src/notify_missing_titles.py` | `USER_AGENT`. This is the string MAE's server admins see when tracing traffic, so it should name the repository actually making the requests |
| `tests/test_verify_published_feed.py`, `tests/test_notify_missing_titles.py` | `REPO` / `BASE_URL` fixtures. Test-local, so cosmetic |
| `.github/CODEOWNERS` | `@jaddo` on everything, plus the four files where the ORFE/MAE inversion gets decided |

The pipeline reads none of these from its own URLs, which is why the sweep is
safe to do ahead of a transfer: the only thing that cares is
`verify_published_feed.yml`, and the repository variable overrides it until the
destination exists.

Keep `README.md`, `copilot-instructions.md` and this file in agreement — they
are the three places a newcomer looks, and a stale one of the three is worse
than none.
