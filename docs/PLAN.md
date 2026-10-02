# Flight Pulse — Implementation Plan

## Project Objective

Build Flight Pulse as an end-to-end flight analytics application that combines flight data, weather information, disruption news, SQL analytics, an interactive dashboard, and an AI analyst.

Development should proceed incrementally.

Do not attempt to build the chatbot before the underlying data platform works.

---

# Phase 0 — Project Foundation

## Objectives

Create a stable development environment and project structure.

## Tasks

- [ ] Initialize Git repository
- [ ] Create Python environment
- [ ] Create project folder structure
- [ ] Add `.gitignore`
- [ ] Add `.env.example`
- [ ] Create `AGENTS.md`
- [ ] Add `docs/SPEC.md`
- [ ] Add `docs/PLAN.md`
- [ ] Configure logging
- [ ] Configure testing
- [ ] Configure linting/formatting
- [ ] Create basic README

## Acceptance Criteria

- project runs locally
- tests can be executed
- secrets are excluded from Git
- Codex can read AGENTS.md, SPEC.md and PLAN.md

---

# Phase 1 — Investigate Flight Data Sources

## Objective

Determine a reliable source for flight information.

## Tasks

- [ ] Research available flight APIs
- [ ] Research permitted public flight websites
- [ ] determine API vs scraping approach
- [ ] identify rate limits
- [ ] verify available fields
- [ ] verify historical/live availability
- [ ] document source limitations

## Required Fields

Confirm that the source can provide enough of:

- flight number
- airline
- departure airport
- arrival airport
- scheduled departure
- actual departure
- scheduled arrival
- actual arrival
- flight status

## Deliverable

Create:

`docs/DATA_SOURCES.md`

## Acceptance Criteria

A flight source is selected before implementing the production ingestion pipeline.

---

# Phase 2 — MySQL Database

## Objective

Create the relational data layer.

## Tasks

- [ ] Install/configure MySQL
- [ ] Configure SQLAlchemy connection
- [ ] Create schema
- [ ] Create migrations if needed
- [ ] Create airports table
- [ ] Create airlines table
- [ ] Create flights table
- [ ] Create weather table
- [ ] Create news table
- [ ] Add indexes
- [ ] Add database tests

## Important Indexes

Consider indexes for:

- flight_number
- departure_airport
- arrival_airport
- scheduled_departure
- airline_code
- flight_status

## Acceptance Criteria

Python can:

- connect to MySQL
- create records
- retrieve flights
- filter flights
- execute analytical SQL

---

# Phase 3 — Flight Data Ingestion

## Objective

Collect and persist flight information.

## Tasks

- [ ] Build source client/scraper
- [ ] retrieve flight records
- [ ] parse response
- [ ] normalize field names
- [ ] normalize timestamps
- [ ] normalize airport codes
- [ ] normalize airlines
- [ ] calculate delays
- [ ] determine flight status
- [ ] prevent duplicate ingestion
- [ ] save records to MySQL
- [ ] log ingestion failures

## Tests

- [ ] parser tests
- [ ] timestamp tests
- [ ] duplicate tests
- [ ] delay calculation tests
- [ ] status tests

## Acceptance Criteria

Running the ingestion pipeline produces valid flight records in MySQL.

---

# Phase 4 — Data Quality Layer

## Objective

Ensure incoming flight data is analytically trustworthy.

## Checks

- [ ] missingness
- [ ] duplicates
- [ ] airport code validity
- [ ] airline identifier validity
- [ ] timestamp consistency
- [ ] impossible delay values
- [ ] stale records
- [ ] incomplete flights

## Output

Produce a data-quality summary for each ingestion run.

## Acceptance Criteria

Invalid records are detected and reported rather than silently entering analytical tables.

---

# Phase 5 — Initial Flight Analytics

## Objective

Build useful analytics before adding external context.

## Metrics

Implement:

- [ ] total flights
- [ ] on-time flights
- [ ] delayed flights
- [ ] cancelled flights
- [ ] delay percentage
- [ ] average delay
- [ ] median delay

## Analysis

Implement SQL for:

### Airlines

- [ ] delay rate
- [ ] average delay
- [ ] total delayed flights

### Airports

- [ ] flight volume
- [ ] delay rate
- [ ] average delay

### Routes

- [ ] busiest routes
- [ ] most delayed routes
- [ ] average route delay

### Time

- [ ] hourly delay pattern
- [ ] daily delay pattern
- [ ] weekday pattern

## Acceptance Criteria

All metrics can be retrieved through tested SQL queries.

---

