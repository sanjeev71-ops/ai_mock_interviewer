# AI Mock Interviewer 🎯

A Streamlit-powered technical interview simulator. Pick a role, difficulty,
and question count — the app generates multiple-choice questions with an
LLM, scores your answers instantly, and produces a full performance report
with topic-wise analytics. Interview history persists in SQLite.

## Features

- **MCQ interviews** — 4 options per question (A–D), correct position varied,
  plausible distractors, short explanation per question
- **Role blueprints** — Python / Java / Web / Data Science / ML / Sprint… 6
  roles × 10 curated topics with deterministic topic distribution + cycling
- **Difficulty enforcement** — Easy / Medium / Hard guidelines baked into the
  prompt and validated on output
- **Quality gates** — Pydantic schema checks, exact + near-duplicate
  detection (keyword overlap), per-batch retries, cross-batch validation
- **Instant auto-scoring** — correct = 10, wrong = 0, computed in Python
  (no eval API calls, no score hallucination)
- **Exam-style flow** — free Back/Forward navigation, Skip, ⚑ Mark for
  review, Submit Test early, per-question or end-of-test evaluation timing
- **Whole-test timer** — optional 10–60 min limit with live countdown and
  auto-finish on expiry
- **Final report** — overall / technical / communication scores, strengths,
  weaknesses, recommendations, Plotly topic chart, Markdown download
- **Multi-model Groq support** — pick from free chat models at setup with
  automatic failover, pinned per interview
- **SQLite history** — every finished interview saved; browse past reports,
  per-attempt answers, and scores
- **Video-background UI** — looping background with dark overlay, frosted-
  glass inputs, centered layout

## Tech Stack

Python · Streamlit · Groq (OpenAI-compatible API) · Pydantic · SQLite ·
Plotly · python-dotenv

## Project Structure
# AI Mock Interviewer 🎯

A Streamlit-powered technical interview simulator. Pick a role, difficulty,
and question count — the app generates multiple-choice questions with an
LLM, scores your answers instantly, and produces a full performance report
with topic-wise analytics. Interview history persists in SQLite.

## Features

- **MCQ interviews** — 4 options per question (A–D), correct position varied,
  plausible distractors, short explanation per question
- **Role blueprints** — Python / Java / Web / Data Science / ML / Sprint… 6
  roles × 10 curated topics with deterministic topic distribution + cycling
- **Difficulty enforcement** — Easy / Medium / Hard guidelines baked into the
  prompt and validated on output
- **Quality gates** — Pydantic schema checks, exact + near-duplicate
  detection (keyword overlap), per-batch retries, cross-batch validation
- **Instant auto-scoring** — correct = 10, wrong = 0, computed in Python
  (no eval API calls, no score hallucination)
- **Exam-style flow** — free Back/Forward navigation, Skip, ⚑ Mark for
  review, Submit Test early, per-question or end-of-test evaluation timing
- **Whole-test timer** — optional 10–60 min limit with live countdown and
  auto-finish on expiry
- **Final report** — overall / technical / communication scores, strengths,
  weaknesses, recommendations, Plotly topic chart, Markdown download
- **Multi-model Groq support** — pick from free chat models at setup with
  automatic failover, pinned per interview
- **SQLite history** — every finished interview saved; browse past reports,
  per-attempt answers, and scores
- **Video-background UI** — looping background with dark overlay, frosted-
  glass inputs, centered layout


## Project Structure
