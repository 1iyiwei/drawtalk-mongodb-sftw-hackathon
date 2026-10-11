# Design

> Written before the event (Oct 10). The section below records how the design changed while building
> (Oct 11); the rest is the original design.

## As built (Oct 11): changes from the original design

- **Three stroke kinds, as separate modes**: *Ink* (drawing characters), *Path* (where to go) and
  *Gesture* (a drawn word for how to move, attached to the nearest character). A path's shape is only
  the trajectory. A gesture's shape is its meaning. This keeps "where" and "how" independent: a straight
  path plus a hop gesture means hopping along a straight line.
- **Text-free routing without the LLM**: a gesture is matched by shape ($P) against taught gestures; a
  path alone uses the character's learned habit. An unknown gesture with no text asks to be taught
  instead of guessing.
- **Routing policy is versioned and self-tuned** (`harness_config`): accepted fast-path guesses relax the
  threshold, and undone ones tighten it.
- **Scene starts are derived, not copied**: each scene stores its own additions/removals. When an earlier
  scene changes, later scenes re-simulate their clips with the pinned behavior versions.
- **Refinement** scales each existing clip's parameters by the change in the default (so "faster" speeds
  every clip up while keeping their differences). Regression replay checks that each clip still ends
  where the story needs it.
- **Timing**: one per-command field (`together` / `in_order`), plus a per-clip toggle in the UI.
- **Voice dropped** for the event (noisy venue); text input only.

## Guiding principle: adaptive defaults that stay visible and controllable

Every adaptation follows the same loop: **guess → show → confirm/override → learn**.

- The system always acts on its *current best default*: a scope, a behavior, a parameter value, a routing
  decision, or whether to update an earlier scene.
- The user can always see what it decided and why (**transparency**): a small chip such as
  "fast: from stroke speed", "scope: all of Pip's flights?", "matched from 6 earlier examples".
- One tap confirms or overrides it (**controllability**).
- The response becomes evidence that shapes the next default. Defaults start cautious (ask often) and
  get bolder as evidence builds up (ask less, act more).

This applies on both sides:
- **front end**: less friction over time (fewer prompts, shorthand strokes, smarter previews)
- **back end**: the database updates differently by case (instance override, behavior version, context
  specialization, policy change)

## Core unit: a stroke + text pair → a behavior

A stroke alone is ambiguous: an arrow from bird to cage could mean fly into, chase, look at, or throw. A text
alone has no spatial detail. Together they pick out one motion (as in DrawTalking):

- **text** → *which* behavior (type, style): "fly in, bouncing"
- **stroke** → *where / how* (parameters): path shape, source and target objects, and maybe **timing from
  drawing speed** (a fast stroke gives a fast motion)
- **objects** → *to what*: the labels of what the stroke touches (bird, cage)

A **behavior** is a parameterized motion program (motion DSL, designed later) plus a binding that says how
stroke, text and object features fill its parameters. An **example** is one authored instance: stroke,
text, objects, resolved behavior@version, parameters, and how it turned out. Each example is stored, embedded
and kept forever. Examples are the raw material for everything below.

Resolution pipeline for a new stroke (+ optional text):

1. Find candidates: nearest examples by text embedding (Voyage, `$vectorSearch`), stroke shape ($P
   recognizer) and object labels.
2. **Fast path**: one candidate wins clearly → apply its behavior directly. No LLM call.
3. **Slow path**: ambiguous or new → the LLM gets the stroke features, text, objects and top-k examples as
   few-shot. It then picks an existing behavior, refines one, or writes a new one.
4. If it's still ambiguous → show 2–3 ghost previews and the user picks. The pick is a labeled signal.
5. The outcome (accepted / adjusted / undone / re-explained) is written back to the example.

## Input modes: stroke, text, or both

Any of the three can determine a behavior. The missing part is filled by a default and shown to the user:

| Input | What's missing | Default |
|---|---|---|
| stroke + text | nothing | (fully specified) |
| text only ("the rabbit runs to the tree") | path, and which objects if ambiguous | resolve references (one rabbit, one tree → obvious; several → the most recent or selected one, highlighted as a guess). Path = straight line from the actor's center to the target's bounding-box boundary (stop on contact) |
| stroke only | behavior type | stroke shape + objects touched → learned abbreviation, or ask |

