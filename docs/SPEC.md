# Flight Pulse — Product Specification

## 1. Product Overview

Flight Pulse is a data analytics application that helps users monitor commercial flight performance and investigate flight delays.

The system combines:

- flight data
- weather data
- relevant news and disruption information
- SQL analytics
- an interactive dashboard
- an AI chatbot

The primary question Flight Pulse should answer is:

> Why was this flight delayed?

The system must not only display whether a flight was delayed but also gather supporting evidence that may explain the disruption.

---

# 2. Primary Goals

Flight Pulse must allow a user to:

1. View flights and determine whether each flight is:
   - on time
   - delayed
   - cancelled
   - unknown

2. Search for a specific flight.

3. Analyze delay patterns.

4. View weather conditions associated with a flight.

5. View relevant airport, airline, route, or disruption news.

6. Ask questions using natural language.

7. Allow the AI analyst to query the Flight Pulse database.

8. Allow the AI analyst to investigate weather and news when necessary.

9. Return an evidence-grounded explanation of a flight delay.

---

# 3. Example User Questions

The system should eventually support questions such as:

- Why was AC123 delayed?
- Was AC123 delayed because of weather?
- Show delayed flights from Toronto today.
- Which airline had the most delays today?
- Which airport has the highest delay rate?
- Which routes experience the most delays?
- How many flights were delayed today?
- Were delays worse during bad weather?
- What happened at Toronto Pearson this afternoon?
- Were multiple flights affected at the same time?
- What are the major flight disruptions today?
- Summarize the likely reasons for today's delays.

---

# 4. System Architecture

The high-level architecture is:

Flight Data Source
→ Flight Ingestion
→ Data Cleaning
→ MySQL

Weather API
→ Weather Ingestion
→ Data Cleaning
→ MySQL

News Sources
→ News Retrieval
→ Relevance Filtering
→ MySQL

MySQL
→ Analytics Layer
→ Dashboard

MySQL + Weather + News
→ AI Investigation Layer
→ Chatbot

---

# 5. Technology Direction

## Backend

Primary language:

- Python

Potential libraries:

- pandas
- requests/httpx
- BeautifulSoup or Playwright when scraping is required
- SQLAlchemy
- Pydantic
- FastAPI

Exact libraries may change during implementation.

---

# 6. Database

Use MySQL as the primary analytical database.

Do not use MongoDB for the first version.

MySQL is preferred because:

- flight data is structured
- airport and airline relationships are relational
- weather observations can be joined by airport and timestamp
- analytical queries are naturally expressed using SQL
- the AI chatbot will need to generate/read SQL
- SQL ability is an important part of the portfolio project

---

# 7. Core Data Model

## flights

Suggested fields:

- id
- flight_number
- airline_code
- airline_name
- departure_airport
- arrival_airport
- scheduled_departure
- actual_departure
- scheduled_arrival
- actual_arrival
- departure_delay_minutes
- arrival_delay_minutes
- flight_status
- aircraft
- source
- collected_at

---

## airports

Suggested fields:

- airport_code
- airport_name
- city
- country
- latitude
- longitude
- timezone

---

## airlines

Suggested fields:

- airline_code
- airline_name
- country

---

## weather_observations

Suggested fields:

- id
- airport_code
- observed_at
- temperature
- precipitation
- snowfall
- wind_speed
- wind_gust
- visibility
- weather_condition
- pressure
- source

---

## news_articles

Suggested fields:

- id
- title
- summary
- source
- published_at
- url
- airline
- airport
- disruption_type
- relevance_score
- collected_at

---

# 8. Flight Data Ingestion

The system should collect useful commercial flight information from an appropriate legal and technically reliable source.

Possible collection mechanisms include:

- public APIs
- permitted web scraping
- public datasets

The ingestion pipeline should collect at minimum:

- flight number
- airline
- departure airport
- arrival airport
- scheduled departure
- actual departure
- scheduled arrival
- actual arrival
- flight status

The application must preserve the original source information where practical.

---

# 9. Data Cleaning

The ingestion pipeline must handle:

- missing values
- duplicate flights
- inconsistent airport codes
- inconsistent airline names
- timestamp parsing
- timezone conversion
- incorrect data types
- invalid records

Raw source data must not be silently modified.

Transformations should be reproducible.

---

# 10. Delay Definition

Flight Pulse must use a clearly documented definition of a delayed flight.

For example:

departure_delay_minutes =
actual_departure - scheduled_departure

A configurable threshold may determine when a flight is considered delayed.

The exact threshold should be documented and consistently used throughout the project.

Possible statuses:

- On Time
- Delayed
- Cancelled
- Diverted
- Unknown

---

# 11. Weather Integration

Weather data should be retrieved using an appropriate weather API.

Weather observations should be associated with:

- departure airport
- arrival airport
- relevant timestamps

Useful weather variables may include:

- rain
- snow
- storms
- wind
- wind gusts
- visibility
- temperature
- precipitation
- weather condition

The system should support analyzing whether poor weather coincides with elevated flight delays.

Weather correlation must not automatically be described as causation.

---

# 12. News Analysis

Flight Pulse should collect relevant news or disruption information.

Useful categories include:

- airport disruptions
- airline operational issues
- strikes
- severe weather
- airport closures
- air traffic control issues
- security incidents
- major technical outages
- infrastructure failures
- large-scale travel disruptions

News should be filtered based on:

- airport
- airline
- route
- location
- publication time
- relevance to the flight disruption

The system should avoid presenting unrelated news as evidence.

---

# 13. Analytics Layer

The analytics system should calculate metrics such as:

## Overall

- total flights
- on-time flights
- delayed flights
- cancelled flights
- average delay
- median delay
- delay rate

