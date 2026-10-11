"""The harness: turns a command (text and/or stroke) into versioned behaviors, clips, examples and events."""

import json
import math
import re
import time

import asyncio

import raindrop.analytics as raindrop

from app import db, dsl, geometry, llm, memory, recognizer, refine

DEFAULT_STATE = {"rot": 0.0, "sx": 1.0, "sy": 1.0, "op": 1.0}

SYSTEM = """You are the motion interpreter of a sketch-and-talk 2D animation tool.
The user drew named characters on a canvas (pixels, x right, y DOWN) and gives commands by text and/or a
drawn stroke. Turn the command into one action per moving character.

For each action choose a behavior:
- decision "apply": reuse a behavior from the catalog (use its exact behavior_id) and set its parameters.
- decision "create": no catalog behavior fits; write a new behavior (snake_case id, short description,
  taxonomy path like ["travel","run","dash"], parameter specs, and a motion program). Keep programs small.
Prefer apply when a catalog behavior's description matches; create when the motion type is new.
A behavior is a MOTION STYLE (dash, hop, plod, waddle, nap), not a situation: "race" or "go home" is the
situation. WHERE a character goes (a target, a drawn path, a direction) is never part of a behavior: "plods to
the rock", "plods along this path" and "plods on" all apply the same "plod". If characters move differently by nature (a hare dashes with hops, a tortoise plods with a slight
bob), give each its own style behavior. Make motions lively with modifiers (hop, bob, breathe, face_motion)
where they fit the character. Name behaviors after the style (e.g. "dash", "plod"), not the actor.

Motion program (JSON, every node has "type"):
- move_along {path: "default"|"stroke"|"arc", speed px/s OR duration s (other null), arc_height (arc only), easing}
  "default" = straight to the target (stops on contact); "stroke" = the user's drawn path; "arc" = jump-like.
- stay {duration}; wait {duration}; turn_to {angle in DEGREES (absolute pose), duration, easing};
  rotate_by {degrees (relative; 1 turn = 360, can be negative), duration, easing}; scale_to {sx, sy, duration, easing};
  fade_to {opacity, duration}
- seq {steps}; par {steps}; layer {base, mods}
- mods: hop {height px, every_px, squash 0..0.4}, bob {amplitude px, period s}, breathe {amount 0..0.2, period s},
  face_motion {}, emit {glyph, every s, rise px, fade s}
Idioms: lie down / fall asleep = seq[turn_to angle 80-90, layer{stay, breathe + emit "Z"}]; get up / wake = turn_to 0
(+ a quick scale_to pop); jump = move_along path "arc"; spin / rotate / turn around = rotate_by 360 per turn
(expose a "degrees" parameter, default 360, range 90..1440, and use it as rotate_by.degrees; one turn = 360);
wobble / shake = seq of small rotate_by ±10-15 or a bob. All angles are degrees, never turns or radians.
Numbers may be {"param": name} referencing a declared parameter. Expose the things a user would tweak
(speed, hop height, nap length) as parameters with sensible ranges.

Parameter values (param_values): fill every parameter of the chosen behavior. Priority of cues:
explicit words in the text ("slowly", "dash") > the character's nature/traits (a hare is quick, a tortoise is
slow) > the stroke's drawing speed > the behavior default. Record the deciding cue in `source`, e.g.
"text: 'slowly'", "trait: tortoise is slow", "stroke: drawn fast", "default".
Typical speeds: plod/slow walk 60-110 px/s, walk 110-180, run 200-400, dash 400-700.
Screen pacing: keep each motion between about 1 and 6 seconds; a slow character should take roughly 2-4x
longer than a fast one, not 10x.

actor_traits: 0-3 short adjectives about the character's nature that affect motion (e.g. "quick", "slow",
"sleepy"), only if implied by the character type or the text.
path: "stroke" only if a path stroke was drawn for this actor; "default" when moving to a target OR in a direction;
"none" for in-place motions.
direction: when there is no target character but the text gives a direction ("moves right", "jumps up"), set
left/right/up/down and distance_px (default ~250, "a little" ~100, "far"/"across" ~600); otherwise "none" and null.
If the text implies continuing ("on", "onward", "through", "past", "keeps going", "continues") with no target,
use the character's "last moved" direction.
timing: "together" if the actions happen at the same time ("race", "both", "while", "meanwhile", "together"),
"in_order" if one after another ("then", "after").
message: one short sentence describing what will happen, for the user.

intent: "animate" for commands that make characters move now, including plain actions like "the windmill rotates".
"refine" ONLY when the user talks about how an existing behavior SHOULD look (cues: "should", "always", "next time",
"instead", "too fast/slow", "more", "less", "-er than") — it corrects or changes HOW an existing behavior looks ("should always plod steadily", "jump higher", "make the nap lie down with Zzz",
"slower next time"). For refine, set actions to [] and fill `refine`:
- behavior_id: the catalog behavior being changed; actor: the character it was about (or null)
- program and params: the COMPLETE new version (edit the current program shown in the catalog; keep what the
  user didn't ask to change; keep parameter names stable). Never replace a {"param": name} reference with a
  number: to make something faster/higher/longer, change that parameter's default (and range) instead.
- description: updated one-line description; change_summary: one short sentence of what changed
- scope_guess: "behavior" if it should apply everywhere ("always", "should", general wording),
  "instance" if only this one time ("this time", "here"); scope_reason: the words that suggested it.
For animate, set refine to null."""