Defaults are learnable too. If the user keeps redrawing "jumps to" as an arc, the text-only default path for
"jump" becomes an arc.

## Scenes and the story structure

**Entities vs. instances.**
- **Entities** (`entities` collection) are project-level: geometry as vector strokes in local coordinates
  (raw points + smoothed SVG `d`), local bounding box and pivot, name, traits. Redrawing the hare updates
  every scene.
- A scene holds **instances**: an entity id + transform (x, y, rotation, scale) + visibility.
- Unlabeled ink stays a scene-local **prop** until it's named.

**Scene document** (`scenes`, one doc per scene; size is bounded, so the timeline is embedded):

```
{ _id, project_id, order, title,
  start_state: { <entity_id>: {x, y, rot, scale, visible} },   // default: end state of the previous scene
  timeline: [ { clip_id, actor, target?, behavior_id, behavior_version, params, param_sources,
                start, duration, example_id } ],
  props: [ ...scene-local vector ink... ] }
```

- **Continuity default**: a new scene starts from the previous scene's computed end state (the hare that
  reached the tree starts at the tree). This is shown in the UI and can be overridden by dragging.
- **Timeline default**: each new command appends sequentially. "while" / "meanwhile" / "at the same time"
  makes it parallel with the previous clip. The text cue decides, and the user can drag clips on a mini
  timeline.
- **Version pinning**: each clip stores `behavior_version` (used for propagation, see below).
- **Playback**: the front end compiles a scene timeline into Web Animations / GSAP timeline objects.
  "Play story" chains scenes in order. Animations transform whole entities (translate / rotate / scale,
  plus squash-and-stretch through scale). Deforming body parts is out of scope.
- **UI**: a storyboard strip of scene thumbnails along the bottom. "+ scene" continues from the current
  end state.
