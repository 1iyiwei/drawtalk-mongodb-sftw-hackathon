"""The harness: turns a command (text and/or stroke) into versioned behaviors, clips, examples and events."""

import math
import re
import time

from app import db, dsl, geometry, llm

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
situation. If characters move differently by nature (a hare dashes with hops, a tortoise plods with a slight
bob), give each its own style behavior. Make motions lively with modifiers (hop, bob, breathe, face_motion)
where they fit the character. Name behaviors after the style (e.g. "dash", "plod"), not the actor.

Motion program (JSON, every node has "type"):
- move_along {path: "default"|"stroke"|"arc", speed px/s OR duration s (other null), arc_height (arc only), easing}
  "default" = straight to the target (stops on contact); "stroke" = the user's drawn path; "arc" = jump-like.
- stay {duration}; wait {duration}; turn_to {angle deg, duration, easing}; scale_to {sx, sy, duration, easing};
  fade_to {opacity, duration}
- seq {steps}; par {steps}; layer {base, mods}
- mods: hop {height px, every_px, squash 0..0.4}, bob {amplitude px, period s}, breathe {amount 0..0.2, period s},
  face_motion {}, emit {glyph, every s, rise px, fade s}
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
path: "stroke" only if a stroke was drawn for this actor; "default" when moving to a target OR in a direction;
"none" for in-place motions.
direction: when there is no target character but the text gives a direction ("moves right", "jumps up"), set
left/right/up/down and distance_px (default ~250, "a little" ~100, "far"/"across" ~600); otherwise "none" and null.
timing: "together" if the actions happen at the same time ("race", "both", "while", "meanwhile", "together"),
"in_order" if one after another ("then", "after").
message: one short sentence describing what will happen, for the user."""


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
            "actions": {"type": "array", "items": action},
            "timing": {"type": "string", "enum": ["together", "in_order"]},
            "message": {"type": "string"},
        },
        "required": ["actions", "timing", "message"],
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
        lines.append(f"- behavior_id={b['behavior_id']} (version {b['version']}): {b['description']} | params: {ps or 'none'}")
    return "\n".join(lines)


# ---------------------------------------------------------------- command


async def run_command(project_id: str, scene_id: str, text: str, stroke: list | None) -> dict:
    t0 = time.time()
    scene = await db.col("scenes").find_one({"_id": scene_id, "project_id": project_id})
    if not scene:
        raise ValueError("scene not found")
    entities = {e["_id"]: e async for e in db.col("entities").find({"project_id": project_id})}
    states = current_states(scene)
    in_scene = {eid: e for eid, e in entities.items() if eid in states}
    by_name = {e["name"]: eid for eid, e in in_scene.items()}
    behaviors = await latest_behaviors(project_id)

    summary = stroke_summary(stroke, in_scene, states) if stroke and len(stroke) > 1 else None
    chars = "\n".join(
        f"- {e['name']}: at ({states[eid]['x']:.0f},{states[eid]['y']:.0f}), size {e['bbox'][2]-e['bbox'][0]:.0f}x{e['bbox'][3]-e['bbox'][1]:.0f}"
        + (f", traits: {', '.join(e.get('traits', []))}" if e.get("traits") else "")
        for eid, e in in_scene.items()
    )
    user = (
        f"Characters in the scene:\n{chars or '(none)'}\n\nBehavior catalog:\n{catalog_text(behaviors)}\n\n"
        f"Command text: {text!r}\n"
        f"Stroke: {summary if summary else 'none'}"
    )
    decision, meta = llm.structured(SYSTEM, user, "motion_decision", decision_schema(list(by_name)))
    cmd_event = await db.log_event(
        project_id, "command", scene_id=scene_id, text=text, has_stroke=bool(summary), route="llm", llm=meta,
        n_actions=len(decision["actions"]),
    )

    clips, written, trace = [], [], {"llm": meta, "stroke": summary, "decision": decision, "steps": []}
    prev_start = None
    cursor = scene_end_time(scene)
    for a in decision["actions"]:
        actor_id = by_name.get(a["actor"])
        if not actor_id:
            trace["steps"].append(f"skipped: unknown actor {a['actor']!r}")
            continue
        actor = in_scene[actor_id]

        # behavior: apply an existing one or create v1
        a["behavior_id"] = normalize_id(a["behavior_id"])
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
        path_stroke = geometry.stroke_path(start, [(p[0], p[1]) for p in stroke]) if stroke and a["path"] == "stroke" else None

        ctx = dsl.Ctx(params=params, path_default=path_default, path_stroke=path_stroke, clamps=clamps)
        result = dsl.run(b["program"], start, ctx)

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
        }
        clips.append(clip)
        cursor = max(cursor, clip_start + result["duration"])
        states[actor_id] = result["end_state"]

        await db.col("examples").insert_one({
            "_id": example_id, "project_id": project_id, "scene_id": scene_id, "clip_id": clip["clip_id"],
            "text": text, "stroke": summary, "actor_name": actor["name"],
            "target_name": in_scene[target_id]["name"] if target_id else None,
            "behavior_id": b["behavior_id"], "behavior_version": b["version"], "params": params,
            "param_sources": sources, "outcome": "pending", "route": "llm", "command_event": cmd_event,
            "created": db.now(),
        })
        written.append({"collection": "examples", "id": example_id, "what": f"{actor['name']} → {b['behavior_id']}"})
        await db.col("behaviors").update_one({"_id": b["_id"]}, {"$inc": {"stats.uses": 1}})

        new_traits = [t for t in a["actor_traits"] if t not in actor.get("traits", [])]
        if new_traits:
            await db.col("entities").update_one({"_id": actor_id}, {"$addToSet": {"traits": {"$each": new_traits}}})
            actor.setdefault("traits", []).extend(new_traits)
            written.append({"collection": "entities", "id": actor_id, "what": f"{actor['name']} traits += {', '.join(new_traits)}"})
        if clamps:
            await db.log_event(project_id, "clamp", behavior_id=b["behavior_id"], clamps=clamps, command=cmd_event)
            trace["steps"].append("guardrail: " + "; ".join(clamps))

    if clips:
        await db.col("scenes").update_one({"_id": scene_id}, {"$push": {"timeline": {"$each": clips}}})
        written.append({"collection": "scenes", "id": scene_id, "what": f"+{len(clips)} clip(s)"})
    trace["total_ms"] = round((time.time() - t0) * 1000)
    return {"message": decision["message"], "clips": clips, "written": written, "trace": trace, "event_id": cmd_event}
