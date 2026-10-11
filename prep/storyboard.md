# Storyboard: 1-minute demo video

Story: **The Tortoise and the Hare**. Submission needs a 1-minute video that shows "the code & functionality".
The user's spoken commands are the narration; captions repeat them. A small caption marks every cut or
speed-up, so nothing looks faked.

Layout on screen throughout: **canvas** (center), **scene strip** (bottom), **clip list** (right of canvas),
**inspector** (far right: live MongoDB documents, diffs, metrics), **mic / text box** (below canvas).

## Shot list

| # | Time | What the user does | What the screen shows | Point for judges |
|---|---|---|---|---|
| 0 | 0:00–0:04 | — | Title: *"An animation tool that learns your language."* Empty canvas. Inspector: `behaviors: 0` | Starts with no preset library |
| 1 | 0:04–0:16 | Scene 1 "The race". Draws a hare, a tortoise, a tree (sped up 4×, captioned). Says **"the hare and the tortoise race to the tree."** | Text-only: straight default paths, badges `1` and `1′` (parallel). Hare hops fast, tortoise crawls. Chips: `fast: hare`, `slow: tortoise`, `path: default`. Inspector: new `behaviors.race_to v1` (via LLM), `entities.hare.traits: quick` | Text-only input; meaning-driven parameters; new tool written to the DB |
| 2 | 0:16–0:26 | `+ scene` ("The nap"). Draws a small zig-zag over the hare and says **"the hare takes a nap."** | Chip `start: end of scene 1` (hare already ahead). Hare settles and breathes, "Zzz" floats. Inspector: `behaviors.nap v1` + the stroke template saved | Scene continuity; stroke + text teaches a new behavior |
| 3 | 0:26–0:38 | Says **"the tortoise should always plod steadily."** | Scope chip `all tortoise moves? ✓` → user taps ✓. Inspector diff `crawl v1 → v2` (easing, bob, `reason`, `evidence`). Toast: `scene 1 uses crawl v1 → upgraded, regression check passed ✓` | Self-modification that's versioned, explained and tested; propagation to earlier scenes |
| 4 | 0:38–0:50 | Caption: *"…after a few more scenes"*. Scene 3 "The finish". Draws a curved stroke from the tortoise past the sleeping hare to a flag. **No words.** Then says **"the hare wakes up and dashes to the flag."** | Chip `≈ plod (learned shorthand) · ⚡ no LLM · 40 ms`. Tortoise follows the curve. The hare's dash starts late; the tortoise wins | Stroke-only shorthand; the harness compiled a pair into a fast path |
| 5 | 0:50–1:00 | Clicks **Play story** | Scenes 1–3 play in a corner. (Optional ~2 s flash of the behavior-compiler code / Atlas collections.) Inspector shows the **learning curve** (corrections/action ↓, LLM calls/action ↓, fast-path share ↑) and the collections: `entities · scenes · behaviors (versions) · examples · events · harness_config`. End card: *MongoDB Atlas · Vector Search · Voyage · repo URL* | Long-horizon memory and hard metrics, all in MongoDB |

Backups: if the mic is flaky on the day, type the same sentences (the text box goes through the same path).
Record 2–3 full takes and cut the best. Keep raw takes as proof.

## What the video needs (scope for the build)

### Behaviors to support (and so the motion DSL)

| Behavior | Look | Likely primitives |
|---|---|---|
| dash / hop-run | hops along the path, squash on landing | `move_along(path)`, `hop(height, count)`, `squash` |
| plod / crawl | slow, steady, slight bob | `move_along`, `bob(amplitude)`, linear easing |
| nap | lies down (rotate/scale), breathes, "Zzz" rises | `rotate`, `breathe(scale osc)`, `emit_glyph("Z")` |
| wake + dash | pop up, then dash | `squash` pop, `sequence(...)`, `delay` |
| race_to (composite) | runs per-actor behaviors in parallel | `parallel(...)` with per-actor params |

All of these are transforms on whole entities. The DSL comes next, from this table.

### Harness features the video depends on

Must work live:
- text-only resolution (references + default straight path to the bounding-box boundary)
- stroke + text teaching → new behavior + example in Mongo
- parameter fusion with source chips (text > object trait ⨯ stroke speed)
- scene continuity (start = previous end state)
- refinement with a scope chip → behavior v2 with a diff, plus regression replay over its examples
- stroke-only recognition → fast path with no LLM call ($P + example lookup)
- inspector: live documents, version diff, learning-curve chart (from `events`)

Can be simple or partly scripted:
- learning-curve data comes from real events recorded while building and rehearsing. It's real, just
  made earlier in the day
- "Zzz" glyph, the flag, other polish

### UI pieces

canvas with vector strokes · label/lasso to name an entity · scene strip with `+ scene` · clip list with
badges · chips (sources, scope, fast path) · inspector (doc viewer + diff + chart) · mic button (ElevenLabs
Scribe) + text box · Play / Play story.

## Decided (2026-10-10)

1. Everything is drawn live by the user, in **pure 2D** (no perspective). Speed up only to fit the minute,
   with a caption.
2. Everything is recorded live: real voice commands, real app, no separate voice-over.
3. The repo link goes in the submission form. Add a ~2 s code/collections flash in shot 5 only if it fits.
