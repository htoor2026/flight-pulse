# Flight Pulse — AGENTS.md

## Purpose

Flight Pulse is a portfolio data project.

Main flow:

Flight data
→ MySQL
→ analysis
→ weather/news context
→ dashboard
→ AI assistant

Follow Spec-Driven Development, but keep the process lightweight.

---

## Source of Truth

Use this order:

1. Current user instruction
2. `docs/SPEC.md`
3. `docs/ARCHITECTURE.md`
4. `docs/PLAN.md`
5. Current approved task
6. `docs/STATUS.md`
7. Existing code

For provider work also use:

`docs/DATA_SOURCES.md`

If important sources conflict, stop and report the conflict.

---

## Work Style

Once a task is approved, autonomously complete normal local and reversible work.

Do not repeatedly ask permission for routine development steps.

Prefer the smallest implementation that satisfies the requirement.

Do not add features outside the active milestone.

Do not overengineer.

---

## No Approval Required

Within an approved task, you may:

- read/search project files
- edit/create project files
- create directories
- run Python commands
- run tests and validation
- use mocks/fixtures
- inspect Git status/log/diff
- update task-related documentation
- update `docs/STATUS.md`
- connect to the local `flight_pulse` MySQL database
- create approved local tables
- run non-destructive SQL
- insert/update/query development data
- create normal feature/fix/research branches
- commit approved work
- push non-main branches
- fix routine implementation problems
- run `git fetch` and refresh remote-tracking references

Continue until the task is complete or a real approval boundary is reached.


---

## Approval Required

Ask before:

### External
- live API requests that consume quota
- new web research outside an approved research batch
- new MCP/external services
- uploading project data externally

### Cost
- paid APIs
- overages
- purchases
- cloud resources
- paid deployment

### Dependencies
- adding/removing/upgrading dependencies
- changing Python version

### Security
- creating/changing credentials
- changing authentication
- exposing or transmitting secrets

### Destructive actions
- dropping tables/databases
- deleting important data/files
- destructive migrations
- force push
- hard reset

### Major decisions
- changing SPEC requirements
- changing major architecture
- changing MySQL
- changing the selected flight provider
- adding major components outside the approved plan

### Publishing
- merging into `main`
- public deployment

Group related approvals together. Do not ask one-by-one.

---

## Current Technical Decisions

- Python 3.11
- Conda environment: `flight-pulse`
- MySQL for persistence
- AeroDataBox via RapidAPI for MVP flight data
- initial airport: YYZ

Approved dependencies:

- `mysql-connector-python`
- `python-dotenv`

Secrets must stay in `.env`.

Never commit or print secrets.

---

## API Usage

RapidAPI quota is limited.

Therefore:

- use mocked API responses during development
- do not use live API calls in unit tests
- avoid unnecessary repeated requests
- require approval before additional live request batches
- never enable paid overages automatically

---

## Data Rules

Keep AeroDataBox-specific parsing inside the ingestion layer.

Normalize before persistence.

Do not fabricate missing values.

Delay should be calculated from actual minus scheduled time when both exist.

If actual timing is unknown, keep delay null.

Use consistent UTC-normalized timestamps internally where practical.

---

## Scope Discipline

Work only on the active milestone.

During Flight Data → MySQL, do not build:

- weather
- news
- dashboard
- chatbot
- prediction models
- deployment
- unnecessary agents/plugins

---

## Git

Do not develop major work directly on `main`.

Use branches such as:

- `feature/...`
- `research/...`
- `fix/...`
- `docs/...`

Normal commits and pushes on approved non-main branches are allowed.

Do not merge to `main` or force push without approval.

---

## Testing

Use mocks for external APIs.

Tests must not consume RapidAPI quota.

Test important logic such as:

- normalization
- timestamps
- delay calculation
- missing fields
- duplicate handling
- repository behavior

Run relevant tests before completing a task.

---

## Task Completion Report

At the end of every meaningful task, report:

1. What was completed
2. Files changed
3. Tests/validation run
4. Results
5. Remaining limitations
6. Next recommended task
7. Anything requiring approval

Do not make the user ask what was done.

---

## Operating Principle

Approved task
→ implement autonomously
→ test
→ validate
→ report

Ask only for meaningful external, costly, destructive, security-sensitive,
or major product decisions.

---

## Native Multi-Agent Workflow

The root Codex agent is the Master / Orchestrator. It receives the objective,
loads the active Genesis brief, delegates bounded work, synthesizes specialist
reports, decides which findings require action, and records task evidence. It
must not bypass Genesis gates or human approval boundaries.

Native specialist roles are registered in `.codex/config.toml`, with role
instructions under `.codex/agents/`:

- `implementation`: primary application-code writer for explicitly assigned paths
- `code_review`: read-only maintainability and architecture review
- `security`: read-only security and boundary review
- `test`: local validation; may edit tests only when explicitly delegated
- `documentation`: documentation-only updates by default
- `shipping`: approved Git and pull-request operations, never merge or force push

Reviewer agents report findings and do not independently rewrite application
code. The Master accepts or rejects each material finding and delegates accepted
fixes to the Implementation Agent. Only one application-code writer should work
at a time.

The Master is the sole writer of Genesis task state, evidence, decisions,
blockers, and checkpoints. Specialist agents may read Genesis context but return
their evidence to the Master. This avoids conflicting concurrent state updates.

The normal sequence is:

Genesis brief → bounded implementation → tests → code/security review →
Master triage and delegated fixes → executable Genesis gates → human approval
gates → approved shipping.

Human approval remains required for architecture changes, dependencies, live
external API calls, billable services, credentials/authentication changes,
destructive actions, deployment, and merging to `main`.

<!-- genesis:start -->
## Genesis workflow

Before changing this repository, load the Genesis and Ponytail skills and read `.genesis/KICKOFF.md`. Obey its phase instruction: do not write product implementation code during discovery, specification, or planning. Use the Genesis CLI for tasks, proof, decisions, approvals, and checkpoints. End every work session with `genesis checkpoint .`.

### Ask the index before reading the code

This repository is indexed. Querying it is faster than grepping and answers questions grep cannot.

- `genesis query . search NAME` — where a name is defined, when you know the name but not the file
- `genesis query . scope PATH` — what a file or directory depends on, and what depends on it
- `genesis query . callers REF` / `callees REF` — call edges for a symbol
- `genesis query . impact PATH` — everything that transitively imports a file. Run this before editing shared code; it is the blast radius
- `genesis query . path FROM TO` — how two files are connected
- Add `--json` for machine-readable output.

Start from the scope cards and symptom map already in `genesis brief .`; they point at declarations before you read anything. Treat every answer as advisory: it is static analysis, so confirm in source before relying on it. A result marked `ambiguous` means several definitions matched and none were ruled out — check the candidates rather than assuming the first.

Run `genesis serve .` when the structure is unclear or you want to show a human what changed. It draws the repository as a live map, reindexes on save, and is read-only. If the index looks stale and nothing is watching, run `genesis index .`.

Hosts that speak MCP can mount the same questions as tools with `genesis mcp .`.
<!-- genesis:end -->
