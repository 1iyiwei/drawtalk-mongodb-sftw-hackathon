# Plan: sketch-and-talk animation with a self-evolving harness

Brainstorm with Claude Code, 2026-10-10. Builds on `ideation.md` (the agentic DrawTalking direction).

## Event facts (resource guide Google Doc + public page)

- Sun Oct 11 at Shack15, SF. Judges: Raindrop, AWS, MongoDB, Modelence.
- Prizes: MongoDB $7k / $5k / $3k, plus ElevenLabs tiers.
- **Hard rules**
  - To be a finalist you must build in the **MongoDB Atlas Hackathon Sandbox** (link arrives by email).
    Create the project and cluster through that link.
  - **No prior projects: all work original.** Tonight is for accounts, keys and tooling only, not app code.
  - Submit on the Cerebral Valley platform: **public GitHub repo, a 1-minute demo video** (check that audio
    plays) and a short description. Finalists demo on site.
- Problem statements: (1) Recursive Harnessing, (2) Long Horizon Engineering. Use MongoDB as the data and
  memory layer.
- **Atlas Agent Engine** is in public preview (`agentengine` CLI, Python). Its
  **standalone memory service** (`agent-engine-sdk-memory`, a Python SDK, needs a Voyage key) can record
  and recall turns from an outside app. That's the cheap way in: use it for episodic/semantic memory and keep
  gestures and skills in plain collections. The resource guide doesn't list it, so it's a bonus, not a must.
- Partner extras (all optional):
  - ElevenLabs: speech-to-text for the "talk" half. A natural fit, and it has its own prizes.
  - Raindrop: agent monitoring; a Raindrop judge would notice feedback signals sent there.
  - Modelence: hosting. Watch out: it provisions its *own* MongoDB, so to stay sandbox-compliant, point it
    at the sandbox cluster's URI or skip it.
- Claude Code setup: MongoDB Claude plugin (MCP server + agent skills):
  `claude plugin install mongodb@claude-plugins-official` (connection string), or `mongodb-atlas@…`
  (managed MCP, Atlas login).

## Pitch in one line

**"The animation vocabulary isn't built in. You teach it by drawing and talking, and the harness turns what it
learns into stored, versioned skills in MongoDB."**

DrawTalking with an empty library. Every motion is either taught, generated or improved, and the harness
remembers it across sessions.

## What judges have to see (the demo carries the score)

The canvas is how you show it. The harness changing is what you're showing. **The video is 1 minute**, so
that's about 15 s per moment plus a title card. Plan three moments you can see:

1. **Teach**: draw a bird and a tree, label them by voice or text. Draw a loopy arrow from bird to tree and
   say "this means fly over there, bouncing." The harness writes a new skill and a new gesture template. A side
   panel shows the new MongoDB document.
2. **Reuse**: in a new scene, draw a similar loopy arrow from a fish to a rock and say nothing. The harness
   recognizes the gesture and applies the skill. **This proves the harness evolved.**
3. **Improve from signals**: the user drags the result or hits undo, or says "slower". The harness logs the
   signal, revises the skill to v2 and records why (a diff view). After a few sessions it shows a learned user
   policy, e.g. "this user prefers 2–3 s ease-in-out and never wants auto-delete."

Optional 4th moment for Statement 2: "make the fish move the way the cloud did in scene 1." It retrieves over
episodic memory and reuses that exact motion.

## Architecture

```
Browser (SVG canvas + text/voice box + "harness inspector" panel)
   │ strokes, labels, utterances, feedback events
   ▼
Backend (Python FastAPI; Python because of the Agent Engine memory SDK)
   ├─ Gesture recognizer: $P point-cloud recognizer, few-shot, templates in Mongo (no LLM needed)
   ├─ Intent agent (LLM): {strokes, recognized gesture + score, selection, utterance, retrieved memories}
   │      → one of: define_object | define_gesture | apply_skill | edit_skill | set_policy | query_history
   ├─ Skill compiler (LLM): writes or revises a skill as a motion DSL program, validated against a schema
   └─ Harness optimizer (offline or background): reads feedback events, rewrites skills and policies
   ▼
MongoDB Atlas (and Agent Engine where it fits)
   objects, scenes (version tree), gestures, skills (versioned), policies, events, memories (+ Voyage vectors)
```