- **No timeline editor** (decided). Timing is set by language and defaults, not by dragging bars. To stay
  transparent, each scene shows:
  - motion paths drawn on the canvas with **numbered badges** (1, 2, 2' for parallel), so order is
    readable at a glance
  - a compact **clip list** beside the canvas: "1 · hare dashes to tree · fast: hare", "2 · tortoise
    plods (with 1)". Click to select or delete, hover to see where each parameter came from
  - play / pause / restart and a progress bar (playback only, no editing)
  - edits by direct manipulation (drag characters, redraw or delete a path) or by language ("make 2
    happen at the same time as 1", "after the hare naps")
- **Scope rule**: the hackathon is about agent + database, not graphics. Keep the motion simple and put
  the effort into the harness, memory and the inspector.
- **Branching**: scenes are a linear list for now. Alternate versions of a scene (a variant pointing to a
  parent) are a stretch goal (decided).

## Recursive harnessing (Statement 1): what the harness changes about itself

The harness stores its own configuration as versioned documents (`harness_config`, `behaviors`,
`policies`). Each change records `parent`, `reason` and `evidence` (the example/event ids that triggered it).

| What adapts | Signal that triggers it | What changes |
|---|---|---|
| **Tool library** | new stroke+text pair the user accepts | a new behavior is saved **and shows up as a tool** in the LLM's tool list next time |
| **Routing (fast vs slow path)** | a behavior is accepted N times without correction | the pair is "compiled": matched directly with no LLM call. Correction rate goes up → back to the slow path |
| **Abbreviation** | a stroke shape + object types consistently mean one behavior | the stroke alone is enough (text becomes optional), confirmed with a one-tap prompt |
| **When to ask** | how often the user corrects guesses | per-user confidence threshold: act, preview, or ask |
| **Context policy** | which retrieved examples actually helped (the chosen behavior was among them) | retrieval k, filters, and which memory types go into the prompt |
| **Guardrails / rules** | repeated manual fixes ("drags objects back on screen", "always slows things down") | learned rules: keep objects in frame, default easing/duration, never delete without asking |

Story for judges: **the harness compiles itself.** It starts as an LLM interpreting everything and
gradually turns the user's vocabulary into deterministic, versioned, tested tools. You can measure this:
LLM calls per action and latency go down while acceptance goes up.

### Behaviors carry their own tests

Every accepted example becomes a **regression test** for its behavior. When the optimizer or the user
revises a behavior (v1 → v2), the new version is replayed against its past accepted examples first.
Examples that would change visibly are flagged for review. This is the guardrail on self-modification:
the harness can't silently break what the user already approved.

## Long horizon (Statement 2): staying coherent across a long project

The target use case is an animated story built scene by scene over hours or days, not a single sketch.

**Memory in four layers** (named after the Agent Engine types, implemented as collections):

| Type | Content | Collection |
|---|---|---|
| episodic | every stroke, utterance, decision and outcome | `events`, `examples` |
| semantic | facts about the story: characters, names, traits ("Pip the bird is cheerful, always bounces") | `entities` |
| procedural | behaviors (motion programs + bindings + tests) | `behaviors` |
| taxonomic | behavior hierarchy: bounce-fly *is a* fly *is a* travel; parameters inherited, traits propagated | `behaviors.parent_type` |

**Long-horizon mechanisms:**

- **Character continuity**: traits attach to entities, not scenes. In scene 9, "Pip goes home" uses Pip's
  learned style without the user repeating it.
- **Version pinning + propagation**: each scene records behavior@version. When a behavior improves, the
  harness lists the earlier scenes that use the old version and offers to upgrade them (like dependency
  updates), running their regression tests.
- **Consolidation ("sleep")**: a background pass merges near-duplicate behaviors, generalizes parameters
  across examples, sorts behaviors into the taxonomy and archives unused ones. This keeps the library and
  the prompt context small as history grows.
- **Bounded context**: the prompt never sees raw history. It gets retrieved examples, entity facts for the
  objects in view, and relevant behaviors, all under a token budget.
- **Hard metric signals** over time: acceptance rate, undo rate, corrections per action, time to accept,
  LLM calls per action, reuse count per behavior. The inspector shows them as a **learning curve**.

## Refinement: updating an existing behavior

The user re-explains ("bouncier"), drags a keyframe or redraws the path. The change gets one of three scopes:

- this instance only (stored as a parameter override on the example)
- this behavior everywhere (new version → propagation offer)
- this behavior for this context (e.g., only for Pip: a specialized child behavior in the taxonomy)

**Decided**: infer scope from wording ("always", "Pip should", "this time") and history, show the guess,
and let the user confirm or change it. How the user picks scope trains later guesses.

## Parameter fusion: several cues → one value

Parameters such as speed come from several cues at once. This is a fun place for meaning to affect motion:

| Cue | Example | Strength |
|---|---|---|
| explicit text | "slowly", "dash" | strongest, overrides the others |
| object semantics | rabbit → quick and hoppy, turtle → slow (LLM common sense, stored as entity traits, user can edit) | prior |
| stroke dynamics | drawing speed, pressure, pauses along the path (timing / easing) | modulates the prior |
| learned user habit | "this user's 'fast' is about 0.6 s" | calibrates the scale |

Default rule: text > (object prior modulated by stroke speed), calibrated per user. The chip shows which cue
won ("slow: turtle"). The interesting case is a conflict, e.g. "fast" + turtle → a fast turtle, which is
funny on purpose and shows that text wins. The weights themselves are a learnable policy.

## Earlier scenes: propagation

**Decided**: always track behavior@version for each scene (core). When a behavior changes, apply a heuristic
default for earlier scenes, based on past feedback: auto-upgrade, ask, or leave pinned. Always show what
happened ("3 earlier scenes updated, 1 kept on v1"), and allow undo per scene.

## Resolved questions (2026-10-10)

1. Scope inference: guess + confirm is OK, as long as the user sees the guess.
2. Stroke-only abbreviation: yes, as gradual learning on both the front end and the back end.
3. Drawing speed → timing: yes, combined with text cues and object semantics (see Parameter fusion).
4. Earlier-scene propagation: an adaptive default, always transparent and controllable.
