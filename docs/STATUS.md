# Flight Pulse — Project Status

Last updated: 2026-10-02

---

# Current State

The flight-data source investigation is complete, and AeroDataBox is approved
as the primary provider for the MVP.

Milestone 1 — Flight Data → MySQL is complete. The documented Conda
environment and the local client, normalization, delay calculation, repository,
schema definition, and tests are complete. The local schema, synthetic database
validation, and live YYZ end-to-end validation have completed successfully.
The live request returned HTTP 200; 72 flights were returned, normalized, and
upserted into MySQL.

Milestone 2 — Flight Analysis is complete. A reusable read-only analysis layer
now reports flight volume, status and delay metrics, airline/route/hour
breakdowns, top delayed flights, and basic data-quality indicators from the
existing 72-row MySQL dataset.

Milestone 3 — Weather Integration is complete. The keyless Open-Meteo forecast
endpoint returned 48 hourly YYZ weather records, which were normalized to UTC,
stored in MySQL, and matched to all 72 existing flights by scheduled YYZ event
hour.

Milestone 4 — News / Disruption Context is implemented locally. The GDELT DOC
2.0 client, metadata normalization, deterministic URL identity, MySQL
persistence, schema, and mocked tests are complete. The single permitted live
validation request returned HTTP 429, so no live article metadata was stored.

Milestone 5 — Dashboard MVP is complete. A Streamlit dashboard now reads the
existing MySQL flight and weather data through the reusable analytics layer and
presents overview, status, airline, route, time, weather, and data-quality
sections for the current 72-flight sample.

Milestone 6 — AI Analyst Foundation is complete. Seven structured, read-only
tools now expose grounded flight, airline, route, weather, news, and delay-
investigation results from the existing MySQL data without unrestricted SQL or
an external language model.

No additional AeroDataBox or RapidAPI request is authorized.

---

# Current Phase

Milestone 6 — AI Analyst Foundation

Status:

COMPLETE

The analytical tool implementation, mocked tests, real read-only MySQL
validation, and complete local test suite are successful.

---

# Completed

## Flight Data Source Investigation

- [x] evaluated AeroDataBox, Aviationstack, FlightAware AeroAPI, Cirium, and OpenSky
- [x] selected AeroDataBox as the primary MVP provider
- [x] recorded the approved decision in `docs/DATA_SOURCES.md`
- [x] limited the initial geographic scope to Toronto Pearson (YYZ)

## Milestone 1 Environment

- [x] confirmed Conda environment `flight-pulse`
- [x] confirmed Python 3.11.17
- [x] installed `mysql-connector-python==26.7.0`
- [x] installed `python-dotenv==1.2.4`
- [x] removed the unintended Python 3.9 `.venv`
- [x] completed an authorized live YYZ request with HTTP 200
- [x] normalized and upserted 72 live flight records
- [x] validated a real MySQL insert, query, and cleanup with synthetic data

## Milestone 1 Local Implementation

- [x] added environment-backed RapidAPI and MySQL configuration
- [x] built the AeroDataBox request constructor and injectable HTTP client
- [x] isolated AeroDataBox JSON handling in the ingestion layer
- [x] normalized flight records and UTC-aware timestamps
- [x] calculated delays only when scheduled and actual timestamps exist
- [x] added deterministic provider flight identifiers and duplicate handling
- [x] defined the provisional one-table MySQL schema without executing it
- [x] implemented parameterized, duplicate-safe MySQL persistence
- [x] added synthetic AeroDataBox fixtures and mocked unit tests
- [x] passed all 15 unit tests

## Milestone 2 — Flight Analysis

- [x] added reusable read-only analytics under `flight_pulse/analysis/`
- [x] implemented overview and status counts
- [x] implemented delay summaries by airline, route, and YYZ event hour
- [x] implemented top-delayed-flight ranking
- [x] implemented basic missing-data, duplicate, and extreme-delay checks
- [x] validated the analytics against the existing 72 MySQL rows
- [x] added focused mocked-database unit tests

## Milestone 3 — Weather Integration

- [x] selected Open-Meteo's free non-commercial, keyless API
- [x] configured YYZ coordinates at 43.6777, -79.6248
- [x] retrieved temperature, precipitation, snowfall, visibility, wind speed,
  wind gusts, and weather code
- [x] normalized all weather timestamps to UTC
- [x] added duplicate-safe MySQL weather persistence
- [x] stored 48 hourly YYZ weather records
- [x] matched 72 of 72 flights to their scheduled YYZ event hour
- [x] added focused mocked HTTP and database tests

## Milestone 4 — News / Disruption Context

