# Submission

## Team Name

DrawTalk Harness

## Project Description

An animation tool that learns your language. You sketch 2D characters, then animate them by typing ("the
rabbit and the turtle race to the rock"), drawing a path, or drawing a gesture. There is no preset motion
library: an LLM composes each new verb (dash, plod, nap, spin) from a small motion DSL, and the harness stores
it as a versioned, tested tool in MongoDB.

The harness improves itself (Recursive Harnessing):
- it writes new tools (behaviors) and checks them before use (a "no visible motion" self-check asks the LLM for a fix);
- refinements ("the turtle should always plod faster") become v2 proposals with a readable diff, a regression
  replay over every clip that uses the behavior, and a scope guess (everywhere vs. only this time) that you confirm;
- it compiles your vocabulary into fast paths: taught gestures and learned habits run in ~100 ms with no LLM call;
- it retunes its own routing thresholds from hard signals (accepted / undone clips, missed gestures), each change a
  new versioned policy document with its reason and evidence.

It stays coherent over long stories (Long Horizon): scenes derive their start from the previous scene and
re-simulate when earlier scenes are edited, characters keep learned traits and habits, every clip is pinned to a
behavior version, and a learning curve tracks how often the LLM is still needed.

Built today. Inspired by the author's earlier DrawTalking research (a preset motion library); no code from it is reused.

## Public GitHub Repository

https://github.com/1iyiwei/drawtalk-mongodb-sftw-hackathon

## Demo Video (youtube)

https://youtu.be/-H8eB0-2pQw

## Did you use any partner technologies in your project?*This field is required.(Select all)

- [ ] AWS
- [ ] ElevenLabs (set up and tested, but not used in the final app: free-tier access was blocked from the venue network and the room was too noisy for voice)
- [x] Raindrop
- [ ] Mondelance
- [ ] Cursor

## Are you submitting for the Raindrop RSI Prize?

Yes

<!-- Optional pitch if the form has room:
Raindrop tracks the harness's self-improvement loop: every command is an event (route: LLM vs. fast path,
latency, tokens, created vs. reused behaviors), and the hard signals the harness learns from are attached as
Raindrop signals: accepted, clip_undone, refinement_applied (scope, version, regression pass/total, diff) and
routing_policy_changed (new threshold + reason). -->

## Describe your use of MongoDB products to build the submitted project.

MongoDB Atlas (hackathon sandbox, M10) is the harness's data and memory layer:
- **Versioned self-modification as documents**: `behaviors` (one document per version, with program, params,
  parent_version, reason, diff, evidence, regression results, stats), `harness_config` (versions of the routing
  policy), and `proposals` (refinements awaiting a scope decision). Nothing is overwritten.
- **Long-horizon story state**: `scenes` (own additions/removals, derived start state, a timeline of clips pinned to
  behavior versions), `entities` (vector strokes, learned traits), `examples` (every authored instance with its
  outcome), and `events` (the log behind the learning curve and the "why" trace).
- **Atlas Vector Search** over `examples.text_vec` (Voyage AI `voyage-4-lite` embeddings, filtered by project and
  outcome): similar past commands are retrieved and given to the LLM so it reuses behaviors instead of creating
  duplicates.
- PyMongo's async driver from FastAPI, with parallel reads and bulk writes to keep fast-path commands around 100–300 ms.
- During development: the MongoDB Atlas Claude Code plugin (hosted MCP server + agent skills) to inspect collections
  and manage the IP access list.

## Provide feedback from your experience using partner products

- **MongoDB Atlas / MCP**: the sandbox and the Claude Code plugin worked smoothly. The vector index took ~50 s to
  become queryable, so we poll `queryable` first. The venue Wi-Fi used two outgoing IPs, which took a moment to
  figure out on the access list. The Atlas Agent Engine CLI download kept failing partway through (server-side), so
  we used plain Atlas + Vector Search instead.
- **Voyage AI**: great embedding quality for short commands, but the free tier's rate limit (`RateLimitError`) hit us
  quickly; we cut to one embedding call per command.
- **Raindrop**: the Python SDK was quick to add with `track_ai` for each command and `track_signal` for feedback. One gotcha: properties
  must be strings/numbers/booleans (lists and None need flattening), and debug logs are hidden under uvicorn unless
  the logger level is set explicitly.
- **ElevenLabs**: speech-to-text (`scribe_v2`) worked from home, but at the venue the free tier was blocked with
  "unusual activity detected" (shared IP), so we used text input.