REFINE_SCHEMA = {
    "type": "object",
    "properties": {
        "behavior_id": {"type": "string"},
        "actor": {"anyOf": [{"type": "string"}, {"type": "null"}]},
        "description": {"type": "string"},
        "params": {"type": "array", "items": dsl.PARAM_SPEC_SCHEMA},
        "program": {"$ref": "#/$defs/node"},
        "change_summary": {"type": "string"},
        "scope_guess": {"type": "string", "enum": ["behavior", "instance"]},
        "scope_reason": {"type": "string"},
    },
    "required": ["behavior_id", "actor", "description", "params", "program", "change_summary", "scope_guess", "scope_reason"],
    "additionalProperties": False,
}


def decision_schema(entity_names: list[str]) -> dict:
    names = entity_names or ["(none)"]
    action = {
        "type": "object",
        "properties": {
            "actor": {"type": "string", "enum": names},
            "target": {"anyOf": [{"type": "string", "enum": names}, {"type": "null"}]},
            "path": {"type": "string", "enum": dsl.PATHS},
            "direction": {"type": "string", "enum": ["none", "left", "right", "up", "down"]},
            "distance_px": {"anyOf": [{"type": "number"}, {"type": "null"}]},
            "decision": {"type": "string", "enum": ["apply", "create"]},
            "behavior_id": {"type": "string"},
            "new_behavior": {
                "anyOf": [
                    {
                        "type": "object",
                        "properties": {
                            "description": {"type": "string"},
                            "type_path": {"type": "array", "items": {"type": "string"}},
                            "params": {"type": "array", "items": dsl.PARAM_SPEC_SCHEMA},
                            "program": {"$ref": "#/$defs/node"},
                        },
                        "required": ["description", "type_path", "params", "program"],
                        "additionalProperties": False,
                    },
                    {"type": "null"},
                ]
            },
            "param_values": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}, "value": {"type": "number"}, "source": {"type": "string"}},
                    "required": ["name", "value", "source"],
                    "additionalProperties": False,
                },
            },
            "actor_traits": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["actor", "target", "path", "direction", "distance_px", "decision", "behavior_id", "new_behavior", "param_values", "actor_traits"],
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {
            "intent": {"type": "string", "enum": ["animate", "refine"]},
            "actions": {"type": "array", "items": action},
            "timing": {"type": "string", "enum": ["together", "in_order"]},
            "refine": {"anyOf": [REFINE_SCHEMA, {"type": "null"}]},
            "message": {"type": "string"},
        },
        "required": ["intent", "actions", "timing", "refine", "message"],
        "additionalProperties": False,
        "$defs": dsl.SCHEMA_DEFS,
    }


# ---------------------------------------------------------------- scene state


def current_states(scene: dict) -> dict[str, dict]:
    """Entity states at the end of the scene: start state overridden by each clip's end state in time order."""
    states = {eid: {**DEFAULT_STATE, **s} for eid, s in scene.get("start_state", {}).items()}
    for clip in sorted(scene.get("timeline", []), key=lambda c: c["start"] + c["duration"]):
        states[clip["actor"]] = clip["end_state"]
    return states


def scene_end_time(scene: dict) -> float:
    return max((c["start"] + c["duration"] for c in scene.get("timeline", [])), default=0.0)


async def latest_behaviors(project_id: str) -> dict[str, dict]:
    out = {}
    async for b in db.col("behaviors").find({"project_id": project_id}).sort("version", 1):
        out[b["behavior_id"]] = b
    return out