# Phase 6 — Weather Integration

## Objective

Add environmental context to flights.

## Tasks

- [ ] select weather API
- [ ] obtain airport coordinates
- [ ] build weather API client
- [ ] retrieve weather observations
- [ ] handle API failures
- [ ] normalize timestamps
- [ ] store weather records
- [ ] join weather to flights by airport/time

## Weather Variables

Prioritize:

- temperature
- precipitation
- rain
- snow
- wind speed
- wind gust
- visibility
- weather condition

## Analysis

Investigate:

- delay rate under poor weather
- average delay by weather condition
- high wind periods
- low visibility periods
- rain/snow disruption patterns

## Acceptance Criteria

A flight can be connected to the relevant weather observations for its departure/arrival period.

---

# Phase 7 — News and Disruption Analysis

## Objective

Add external operational context.

## Tasks

- [ ] choose news source
- [ ] implement news retrieval
- [ ] search using airports
- [ ] search using airlines
- [ ] search disruption terminology
- [ ] store article metadata
- [ ] remove duplicate articles
- [ ] filter irrelevant articles
- [ ] generate short summaries
- [ ] calculate relevance to flight/time/location

## Possible Categories

- weather disruption
- airline outage
- airport closure
- labour disruption
- ATC issue
- security incident
- technical failure
- infrastructure failure

## Acceptance Criteria

The system can retrieve a small set of relevant news/context items for an airport, airline, or disruption time window.

---

# Phase 8 — Dashboard MVP

## Objective

Build the primary user interface.

## Suggested Technology

Start with Streamlit unless there is a strong technical reason to use another framework.

## Page 1 — Overview

Display:

- total flights
- on-time flights
- delayed flights
- cancelled flights
- average delay

Charts:

- delay status breakdown
- delays over time
- delay rate by airline
- delay rate by airport

---

## Page 2 — Flight Explorer

Create searchable/filterable flight table.

Filters:

- date
- airline
- departure airport
- arrival airport
- route
- status

Columns:

- flight
- airline
- origin
- destination
- scheduled time
- actual time
- delay
- status

---

## Page 3 — Flight Investigation

User selects a flight.

Display:

### Flight

- schedule
- actual timing
- delay
- status

### Weather

Display relevant departure/arrival weather.

### Operational context

Display:

- airport delay rate
- nearby delayed flights
- airline delay activity

### News

Display potentially related disruptions.

---

## Page 4 — Analytics

Include:

- airline analysis
- airport analysis
- route analysis
- temporal analysis
- weather analysis

## Acceptance Criteria

A non-technical user can quickly identify:

- which flights are delayed
- how long they are delayed
- where larger disruption patterns are occurring

---

# Phase 9 — AI SQL Analyst

## Objective

Allow natural-language analysis of Flight Pulse data.

## Architecture

User Question
→ LLM
→ determine query
→ SQL tool
→ MySQL
→ query result
→ LLM explanation

## Tasks

- [ ] define database schema context
- [ ] implement SQL generation
- [ ] implement SQL validation
- [ ] enforce read-only queries
- [ ] execute SQL
- [ ] format results
- [ ] generate explanation

## Safety

Allow:

- SELECT

Potentially allow:

- CTE
- GROUP BY
- JOIN
- aggregate functions
- window functions

Reject:

- INSERT
- UPDATE
- DELETE
- DROP
- ALTER
- TRUNCATE

## Evaluation Questions

Test:

- Which airline has the highest delay rate?
- How many flights are delayed today?
- What airport experienced the longest average delay?
- Show Toronto departures delayed more than 30 minutes.
- Compare delay rate during rain vs clear weather.

## Acceptance Criteria

The AI can correctly answer a predefined evaluation set of SQL questions.

---

# Phase 10 — Delay Investigation Engine

## Objective

Move from generic SQL chatbot to Flight Pulse's core feature:

"Why was this flight delayed?"

## Investigation Workflow

When a flight investigation starts:

### Step 1

Retrieve flight record.

### Step 2

Calculate:

- departure delay
- arrival delay
- flight status

### Step 3

Retrieve departure weather around the flight's departure window.

### Step 4

Retrieve arrival weather.

### Step 5

Analyze airport disruption.

Calculate:

- number of flights
- delayed flights
- delay rate
- average delay

around the same airport and time.

### Step 6

Analyze airline disruption.

Determine whether other flights from the airline were also delayed.

### Step 7

Analyze route disruption.

Check whether the same route experienced unusual delays.

### Step 8

Retrieve relevant news.

Search using:

- airline
- airport
- location
- time
- disruption keywords

