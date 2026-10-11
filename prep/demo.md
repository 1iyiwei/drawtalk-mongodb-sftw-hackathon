# Demo runbook (live, ~3 min, text input only)

Two projects, one tab:
- **Live**: a fresh story every run (header **project ▾ → ＋ new story…**, e.g. `demo-3`): an empty canvas
  and an **empty behavior library**
- **History**: `rehearsal`, where you rehearsed all day, with a long learning curve and history. Switch with
  the **project ▾** menu, then press **📈 Learning** (it scrolls to the curve and opens the history).

Layout to draw (left to right): **hare** (top left), **tortoise** (bottom left), **rock** (middle), **tree**
(right edge).

| Time | Do | Type | Point at |
|---|---|---|---|
| 0:00 | Pitch (live story, empty) | | "Everything you'll see was built today. The motion library is **empty**: it learns my vocabulary, and every change it makes to itself is a versioned MongoDB document." |
| 0:20 | ✏️ Ink: draw hare, name it; tortoise; rock; tree | `hare` ⏎ `tortoise` ⏎ `rock` ⏎ `tree` ⏎ | names appear under each character |
| 0:45 | Animate | `the hare and the tortoise race to the rock` | hare dashes with hops, tortoise plods (badges 1, 1′); chips `fast: trait hare is quick`; Why: **created dash v1, plod v1**, MongoDB writes |
| 1:00 | ＋ scene ("starts where scene 1 ends") · ✳️ Gesture: zigzag above the hare | `the hare takes a nap` | Why: "✳️ learned gesture: this shape now means nap" |
| 1:15 | ➰ Path: from the tortoise, past the hare, to the tree | `the tortoise plods along this path` | tortoise follows your curve; **applied plod v1** (reuse, not a new behavior) |
| 1:30 | Refine | `the tortoise should always plod a bit faster` | card: diff `speed 55 → 70`, regression replay ✓ for both clips, scope guess "everywhere ('always')" → click **All** → toast "v2 saved, 2 clips upgraded" |
| 2:00 | ＋ scene · Animate | `the hare wakes up and dashes to the tree` | hare is too late |
| 2:15 | ✳️ Gesture: the **same zigzag** on the tortoise, **no text** | (empty) ⏎ | **⚡ fast path, no LLM, ~0.4 s**: the winner naps. "A drawn word it learned 1 minute ago, transferred to another character" |
| 2:30 | ▶▶ Play story | | three scenes play back to back |
| 2:40 | First press **📈 Learning** here (this run's curve), then **project ▾ → rehearsal** and **📈 Learning** again | | learning curve (LLM share falling), tiles (latency first → last), **History**: new behaviors, v2s, routing threshold changes with reasons |
| 2:55 | Close | | "Every decision is a MongoDB document: versioned, retrievable, testable." |

## If something goes wrong

- LLM slow (> 8 s): keep talking about the Why panel; it shows each step when it lands.
- Wrong behavior: ✕ the clip ("this is a correction signal the harness learns from") and retype.
- Refinement card picks the wrong behavior: Cancel, then name it: `plod should always be a bit faster`.
- Unknown gesture: the app asks for words, so add the words. That's a feature to show, not a failure.
- Network/Atlas down: switch to the recorded video.

## Q&A one-liners

- **Why not the whole history in the prompt?** Cost and latency grow and it can't be regression-tested.
  We compile stable patterns into tested tools and keep the LLM for new cases.
- **What stops bad self-modification?** Schema validation, range clamps, versioned documents with reason +
  evidence, regression replay against approved clips, and a confirmation step with a scope guess.
- **Where's MongoDB?** Behaviors/scenes/examples are nested versioned JSON. Vector Search over the same
  examples (Voyage embeddings). Events are the source of truth for metrics. The routing policy itself
  is a versioned document.
- **Long horizon?** Scenes derive their start from earlier scenes and re-simulate when edited; traits and
  habits persist; versions are pinned per clip.