def stroke_summary(stroke: list, entities: dict[str, dict], states: dict[str, dict]) -> dict:
    pts = [(p[0], p[1]) for p in stroke]
    t = [p[2] for p in stroke] if len(stroke[0]) > 2 else None

    def on(p):
        for eid, e in entities.items():
            if eid in states and geometry.contains(geometry.entity_world_bbox(e, states[eid]), p, pad=12):
                return e["name"]
        return None

    length = geometry.polyline_length(pts)
    dur = (t[-1] - t[0]) / 1000 if t and t[-1] > t[0] else None
    chord = math.dist(pts[0], pts[-1])
    return {
        "starts_on": on(pts[0]),
        "ends_on": on(pts[-1]),
        "length_px": round(length),
        "drawing_speed_px_s": round(length / dur) if dur else None,
        "straightness": round(chord / length, 2) if length else 1.0,
        "points": [[round(x), round(y)] for x, y in pts[:: max(1, len(pts) // 12)]],
    }


def normalize_id(raw: str) -> str:
    """'Dash v1' / 'dash (version 2)' / 'race-to' → 'dash' / 'dash' / 'race_to'."""
    s = re.sub(r"\s*\(?(v|version)\s*\d+\)?\s*$", "", raw.strip(), flags=re.I)
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_") or "behavior"


def catalog_text(behaviors: dict[str, dict]) -> str:
    if not behaviors:
        return "(empty: no behaviors yet)"
    lines = []
    for b in behaviors.values():
        ps = ", ".join(f"{p['name']}={p['default']:g}{p['unit']} [{p['min']:g}..{p['max']:g}]" for p in b["params"])
        lines.append(f"- behavior_id={b['behavior_id']} (version {b['version']}): {b['description']} | params: {ps or 'none'}"
                     f"\n  program: {json.dumps(b['program'], separators=(',', ':'))}")
    return "\n".join(lines)


def undefined_behaviors(decision: dict, behaviors: dict) -> list[str]:
    """Actions that would be skipped: an unknown behavior with no definition, or an invalid new program."""
    out = []
    for a in decision.get("actions", []):
        nb = a.get("new_behavior")
        known = normalize_id(a.get("behavior_id") or "") in behaviors
        if not nb and not known:
            out.append(f"{a['actor']}'s behavior '{a.get('behavior_id')}' is not in the catalog and has no definition")
        elif nb:
            try:
                dsl.validate(nb["program"], {p["name"] for p in nb["params"]})
            except dsl.DSLError as e:
                out.append(f"{a['actor']}'s new behavior '{a.get('behavior_id')}' is invalid: {e}")
    return out


def invisible_new_behaviors(decision: dict) -> list[str]:
    """Test-run each newly created behavior with its own parameter values on a 300 px straight path."""
    out = []
    for a in decision.get("actions", []):
        nb = a.get("new_behavior")
        if not nb:
            continue
        try:
            dsl.validate(nb["program"], {p["name"] for p in nb["params"]})
            given = {p["name"]: p["value"] for p in a["param_values"]}
            params = dsl.resolve_params(nb["params"], given, [])
            start = {"x": 100.0, "y": 300.0}
            res = dsl.run(nb["program"], start, dsl.Ctx(params=params, path_default=[(100.0, 300.0), (400.0, 300.0)]))
            vis = dsl.visible_change(res, start)
            if not vis["visible"]:
                out.append(f"new behavior {a['behavior_id']} has no visible motion (moved {vis['move_px']} px, rotated {vis['rotate_deg']}°, "
                           f"scaled {vis['scale']}, faded {vis['fade']}, {vis['glyphs']} glyphs)")
        except dsl.DSLError:
            continue  # rejected later with its own message
    return out


def flat_props(props: dict) -> dict:
    """Raindrop properties must be str/int/float/bool: join lists, drop Nones."""
    out = {}
    for k, v in props.items():
        if v is None:
            continue
        out[k] = ", ".join(map(str, v)) if isinstance(v, (list, tuple, set)) else v if isinstance(v, (str, int, float, bool)) else str(v)
    return out


async def accept_pending(project_id: str) -> int:
    """Implicit acceptance: moving on to the next command without undoing a clip accepts it (a hard signal)."""
    pending = [e async for e in db.col("examples").find({"project_id": project_id, "outcome": "pending"},
                                                          {"behavior_id": 1, "behavior_version": 1, "route": 1,
                                                           "command_event": 1})]
    if not pending:
        return 0
    from collections import Counter
    from pymongo import UpdateOne

    await db.col("examples").update_many({"_id": {"$in": [e["_id"] for e in pending]}}, {"$set": {"outcome": "accepted"}})
    counts = Counter((e["behavior_id"], e["behavior_version"]) for e in pending)
    await db.col("behaviors").bulk_write([
        UpdateOne({"project_id": project_id, "behavior_id": b, "version": v}, {"$inc": {"stats.accepted": n}})
        for (b, v), n in counts.items()])
    await db.log_event(project_id, "examples_accepted", n=len(pending), background=True)
    for ev in {e.get("command_event") for e in pending} - {None}:
        raindrop.track_signal(event_id=ev, name="accepted", sentiment="POSITIVE",
                              properties={"how": "implicit: user moved on without undoing"})
    n_fast = sum(1 for e in pending if e.get("route") == "fast")
    if n_fast:
        await memory.count_fast_accepted(project_id, n_fast, [e["_id"] for e in pending])
    return len(pending)


def closest_entity(pts: list, entities: dict[str, dict], states: dict[str, dict]) -> str | None:
    """The character a gesture belongs to: nearest bounding box to the gesture's centroid."""
    cx, cy = sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)
    best, best_d = None, math.inf
    for eid, e in entities.items():
        if eid not in states:
            continue
        x0, y0, x1, y1 = geometry.entity_world_bbox(e, states[eid])
        d = math.hypot(max(x0 - cx, 0, cx - x1), max(y0 - cy, 0, cy - y1))
        if d < best_d:
            best, best_d = eid, d
    return best


def _fast_decision(actor, target, path_kind, bid, ex, message):
    action = {
        "actor": actor, "target": target, "path": path_kind, "direction": "none", "distance_px": None,
        "decision": "apply", "behavior_id": bid, "new_behavior": None, "actor_traits": [],
        "param_values": [{"name": k, "value": v, "source": f"learned: example {ex['_id'][-4:]} ({ex['actor_name']})"}
                         for k, v in ex["params"].items()],
    }
    return {"intent": "animate", "actions": [action], "timing": "in_order", "refine": None, "message": message}


async def fast_match(project_id: str, gesture: dict | None, path: dict | None, by_name: dict) -> dict:
    """Text-free commands, decided without the LLM when the evidence is clear.

    - gesture (± path): the gesture's SHAPE says how ($P against taught gestures); the path says where.
    - path alone: the path is only the trajectory; HOW comes from the character's learned habit.
    Thresholds come from the versioned harness_config, which the harness tunes from feedback."""
    cfg = (await memory.get_config(project_id))["fast_path"]
    info: dict = {"threshold": cfg["min_score"], "min_examples": cfg["min_examples"], "candidates": []}

    if gesture:
        actor = gesture["actor"]
        best: dict[str, dict] = {}
        async for ex in db.col("examples").find(
            {"project_id": project_id, "outcome": "accepted", "gesture_template": {"$ne": None}},
            {"gesture_template": 1, "behavior_id": 1, "actor_name": 1, "params": 1},
        ):
            sim = recognizer.gesture_similarity(gesture["template"], [tuple(p) for p in ex["gesture_template"]])
            cur = best.setdefault(ex["behavior_id"], {"score": 0.0, "support": 0, "example": None})
            cur["support"] += sim >= cfg["gesture_min_score"]
            if sim + (0.02 if ex["actor_name"] == actor else 0) > cur["score"]:
                cur.update(score=sim + (0.02 if ex["actor_name"] == actor else 0), example=ex)
        cands = sorted(best.items(), key=lambda kv: -kv[1]["score"])
        info.update(kind="gesture", actor=actor, threshold=cfg["gesture_min_score"], candidates=[
            {"behavior": b, "score": round(v["score"], 3), "support": v["support"]} for b, v in cands[:4]])
        runner = cands[1][1]["score"] if len(cands) > 1 else 0.0
        if not cands or cands[0][1]["score"] < cfg["gesture_min_score"] or cands[0][1]["score"] - runner < cfg["gesture_margin"]:
            return {**info, "decision": None, "unknown_gesture": True, "reason": "gesture not recognized"}
        bid, top = cands[0]
        on_path = path and path.get("starts_on") == actor
        decision = _fast_decision(actor, path.get("ends_on") if on_path else None, "stroke" if on_path else "none", bid,
                                  top["example"], f"{actor} → {bid} (recognized your gesture)")
        return {**info, "decision": decision, "behavior_id": bid, "score": round(top["score"], 3),
                "support": top["support"], "reason": "gesture recognized"}

    actor = path.get("starts_on")
    if not actor or actor not in by_name:
        return {**info, "kind": "path", "decision": None, "reason": "the path does not start on a character"}
    habits: dict[str, dict] = {}
    async for ex in db.col("examples").find(
        {"project_id": project_id, "outcome": "accepted", "actor_name": actor, "stroke_template": {"$ne": None}},
        {"behavior_id": 1, "actor_name": 1, "params": 1, "target_name": 1},
    ).sort("created", -1).limit(20):
        h = habits.setdefault(ex["behavior_id"], {"count": 0, "example": ex})
        h["count"] += 1
    total = sum(h["count"] for h in habits.values())
    cands = sorted(habits.items(), key=lambda kv: -kv[1]["count"])
    info.update(kind="path", actor=actor, candidates=[
        {"behavior": b, "score": round(h["count"] / total, 2), "support": h["count"]} for b, h in cands[:4]])
    if not cands:
        return {**info, "decision": None, "reason": f"no path habits for {actor} yet"}
    bid, top = cands[0]
    share = top["count"] / total
    if top["count"] < cfg["min_examples"] or share < cfg["min_score"]:
        return {**info, "decision": None, "reason": f"{actor}'s habit is not clear yet"}
    decision = _fast_decision(actor, path.get("ends_on") if path.get("ends_on") != actor else None, "stroke", bid,
                              top["example"], f"{actor} → {bid} along your path (learned habit)")
    return {**info, "decision": decision, "behavior_id": bid, "score": round(share, 2), "support": top["count"],
            "reason": f"{actor} usually does {bid} along paths"}


# ---------------------------------------------------------------- command


async def run_command(project_id: str, scene_id: str, text: str, stroke: list | None, gesture: list | None = None) -> dict:
    t0 = time.time()
    timings: dict[str, int] = {}

    def mark(name):
        timings[name] = round((time.time() - t0) * 1000)

    async def load_entities():
        return {e["_id"]: e async for e in db.col("entities").find({"project_id": project_id})}

    scene, entities, behaviors, _, project = await asyncio.gather(
        db.col("scenes").find_one({"_id": scene_id, "project_id": project_id}), load_entities(),
        latest_behaviors(project_id), accept_pending(project_id),
        db.col("projects").find_one({"_id": project_id}, {"name": 1}))
    if not scene:
        raise ValueError("scene not found")
    states = current_states(scene)
    in_scene = {eid: e for eid, e in entities.items() if eid in states}
    by_name = {e["name"]: eid for eid, e in in_scene.items()}
    mark("loaded")

    summary = stroke_summary(stroke, in_scene, states) if stroke and len(stroke) > 1 else None
    earlier = [c async for sc in db.col("scenes").find(
        {"project_id": project_id, "order": {"$lt": scene.get("order", 0)}}, {"timeline.actor": 1, "timeline.path": 1,
                                                                              "timeline.start": 1, "order": 1}).sort("order", -1)
               for c in sorted(sc.get("timeline", []), key=lambda c: -c["start"])]

    def heading(eid):
        for c in sorted(scene.get("timeline", []), key=lambda c: -c["start"]) + earlier:
            pts = c["path"]["points"]
            if c["actor"] == eid and len(pts) > 1:
                dx, dy = pts[-1][0] - pts[0][0], pts[-1][1] - pts[0][1]
                if abs(dx) + abs(dy) > 5:
                    return ("right" if dx > 0 else "left") if abs(dx) >= abs(dy) else ("down" if dy > 0 else "up")
        return None

    chars = "\n".join(
        f"- {e['name']}: at ({states[eid]['x']:.0f},{states[eid]['y']:.0f}), size {e['bbox'][2]-e['bbox'][0]:.0f}x{e['bbox'][3]-e['bbox'][1]:.0f}"
        + (f", traits: {', '.join(e.get('traits', []))}" if e.get("traits") else "")
        + (f", last moved {heading(eid)}" if heading(eid) else "")
        for eid, e in in_scene.items()
    )
    recent = "\n".join(
        f"- {entities.get(c['actor'], {}).get('name', '?')}: {c['behavior_id']} v{c['behavior_version']} "
        f"(path {c['path']['kind']}, {c['duration']:.1f}s, text {c.get('text', '')!r})"
        for c in sorted(scene.get("timeline", []), key=lambda c: c["start"])[-6:]
    )
    user = (
        f"Characters in the scene:\n{chars or '(none)'}\n\n"
        f"Clips so far in this scene (latest last; a refinement usually targets the latest clip's behavior):\n{recent or '(none)'}\n\n"
        f"Behavior catalog:\n{catalog_text(behaviors)}\n\n"
        f"Command text: {text!r}\n"
        f"Path stroke: {summary if summary else 'none'}"
    )
    route_info: dict = {}
    template = recognizer.normalize([(p[0], p[1]) for p in stroke]) if summary else None
    g_info = None
    if gesture and len(gesture) > 1:
        g_actor = closest_entity(gesture, in_scene, states)
        if g_actor:
            g_info = {"actor": in_scene[g_actor]["name"], "template": recognizer.normalize([(p[0], p[1]) for p in gesture]),
                      "size_px": round(geometry.polyline_length([(p[0], p[1]) for p in gesture]))}
            user += (f"\nGesture: a small symbol drawn on/near {g_info['actor']} (a drawn word). When text is present, "
                     f"the text says what the gesture means; apply that behavior to {g_info['actor']}.")
    async def none():
        return None

    text_vec = await memory.embed(text, "query") if text else None
    fast, retrieved = await asyncio.gather(
        fast_match(project_id, g_info, summary, by_name) if ((g_info or summary) and not text) else none(),
        memory.similar_examples(project_id, text_vec) if text_vec else none())
    retrieved = retrieved or []
    mark("routed")
    if retrieved:
        user += "\n\nSimilar past commands (from vector memory; reuse their behaviors when they fit):\n" + "\n".join(
            f"- {r['text']!r}: {r['actor_name']} → {r['behavior_id']} v{r['behavior_version']} params {r['params']} "
            f"(similarity {r['score']:.2f})" for r in retrieved)
    if fast and fast.get("unknown_gesture"):
        msg = (f"I don't know this gesture yet. Draw it again with a few words (e.g. “{g_info['actor']} naps”) "
               f"to teach me what it means.")
        trace = {"route": "ask", "fast_match": {k: v for k, v in fast.items() if k != "decision"}, "steps": [msg],
                 "total_ms": round((time.time() - t0) * 1000)}
        await db.log_event(project_id, "gesture_unknown", scene_id=scene_id, actor=g_info["actor"], template=g_info["template"],
                           candidates=fast.get("candidates"), threshold=fast.get("threshold"), background=True)
        return {"message": msg, "clips": [], "written": [], "trace": trace, "event_id": None}
    self_check: list[str] = []
    if fast and fast["decision"]:
        decision, meta, route = fast["decision"], None, "fast"
    else:
        decision, meta = await asyncio.to_thread(llm.structured, SYSTEM, user, "motion_decision", decision_schema(list(by_name)))
        route = "llm"
        mark("llm")
        problems = invisible_new_behaviors(decision) + undefined_behaviors(decision, behaviors)
        if problems:  # the harness checks its own new tools before using them, and asks for a fix once
            self_check = [f"self-check: {p} → asked the LLM to fix it" for p in problems]
            decision, meta2 = await asyncio.to_thread(
                llm.structured, SYSTEM, user + "\n\nYour previous answer created behaviors with NO VISIBLE MOTION: "
                + "; ".join(problems) + ". Fix them: every action must apply an existing catalog behavior or define a "
                "new one with a valid program (angles are degrees; spins use rotate_by 360 per turn; disappearing = "
                "fade_to opacity 0).",
                "motion_decision", decision_schema(list(by_name)))
            meta = {**meta2, "latency_ms": meta["latency_ms"] + meta2["latency_ms"], "retried": True}
            still = invisible_new_behaviors(decision) + undefined_behaviors(decision, behaviors)
            self_check.append("self-check: fixed ✓" if not still else f"self-check: still invisible: {'; '.join(still)}")
            mark("llm_retry")
    route_info = {"route": route, "fast_match": fast and {k: v for k, v in fast.items() if k != "decision"},
                  "retrieved": [{"text": r["text"], "behavior": r["behavior_id"], "score": round(r["score"], 3)} for r in retrieved]}
    cmd_event = await db.log_event(
        project_id, "command", scene_id=scene_id, text=text, has_stroke=bool(summary), route=route, llm=meta,
        intent=decision["intent"], n_actions=len(decision["actions"]),
        latency_ms=round((time.time() - t0) * 1000), background=True,
    )

    def report(output: str, extra: dict):
        """Raindrop: one event per command; signals attach to it later by the same id."""
        project_name = project.get("name", project_id) if project else project_id
        raindrop.track_ai(
            user_id=project_name, convo_id=scene_id, event_id=cmd_event, event="animate_command",
            model=meta["model"] if meta else "fast-path (no LLM)",
            input=text + (" [path]" if summary else "") + (" [gesture]" if g_info else ""),
            output=output,
            properties=flat_props({"route": route, "intent": decision["intent"], "latency_ms": round((time.time() - t0) * 1000),
                                   "tokens_in": (meta or {}).get("tokens_in"), "tokens_out": (meta or {}).get("tokens_out"),
                                   "fast_score": (fast or {}).get("score"), "fast_threshold": (fast or {}).get("threshold"),
                                   "fast_kind": (fast or {}).get("kind"), **extra}),
        )

    if decision["intent"] == "refine" and decision["refine"]:
        r = decision["refine"]
        r["behavior_id"] = normalize_id(r["behavior_id"])
        current = behaviors.get(r["behavior_id"])
        trace = {"llm": meta, "decision": decision, "steps": [], **route_info}
        if not current:
            trace["steps"].append(f"refine target {r['behavior_id']!r} not in the library")
            return {"message": f"I couldn't find a behavior called {r['behavior_id']!r} to change.", "clips": [],
                    "written": [], "trace": trace, "event_id": cmd_event}
        try:
            try:
                prop = await refine.propose(project_id, scene_id, text, current, r, cmd_event, entities)
            except refine.InvisibleMotion as e:  # the harness rejects its own invisible change and asks for a fix once
                trace["steps"].append(f"self-check: {e}; asked the LLM to fix it")
                fixed, meta2 = await asyncio.to_thread(
                    llm.structured, SYSTEM, user + f"\n\nYour refinement of {current['behavior_id']} has NO VISIBLE MOTION: {e}. "
                    "Rewrite the program so the change is clearly visible (angles are degrees; spins use rotate_by "
                    "with a 'degrees' parameter, 360 per turn; never use a turn count as an angle).",
                    "motion_decision", decision_schema(list(by_name)))
                trace["llm"] = {**meta2, "retried": True}
                if not (fixed["intent"] == "refine" and fixed["refine"]):
                    raise refine.InvisibleMotion(str(e))
                fixed["refine"]["behavior_id"] = current["behavior_id"]
                decision, r = fixed, fixed["refine"]
                prop = await refine.propose(project_id, scene_id, text, current, r, cmd_event, entities)
                trace["steps"].append("self-check: fixed ✓")
        except refine.InvisibleMotion as e:
            trace["steps"].append(f"self-check failed: {e}")
            return {"message": "That change would make no visible motion; try describing it differently.", "clips": [],
                    "written": [], "trace": trace, "event_id": cmd_event}
        except dsl.DSLError as e:
            trace["steps"].append(f"rejected refinement: {e}")
            return {"message": "That change produced an invalid motion program; try rephrasing.", "clips": [],
                    "written": [], "trace": trace, "event_id": cmd_event}
        n_pass = sum(c["pass"] for c in prop["checks"])
        trace["steps"] += [f"proposed {current['behavior_id']} v{current['version']} → v{current['version'] + 1}",
                           f"regression replay: {n_pass}/{len(prop['checks'])} clips keep their end position"]
        trace["steps"] += [f"guardrail: {f}" for f in prop.get("guardrail_fixes", [])]
        trace["total_ms"] = round((time.time() - t0) * 1000)
        prop.pop("created", None)
        report(f"{decision['message']}\nproposal {current['behavior_id']} v{current['version']}→v{current['version'] + 1}: "
               + "; ".join(prop["diff"]),
               {"behavior": current["behavior_id"], "regression_pass": n_pass, "regression_total": len(prop["checks"]),
                "scope_guess": prop["scope_guess"], "guardrail_fixes": len(prop.get("guardrail_fixes", []))})
        return {"message": decision["message"], "clips": [], "proposal": prop,
                "written": [{"collection": "proposals", "id": prop["_id"], "what": "pending refinement"}],
                "trace": trace, "event_id": cmd_event}

    clips, written, trace = [], [], {"llm": meta, "stroke": summary, "decision": decision, "steps": list(self_check), **route_info}
    if route == "fast":
        trace["steps"].append(f"⚡ fast path ({fast['kind']}): {fast['reason']} → {fast['behavior_id']} "
                              f"(score {fast['score']}, {fast['support']} example(s)), no LLM call")
    prev_start = None
    writes = []
    created_here: dict[str, dict] = {}
    cursor = scene_end_time(scene)
    for a in decision["actions"]:
        actor_id = by_name.get(a["actor"])
        if not actor_id:
            trace["steps"].append(f"skipped: unknown actor {a['actor']!r}")
            continue
        actor = in_scene[actor_id]

        # behavior: apply an existing one or create v1. Never accept an empty id or a silent collision.
        raw = a["behavior_id"].strip()
        if not raw and a["new_behavior"]:
            raw = (a["new_behavior"].get("type_path") or ["move"])[-1]
        a["behavior_id"] = normalize_id(raw or f"move_{a['actor']}")
        made_now = created_here.get(a["behavior_id"])
        if made_now is not None and a["new_behavior"] and a["new_behavior"]["program"] != made_now:
            a["behavior_id"] = normalize_id(f"{a['behavior_id']}_{a['actor']}")
        b = behaviors.get(a["behavior_id"])
        if b is None:
            nb = a["new_behavior"]
            if not nb:
                trace["steps"].append(f"skipped: behavior {a['behavior_id']!r} not found and no definition given")
                continue
            names = {p["name"] for p in nb["params"]}
            try:
                dsl.validate(nb["program"], names)
            except dsl.DSLError as e:
                trace["steps"].append(f"rejected new behavior {a['behavior_id']}: {e}")
                await db.log_event(project_id, "behavior_rejected", behavior_id=a["behavior_id"], error=str(e), command=cmd_event)
                continue
            b = {
                "_id": db.new_id("beh"), "project_id": project_id, "behavior_id": a["behavior_id"], "version": 1,
                "parent_version": None, "description": nb["description"], "type_path": nb["type_path"],
                "params": nb["params"], "program": nb["program"],
                "reason": f"created from command {text!r}" if text else "created from a stroke", "evidence": [cmd_event],
                "tests": [], "stats": {"uses": 0, "accepted": 0, "corrected": 0}, "created": db.now(),
            }
            await db.col("behaviors").insert_one(b)
            behaviors[b["behavior_id"]] = b
            created_here[b["behavior_id"]] = b["program"]
            written.append({"collection": "behaviors", "id": b["_id"], "what": f"{b['behavior_id']} v1 (new tool)"})
            trace["steps"].append(f"created behavior {b['behavior_id']} v1")
        else:
            trace["steps"].append(f"applied behavior {b['behavior_id']} v{b['version']}")

        # parameters: fuse cues (LLM-picked values) + clamp to declared ranges
        clamps: list[str] = []
        given = {p["name"]: p["value"] for p in a["param_values"]}
        params = dsl.resolve_params(b["params"], given, clamps)
        sources = {p["name"]: p["source"] for p in a["param_values"] if p["name"] in params}
        for name in params:
            sources.setdefault(name, "default")

        # path
        start = states[actor_id]
        target_id = by_name.get(a["target"]) if a["target"] else None
        path_default = None
        if target_id and target_id != actor_id:
            path_default = geometry.default_path(start, actor, geometry.entity_world_bbox(in_scene[target_id], states[target_id]))
        elif a["direction"] != "none":
            path_default = geometry.direction_path(start, actor, a["direction"], a["distance_px"] or 250)
            trace["steps"].append(f"path: {a['direction']} {round(geometry.polyline_length(path_default))} px (no target)")
        path_stroke = geometry.stroke_path(start, [(p[0], p[1]) for p in stroke], actor) if stroke and a["path"] == "stroke" else None
        if path_stroke and len(path_stroke) == len(stroke) + 1:
            trace["steps"].append(f"path starts away from {actor['name']}: it goes to the start of your path first, "
                                  f"then follows it where you drew it")

        ctx = dsl.Ctx(params=params, path_default=path_default, path_stroke=path_stroke, clamps=clamps)
        result = dsl.run(b["program"], start, ctx)
        vis = dsl.visible_change(result, start)
        if not vis["visible"]:
            trace["steps"].append(f"⚠ {b['behavior_id']} v{b['version']} made no visible motion for {actor['name']} "
                                  f"(moved {vis['move_px']} px, rotated {vis['rotate_deg']}°). Fix it with "
                                  f"“{b['behavior_id']} should …”, e.g. “{b['behavior_id']} should be a full turn”.")

        clip_start = prev_start if (decision["timing"] == "together" and prev_start is not None) else cursor
        prev_start = clip_start
        example_id = db.new_id("ex")
        clip = {
            "clip_id": db.new_id("clip"), "actor": actor_id, "target": target_id,
            "behavior_id": b["behavior_id"], "behavior_version": b["version"],
            "path": {"kind": a["path"], "points": [list(p) for p in (path_stroke or path_default or [])]},
            "params": params, "param_sources": sources, "start": clip_start,
            "duration": result["duration"], "end_state": result["end_state"],
            "frames": result["frames"], "events": result["events"], "example_id": example_id, "text": text,
            "route": route,
        }
        clips.append(clip)
        cursor = max(cursor, clip_start + result["duration"])
        states[actor_id] = result["end_state"]

        writes.append(db.col("examples").insert_one({
            "_id": example_id, "project_id": project_id, "scene_id": scene_id, "clip_id": clip["clip_id"],
            "text": text, "stroke": summary, "actor_name": actor["name"],
            "target_name": in_scene[target_id]["name"] if target_id else None,
            "behavior_id": b["behavior_id"], "behavior_version": b["version"], "params": params,
            "param_sources": sources, "outcome": "pending", "route": route, "command_event": cmd_event,
            "stroke_template": template if a["path"] == "stroke" else None,
            "gesture_template": g_info["template"] if g_info and g_info["actor"] == actor["name"] else None,
            **({"text_vec": text_vec} if text_vec else {}),
            "created": db.now(),
        }))
        if g_info and g_info["actor"] == actor["name"] and text:
            trace["steps"].append(f"✳️ learned gesture: this shape now means {b['behavior_id']} (draw it alone next time)")
            lowered = await memory.learn_from_missed_gesture(project_id, b["behavior_id"], example_id)
            if lowered:
                trace["steps"].append(f"routing: your earlier {b['behavior_id']} gesture was missed; "
                                      f"gesture threshold lowered to {lowered} (new policy version)")
        written.append({"collection": "examples", "id": example_id, "what": f"{actor['name']} → {b['behavior_id']}"})
        writes.append(db.col("behaviors").update_one({"_id": b["_id"]}, {"$inc": {"stats.uses": 1}}))

        new_traits = [t for t in a["actor_traits"] if t not in actor.get("traits", [])]
        if new_traits:
            writes.append(db.col("entities").update_one({"_id": actor_id}, {"$addToSet": {"traits": {"$each": new_traits}}}))
            actor.setdefault("traits", []).extend(new_traits)
            written.append({"collection": "entities", "id": actor_id, "what": f"{actor['name']} traits += {', '.join(new_traits)}"})
        if clamps:
            await db.log_event(project_id, "clamp", behavior_id=b["behavior_id"], clamps=clamps, command=cmd_event, background=True)
            trace["steps"].append("guardrail: " + "; ".join(clamps))

    if clips:
        writes.append(db.col("scenes").update_one({"_id": scene_id}, {"$push": {"timeline": {"$each": clips}}}))
        written.append({"collection": "scenes", "id": scene_id, "what": f"+{len(clips)} clip(s)"})
    await asyncio.gather(*writes)
    mark("saved")
    trace["timings_ms"] = timings
    trace["total_ms"] = round((time.time() - t0) * 1000)
    created = [st.split()[2] for st in trace["steps"] if st.startswith("created behavior")]
    report(decision["message"] + "\n" + "; ".join(f"{in_scene[c['actor']]['name']}: {c['behavior_id']} v{c['behavior_version']}"
                                                   for c in clips),
           {"behaviors": [c["behavior_id"] for c in clips], "created": created, "n_clips": len(clips)})
    return {"message": decision["message"], "clips": clips, "written": written, "trace": trace, "event_id": cmd_event}
