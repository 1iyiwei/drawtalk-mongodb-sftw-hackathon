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

## Day plan (solo, ≈9:30–17:00 build)

| time | goal |
|---|---|
| 9:30–10:15 | Sandbox cluster + DB user, MCP connected, public repo created, FastAPI + static SVG canvas page |
| 10:15–11:45 | Stroke capture, group + label objects, motion DSL runtime (6 primitives), hand-written skill plays |
| 11:45–13:15 | Intent agent + skill compiler (LLM → DSL JSON, validated), "teach" works end to end |
| 13:15–14:15 | $P recognizer + gesture templates in Mongo, "reuse" works |
| 14:15–15:45 | Feedback events → optimizer → skill v2 + policy; inspector panel with version lineage |
| 15:45–16:30 | Agent Engine memory or Vector Search for "like the cloud did", **only if solid** |
| 16:30– | Freeze. Record the 1-min video (2–3 takes), README with architecture + collections, submit early |

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
- [ ] Cluster created (note its tier: Agent Engine hosted memory needs **Flex or higher**, M0 won't do)
- [ ] Home IP on the access list + DB user. Tomorrow: add the venue IP (or `0.0.0.0/0` for the day)
- [ ] `.env` filled, connection smoke test (ping + insert + `$vectorSearch` on a toy collection)
- [ ] MCP OAuth sign-in (new Claude Code session in this folder)
- [ ] Agent Engine: sign in at agentengine.mongodb.com, download CLI, `agentengine auth login`.
      Drop it if it isn't working by tonight
- [ ] Decide the public repo (keep `ideation.md` / `sandbox.*` out of it?)

## Open questions

- Solo, so the 4th moment is a stretch goal only.
- LLM: Claude for the intent agent and skill compiler (structured JSON output).
- Is the CoreWeave sandbox useful? Probably not for this one (skills are DSL, rendered in the browser).
  Keep it in mind only if the skill compiler starts producing real code.
