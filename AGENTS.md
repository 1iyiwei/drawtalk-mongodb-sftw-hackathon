# Agent notes

Shared instructions for any coding agent working in this repo. Human setup and reproduction steps are in
`README.md`. Read `ideation/design.md` and `ideation/motion-dsl.md` before larger changes, and `plan.md` for
the current schedule and status.

## Commands

- `uv sync`: install dependencies (Python 3.13, managed by `uv`; add packages with `uv add`, never pip)
- `uv run python scripts/check_setup.py [mongo|voyage|openai|anthropic|elevenlabs]`: smoke-test external
  services. Re-run after any network change (the Atlas IP access list).
- Run the app: *TBD*

## Rules

- **Hackathon rules**: all app code is written on Oct 11 2026 in the Atlas Hackathon Sandbox project. The
  repo becomes public at submission.
- **Secrets** live only in `.env` (git-ignored). `.env.example` lists names with empty values. Never print,
  log, commit or send key values or the full `MONGODB_URI`. Logs record ids, types and counts.
- **Motion is described only by the motion DSL** (`ideation/motion-dsl.md`): JSON checked against a schema.
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
- OpenAI `gpt-5.4-mini` supports JSON mode / Structured Outputs.
- Anthropic: the key works but the account has no credit, so OpenAI is the default.
- Atlas Agent Engine: the CLI download from agentengine.mongodb.com kept failing partway through
  (server-side). Not used unless that's fixed.
