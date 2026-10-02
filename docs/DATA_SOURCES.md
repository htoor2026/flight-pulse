# Flight Pulse — Data Source Investigation

Last updated: 2026-10-02

## Status

IN PROGRESS

No production flight-data provider has been approved yet.

No ingestion implementation should begin until the primary source is selected and documented here.

---

# 1. Objective

Identify the flight-data source that best supports Flight Pulse.

Flight Pulse requires enough operational flight information to:

- identify flights
- determine whether flights are on time or delayed
- calculate delay duration
- analyze airline, airport, and route delays
- connect flights with weather observations
- investigate disruption patterns
- support the AI delay-investigation workflow

The selected source must be technically usable, financially reasonable, and appropriate for portfolio/personal use.

---

# 2. Minimum Required Flight Fields

The preferred source should provide:

| Field | Required |
|---|---|
| Flight number | Yes |
| Airline | Yes |
| Departure airport | Yes |
| Arrival airport | Yes |
| Scheduled departure | Yes |
| Actual departure | Yes |
| Scheduled arrival | Yes |
| Actual arrival | Preferred |
| Flight status | Yes |
| Cancellation status | Preferred |
| Diversion status | Preferred |
| Delay information | Preferred |
| Aircraft information | Optional |
| Gate / terminal | Optional |

If delay minutes are not provided directly, Flight Pulse should be able to calculate them from scheduled and actual timestamps.

---

# 3. Geographic Requirement

The source must support airports relevant to the initial Flight Pulse scope.

Initial priority:

- Toronto Pearson International Airport — YYZ
- major Canadian airports
- flights operating to/from Canadian airports

Potential future expansion:

- United States
- international routes

---

# 4. Data Scope Requirements

The investigation must distinguish between:

## Current / Recent Flight Data

Needed for:

- current dashboard
- recent delays
- flight investigation
- operational context

## Historical Flight Data

Needed for:

- historical delay analysis
- airline comparisons
- route analysis
- airport analysis
- trend analysis
- portfolio demonstrations

A source that provides only live aircraft positions is not sufficient by itself.

---

# 5. Candidate Sources

The following candidates should be investigated.

## 5.1 AeroDataBox

Investigate:

- flight status API
- airport arrivals/departures
- scheduled timestamps
- actual/revised timestamps
- historical availability
- delay-related information
- Canadian airport coverage
- free/paid access
- request limits
- storage restrictions
- portfolio usage terms

Status:

UNDER INVESTIGATION

---

## 5.2 Aviationstack

Investigate:

- live flight endpoint
- historical flight availability
- scheduled and actual timestamps
- flight status
- airline/airport information
- free-tier restrictions
- request limits
- commercial vs personal-use restrictions

Status:

UNDER INVESTIGATION

---

## 5.3 FlightAware AeroAPI

Investigate:

- flight status
- scheduled/actual timestamps
- historical availability
- cancellation/diversion information
- airport operational data
- delay information
- Canadian coverage
- pricing
- minimum billing requirements
- usage/storage restrictions

Status:

UNDER INVESTIGATION

---

## 5.4 Cirium

Investigate:

- flight status
- scheduled/estimated/actual timestamps
- historical data
- delay calculations
- airline and airport coverage
- API accessibility
- developer access
- pricing
- portfolio suitability

Status:

UNDER INVESTIGATION

---

## 5.5 OpenSky Network

Investigate:

- aircraft state data
- flight records
- available identifiers
- historical availability
- whether commercial flight numbers are consistently available
- whether schedules are available
- whether delays/cancellations are available
- API limits
- licensing restrictions

Status:

UNDER INVESTIGATION

---

# 6. Comparison Criteria

Each candidate should be evaluated using the same criteria.

| Criterion | Importance |
|---|---|
| Flight number | Critical |
| Scheduled departure | Critical |
| Actual departure | Critical |
| Origin/destination | Critical |
| Flight status | Critical |
| Canadian/YYZ coverage | Critical |
| Recent/live data | High |
| Historical data | High |
| Cancellation/diversion data | Medium |
| Delay information | High |
| API reliability | High |
| Documentation quality | Medium |
| Free tier | Medium |
| Affordable paid tier | High |
| Reasonable rate limits | High |
| Data-storage permission | Critical |
| Portfolio-use permission | Critical |
| Authentication complexity | Low |
| Integration complexity | Medium |

---

# 7. Comparison Matrix

Do not complete this table from assumptions.

Values must be verified from provider documentation.

| Capability | AeroDataBox | Aviationstack | FlightAware | Cirium | OpenSky |
|---|---|---|---|---|---|
| Flight number | TBD | TBD | TBD | TBD | TBD |
| Scheduled departure | TBD | TBD | TBD | TBD | TBD |
| Actual departure | TBD | TBD | TBD | TBD | TBD |
| Scheduled arrival | TBD | TBD | TBD | TBD | TBD |
| Actual arrival | TBD | TBD | TBD | TBD | TBD |
| Flight status | TBD | TBD | TBD | TBD | TBD |
| Delay information | TBD | TBD | TBD | TBD | TBD |
| Cancellation | TBD | TBD | TBD | TBD | TBD |
| Diversion | TBD | TBD | TBD | TBD | TBD |
| YYZ coverage | TBD | TBD | TBD | TBD | TBD |
| Recent/live data | TBD | TBD | TBD | TBD | TBD |
| Historical data | TBD | TBD | TBD | TBD | TBD |
| Free tier | TBD | TBD | TBD | TBD | TBD |
| Paid cost | TBD | TBD | TBD | TBD | TBD |
| Rate limits | TBD | TBD | TBD | TBD | TBD |
| Data storage allowed | TBD | TBD | TBD | TBD | TBD |
| Portfolio use allowed | TBD | TBD | TBD | TBD | TBD |
| Integration difficulty | TBD | TBD | TBD | TBD | TBD |

---

# 8. Research Method

For every provider:

1. Read official API documentation.
2. Read current pricing documentation.
3. Read usage/licensing terms relevant to API data.
4. Confirm required fields.
5. Confirm YYZ/Canadian support.
6. Confirm live/recent availability.
7. Confirm historical availability.
8. Confirm rate limits.
9. Determine whether data can be stored locally.
10. Determine whether personal portfolio usage is allowed.
11. Record limitations.
12. Test the API only after credentials/API usage are explicitly approved.

Prefer official provider documentation over blogs or third-party tutorials.

---

# 9. Sample Response Validation

Before selecting a provider, obtain or inspect a representative flight response.

Verify that it can support a normalized record similar to:

```json
{
  "flight_number": "AC123",
  "airline": "Air Canada",
  "departure_airport": "YYZ",
  "arrival_airport": "YVR",
  "scheduled_departure": "...",
  "actual_departure": "...",
  "scheduled_arrival": "...",
  "actual_arrival": "...",
  "status": "...",
  "cancelled": false,
  "diverted": false
}