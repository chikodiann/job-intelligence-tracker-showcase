# Project walkthrough

## Problem
Searching across multiple job boards creates repetitive work: collecting listings, removing duplicates, comparing requirements, checking location restrictions, and maintaining a separate record of applications.

## Approach
The application separates discovery, evaluation, persistence, presentation, and application management into distinct components.

## Data flow
1. Source adapters retrieve listings from configured public feeds and APIs.
2. Normalisation maps source-specific fields into a common representation.
3. Deduplication prevents repeated listings from dominating the results.
4. Eligibility and relevance modules evaluate geography and candidate criteria.
5. Scoring and ranking prioritise listings for human review.
6. SQLite stores job and application data.
7. The dashboard presents opportunities and application progress.

## What to inspect in the code
- `src/job_monitor/ingestion/`: adapters and ingestion pipeline
- `src/job_monitor/scoring/`: relevance, eligibility, classification and ranking
- `src/job_monitor/db/`: persistence layer and schema
- `src/job_monitor/dashboard/`: local dashboard
- `src/job_monitor/models/`: domain objects
- `src/job_monitor/reports/`: analytics and export
- `tests/`: regression and behaviour tests

## Design principles
- Keep the system local-first and proportionate to the use case.
- Keep job discovery separate from application state.
- Preserve application status transitions for meaningful analytics.
- Treat geographic eligibility as an important factor in opportunity relevance.
- Keep humans in control of application decisions.

## Discussion topics
A technical review can explore ingestion failure handling, source-specific parsing, deduplication strategy, SQLite schema choices, scoring trade-offs, test coverage, and the reasons for keeping the system local-first.
