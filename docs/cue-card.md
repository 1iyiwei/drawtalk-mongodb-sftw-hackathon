# Live demo cue card (3 min + Q&A)

**Before judges arrive:** check that the server is running, `check_setup.py mongo` passes, then open **project ▾ → ＋ new
story → `live-N`** and draw **rabbit, turtle, rock, tree** (named). The library stays EMPTY. Keep the short video
open in another tab as a fallback.

| ⏱ | Do | Type (copy-paste) | Say while it thinks |
|---|---|---|---|
| 0:00 | (canvas with 4 characters) | | "Built today. An animation tool with **no preset motions**: it learns my vocabulary, and every change it makes to itself is a versioned MongoDB document." |
| 0:15 | Animate | `the rabbit and the turtle race towards the rock` | "The library is empty, so the LLM **writes two new behaviors**, dash and plod, as small motion programs." → point at the **chips**: speed from *rabbit is quick / turtle is slow* |
| 0:40 | Global edit | `the turtle should always move more slowly` | "A **refinement**: the harness proposes **v2** with a diff, **replays every existing clip as a regression test**, and guesses the scope." → click **All** |
| 1:05 | ＋ scene · ✳️ Gesture: **zigzag** on the rabbit | `the rabbit sleeps` | "Scene 2 starts where scene 1 ended. Gesture + words = **teaching**: the shape is now a drawn word for *nap*." |
| 1:25 | ➰ Path: from the turtle to the tree | `while the turtle plods through towards the tree` | "The path says **where**, the words say **how**. It **reuses** plod v2, found via **Atlas Vector Search**." |
| 1:45 | Local edit | `the turtle should move faster this time` | "Same kind of edit, but **only this time**: one clip changes, plod v2 stays." → **Only this time** |
| 2:05 | ＋ scene · Animate | `the rabbit wakes up and dashes towards the tree` | "A **guardrail** makes it get up first. Too late: the turtle wins." |
| 2:25 | ＋ scene · ✳️ same zigzag on the **turtle**, **no text** | (empty) ⏎ | "**No words**: ⚡ recognized in ~100 ms, **no LLM call**. A word it learned a minute ago, on a different character." |
| 2:40 | **📈 Learning** | | "The LLM share **falls** as it compiles my vocabulary. **History**: every self-change, with its reason." |
| 2:55 | ▶▶ Play story | | "Every decision is a MongoDB document: versioned, retrievable, testable." |

## If something goes wrong

| Problem | Do / say |
|---|---|
| LLM slow (> 8 s) | Talk through the **Why** panel: it shows each step and every MongoDB write as it lands |
| Gesture not recognized | "It **asks** instead of guessing." Redraw it bigger, or add words; the harness lowers its own threshold when you confirm |
| Wrong behavior | ✕ the clip: "that's a correction signal it learns from", then retype |
| Scope guess differs from what you wanted | "The guess is shown and **overridable**", then click the other button |
| Network / Atlas down | Switch to the short video tab |

## Q&A one-liners

- **Why not just put history in the prompt?** Cost and latency grow and it can't be tested. We compile stable patterns into **tested tools**; the LLM handles new cases.
- **What stops bad self-modification?** Schema validation, range clamps, a "no visible motion" self-check, regression replay, a scope confirmation, and **versions instead of overwrites**.
- **Where's MongoDB?** Behaviors, policies and proposals are versioned documents; scenes and examples hold the story; **Vector Search** over Voyage embeddings; events drive the learning curve.
- **Long horizon?** Scenes derive their start from earlier scenes and **re-simulate when edited**; traits and habits persist; clips are pinned to versions.
- **Recursive self-improvement?** It writes its tools, checks them, versions them, and **retunes its own routing thresholds** from accepted / undone clips and missed gestures (also tracked in Raindrop).
- **Built today?** Yes: the README has a "what was built when" table, and the git history shows it.
