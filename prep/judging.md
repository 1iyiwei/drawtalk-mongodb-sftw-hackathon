# Judging: how the plan scores, and what to change

**The scored event is a live 3-minute demo plus 1–2 min of Q&A** (round 1: in rooms; round 2: top 6 on stage).
The 1-minute video is a submission requirement. The **live demo** decides the score.

| Criterion | Round 1 weight | Current plan | Risk | Fix |
|---|---|---|---|---|
| Impact | 20% | weakest: "animation tool" sounds niche to infra judges | judges file it as a toy | frame it as a **general harness pattern**, with animation as the vivid testbed (see below) |
| Technical demo | 35% | strong visuals; the agent's decisions are visible on screen | live failures: Wi-Fi, LLM latency, noisy-room speech, mouse sketching under time pressure | demo-proofing (below); rehearse the 3-min script 3× |
| Creativity | 15% | strong: sketch + talk → self-compiling tool library is unusual at an infra hackathon | low | keep the hare/tortoise story; it's memorable |
| Implementation difficulty | 30% | good depth: $P recognizer, DSL + evaluator, trajectory regression tests, versioned self-modification, vector retrieval, fast/slow routing, parameter fusion | depth is invisible if the UI only shows cartoons; solo scope could end up shallow everywhere | **make depth visible** with a "why" trace; build the core pieces deep and cut breadth first |

In round 2, weights are equal (25% each), so **impact gains 5 points and difficulty loses 5**. The framing
matters more on stage.

## Rule: show only what was built today

The guide disqualifies demos that don't clearly separate work done during the event. Say it in one line at the
start: *"Everything you'll see was built today; it's inspired by my earlier DrawTalking research, but no code
is reused."* The README has a "what was built when" table, and the git history backs it up. Don't show
DrawTalking footage.

Avoid the anti-project patterns: the inspector and learning curve *support* the demo. A dashboard must not be
the main feature, so lead with the canvas.

## Impact framing (say it in the first 20 seconds)

> "Agents interpret ambiguous human input (a sketch, a phrase, a gesture) with an expensive LLM call every
> time, and they never become *yours*. We built a harness that **compiles a user's personal vocabulary into
> versioned, tested tools**. Each correction makes it faster, cheaper and more predictable, and it can't
> silently break what you already approved. Animation is our testbed because you can *see* it learning."

The same pattern applies to design tools, robot or drone commands, voice assistants, and enterprise
workflows where users keep teaching the same shorthand. Back it with numbers from the demo: LLM calls per
action ↓, latency ↓, acceptance ↑.

## Live 3-minute demo script (primary; the video is cut from it)

| Time | Beat |
|---|---|
| 0:00–0:20 | Impact framing (above), with the app open on an empty scene |
| 0:20–0:50 | Draw a quick hare + tortoise + tree (mouse; simple shapes). Type or say "the hare and the tortoise race to the tree" → source chips `fast: hare`, `slow: tortoise`; inspector shows the new `behaviors` doc |
| 0:50–1:20 | `+ scene`: zig-zag + "the hare takes a nap" → teaches `nap`. Point at the continuity chip |
| 1:20–1:55 | "the tortoise should always plod steadily" → scope chip → v2 diff + regression replay + "scene 1 upgraded" |
| 1:55–2:25 | Stroke-only curve → `⚡ no LLM, 40 ms` + the **why trace** (top examples, $P score, vector score, routing decision) |
| 2:25–2:50 | Open the **rehearsal project** (built earlier in the day): learning curve over ~50 actions, behavior lineage |
| 2:50–3:00 | Play story; one closing line: "every decision is a MongoDB document: versioned, retrievable, testable" |

## Plan changes

1. **Why trace in the inspector** (new, high value for difficulty): for each action, show the input → retrieved
   examples with scores → fast or slow path → which LLM action → validation/clamps → document written.
   It's cheap to build from the `events` log, and it turns invisible engineering into something on screen.
2. **Rehearsal project**: do the build-time testing and rehearsals in a named project, so the learning curve
   and lineage show real history. Use a **fresh project** for the live part.
3. **Demo-proofing**
   - the text box is always there; voice is a bonus. In a noisy room, type
   - phone hotspot as a network backup; add its IP to Atlas ahead of time (or `0.0.0.0/0` for the day)
   - LLM call timeout (~8 s) with a visible "thinking…" state; prefer `gpt-5.4-mini`
   - "reset demo" button that clears the live project only
   - the 1-min video ready on the laptop as a last-resort backup
   - keep sketches minimal: a few strokes per character with the mouse
4. **Cut order if behind** (keep depth, drop breadth): ElevenLabs mic → automatic propagation to earlier
   scenes (keep the version pins and the diff) → scene strip polish → speed variation along the stroke.
   **Never cut**: versioned behaviors + regression replay, the fast path, the why trace.

## Q&A prep

- *Why not just put the whole history in the prompt?* Cost and latency grow with history, it isn't
  deterministic, and you can't regression-test it. We turn stable patterns into tested tools and keep the
  LLM for new cases.
- *How do you stop self-modification from going wrong?* Schema validation, range clamps, versioned documents
  with reason + evidence, regression replay against approved examples, and visible, reversible defaults.
- *Why MongoDB?* Behaviors, scenes and examples are naturally nested, versioned JSON. Vector Search runs over
  the same documents (no second database). The events log is the source of truth for metrics.
- *What's the long horizon here?* Stories built over many scenes and sessions: character traits, version
  pins, consolidation, and learning curves from hard signals. All of it lives outside the context window.
- *Agent Engine?* We tried it; the CLI download failed on the server side the night before. The memory
  layers follow its four types (episodic, semantic, procedural, taxonomic), so moving onto it is mechanical.
- *How hard is this to recreate?* The DSL + evaluator, the $P recognizer, trajectory-based regression
  tests, and the routing/versioning loop are each real engineering. The LLM is one component among them.
