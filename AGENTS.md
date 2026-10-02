# Flight Pulse — Codex Operating Rules

## 1. Project

Flight Pulse is a flight analytics system that combines:

- flight data
- MySQL
- weather data
- news/disruption analysis
- SQL analytics
- an interactive dashboard
- an AI chatbot
- evidence-grounded flight delay investigation

The project specification is:

`docs/SPEC.md`

The implementation roadmap is:

`docs/PLAN.md`

The current project state is:

`docs/STATUS.md`

---

# 2. Source of Truth

Use the following priority:

1. Explicit instructions from the user in the current conversation
2. `docs/SPEC.md`
3. `docs/PLAN.md`
4. `docs/STATUS.md`
5. Existing repository implementation

If documents conflict, stop and ask the user.

Do not resolve requirement conflicts independently.

---

# 3. Mandatory Human Approval

This project operates in STRICT MANUAL APPROVAL MODE.

Codex MUST obtain explicit user approval BEFORE performing ANY action.

This applies even to very small actions.

Examples include, but are not limited to:

- reading a file that has not already been examined
- searching the repository
- creating a file
- editing a file
- deleting a file
- renaming a file
- moving a file
- creating a folder
- running a shell command
- running Python
- running tests
- running formatting
- running linting
- running type checking
- installing a package
- modifying dependencies
- accessing the internet
- calling an API
- using MCP
- using a skill
- spawning a subagent
- creating a hook
- executing a hook
- connecting to a database
- creating a database
- modifying a database
- running SQL
- scraping a website
- creating a Git branch
- switching Git branches
- staging files
- committing
- pushing
- creating a pull request
- merging a pull request
- deleting a branch
- changing configuration
- updating PLAN.md
- updating STATUS.md
- updating SPEC.md

Do not assume approval from a previous action applies to a new action.

---

# 4. Approval Protocol

Before every action, Codex must explain:

1. What it wants to do
2. Why it wants to do it
3. What file, command, service, or resource will be affected
4. What result is expected
5. Any meaningful risk or side effect

Then STOP.

Wait for explicit user approval.

Example:

Proposed action:

Create `src/ingestion/flight_client.py`

Purpose:
Create the initial flight data ingestion module.

Changes:
- create one Python file
- no dependencies installed
- no external API call yet

Expected result:
Project will contain the initial ingestion interface.

Risk:
None beyond creating the file.

Proceed?

Codex must not perform the action until the user explicitly approves it.

---

# 5. No Implicit Approval

The following do NOT count as approval:

- silence
- previous approval
- an approved PLAN
- an approved SPEC
- an approved milestone
- "continue later"
- assumptions about user intent

Approval must relate to the specific proposed action.

If uncertain, ask.

---

# 6. One Action at a Time

Do not bundle unrelated actions into one approval request.

Bad:

"Can I create five files, install packages, initialize Git, create MySQL tables,
run tests, and commit everything?"

Good:

"Can I create the initial project directories?"

After completion, request approval for the next action.

---

# 7. Never Automatically Continue

After completing an approved action:

1. report what happened
2. report any relevant result
3. propose the next action
4. wait for approval

Do not automatically proceed to the next PLAN.md task.

---

# 8. Planning Rules

For substantial work:

1. inspect the approved source material
2. propose the implementation approach
3. obtain approval
4. perform only the approved action

Do not change architecture independently.

Do not expand scope without user approval.

Do not add features just because they seem useful.

---

# 9. SPEC Rules

`docs/SPEC.md` defines WHAT Flight Pulse should become.

Do not modify SPEC.md unless the user explicitly approves the exact change.

Do not reinterpret requirements to increase project scope.

If implementation reveals a problem with the specification:

STOP and explain the problem.

---

# 10. PLAN Rules

`docs/PLAN.md` defines HOW Flight Pulse will be built.

Do not automatically implement the next phase.

Each phase requires explicit user approval.

Do not mark checklist items complete until the user approves updating PLAN.md.

---

# 11. STATUS Rules

`docs/STATUS.md` records the current state of the repository.

It should contain:

- current phase
- completed work
- current work
- next proposed action
- decisions
- known issues
- validation results

Updating STATUS.md is itself an action and therefore requires approval.

---

# 12. Software Engineering Rules

Prefer:

- clear module boundaries
- simple designs
- small functions
- type hints
- reproducible data pipelines
- testable components
- explicit configuration
- environment variables for secrets

Avoid:

- premature abstraction
- unnecessary frameworks
- unnecessary dependencies
- duplicate logic
- giant files
- hidden side effects

---

# 13. Data Rules

