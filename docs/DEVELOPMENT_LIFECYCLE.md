# Flight Pulse — Development Lifecycle

## Purpose

Flight Pulse follows a controlled software development lifecycle.

Every meaningful feature should move through:

SPEC
→ DESIGN
→ TASK
→ BRANCH
→ BUILD
→ VALIDATE
→ SELF REVIEW
→ COMMIT
→ PUSH
→ PULL REQUEST
→ CI
→ REVIEW
→ MERGE
→ CLEANUP

Human approval is required according to AGENTS.md.

---

# 1. Requirement / Specification

Source:

`docs/SPEC.md`

Before building a feature, verify that it belongs to the approved product scope.

If the requirement does not exist in SPEC.md:

STOP.

Discuss it before implementation.

---

# 2. Design

For substantial features, determine:

- component affected
- inputs
- outputs
- database impact
- API impact
- failure cases
- testing requirements
- security implications

Significant architecture decisions should be documented in:

`docs/ARCHITECTURE.md`

---

# 3. Task Definition

Convert the approved feature into a small implementation task.

Example:

Feature:

Weather integration

Tasks:

1. select weather provider
2. design weather schema
3. implement API client
4. normalize responses
5. persist weather
6. connect weather with flights
7. test

Do not start with one giant implementation request.

---

# 4. Feature Branch

Every meaningful feature should be developed on a branch.

Naming:

feature/<name>
fix/<name>
docs/<name>
refactor/<name>
test/<name>

Examples:

feature/flight-ingestion
feature/weather-api
feature/mysql-schema
fix/timezone-parsing
docs/architecture

Do not develop major features directly on main.

---

# 5. Build

Implement only the approved task.

Principles:

- smallest complete change
- clear module boundaries
- testable code
- no unnecessary dependencies
- no unrelated refactoring

---

# 6. Local Validation

Relevant validation may include:

- unit tests
- integration tests
- linting
- formatting
- type checking
- SQL validation
- data-quality checks

The exact checks depend on the component being changed.

---

# 7. Self Code Review

Before commit, review:

## Correctness

Does the implementation satisfy the requirement?

## Scope

Did unrelated functionality change?

## Security

Are secrets exposed?

## Data

Could data be lost or corrupted?

## Error Handling

Are expected failures handled?

## Maintainability

Is the code understandable?

## Testing

Are important paths tested?

---

# 8. Commit

Commit only reviewed and validated work.

Commit messages should describe the change clearly.

Examples:

feat: add flight ingestion client

feat: add weather observation schema

fix: handle missing actual departure time

test: add delay calculation tests

docs: document ingestion architecture

# 9. Push

Push the feature branch to GitHub.

Do not push secrets, local environments, or `.env`.

---

# 10. Pull Request

Every meaningful feature should create a pull request.

PR should contain:

## What changed

Short description.

## Why

Business/technical reason.

## Testing

What validation was performed.

## Risks

Known limitations.

## Screenshots

Only when relevant to UI changes.

---

# 11. Continuous Integration

GitHub Actions should independently verify the code.

Planned checks:

- Python tests
- linting
- formatting verification
- type checking
- security scanning
- secret detection

Additional checks will be added later for:

- SQL
- ingestion
- data quality
- AI evaluation

---

# 12. Review

A change should not be merged merely because Codex generated it.

Review:

- implementation
- tests
- CI results
- scope
- architecture implications
- security implications

For Genesis-managed multi-agent work, the root Master / Orchestrator delegates
bounded implementation and then requests independent code, security, and test
review as appropriate to task risk. Reviewer agents report findings; they do
not rewrite application code. The Master decides which findings are accepted
and delegates accepted fixes to the Implementation Agent.

The Master records commands, results, findings, blockers, and checkpoint state
in Genesis. Specialist agents read the active brief but do not independently
mutate Genesis state. Executable gates must pass before shipping, and any
human-controlled gate remains pending until a human explicitly approves it.

The Shipping Agent may act only after explicit delegation and required
approval. It may prepare a feature branch, stage approved files, commit, push,
and prepare or open a pull request. It must never merge `main`, force push,
delete branches, or expose credentials.

---

# 13. Merge

Merge only after:

- tests pass
- CI passes
- review is complete
- user approves merge

Primary integration branch:

main

---

# 14. Cleanup

After successful merge:

- switch back to main
- pull latest main
- delete obsolete feature branch

---

# 15. Definition of Done

A task is DONE only when:

- requirement is satisfied
- implementation is complete
- appropriate tests pass
- code has been reviewed
- CI passes
- documentation is updated when necessary
- PR is merged
- STATUS.md reflects the completed state

Writing code alone does not mean the task is complete.

---

# Lifecycle Summary

```text
                 REQUIREMENT
                     |
                     v
                  SPEC.md
                     |
                     v
                   DESIGN
                     |
                     v
                    TASK
                     |
                     v
              FEATURE BRANCH
                     |
                     v
                   BUILD
                     |
                     v
                 VALIDATE
                     |
                     v
               SELF REVIEW
                     |
                     v
                  COMMIT
                     |
                     v
                   PUSH
                     |
                     v
              PULL REQUEST
                     |
                     v
              GITHUB ACTIONS
                     |
            +--------+--------+
            |                 |
          FAIL               PASS
            |                 |
            v                 v
           FIX              REVIEW
            |                 |
            +------->         v
                            MERGE
                              |
                              v
                           CLEANUP