- [x] selected the GDELT DOC 2.0 API
- [x] added a reusable `urllib.request` article-list client
- [x] normalized metadata without storing copyrighted article body text
- [x] generated deterministic SHA-256 identities from canonical article URLs
- [x] added in-response and duplicate-safe MySQL handling
- [x] added the `news_articles` table and supporting indexes
- [x] added a focused YYZ operational-disruption query
- [x] passed five focused mocked HTTP, normalization, repository, and pipeline tests
- [ ] complete live validation; the single permitted request returned HTTP 429

## Milestone 5 — Dashboard MVP

- [x] added `streamlit==1.64.0` as the only new direct dependency
- [x] added overview, flight-status, airline, route, time, weather, and
  data-quality sections
- [x] reused the MySQL-backed `FlightAnalysis` layer
- [x] added delayed/cancelled flight and hourly weather-context queries
- [x] labeled the current 72-flight sample and sparse actual-time coverage
- [x] limited airline average-delay display to groups with meaningful samples
- [x] included explicit weather association and non-causality language
- [x] validated all dashboard sections against the local MySQL data
- [x] passed Streamlit component validation without exceptions

## Milestone 6 — AI Analyst Foundation

- [x] added structured `get_flight_overview` and `find_flight` tools
- [x] added parameterized airline and route analysis tools
- [x] added stored YYZ weather and news context tools
- [x] added evidence-grounded delay investigation
- [x] restricted the analyst to fixed read-only queries with no arbitrary SQL
- [x] returned JSON-safe values suitable for future model tool calls
- [x] handled missing flight, weather, and news data explicitly
- [x] returned an insufficient-evidence conclusion without claiming causality
- [x] validated the tools against the existing local MySQL dataset

## Project Planning

- [x] Flight Pulse concept defined
- [x] Product scope defined
- [x] `SPEC.md` created
- [x] `PLAN.md` created
- [x] `ARCHITECTURE.md` created
- [x] `DEVELOPMENT_LIFECYCLE.md` created
- [x] `STATUS.md` created

---

## Development Environment

- [x] Conda environment created
- [x] Python 3.11 selected
- [x] `.env.example` created
- [x] `.gitignore` configured
- [x] project repository initialized

Conda environment:

`flight-pulse`

---

## Codex Governance

- [x] Root `AGENTS.md` created
- [x] strict human-approval rules defined
- [x] security rules defined
- [x] privacy rules defined
- [x] billing/spending protections defined
- [x] deployment restrictions defined
- [x] secrets policy defined
- [x] external-service approval rules defined
- [x] MCP approval rules defined
- [x] hooks approval rules defined
- [x] subagent approval rules defined
- [x] destructive-operation restrictions defined

Codex must follow:

Propose
→ Explain
→ Ask
→ Wait
→ Execute approved action
→ Report
→ Ask again

---

# Git / GitHub Setup

Repository:

`htoor2026/flight-pulse`

Primary branch:

`main`

Remote:

`origin`

GitHub repository is connected to the local VS Code project.

---

# GitHub Development Lifecycle

The following lifecycle has now been established:

SPEC
→ DESIGN
→ TASK
→ FEATURE BRANCH
→ IMPLEMENT
→ LOCAL VALIDATION
→ SELF REVIEW
→ COMMIT
→ PUSH
→ PULL REQUEST
→ CI
→ REVIEW
→ MERGE
→ CLEANUP

---

# GitHub Lifecycle Components

## Pull Request Template

Created:

`.github/pull_request_template.md`

Purpose:

Standardize:

- change description
- validation
- database impact
- security review
- risks
- documentation review
- reviewer checklist

---

## Feature Request Template

Created:

`.github/ISSUE_TEMPLATE/feature_request.md`

Purpose:

Standardize future Flight Pulse implementation tasks.

Each feature should define:

- specification reference
- PLAN phase
- problem
- proposed solution
- acceptance criteria
- testing requirements
- architecture impact
- risks
- definition of done

---

## Continuous Integration

Created:

`.github/workflows/ci.yml`

Current CI validates:

- repository checkout
- Python 3.11 environment
- Python availability
- Python syntax
- test-directory presence

Security hardening includes:

- read-only repository permissions
- non-persistent checkout credentials
- workflow timeout
- duplicate-run cancellation

Current CI is intentionally minimal because application code has not yet been implemented.

---

# First Lifecycle Validation

The Git/GitHub lifecycle has been exercised successfully.

Completed workflow:

1. created `feature/project-foundation`
2. implemented project lifecycle configuration
3. committed changes
4. pushed feature branch
5. created GitHub Pull Request
6. GitHub Actions executed
7. `CI / validate` passed
8. main-branch protection/ruleset configured
9. Pull Request merged
10. returned to local `main`
11. synchronized local `main`
12. deleted local feature branch

Result:

PASS

---

# GitHub Main Protection