## Airline

- flights by airline
- delays by airline
- average delay by airline
- airline delay rate

## Airport

- departures by airport
- delay rate by airport
- average airport delay
- number of simultaneous delayed flights

## Route

- flights by route
- average route delay
- route delay rate

## Time

- delays by hour
- delays by weekday
- delays by date
- delay trends over time

## Weather

- delay rate by weather condition
- average delay under poor weather
- delay patterns during high winds
- delay patterns during low visibility
- delay patterns during rain/snow

---

# 14. Dashboard

The dashboard must be user-friendly and prioritize operational clarity.

## Dashboard Home

Display:

- total flights
- on-time flights
- delayed flights
- cancellations
- average delay
- current disruption summary

---

## Flight Table

Display:

- flight
- airline
- origin
- destination
- scheduled departure
- actual departure
- delay
- status

Status must be visually easy to distinguish.

---

## Filters

Users should be able to filter by:

- date
- airline
- airport
- route
- flight status

---

## Flight Detail Page

Selecting a flight should show:

### Flight information

- airline
- route
- schedule
- actual timing
- delay duration
- status

### Weather

- departure weather
- arrival weather
- relevant weather conditions around the flight

### Operational context

- nearby flights
- airport delay activity
- airline delay activity

### News

- potentially relevant disruption articles

### AI investigation

Allow the user to ask why the flight may have been delayed.

---

# 15. AI Chatbot

The dashboard should contain an AI analyst/chatbot.

The chatbot must be able to use tools rather than relying entirely on its internal knowledge.

Potential tools:

- query_sql
- get_flight
- get_airport_delays
- get_airline_delays
- get_route_delays
- get_weather
- search_news
- investigate_delay

---

# 16. SQL Analysis

For analytical questions, the AI should generate or select appropriate SQL queries against the Flight Pulse database.

Example:

User:

> Which airline had the most delays today?

Process:

Natural language
→ determine analytical intent
→ generate SQL
→ validate query
→ execute read-only SQL
→ receive results
→ explain results

The AI must not have permission to execute destructive SQL.

Disallowed operations include:

- DROP
- DELETE
- UPDATE
- ALTER
- TRUNCATE

The AI analytics database connection should ideally be read-only.

---

# 17. Delay Investigation

When the user asks:

> Why was Flight X delayed?

The system should perform an investigation.

Possible workflow:

1. Retrieve the flight.
2. Calculate the actual delay.
3. Examine departure weather.
4. Examine arrival weather.
5. Examine airport-wide delays.
6. Examine other flights in the same time window.
7. Examine airline-wide delays.
8. Search relevant news.
9. Combine available evidence.
10. Generate an explanation.

---

# 18. Explanation Confidence

Flight Pulse must not manufacture a definitive reason.

Delay explanations should distinguish between:

## Confirmed

A reliable source explicitly states the reason.

## Strongly Supported

Multiple independent signals strongly support the explanation.

Example:

- severe weather
- airport-wide delays
- similar flights affected
- relevant airport warning

## Possible Contributor

Some evidence supports the explanation, but the exact cause is unavailable.

## Unknown

Available data does not support a reliable explanation.

Example output:

> AC123 departed 68 minutes late. Severe wind and reduced visibility were present at Toronto Pearson during the departure window, and other departures experienced elevated delays at the same time. Weather is therefore a plausible contributor, but the available sources do not confirm that it was the direct cause of this flight's delay.

---

# 19. AI Grounding Requirements

The chatbot must:

- use database results when answering analytical questions
- use weather information when relevant
- use news evidence when relevant
- distinguish facts from interpretation
- avoid inventing missing information
- state when evidence is unavailable
- include the evidence used in an investigation

---

# 20. Data Quality

The project must contain checks for:

- missing required columns
- duplicates
- null flight identifiers
- impossible timestamps
- negative delays where inappropriate
- invalid airport identifiers
- duplicate ingestion
- stale API data

---

# 21. Testing

The application should include:

## Unit tests

For:

- cleaning
- delay calculations
- transformations
- API parsing
- SQL utilities

## Integration tests

For:

- ingestion → database
- weather → database
- dashboard queries
- chatbot tools

## AI evaluation

Test questions should include:

- simple SQL questions
- complex aggregation questions
- individual flight investigations
- questions without sufficient evidence
- attempts to produce unsupported causal explanations

---

# 22. User Experience Principles

The product should prioritize:

- clarity
- fast navigation
- minimal visual clutter
- understandable metrics
- explainable conclusions

The dashboard should tell a story rather than merely contain charts.

---

# 23. MVP Scope

The first working version requires:

1. working flight ingestion
2. MySQL database
3. cleaned flight data
4. delay status calculation
5. weather integration
6. relevant news retrieval
7. analytical SQL queries
8. interactive dashboard
9. specific flight detail page
10. AI chatbot
11. SQL question answering
12. flight delay investigation
13. evidence-grounded explanations

---

# 24. Out of Scope for Initial Version

Do not initially build:

- flight delay prediction models
- deep learning models
- airline recommendation engines
- automated model retraining
- causal inference systems
- mobile apps
- complex multi-agent orchestration
- dozens of external APIs

These may be considered only after the core Flight Pulse system works reliably.

---

# 25. Definition of Done

Flight Pulse v1 is complete when a user can:

1. open the dashboard
2. see which flights are delayed or on time
3. filter and search flights
4. select a specific flight
5. inspect its timing and weather
6. ask the AI why it was delayed
7. have the AI query the database
8. have the system investigate relevant weather/news/operational context
9. receive an evidence-grounded explanation
10. clearly understand when the exact reason cannot be determined