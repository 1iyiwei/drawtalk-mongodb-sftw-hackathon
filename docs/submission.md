# Submission

## Team Name

DrawTalk Harness

## Project Description

**The problem:** agents interpret ambiguous human input (a sketch, a phrase, a gesture) with an expensive LLM call every time, and they never become *yours*. **DrawTalk Harness compiles a user's personal vocabulary into versioned, tested tools.** Each correction makes it faster, cheaper and more predictable, and it can't silently break what you already approved. Animation is our testbed because you can *see* it learning. The same pattern applies to design tools, robot and drone commands, voice assistants, and enterprise workflows where people keep teaching the same shorthand.

**What it does:** you sketch 2D characters, then animate them by typing ("the rabbit and the turtle race to the rock"), drawing a path, or drawing a gesture. There is no preset motion library: an LLM composes each new verb (dash, plod, nap, spin) from a small motion DSL, and the harness stores it as a versioned, tested tool in MongoDB.

**From today's sessions** (77 commands across our demo stories): an LLM-routed command takes a median 3.6 s and ~3,500 tokens; once a gesture or habit is learned, the fast path takes a median 0.14 s with no LLM call (~25× faster, zero tokens), and none of its guesses were undone. 42 behaviors were learned, 8 of them refined to v2+.

**Recursive Harnessing**, how the harness improves itself:
- it writes new tools (behaviors) and checks them before use (a "no visible motion" self-check asks the LLM for a fix);
- refinements ("the turtle should always plod faster") become v2 proposals with a readable diff, a regression replay over every clip that uses the behavior, and a scope guess (everywhere vs. only this time) that you confirm;
- it compiles your vocabulary into fast paths: taught gestures and learned habits run without the LLM;
- it retunes its own routing thresholds from hard signals (accepted / undone clips, missed gestures), each change a new versioned policy document with its reason and evidence, also tracked in Raindrop.

**Long Horizon**: stories stay coherent while you edit them. Scenes derive their start from the previous scene and re-simulate when earlier scenes change, characters keep learned traits and habits, every clip is pinned to a behavior version, and a learning curve tracks how often the LLM is still needed.

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
Raindrop tracks the harness's self-improvement loop: every command is an event (route: LLM vs. fast path, latency, tokens, created vs. reused behaviors), and the hard signals the harness learns from are attached as Raindrop signals: accepted, clip_undone, refinement_applied (scope, version, regression pass/total, diff) and routing_policy_changed (new threshold + reason). -->

## Describe your use of MongoDB products to build the submitted project.

MongoDB Atlas (hackathon sandbox, M10) is the harness's data and memory layer:
- **Versioned self-modification as documents**: `behaviors` (one document per version, with program, params, parent_version, reason, diff, evidence, regression results, stats), `harness_config` (versions of the routing policy), and `proposals` (refinements awaiting a scope decision). Nothing is overwritten.
- **Long-horizon story state**: `scenes` (own additions/removals, derived start state, a timeline of clips pinned to behavior versions), `entities` (vector strokes, learned traits), `examples` (every authored instance with its outcome), and `events` (the log behind the learning curve and the "why" trace).
- **Atlas Vector Search** over `examples.text_vec` (Voyage AI `voyage-4-lite` embeddings, filtered by project and outcome): similar past commands are retrieved and given to the LLM so it reuses behaviors instead of creating duplicates.
- PyMongo's async driver from FastAPI, with parallel reads and bulk writes to keep fast-path commands around 100–300 ms.
- During development: the MongoDB Atlas Claude Code plugin (hosted MCP server + agent skills) to inspect collections and manage the IP access list.

## Provide feedback from your experience using MongoDB products.

- **Document model**: a great fit for a self-modifying harness. Behaviors, routing policies and proposals are nested JSON that the harness *versions* (one document per version, never overwritten), and each scene's timeline of clips fits in a single document. No migrations were needed while the schema evolved all day.
- **Atlas Vector Search**: having vectors and filter fields (`project_id`, `outcome`) on the same `examples` documents meant no second datastore and no sync code. The index took ~50 s to become queryable, and new vectors appear a few seconds after insert; a clearer "ready" signal in the driver would help.
- **Voyage AI**: excellent embedding quality for short commands ("bounces over" ↔ "hops" at 0.97), but the free tier's rate limit (`RateLimitError`) hit us quickly and silently degraded retrieval; we cut to one embedding call per command. A clearer free-tier quota (or a hackathon key) would help.
- **Atlas sandbox + Claude Code plugin (hosted MCP + agent skills)**: setup was smooth, and inspecting collections and the IP access list from the coding agent was handy. Adding an access-list entry asks for a second confirmation inside the MCP server, which wasn't obvious at first. The venue Wi-Fi used two outgoing IPs, which took a moment to diagnose.
- **Atlas Agent Engine**: we wanted its memory service, but the CLI download kept failing partway through (server-side, no resume support), so we used plain Atlas + Vector Search instead and modeled our memory layers on its four types.

## Provide feedback from your experience using partner products

- **Raindrop**: the Python SDK was quick to add with `track_ai` for each command and `track_signal` for feedback. One gotcha: properties must be strings/numbers/booleans (lists and None need flattening), and debug logs are hidden under uvicorn unless the logger level is set explicitly.
- **ElevenLabs**: speech-to-text (`scribe_v2`) worked from home, but at the venue the free tier was blocked with "unusual activity detected" (shared IP), so we used text input.
