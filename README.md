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

## Streamlit Community Cloud deployment

The verified entry point is **`app.py`** at the repository root. Use
**Python 3.13** in Community Cloud advanced settings, for the local validation environment.
`requirements.txt` lists the five external packages imported by the app.
SQLite, pathlib, and other standard-library modules need no pip packages;
the Groq client uses `openai`, so the `groq` SDK is not required.
Pydantic 2 is required by `model_validate` and the list field constraints.
Direct dependency versions are pinned to the versions validated locally.

Validation on Python 3.13 passed: syntax for all 26 Python files, `pip check`,
secret precedence and dotenv fallback, mocked Groq JSON calls and safe errors,
Pydantic constraints, temporary SQLite schema/save/read/reinitialization,
Markdown export, Plotly figure serialization, and Streamlit AppTest startup
and history screens. Tests used dummy credentials and a temporary database;
no live Groq requests or project database migrations were run.
Live question/report generation and browser video playback remain manual checks.

### Local setup (PowerShell)

```powershell
cd E:\chatgpt\ai_mock_interviewer
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
notepad .env
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Enter your own Groq key in `.env`; never paste it into chat or commit it.
The app loads `.env` relative to this repository, without overriding existing
environment variables. Streamlit secrets take priority over environment values.
Restart Streamlit after changing credentials.

### Deployment checklist

- [ ] Back up any local `data/interviews.db` before running the app against it.
      Existing startup code performs additive schema migrations. No migration
      or database removal is part of this deployment preparation.
- [ ] Review `git diff` and `git status --short`. Verify `.env`,
      `.streamlit/secrets.toml`, virtual environments, and SQLite files stay ignored.
- [ ] Commit and push the reviewed source to your own GitHub repository yourself.
      Keep `static/background.mp4`, the Python packages, and `.streamlit/config.toml`.
- [ ] In https://share.streamlit.io choose Create app, then your repository,
      branch, and main file path `app.py`.
- [ ] In Advanced settings select Python 3.13 and enter secrets in TOML format:

      ```toml
      GROQ_API_KEY = "replace-with-your-own-key-in-the-cloud-secrets-editor"
      GROQ_BASE_URL = "https://api.groq.com/openai/v1"
      GROQ_MODEL = "qwen/qwen3.8-27b"
      ```

      Only `GROQ_API_KEY` is required. The other two settings already have the
      shown defaults. Do not commit a secrets file containing a real key.
- [ ] Click Deploy yourself, review build logs, then test question generation,
      answer scoring, navigation, timer, final report, charts, download, and history.

### Storage and operational limits

SQLite initializes `data/interviews.db` relative to the repository root and
creates its parent directory and missing tables. Cloud storage is not durable:
history can be lost on a rebuild, reboot, or replacement of the app instance.
Your ignored local database is not uploaded; the cloud app starts with empty
history. Download reports you need to keep. Durable history requires a separate
storage decision; this preparation does not migrate or remove any database.

The existing history screen reads the shared database without user authentication.
All app visitors can browse saved interview history. Decide who may access the
app before making it public.

Groq model availability and quotas depend on your account. The configured Qwen
model is currently listed as a preview model; the existing GPT-OSS fallbacks
remain available in the UI. No model is guaranteed to be free for every account.
Live Groq validation requires your own key and is separate from offline checks.
The background video is about 6.8 MB and is embedded as base64; it increases page
transfer size, while the existing gradient remains the fallback.

References:
- https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy
- https://docs.streamlit.io/develop/concepts/connections/secrets-management
- https://console.groq.com/docs/models
