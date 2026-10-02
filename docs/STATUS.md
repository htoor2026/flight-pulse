# Flight Pulse — Project Status

Last updated: 2026-10-01

---

# Current State

Project planning and Codex governance setup.

No Flight Pulse application implementation has started yet.

---

# Current Phase

Phase 0 — Project Foundation

Status:

NOT STARTED

---

# Completed Planning

- [x] Flight Pulse project concept defined
- [x] Core product scope discussed
- [x] MySQL selected as primary database
- [x] Flight data ingestion included
- [x] Weather integration included
- [x] News/disruption analysis included
- [x] Dashboard included
- [x] AI SQL chatbot included
- [x] Flight-delay investigation included
- [x] Evidence-grounded explanations included
- [x] SPEC.md drafted
- [x] PLAN.md drafted
- [x] Strict human-approval workflow chosen
- [x] AGENTS.md drafted
- [x] Codex permissions strategy defined

---

# Not Yet Implemented

No production implementation has been started.

The following have NOT yet been created or configured unless explicitly
done by the user:

- Python environment
- project source structure
- Git workflow
- GitHub repository lifecycle
- MySQL database
- database schema
- flight-data source
- flight scraper/API
- ingestion pipeline
- data-quality pipeline
- weather API
- news ingestion
- analytics layer
- dashboard
- AI chatbot
- delay investigation engine
- tests
- CI pipeline
- GitHub Actions
- hooks
- skills
- subagents
- additional MCP servers
- plugin

---

# Current Governance Mode

STRICT MANUAL APPROVAL

Codex must:

Propose
→ Explain
→ Ask
→ Wait
→ Execute
→ Report
→ Ask again

No autonomous continuation is allowed.

---

# Approved Architecture Direction

High-level target architecture:

Flight Data
→ Ingestion
→ Cleaning
→ MySQL

Weather API
→ Weather Pipeline
→ MySQL

News
→ News Pipeline
→ MySQL

MySQL
→ SQL Analytics
→ Dashboard

Dashboard
→ AI Chatbot
→ SQL / Weather / News Investigation
→ Evidence-Grounded Explanation

---

# Database Decision

Selected:

MySQL

Reason:

Flight Pulse contains strongly relational analytical data and the AI analyst
will need SQL query capabilities.

MongoDB is not planned for the first version.

---

# AI Safety / Analysis Decision

Flight Pulse must not automatically claim causal explanations.

Possible explanation labels:

- Confirmed
- Strongly Supported
- Possible Contributor
- Unknown

---

# Development Lifecycle

The detailed development lifecycle has NOT yet been implemented.

Planned next design step:

Define the Flight Pulse software development lifecycle including:

- requirements/specification
- planning/design
- task creation
- feature branches
- implementation
- local validation
- testing
- self-code review
- commits
- GitHub push
- pull requests
- GitHub Actions
- security checks
- review
- merge
- branch cleanup

This lifecycle must be approved before implementation.

---

# Git Status

Not yet recorded.

Codex must obtain permission before inspecting or changing Git state.

---

# Validation Status

No validation has been run.

Tests:

NOT RUN

Lint:

NOT RUN

Type checking:

NOT RUN

Security scan:

NOT RUN

Data-quality checks:

NOT RUN

---

# Known Issues

None yet.

---

# Open Decisions

These must be decided during future approved steps:

1. exact flight-data source
2. exact weather API
3. exact news source
4. dashboard framework
5. backend framework
6. MySQL schema
7. flight delay threshold
8. LLM/API strategy
9. GitHub CI checks
10. deployment strategy

---

# Next Proposed Milestone

Design the software development lifecycle before implementing Flight Pulse.

The lifecycle should cover:

SPEC
→ PLAN / DESIGN
→ TASK
→ BRANCH
→ BUILD
→ VALIDATE
→ SELF REVIEW
→ COMMIT
→ PUSH
→ PR
→ CI
→ REVIEW
→ MERGE
→ CLEANUP

No implementation should begin until this lifecycle is agreed upon.

---

# Manual Tasks

The following remain human-controlled unless explicitly delegated:

- approval of every Codex action
- important architecture decisions
- GitHub merge decisions
- production credentials
- paid service decisions
- final portfolio demo recording
- final portfolio publishing

---

# Next Action

WAITING FOR USER.

The next action should be:

Design and approve the Flight Pulse development lifecycle.

Do not begin implementation automatically.