### Key design decisions

- **Skills are a small motion DSL, not raw `eval`'d JS.** Primitives: `move_to`, `move_along(path)`,
  `follow(target)`, `rotate`, `scale`, `oscillate`, `fade`, `bounce`, `sequence`, `parallel`, `stagger`, with
  parameters bound to gesture features (length, curvature, endpoints, speed). Why: it's safe, the schema can
  validate it, the diffs are readable on stage, and the parameters can be tuned from feedback. Rendering uses
  the Web Animations API or GSAP. You can add an `expr` field later for custom easing.
- **Gesture recognition is classic HCI, not an LLM.** $P / $Q handles few-shot templates in about 100 lines
  and learns from a single example, which fits "learns from the user" well. The LLM handles meaning, and the
  recognizer handles shape. Store the resampled points as gesture templates, plus a Voyage embedding of the
  spoken meaning so a similar description finds the gesture too.
- **Hard metric signals**: kept vs undone vs manually corrected within N seconds, plus edit distance between
  the generated and the final motion parameters, and how often a skill is reused. All are written to an
  `events` collection, and the optimizer reads them.
- **Self-evolution is versioned**: each skill, gesture and policy document has `version`, `parent`,
  `reason` and `evidence_event_ids`. The inspector panel shows the lineage. That's the Statement 1 story
  in the database.

### Collections (draft)

| collection | holds |
|---|---|
| `objects` | id, label, SVG path(s), centroid/bbox, scene_id |
| `scenes` | version tree: id, parent, snapshot of object states + applied skills |
| `gestures` | name, $P templates (points), meaning text, Voyage embedding, skill_id, version |
| `skills` | DSL program, param bindings, version, parent, reason, stats (uses / keeps / undos) |
| `policies` | per-user rules injected into the intent agent prompt (defaults, confirmations, style) |
| `events` | every stroke, utterance, decision and feedback event (ids/types; this is the trajectory) |
| `memories` | distilled episodic/semantic memories + vectors (or Agent Engine memory, if it fits) |

## Atlas Agent Engine: where to use it

Find out in the first hour whether it is self-serve, which SDK it uses, and what the memory API looks like.
If it's easy, put session/trajectory and long-term memory through it and keep `gestures` / `skills` as
plain collections. If it's slow to get going, use plain Atlas + Vector Search + Voyage and say so. Don't
burn the morning on it. Ask the MongoDB folks on site; they'll want it featured.

On "purity": MongoDB has no generative LLM, so you need one model provider. Use Voyage (MongoDB-owned) for
embeddings and keep only the intent and skill-compiler calls on an outside LLM.

## Scope cuts (what not to build)