Never modify raw source data silently.

Raw data should remain reproducible.

Validate:

- required columns
- data types
- missing values
- duplicates
- timestamps
- timezones
- airline identifiers
- airport identifiers
- impossible values

Do not discard invalid data without reporting it.

---

# 14. Analytics Rules

Always distinguish:

- observed fact
- statistical association
- inference
- confirmed cause

Do not claim:

"Weather caused this flight delay."

unless a reliable source explicitly confirms it.

Otherwise use language such as:

- possible contributor
- associated with
- available evidence suggests
- insufficient evidence

---

# 15. SQL Rules

AI-generated SQL must eventually operate through read-only database credentials.

For AI analytical queries, allow:

- SELECT
- JOIN
- GROUP BY
- ORDER BY
- CTE
- aggregate functions
- window functions

Do not allow the AI analyst to execute:

- DROP
- DELETE
- UPDATE
- INSERT
- ALTER
- TRUNCATE

Database schema modifications must always require explicit user approval.

---

# 16. Secrets

Never place secrets directly in source code.

Never commit:

- API keys
- passwords
- database passwords
- tokens
- credentials
- `.env`

Use environment variables.

Do not print secrets into logs.

---

# 17. Git Rules

Never perform Git write actions without approval.

This includes:

- branch creation
- checkout/switch
- add
- commit
- push
- pull
- rebase
- merge
- reset
- branch deletion
- tag creation
- pull request creation

Before each Git action, show the exact intended command.

---

# 18. Dependency Rules

Do not install packages automatically.

Before proposing installation:

1. explain why the dependency is needed
2. state the package name
3. state whether an existing dependency can solve the problem
4. wait for approval

Never install packages globally unless specifically approved.

Prefer the project's virtual environment.

---

# 19. Internet and API Rules

Do not access external websites, APIs, MCP servers, package registries, or
other network resources without explicit approval.

Before network access, explain:

- destination
- purpose
- data being sent
- expected result

---

# 20. MCP Rules

Do not add, configure, call, remove, or modify an MCP server without approval.

When MCP is proposed, explain:

- what server
- why it is needed
- what capabilities it exposes
- whether it can write or only read

---

# 21. Skills

Do not create or invoke project skills without approval.

Skills should represent stable reusable workflows.

Do not create a skill merely to demonstrate that skills exist.

---

# 22. Subagents

Do not spawn subagents without explicit approval.

Before proposing a subagent, explain:

- task
- why isolated context helps
- what files/resources it may access
- expected output

Subagents must not independently modify shared files unless specifically approved.

---

# 23. Hooks

Do not create or execute hooks without explicit approval.

Hooks should only automate deterministic lifecycle operations.

Examples:

- linting
- testing
- formatting
- secret scanning

Hook definitions must be reviewed by the user before being enabled.

---

# 24. Plugin

Do not create or package a plugin until the user explicitly starts the plugin phase.

Plugin development is not part of the initial MVP.

---

# 25. No Automatic Deployment

Never deploy Flight Pulse without explicit approval.

Do not:

- provision cloud infrastructure
- purchase services
- create paid resources
- expose ports publicly
- configure production credentials
- publish the application

without permission.

---

# 26. No Automatic Media Creation

Do not create:

- videos
- demo recordings
- promotional content
- social media posts
- marketing material

unless explicitly requested.

If PLAN.md mentions a demo video, treat it as:

MANUAL USER TASK.

---

# 27. Testing

Tests must eventually be run before work is considered complete.

However, under strict approval mode:

Do not run tests automatically.

Propose the exact test command and obtain approval first.

Example:

`pytest tests/test_delay_calculation.py -v`

After execution, report the result.

---

# 28. Failure Handling

If an approved action fails:

1. do not immediately attempt another fix
2. explain the error
3. identify the likely cause
4. propose the next action
5. wait for approval

Do not enter autonomous trial-and-error loops.

---

# 29. Session Recovery

At the beginning of a new Codex session:

1. do not modify anything
2. request permission to inspect:
   - AGENTS.md
   - docs/SPEC.md
   - docs/PLAN.md
   - docs/STATUS.md
3. inspect Git status only after approval
4. summarize current state
5. propose the next action
6. wait for approval

Do not rely on previous chat memory.

Repository files and Git are the persistent source of project state.

---

# 30. Definition of Correct Behavior

Correct Codex behavior is:

Propose
→ Explain
→ Ask
→ Wait
→ Execute only approved action
→ Report result
→ Propose next action
→ Ask again

Never:

Propose
→ Assume
→ Execute multiple steps

Human approval always remains the final authority.