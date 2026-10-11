# Motion DSL (draft)

Goal: a small JSON language that the LLM writes, that a schema can validate, that MongoDB can store, and
whose versions diff readably. Graphics stay simple (2D transforms of whole entities). The DSL exists for
the harness, not for animation research.

## Design choices

1. **JSON, checked against a JSON Schema.** The LLM produces it with OpenAI Structured Outputs (strict
   schema). Invalid output is rejected before it reaches the DB or the screen.
2. **One evaluator, in Python.** The backend evaluates a clip into **sampled keyframes** (30 fps per actor:
   x, y, rotation, scaleX, scaleY, opacity) plus timed events (glyphs). The browser only plays keyframes
   (Web Animations API). Benefits:
   - regression tests run server-side with no browser: replay a behavior's past examples and compare
     trajectories numerically
   - no generated code is ever `eval`'d in the browser
   - one implementation instead of two
3. **Base motion + modifiers.** Most motions are "go along a path" plus a texture (hop, bob, breathe). Keeping
   them separate makes refinements small and readable ("bob 4 → 2 px").
4. **Parameters are named slots** with defaults, ranges and cue sources. Values come from parameter fusion
   (text > trait × stroke speed, per-user calibration), and each value records where it came from.

## Structure

```jsonc
// behaviors collection (one doc per version)
{
  "behavior_id": "plod", "version": 2, "parent_version": 1,
  "type_path": ["travel", "walk", "plod"],          // taxonomy
  "description": "slow, steady walk with a slight bob",
  "params": {
    "speed":  { "unit": "px/s", "default": 60, "range": [10, 200], "cues": ["text", "trait", "stroke_speed"] },
    "bob":    { "unit": "px",   "default": 2,  "range": [0, 12] }
  },
  "program": { ... },                              // see below
  "reason": "user: 'the tortoise should always plod steadily'",
  "evidence": ["evt_…", "ex_…"],
  "tests": ["ex_…", "ex_…"],                       // accepted examples to replay
  "stats": { "uses": 7, "accepted": 6, "corrected": 1 }
}
```

### Program nodes

Composition:

| node | fields | meaning |
|---|---|---|
| `seq` | `steps: [node]` | one after another |
| `par` | `steps: [node]` | at the same time (duration = longest) |
| `layer` | `base: node, mods: [modifier]` | modifiers act over the base's duration |
| `wait` | `duration` | pause |

Base motions (a path or an in-place motion):

| node | fields | notes |
|---|---|---|
| `move_along` | `path: "stroke" \| "default" \| "arc"`, `speed` or `duration`, `easing` | `default` = straight from actor center to target bbox boundary; `arc` = default with height |
| `stay` | `duration` | in place (base for nap / breathe) |
| `turn_to` | `angle`, `duration`, `easing` | e.g. lie down = 80° |
| `scale_to` | `sx`, `sy`, `duration`, `easing` | |
| `fade_to` | `opacity`, `duration` | |

Modifiers (layered onto a base):

| modifier | fields | effect |
|---|---|---|
| `hop` | `height`, `every_px`, `squash` | vertical \|sin\| arcs along travel, squash on landing |
| `bob` | `amplitude`, `period` | small vertical sine |
| `breathe` | `amount`, `period` | scale oscillation |
| `face_motion` | — | flip scaleX to face the direction of travel |
| `emit` | `glyph`, `every`, `rise`, `fade` | spawn floating text ("Z", "!") |

Values can be literals or parameter references: `{"$p": "speed"}`. Light arithmetic is allowed:
`{"$mul": [{"$p":"speed"}, 1.5]}`.

### The video's behaviors

```jsonc
// dash (hare)
{ "layer": { "base": { "move_along": { "path": "default", "speed": {"$p":"speed"}, "easing": "easeOut" } },
             "mods": [ { "hop": { "height": {"$p":"hop"}, "every_px": 60, "squash": 0.2 } }, { "face_motion": {} } ] } }

// plod (tortoise)
{ "layer": { "base": { "move_along": { "path": "default", "speed": {"$p":"speed"}, "easing": "linear" } },
             "mods": [ { "bob": { "amplitude": {"$p":"bob"}, "period": 0.8 } }, { "face_motion": {} } ] } }

// nap
{ "seq": { "steps": [
    { "turn_to": { "angle": 80, "duration": 0.6, "easing": "easeInOut" } },
    { "layer": { "base": { "stay": { "duration": {"$p":"length"} } },
                 "mods": [ { "breathe": { "amount": 0.04, "period": 1.6 } },
                           { "emit": { "glyph": "Z", "every": 0.8, "rise": 40, "fade": 1.2 } } ] } } ] } }

// wake_dash = seq(squash pop, dash), with a delay param so it can start late
{ "seq": { "steps": [ { "wait": { "duration": {"$p":"delay"} } },
                      { "turn_to": { "angle": 0, "duration": 0.2 } },
                      { "$ref": "dash@latest" } ] } }

// race_to (composite over actors) is a clip-level `par` of per-actor behaviors; the trait picks each one.
```

`$ref` lets behaviors build on other behaviors (and is how the taxonomy reuses things). A ref pins a version
or tracks `latest`.

## Clip = behavior + bindings (stored in the scene)

```jsonc
{ "clip_id": "c3", "actor": "ent_tortoise", "target": "ent_flag",
  "behavior": "plod", "version": 2,
  "path": { "kind": "stroke", "points": [[x,y,t], ...] },        // or default / arc
  "params": { "speed": 55, "bob": 2 },
  "param_sources": { "speed": "trait:slow × stroke_speed", "bob": "behavior default" },
  "start": 0.0, "duration": 6.3, "after": null, "with": "c2",
  "example_id": "ex_…" }
```

## Guardrails (validation after the schema check)

- every numeric value within its declared range (clamped, and the clamp is logged as an event)
- total clip duration ≤ 20 s; nesting depth ≤ 4; glyph rate limited
- learned rule example: "keep in frame". The evaluator checks the sampled bounding boxes against the
  canvas and nudges or warns. Rules live in `harness_config.rules` and are switched on by evidence

## Regression check (for v1 → v2)

For each test example: evaluate it with the old and new versions (same bindings), then compare sampled
trajectories. Pass if the max position deviation and duration change stay within tolerance, or if the change
is *intended* (it matches the refinement, e.g. a slower speed). Report "scene 1 upgraded ✓ / 1 example
changed a lot → review".

## What the LLM sees

- the JSON Schema (as the Structured Outputs schema)
- the behavior catalog as compact one-liners plus the full program of the 2–3 most relevant behaviors
- top-k retrieved examples (text, stroke features, chosen behavior, params, outcome)
- entity traits for the objects in view, and harness rules

It returns one of: `apply {behavior, version, params}` · `refine {behavior, patch, scope}` ·
`create {behavior doc}` · `ask {question, options}`.

## Decided (2026-10-10)

1. **v1: Python evaluator → keyframes**; the browser only plays them. Stretch goal: a JS engine in the browser
   that receives the program + parameters instead of frames (less data sent, lower latency). This works
   because the DSL is already the interface between the two. The Python evaluator stays as the reference
   for regression tests.
2. **v1: stroke timing sets overall speed only.** Speed variation along the path comes later.
   Principle: **finish the whole pipeline end to end first, then improve it step by step.**
