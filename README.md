# DrawTalk Harness

Built at [The Harness Engineering & Model Wrangling #SFTechWeek Hackathon](https://cerebralvalley.ai/e/mongodb-sftw-hackathon)
(MongoDB × Cerebral Valley, Oct 11 2026).

**Result:** ranked 10 / 93 ([gallery](https://cerebralvalley.ai/e/mongodb-sftw-hackathon/hackathon/gallery?project=4))
· [write-up](https://blog.liyiwei.org/2026/10/11/mongodb-hackathon/)

An animation tool that **learns your language**. You sketch 2D characters and animate them by typing
("the hare and the tortoise race to the tree"), drawing a path, or drawing a gesture. There's no preset
motion library: every behavior is taught, stored as a versioned motion program in MongoDB, regression-tested
against your past examples and improved from your corrections. Over time the harness **compiles your
vocabulary into fast, deterministic tools** that don't need an LLM call.

- **Recursive Harnessing**: the harness writes its own tools (behaviors), versions and tests its own
  changes, and retunes its own routing policy from feedback, with every change stored with a reason and
  evidence.
- **Long Horizon Engineering**: multi-scene stories stay coherent while you edit them. Characters keep
  learned traits and habits, scenes derive their start from the previous scene and re-simulate when it
  changes, behavior versions are pinned per clip, and a learning curve tracks hard signals.
- **Demos:** [1-minute video](https://youtu.be/-H8eB0-2pQw) · [all demo videos](#demo-videos-recorded-during-the-hackathon)
- Docs: [design](docs/design.md) · [motion DSL](docs/motion-dsl.md) · [demo runbook](docs/demo.md)
  · [judging notes + post-mortem](docs/judging.md) · [build plan](docs/plan.md) · [early brainstorm](docs/gemini.md)

## Demo videos (recorded during the hackathon)

<table>
<tr><td align="center" width="50%">
<a href="https://youtu.be/-H8eB0-2pQw"><img src="https://img.youtube.com/vi/-H8eB0-2pQw/mqdefault.jpg" width="260" alt="1-min submission: the rabbit and the turtle"></a><br><sub><b>1-min submission</b>: the rabbit and the turtle</sub></td><td align="center" width="50%"><a href="https://youtu.be/F-DWj3uXoY4"><img src="https://img.youtube.com/vi/F-DWj3uXoY4/mqdefault.jpg" width="260" alt="Full authoring session, in real time"></a><br><sub>Full authoring session, in real time</sub></td>
</tr>
<tr>
<td align="center" width="50%"><a href="https://youtu.be/1l65aWUpue8"><img src="https://img.youtube.com/vi/1l65aWUpue8/mqdefault.jpg" width="260" alt="Windmill: unedited take"></a><br><sub>Windmill: without refinement</sub></td>
<td align="center" width="50%"><a href="https://youtu.be/6RZ8EB5DQ08"><img src="https://img.youtube.com/vi/6RZ8EB5DQ08/mqdefault.jpg" width="260" alt="Windmill: wind and rotation"></a><br><sub>Windmill: with refinement</sub></td>
</tr>
<tr>
<td align="center" width="50%"><a href="https://youtu.be/pNa1l_5tPcE"><img src="https://img.youtube.com/vi/pNa1l_5tPcE/mqdefault.jpg" width="260" alt="Frog: hopping along a drawn path"></a><br><sub>Frog: hopping along a drawn path</sub></td>
<td align="center" width="50%"><a href="https://youtu.be/K0wzUBOYO1U"><img src="https://img.youtube.com/vi/K0wzUBOYO1U/mqdefault.jpg" width="260" alt="Pacman: a vanishing bean, fixes v1 → v6"></a><br><sub>Pacman: a vanishing bean, fixes v1 → v6</sub></td>
</tr>
</table>

All videos are also in the [YouTube playlist](https://www.youtube.com/playlist?list=PLD6Astl07U8A). The raw screen
recordings are not in the repo; the short video was cut from them with `scripts/make_short.py` and the cut lists in
`demos/*-cuts.json`.

## What was built when (hackathon provenance)

| When | What |
|---|---|
| Before the event (Oct 10) | design documents in `prep/` (renamed `docs/` after the event); environment setup (`pyproject.toml`, `.env.example`, `.claude/settings.json`); service smoke test `scripts/check_setup.py`; `scripts/voyage.py` |
| During the event (Oct 11, from 10:30) | **all application code**: `app/` (harness, motion DSL + evaluator, $P recognizer, refinement + regression replay, scene continuity, vector memory, routing policy, API), `static/` (canvas UI), `tests/`, `.claude/launch.json` |

The concept is inspired by the author's prior research prototypes (DrawTalking, Narrative Motion Blocks):
sketch + speech to animate drawings with a **preset** motion library. **No code, data or assets from those
projects are used here.** What's new is the agent harness: behaviors learned instead of preset,
versioned and regression-tested self-modification, fast-path compilation, self-tuned routing, and
long-horizon memory in MongoDB. The git history shows the timeline.

## How it works

| You provide | Where it goes | How it moves | Route |
|---|---|---|---|
| text | target character, direction, or in place | the words | LLM (with vector-memory examples) |
| path + text | along the drawn path | the words | LLM |
| gesture + text | (teaching) | the words; the gesture's shape is saved as a "drawn word" | LLM |
| gesture alone | in place (or along a path, if drawn) | the taught gesture ($P shape match) | ⚡ fast, no LLM |
| path alone | along the drawn path | the character's learned habit | ⚡ fast, no LLM (once the habit is clear) |
| "should always…" / "this time…" | | refines an existing behavior → v2 proposal | LLM + confirmation |

- **Behaviors** are small JSON programs in a motion DSL (`move_along`, `hop`, `bob`, `breathe`, `turn_to`,
  `seq`, `par`, …), written by the LLM against a strict JSON schema and evaluated in Python into keyframes.
  The browser only plays keyframes; no generated code is executed.
- **Parameters** carry their source, e.g. `speed 520: text 'race' + trait: hare is quick`.
- **Refinement** proposes v2 with a readable diff, replays every existing clip of that behavior (does it
  still end where the story needs it?), and asks for scope: *everywhere* (new version, upgrades passing
  clips) or *only this time* (an override on one clip).
- **Routing policy** lives in versioned `harness_config` documents. Accepted fast-path guesses relax the
  threshold, and undone ones tighten it, each change recorded with its reason and evidence.
- **Implicit feedback**: moving on accepts the previous clip; ✕ marks it undone. These are the hard signals
  behind the learning curve.

## Stack

| Layer | Tech |
|---|---|
| Data & memory | MongoDB Atlas (documents + Vector Search), PyMongo async driver |
| Embeddings | Voyage AI (`voyage-4-lite`, 1024-d) |
| LLM | OpenAI (`gpt-5.4-mini` by default). Any OpenAI-compatible server works, e.g. Ollama `qwen3-coder:30b` |
| Gestures | $P point-cloud recognizer (own implementation, `app/recognizer.py`) |
| Backend | Python 3.13, FastAPI, uvicorn, managed with `uv` |
| Frontend | SVG canvas, plain JS (no build step) |

Input is text only: the venue was too noisy for voice. The ElevenLabs speech-to-text check in
`scripts/check_setup.py` is from the pre-event setup.

## Reproduce

### 1. Prerequisites

- [`uv`](https://docs.astral.sh/uv/) (it installs Python 3.13 for you)
- A MongoDB Atlas cluster that supports Vector Search (we used an M10 in the hackathon sandbox)
- API keys: OpenAI and Voyage AI (or a local Ollama for the LLM; Voyage is still needed for memory)

### 2. Atlas

1. Create a cluster.
2. **Database Users** → add a user with *Read and write to any database*.
3. **Network Access** → add your current IP. Re-add it when your network changes; some networks use
   several outgoing IPs.
4. **Connect → Drivers → PyMongo (asynchronous)** → copy the `mongodb+srv://…` string.

### 3. Install and configure

```bash
git clone https://github.com/1iyiwei/drawtalk-mongodb-sftw-hackathon.git
cd drawtalk-mongodb-sftw-hackathon
uv sync
cp .env.example .env   # then fill in the values
```

`.env` is git-ignored. Never commit it. To use a local model instead of OpenAI, set
`LLM_BASE_URL=http://localhost:11434/v1` and `OPENAI_MODEL=qwen3-coder:30b`.

### 4. Check every service

```bash
uv run python scripts/check_setup.py
```

Expected: `PASS` for `voyage`, `mongo` (creates a vector index, ~50 s), and `openai`. `anthropic` and
`elevenlabs` are optional. Check one service with `uv run python scripts/check_setup.py mongo`.

### 5. Run the app

```bash
uv run uvicorn app.main:app --port 8000
```

Open <http://localhost:8000/?project=demo>. Each `?project=` name is an independent story with its own
characters, behavior library and routing policy. The app creates the collections, indexes and the
vector search index on first start; the vector index takes about a minute to become queryable.

1. **✏️ Ink**: draw a character, type its name in the name box, press Enter.
2. Type a command, e.g. `the hare and the tortoise race to the tree`, and press **Animate ▶**.
3. **➰ Path** / **✳️ Gesture**: draw, optionally type, then Animate. **🧽 Erase** is a lasso.
4. **＋ scene** continues the story. **▶▶ Play story** plays every scene.
5. Try `the tortoise should always plod a bit faster` to see a refinement proposal.

Tests: `uv run pytest`.

### 6. Optional: Claude Code with the MongoDB plugin

The repo's [`.claude/settings.json`](.claude/settings.json) enables MongoDB's official `mongodb-atlas`
plugin: the hosted MongoDB MCP server plus MongoDB agent skills. Open the repo in Claude Code, accept the
plugin, run `/mcp` → `plugin:mongodb-atlas:mongodb-atlas` → **Authenticate**, then restart the session.
The app itself doesn't need this.

## Data model (database `sketch_harness`)

| Collection | One document per | Notable fields |
|---|---|---|
| `projects` | story | `name` |
| `entities` | character | vector `strokes` (local coords), `bbox`, learned `traits` |
| `scenes` | scene | `added` / `removed` (own changes), derived `start_state`, `timeline` of clips (behavior + pinned version, params + sources, path, keyframes, `route`) |
| `behaviors` | behavior **version** | `program` (motion DSL), `params` (ranges, cues), `parent_version`, `reason`, `diff`, `evidence`, `tests`, `regression`, `stats` |
| `examples` | authored instance | text, path/gesture templates, chosen behavior@version, params, `outcome` (pending/accepted/undone), `route`, `text_vec` (Voyage, Vector Search) |
| `proposals` | refinement proposal | candidate version, diff, regression checks, scope guess + reason, status |
| `harness_config` | routing-policy version | `fast_path.min_score`, `min_examples`, `reason`, `evidence` |
| `events` | everything that happened | commands (route, latency, LLM tokens), acceptances, deletions, config changes, re-simulations |

Nothing is overwritten when the harness changes itself: new behavior and policy versions are new
documents.

## Repo layout

```
app/        main.py (API) · harness.py (routing, LLM decision, clips) · dsl.py (schema + evaluator)
            refine.py (diff, regression replay, scope) · scenes.py (continuity, re-simulation)
            memory.py (Voyage + Vector Search, harness_config) · recognizer.py ($P) · geometry.py · llm.py · db.py
static/     index.html · app.js · style.css (canvas UI, playback, inspector, learning curve)
tests/      DSL, geometry, recognizer, refinement and scene tests
docs/       design docs (pre-event + "as built"), plan, storyboard, demo runbook, judging notes + post-mortem,
            submission text, event guide, sandbox.md (unrelated CoreWeave notes)
scripts/    check_setup.py (service smoke test), voyage.py, sandbox.py (unrelated CoreWeave sample)
```
