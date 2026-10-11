# DrawTalk Harness

Built at [The Harness Engineering & Model Wrangling #SFTechWeek Hackathon](https://cerebralvalley.ai/e/mongodb-sftw-hackathon)
(MongoDB × Cerebral Valley, Oct 11 2026).

An animation tool that **learns your language**. You sketch 2D characters and animate them by drawing
strokes and/or talking ("the hare and the tortoise race to the tree"). There's no preset library: every
behavior is taught, stored as a versioned motion program in MongoDB, tested against your past examples
and improved from your corrections. Over time the harness turns your vocabulary into fast, deterministic
tools that don't need an LLM call.

- Problem statements: **Recursive Harnessing** (the harness rewrites its own tools, routing and rules) and
  **Long Horizon Engineering** (multi-scene stories with character memory, version pinning and learning
  curves from hard signals).
- Design: [`ideation/design.md`](ideation/design.md) · motion DSL: [`ideation/motion-dsl.md`](ideation/motion-dsl.md)
  · demo script: [`ideation/storyboard.md`](ideation/storyboard.md) · build plan: [`plan.md`](plan.md)
  · early brainstorm: [`ideation/gemini.md`](ideation/gemini.md)

> Status: setup and design done before the event; the app is being built on hackathon day.
> Sections marked *TBD* get filled in as the parts land.

## Stack

| Layer | Tech |
|---|---|
| Data & memory | MongoDB Atlas (documents + Vector Search), PyMongo async driver |
| Embeddings | Voyage AI (`voyage-4-lite`, 1024-d) |
| LLM | OpenAI (`gpt-5.4-mini` by default; set by env var) |
| Speech to text | ElevenLabs Scribe (`scribe_v2`), optional; browser Web Speech API as fallback |
| Backend | Python 3.13, FastAPI, uvicorn, managed with `uv` |
| Frontend | SVG canvas + Web Animations API (no build step) |

## Reproduce

### 1. Prerequisites

- [`uv`](https://docs.astral.sh/uv/) (it installs Python 3.13 for you)
- A MongoDB Atlas cluster that supports Vector Search (we used an M10 in the hackathon sandbox)
- API keys: OpenAI, Voyage AI; optional: ElevenLabs (Speech to Text only), Anthropic
- macOS for the ElevenLabs part of the setup check (it makes test audio with `say` / `afconvert`)

### 2. Atlas

1. Create a cluster.
2. **Database Users** → add a user with *Read and write to any database*.
3. **Network Access** → add your current IP. Re-add it when your network changes.
4. **Connect → Drivers → PyMongo (asynchronous)** → copy the `mongodb+srv://…` string.

### 3. Install and configure

```bash
git clone https://github.com/1iyiwei/drawtalk-mongodb-sftw-hackathon.git
cd drawtalk-mongodb-sftw-hackathon
uv sync
cp .env.example .env   # then fill in the values
```

`.env` is git-ignored. Never commit it.

### 4. Check every service

```bash
uv run python scripts/check_setup.py
```

Expected output (the Anthropic line is optional):

```
PASS voyage     voyage-4-lite, dim=1024
PASS mongo      ping, insert, vector index (~50 s), $vectorSearch top hit: 'a bird flies to a tree'
PASS openai     gpt-5.4-mini: {"ok": true}
PASS elevenlabs scribe_v2: 'This gesture means fly over there bouncing'
```

You can check one service at a time: `uv run python scripts/check_setup.py mongo`. The Mongo check creates
and then drops a temporary `_setup_check` collection.

### 5. Run the app

*TBD (hackathon day).*

### 6. Optional: Claude Code with the MongoDB plugin

The repo's [`.claude/settings.json`](.claude/settings.json) enables MongoDB's official
`mongodb-atlas` plugin: the hosted MongoDB MCP server plus MongoDB agent skills. When you open the
repo in Claude Code, accept the plugin, then run `/mcp` → `plugin:mongodb-atlas:mongodb-atlas` →
**Authenticate** and sign in with your Atlas account. Restart the session to load the tools. The app
itself doesn't need this.

## Data model

*TBD.* Planned collections: `entities`, `scenes`, `behaviors` (one doc per version), `examples`, `events`,
`harness_config` (see [`ideation/design.md`](ideation/design.md)).

## Repo layout

```
ideation/          design docs (design, motion DSL, storyboard) + early brainstorm
plan.md            hackathon plan, setup status, day schedule
scripts/           check_setup.py (service smoke test), voyage.py (embedding demo), sandbox.* (unrelated CoreWeave notes)
.claude/           Claude Code project settings (MongoDB plugin)
.env.example       required environment variable names
```
