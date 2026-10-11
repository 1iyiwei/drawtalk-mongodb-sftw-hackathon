# Agent notes

Shared instructions for any coding agent working in this repo. Human setup and reproduction steps are in
`README.md`. Read `prep/design.md` and `prep/motion-dsl.md` before larger changes, and `prep/plan.md` for
the current schedule and status.

## Commands

- `uv sync`: install dependencies (Python 3.13, managed by `uv`; add packages with `uv add`, never pip)
- `uv run python scripts/check_setup.py [mongo|voyage|openai|anthropic|elevenlabs]`: smoke-test external
  services. Re-run after any network change (the Atlas IP access list).
- `uv run uvicorn app.main:app --port 8000` (or the `app` entry in `.claude/launch.json`): the app at http://localhost:8000/?project=<name>
- `uv run pytest`: unit tests (DSL, geometry, recognizer, refinement, scenes); no network

## Rules

- **Hackathon rules**: all app code is written on Oct 11 2026 (hacking starts 10:30, submissions due 17:00) in the
  Atlas Hackathon Sandbox project. The repo becomes public at submission. Keep the README's "what was built
  when" table current.
- **Secrets** live only in `.env` (git-ignored). `.env.example` lists names with empty values. Never print,
  log, commit or send key values or the full `MONGODB_URI`. Logs record ids, types and counts.
- **Motion is described only by the motion DSL** (`prep/motion-dsl.md`): JSON checked against a schema.
  Never `eval` generated code in the browser. The Python evaluator is the reference implementation that
  regression tests use.
- **Every harness self-modification is a new versioned document** (`behaviors`, `harness_config`) with
  `parent_version`, `reason` and `evidence`. Never overwrite in place.
- **Adaptive defaults stay visible and controllable**: whatever the system guesses (scope, parameters,
  routing, propagation) shows up in the UI with its source and can be overridden.
- **Pipeline first**: keep a working end-to-end slice and improve it step by step. Don't build one stage
  deep while another is missing.
- The LLM sits behind one small module with the model set by env var (`OPENAI_MODEL`, default
  `gpt-5.4-mini`), so providers can be swapped.

## Provider notes (verified 2026-10-10)

- Atlas Vector Search index on M10: queryable about 50 s after creation. Poll `list_search_indexes` for
  `queryable` before querying.
- Voyage `voyage-4-lite` → 1024-d vectors.
- ElevenLabs: `POST /v1/speech-to-text` with `model_id=scribe_v2`. The key is restricted to Speech to Text.
  **At the venue (Oct 11) free-tier access was blocked (HTTP 401 "unusual activity", likely the shared IP)**, so voice
  input uses the browser Web Speech API or typing.
- Venue Wi-Fi (SHACK15) sends traffic out through two IPs (`12.94.170.82`, `4.78.254.114`); both are on the Atlas access list.
- OpenAI `gpt-5.4-mini` supports JSON mode / Structured Outputs.
- Anthropic: the key works but the account has no credit, so OpenAI is the default.
- Atlas Agent Engine: the CLI download from agentengine.mongodb.com kept failing partway through
  (server-side). Not used unless that's fixed.