### Step 9

Rank available evidence.

### Step 10

Generate investigation response.

---

# Phase 11 — Evidence and Confidence System

## Objective

Prevent unsupported AI explanations.

Classify conclusions as:

### Confirmed

Explicit reliable source confirms the cause.

### Strongly Supported

Several signals point toward the same explanation.

### Possible Contributor

Evidence exists but is insufficient for a strong conclusion.

### Unknown

No reliable explanation can be derived.

## Acceptance Criteria

The system must be capable of responding:

> There is insufficient evidence to determine the cause.

That response is preferable to fabricating an explanation.

---

# Phase 12 — AI Chatbot UI

## Objective

Add the AI analyst directly to the dashboard.

## Example Interaction

User:

"Why was AC123 delayed?"

Assistant workflow:

Flight lookup
→ weather lookup
→ airport analysis
→ airline analysis
→ news lookup
→ evidence synthesis

Response:

- flight status
- delay duration
- major evidence
- likely contributor
- confidence level
- limitations

---

# Phase 13 — Testing and Evaluation

## Data Pipeline

Test:

- ingestion
- cleaning
- duplicate handling
- database writes
- API failures

## Analytics

Validate SQL metrics manually against known examples.

## Chatbot

Create a benchmark dataset of questions.

Categories:

- simple lookup
- aggregation
- filters
- joins
- weather questions
- flight investigations
- unanswerable questions

Track:

- SQL correctness
- answer correctness
- evidence correctness
- unsupported claims
- tool failures

---

# Phase 14 — Codex Skills

After stable workflows exist, convert repetitive workflows into skills.

Potential project skills:

## flight-data-quality

Validates newly ingested flight data.

## flight-analysis

Performs standard Flight Pulse exploratory analysis.

## delay-investigation

Runs the standard delay-investigation workflow.

Do not create skills before the workflow is sufficiently stable to be reusable.

---

# Phase 15 — Subagents

Use subagents only for independent work.

Examples:

- source research
- test generation
- analytics review
- documentation review

Avoid multiple agents simultaneously editing tightly coupled application code.

---

# Phase 16 — MCP

Add MCP integrations only when needed.

Initial MCP:

- OpenAI documentation MCP

Possible future MCP capabilities:

- development documentation
- database inspection
- GitHub integration

Do not add an MCP server simply to demonstrate MCP.

It must solve an actual problem.

---

# Phase 17 — Hooks

Once normal development commands are stable, create deterministic hooks.

Possible hooks:

After Python changes:

- lint

Before completion:

- run tests

After data schema changes:

- schema checks

Before commit:

- secret scan

Hooks must automate known deterministic tasks, not replace reasoning.

---

# Phase 18 — Plugin

Plugin packaging is the final optional stage.

Only package reusable Flight Pulse capabilities after:

- ingestion works
- analytics works
- chatbot works
- skills are stable
- MCP needs are understood
- hooks are stable

A plugin should package genuinely reusable functionality rather than exist merely as a portfolio checkbox.

---

# Phase 19 — Portfolio Documentation

Create a high-quality README containing:

## Problem

Why understanding flight disruptions matters.

## Architecture

Show:

Flight data
+
Weather
+
News
→ MySQL
→ Analytics
→ Dashboard
→ AI investigation

## Data

Explain:

- source
- fields
- limitations

## Analytics

Show meaningful findings.

## AI

Explain:

- SQL generation
- tools
- grounding
- uncertainty handling

## Screenshots

Include:

- overview
- flight explorer
- investigation
- chatbot

## Demo

Record a short demonstration including:

1. finding a delayed flight
2. opening the flight
3. asking why it was delayed
4. showing the investigation
5. receiving the evidence-backed answer

---

# Implementation Order

Do not change this order without a concrete technical reason.

1. Repository/Codex setup
2. Flight-source research
3. MySQL
4. Flight ingestion
5. Data quality
6. SQL analytics
7. Weather
8. News
9. Dashboard
10. AI SQL analyst
11. Delay investigation engine
12. Chatbot UI
13. Evaluation
14. Skills
15. Subagents
16. MCP expansion
17. Hooks
18. Plugin
19. Portfolio documentation

---

# Immediate Next Milestone

Do not start with the chatbot.

The first milestone is:

**Flight data → MySQL → clean analytical table → correct delay status**

The milestone is complete when Flight Pulse can reliably show:

- flight number
- airline
- route
- scheduled time
- actual time
- delay minutes
- On Time / Delayed / Cancelled status

Only after this works should weather integration begin.