- No raster or video generation.
- No freehand → clean vector cleanup. Keep raw strokes as SVG paths and group them by "label this".
- Voice is optional (browser Web Speech API if it's free to add). A text box is enough.
- One user, and no auth.

## Judging (read `prep/judging.md`)

**A live 3-min demo + Q&A is what gets scored** (impact 20 / demo 35 / creativity 15 / difficulty 30; equal weights
in round 2). The 1-min video is only a submission requirement. Changes from that: impact framing up front,
a "why trace" in the inspector, a rehearsal project for the learning curve, demo-proofing, and a cut order
that keeps depth.

## Day plan (solo): hacking 10:30–16:45, **submissions due 17:00**

From the official guide (`ideation/guide.md`): doors 9:00, kick-off 10:00, **hacking begins 10:30**,
lunch 13:00, **submissions due 17:00**, round 1 judging 17:00–18:45, finals 19:00–20:00. That's about 6 h of
building, ~1 h less than the earlier plan. No app code before 10:30.

Design lives in `ideation/design.md`, `ideation/motion-dsl.md`, `ideation/storyboard.md`, `ideation/judging.md`.

| time | goal | done when |
|---|---|---|
| 9:00–10:30 | Check in (photo ID), venue Wi-Fi, **add venue + phone-hotspot IPs** in Atlas, `check_setup.py` green, retry Agent Engine (≤ 10 min), Raindrop key if offered, 10 s test recording. **No app code.** | all checks pass |
| 10:30–12:00 | **Slice v0**: FastAPI + SVG canvas captures strokes → lasso + name an entity → "the hare runs to the tree" → LLM picks a hand-written `dash` → Python evaluator → keyframes play. Writes `entities`, `scenes`, `examples`, `events` | text-only shot works end to end |
| 12:00–13:15 | LLM **creates** behaviors (DSL + schema validation), parameter fusion with source chips, clip list + badges (eat lunch at the desk) | race + nap taught |
| 13:15–13:45 | `+ scene` with continuity, scene strip, Play story (minimal) | 3 scenes play |
| 13:45–14:45 | **Refine**: scope chip → behavior v2 + diff, regression replay; propagation as a simple message | shot 3 works |
| 14:45–15:30 | **Fast path** ($P + `$vectorSearch`) with no LLM call; **why trace**; learning-curve chart from `events` | shot 4 works |
| 15:30–16:00 | Rehearse the 3-min script 2× in the rehearsal project (makes the curve data). Mic only if everything else is solid | clean run |
| 16:00–16:45 | **Freeze.** Record the 1-min video, README (incl. **what was built when**), make the repo public, **submit by 16:45** | submitted |

Prize note: **Raindrop RSI Prize ($3k, Recursive Self-Improvement)** fits our core pitch exactly. A cheap way
to qualify: send every action, routing decision and correction to Raindrop (`raindrop-ai` Python SDK) and
point at it in the demo. Do it only after the core works (~20 min).

Stretch goals, in order: front-end animation engine (send the program, not frames) · speed variation along
the stroke · Agent Engine memory (if the CLI downloads) · alternate versions of scenes.

## Prep tonight (setup only, no app code)

- Find the Atlas Sandbox email and accept it. If it hasn't arrived, ask at check-in first thing.
- Keys in a password manager, ready for `.env`: LLM (Anthropic), Voyage (Agent Engine memory and
  embeddings), optional ElevenLabs.
- Install the MongoDB Claude plugin. Install `agentengine` CLI and skim the standalone memory quickstart.
- Write the 1-minute demo script and storyboard: what to draw, what to say, what the inspector shows.
- Optional: list the motion DSL primitives and their parameters on paper (it's design, not code).

## Setup status (2026-10-10 evening)

- [x] Atlas sandbox project created
- [x] MongoDB Atlas plugin (managed MCP + 6 skills) installed at project scope (`.claude/settings.json`)
- [x] `uv` env: pymongo, anthropic, voyageai, fastapi, uvicorn, python-dotenv, agent-engine-sdk-memory
- [x] `.gitignore`, `.env.example`
- [x] Cluster0 is **M10** (fine for Vector Search and Agent Engine hosted memory)
- [x] Home IP on the access list + DB user (read/write). Tomorrow: add the venue IP (or `0.0.0.0/0` for the day)
- [x] `.env` filled; `uv run python scripts/check_setup.py` passes: Mongo (ping, insert, vector index ~50 s,
      `$vectorSearch`), Voyage `voyage-4-lite` (1024-d), OpenAI `gpt-5.4-mini`, ElevenLabs `scribe_v2`.
      Anthropic fails (no credit), so we use OpenAI
- [x] MCP OAuth sign-in done (`plugin:mongodb-atlas:mongodb-atlas`, 42 tools). Visible in **new** sessions only
- [ ] Agent Engine: **CLI download broken on MongoDB's side (2026-10-10 night).** The server cuts the 42 MB
      binary off after 13–31 MB on every try, over HTTP/2 and HTTP/1.1, and doesn't support resuming. Retry
      in the morning, or ask the MongoDB team at the venue. Fallback: plain Vector Search on Cluster0
      (verified working). The expected arm64 v0.1.119 SHA-256 is
      `30f362ad2c1dd1d5072b997a1e8782fe6104cd04a840b78eb09dcccf3b6571c7`
- [ ] Decide the public repo (keep `ideation.md` / `sandbox.*` out of it?)

## Open questions

- Solo, so the 4th moment is a stretch goal only.
- LLM: **OpenAI** (Anthropic account has no credit). `gpt-5.4-mini` for the intent agent (fast), a larger
  GPT-5.x for the skill compiler if quality needs it. Models come from env vars (`OPENAI_MODEL`) behind one
  small `llm.py` so switching costs nothing.
- Is the CoreWeave sandbox useful? Probably not for this one (skills are DSL, rendered in the browser).
  Keep it in mind only if the skill compiler starts producing real code.
