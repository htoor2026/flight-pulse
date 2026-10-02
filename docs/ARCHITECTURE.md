# Flight Pulse — Architecture

## Status

Initial architecture only.

This document will evolve as technical decisions are approved.

---

# System Goal

Flight Pulse is a flight analytics and investigation system that combines:

- flight operational data
- weather data
- disruption/news information
- SQL analytics
- an interactive dashboard
- an AI analyst

The primary analytical question is:

> Why was this flight delayed?

---

# High-Level Architecture

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
     /     \
    /       \
Weather     News
Pipeline    Pipeline
    \       /
     \     /
      MySQL
        |
        v
Analytics Layer
        |
        v
Dashboard
        |
        v
AI Analyst
        |
        +--> SQL Queries
        +--> Flight Lookup
        +--> Weather Context
        +--> News Context
        |
        v
Evidence-Grounded Delay Explanation