The default branch is protected through a GitHub ruleset.

Target:

`Default branch`

Current intended protections include:

- Pull Request required before merge
- required CI status check
- force pushes blocked
- branch deletion restricted

No external reviewer approval is required because this is currently a solo project.

---

# Current Git State

Branch:

`feature/ai-analyst`

The branch includes the completed Milestone 6 AI analyst foundation.

---

# Current Work

Milestone 6 is complete. The analyst reads only from local MySQL through a
fixed set of parameterized tools; no external API request was made.

---

# Next Proposed Action

Review the completed AI analyst feature branch before connecting a real language
model or adding a chat interface.

---

# Known Issues

- no fallback flight-data provider has been selected
- AeroDataBox actual versus estimated timestamp semantics require careful normalization
- AeroDataBox FIDS responses omit the focal airport on some movements; the
  ingestion layer restores it from the requested airport and movement direction
- another live API request requires separate explicit approval
- actual departure data exists for only 3 of 72 rows and actual arrival data
  exists for only 2, so average-delay results are not representative
- one 1,060-minute departure-delay value materially skews the current average
- the dataset is a single short YYZ snapshot rather than a longitudinal sample
- Open-Meteo forecast output is model data, not a direct YYZ weather-station or
  METAR observation
- matching uses the scheduled YYZ departure/arrival timestamp truncated to its
  UTC hour; this is temporal association, not evidence that weather caused delay
- the Open-Meteo free API is non-commercial, has no uptime guarantee, requires
  CC BY 4.0 attribution, and is subject to published request limits
- the single GDELT validation request returned HTTP 429, so live response shape,
  article relevance, and end-to-end storage remain unverified
- GDELT search matches are supporting context only and cannot establish why a
  flight was delayed
- browser-based visual QA was unavailable because browser-control permission was
  not available; Streamlit component validation rendered all required sections
- dashboard results remain constrained by the 72-flight single-window sample and
  sparse actual departure/arrival timestamps
- no language model or free-text question router is connected yet
- delay investigations can surface stored context but cannot establish causality
- stored news context remains empty because GDELT live validation was rate-limited

---

# Validation Results

- Conda environment: PASS
- Python 3.11 requirement: PASS
- approved dependency installation: PASS
- unit tests: PASS (47 tests)
- `git diff --check`: PASS
- local MySQL connection: PASS
- provisional schema execution: PASS
- synthetic MySQL insert/query/delete: PASS
- live YYZ request: PASS (HTTP 200)
- live flights returned: 72
- live flights normalized: 72
- live flights upserted: 72
- MySQL `flights` rows: 72
- stored flights missing origin or destination: 0
- analysis source: local MySQL `flight_pulse.flights`
- analysis total flights: 72
- analysis delayed flights: 8 (11.11%)
- analysis cancelled flights: 1
- analysis average departure delay: 366.33 minutes (3 populated rows)
- analysis average arrival delay: -26.50 minutes (2 populated rows)
- analysis duplicate provider identifiers: 0
- Open-Meteo live request: PASS
- Open-Meteo hourly records returned: 48
- MySQL weather observations stored: 48
- flight/weather matches: 72 of 72
- weather timestamps stored and matched as UTC: PASS
- additional AeroDataBox/RapidAPI requests made during Milestone 3: 0
- GDELT targeted mocked tests: PASS (5 tests)
- GDELT live request: BLOCKED (HTTP 429)
- GDELT live articles returned: 0
- GDELT live articles stored: 0
- additional AeroDataBox/RapidAPI requests made during Milestone 4: 0
- Streamlit version: 1.64.0
- dashboard MySQL snapshot: PASS (72 flights, 48 weather observations)
- Streamlit component test: PASS (0 exceptions, 7 required sections)
- dashboard metrics rendered: 10
- dashboard tables rendered: 6
- dashboard external API requests: 0
- AI analyst read-only MySQL validation: PASS
- AI analyst tools implemented: 7
- AI analyst example flight: AA 3606
- AI analyst delay conclusion: Insufficient evidence to determine the delay cause.
- AI analyst external API requests: 0
- credentials committed: NO
- further live AeroDataBox/RapidAPI requests authorized: NO

---

# Architecture Direction

Current high-level architecture:

```text
Flight Data Source
        |
        v
Flight Ingestion
        |
        v
Cleaning + Validation
        |
        v
      MySQL
      /   \
     /     \
Weather   News
Pipeline  Pipeline
     \     /
      \   /
      MySQL
        |
        v
SQL Analytics
        |
        v
Dashboard
        |
        v
AI Analyst
        |
        +--> SQL
        +--> Flight lookup
        +--> Weather
        +--> News
        |
        v
Evidence-Grounded Delay Explanation
