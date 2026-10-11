"""Motion DSL: JSON schema (for LLM structured output) and the reference evaluator (program → keyframes).

Nodes are tagged with "type". Numeric fields take a number or {"param": "<name>"}.
Frames are sampled at FPS; each frame is [x, y, rot_deg, sx, sy, opacity].
"""

import math
from dataclasses import dataclass, field

FPS = 30
MAX_CLIP_SECONDS = 20.0
MAX_DEPTH = 5
EASINGS = ["linear", "easeIn", "easeOut", "easeInOut"]
PATHS = ["default", "stroke", "arc", "none"]

# ---------------------------------------------------------------- schema

_VAL = {"$ref": "#/$defs/val"}
_OPT_VAL = {"anyOf": [_VAL, {"type": "null"}]}


def _obj(type_name: str, props: dict) -> dict:
    props = {"type": {"type": "string", "enum": [type_name]}, **props}
    return {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}


NODE_TYPES = {
    "seq": {"steps": {"type": "array", "items": {"$ref": "#/$defs/node"}}},
    "par": {"steps": {"type": "array", "items": {"$ref": "#/$defs/node"}}},
    "layer": {"base": {"$ref": "#/$defs/node"}, "mods": {"type": "array", "items": {"$ref": "#/$defs/mod"}}},
    "wait": {"duration": _VAL},
    "move_along": {
        "path": {"type": "string", "enum": PATHS[:3]},
        "speed": _OPT_VAL,
        "duration": _OPT_VAL,
        "arc_height": _OPT_VAL,
        "easing": {"type": "string", "enum": EASINGS},
    },
    "stay": {"duration": _VAL},
    "turn_to": {"angle": _VAL, "duration": _VAL, "easing": {"type": "string", "enum": EASINGS}},
    "scale_to": {"sx": _VAL, "sy": _VAL, "duration": _VAL, "easing": {"type": "string", "enum": EASINGS}},
    "fade_to": {"opacity": _VAL, "duration": _VAL},
}
MOD_TYPES = {
    "hop": {"height": _VAL, "every_px": _VAL, "squash": _VAL},
    "bob": {"amplitude": _VAL, "period": _VAL},
    "breathe": {"amount": _VAL, "period": _VAL},
    "face_motion": {},
    "emit": {"glyph": {"type": "string"}, "every": _VAL, "rise": _VAL, "fade": _VAL},
}

SCHEMA_DEFS = {
    "val": {
        "anyOf": [
            {"type": "number"},
            {"type": "object", "properties": {"param": {"type": "string"}}, "required": ["param"], "additionalProperties": False},
        ]
    },
    "node": {"anyOf": [_obj(t, p) for t, p in NODE_TYPES.items()]},
    "mod": {"anyOf": [_obj(t, p) for t, p in MOD_TYPES.items()]},
}

PARAM_SPEC_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "unit": {"type": "string"},
        "default": {"type": "number"},
        "min": {"type": "number"},
        "max": {"type": "number"},
        "cues": {"type": "array", "items": {"type": "string", "enum": ["text", "trait", "stroke_speed"]}},
    },
    "required": ["name", "unit", "default", "min", "max", "cues"],
    "additionalProperties": False,
}

# ---------------------------------------------------------------- validation


class DSLError(ValueError):
    pass


def validate(program: dict, param_names: set[str], depth: int = 0) -> None:
    """Structural checks beyond the schema: known types, depth, parameter references."""
    if depth > MAX_DEPTH:
        raise DSLError("program nested too deeply")
    t = program.get("type")
    if t not in NODE_TYPES:
        raise DSLError(f"unknown node type {t!r}")
    _check_vals(program, param_names)
    if t in ("seq", "par"):
        if not program["steps"]:
            raise DSLError(f"{t} has no steps")
        for s in program["steps"]:
            validate(s, param_names, depth + 1)
    elif t == "layer":
        validate(program["base"], param_names, depth + 1)
        for m in program["mods"]:
            if m.get("type") not in MOD_TYPES:
                raise DSLError(f"unknown modifier {m.get('type')!r}")
            _check_vals(m, param_names)


def _check_vals(obj: dict, param_names: set[str]):
    for k, v in obj.items():
        if isinstance(v, dict) and set(v) == {"param"} and v["param"] not in param_names:
            raise DSLError(f"{obj['type']}.{k} references unknown param {v['param']!r}")


# ---------------------------------------------------------------- evaluation


@dataclass
class Ctx:
    params: dict[str, float]
    path_default: list[tuple[float, float]] | None = None  # straight line to target
    path_stroke: list[tuple[float, float]] | None = None
    clamps: list[str] = field(default_factory=list)


def val(v, ctx: Ctx, fallback: float = 0.0) -> float:
    if v is None:
        return fallback
    if isinstance(v, dict):
        return float(ctx.params.get(v["param"], fallback))
    return float(v)


def ease(name: str, u: float) -> float:
    u = max(0.0, min(1.0, u))
    if name == "easeIn":
        return u * u
    if name == "easeOut":
        return 1 - (1 - u) ** 2
    if name == "easeInOut":
        return 3 * u * u - 2 * u * u * u
    return u


def _n_frames(duration: float) -> int:
    return max(1, round(duration * FPS))


def evaluate(node: dict, state: list[float], ctx: Ctx) -> tuple[list[list[float]], list[dict]]:
    """Return (frames, events). frames[0] is the start state; consecutive frames are 1/FPS apart."""
    from app import geometry as g

    t = node["type"]
    if t == "seq":
        frames, events = [list(state)], []
        for step in node["steps"]:
            f, e = evaluate(step, frames[-1], ctx)
            offset = (len(frames) - 1) / FPS
            frames += f[1:]
            events += [{**ev, "t": ev["t"] + offset} for ev in e]
        return frames, events
    if t == "par":
        outs = [evaluate(s, state, ctx) for s in node["steps"]]
        n = max(len(f) for f, _ in outs)
        frames = []
        for i in range(n):
            fr = list(state)
            for f, _ in outs:
                cur = f[min(i, len(f) - 1)]
                for c in range(6):  # combine as deltas from the shared start (scale/opacity multiplicative)
                    if c in (3, 4, 5):
                        fr[c] *= cur[c] / state[c] if state[c] else 1
                    else:
                        fr[c] += cur[c] - state[c]
            frames.append(fr)
        return frames, [e for _, es in outs for e in es]
    if t == "layer":
        frames, events = evaluate(node["base"], state, ctx)
        for m in node["mods"]:
            frames, events = _apply_mod(m, frames, events, ctx)
        return frames, events
    if t in ("wait", "stay"):
        n = _n_frames(val(node["duration"], ctx, 1.0))
        return [list(state) for _ in range(n + 1)], []
    if t == "move_along":
        if node["path"] == "stroke" and ctx.path_stroke:
            pts = ctx.path_stroke
        else:
            pts = ctx.path_default or [(state[0], state[1]), (state[0], state[1])]
            if node["path"] == "arc":
                pts = g.arc_path(pts, val(node["arc_height"], ctx, 60.0))
        # anchor the path at the current position (a seq may have moved the actor)
        dx, dy = state[0] - pts[0][0], state[1] - pts[0][1]
        pts = [(x + dx, y + dy) for x, y in pts]
        length = g.polyline_length(pts)
        if node["duration"] is not None:
            duration = val(node["duration"], ctx, 1.0)
        else:
            speed = max(1.0, val(node["speed"], ctx, 150.0))
            duration = length / speed if length > 0 else 0.2
        n = _n_frames(duration)
        frames = []
        for i in range(n + 1):
            x, y = g.point_at(pts, ease(node["easing"], i / n))
            frames.append([x, y, *state[2:]])
        return frames, []
    if t in ("turn_to", "scale_to", "fade_to"):
        n = _n_frames(val(node["duration"], ctx, 0.5))
        easing = node.get("easing", "easeInOut")
        end = list(state)
        if t == "turn_to":
            end[2] = val(node["angle"], ctx)
        elif t == "scale_to":
            sign = -1 if state[3] < 0 else 1
            end[3], end[4] = sign * val(node["sx"], ctx, 1), val(node["sy"], ctx, 1)
        else:
            end[5] = val(node["opacity"], ctx, 1)
        frames = []
        for i in range(n + 1):
            u = ease(easing, i / n)
            frames.append([a + (b - a) * u for a, b in zip(state, end)])
        return frames, []
    raise DSLError(f"unknown node type {t!r}")


def _apply_mod(m: dict, frames, events, ctx: Ctx):
    t = m["type"]
    out = [list(f) for f in frames]
    if t == "hop":
        height, every, squash = val(m["height"], ctx, 30), max(5.0, val(m["every_px"], ctx, 60)), val(m["squash"], ctx, 0.15)
        dist = 0.0
        for i in range(len(out)):
            if i:
                dist += math.dist(frames[i][:2], frames[i - 1][:2])
            s = abs(math.sin(math.pi * dist / every))
            out[i][1] -= height * s
            near_ground = max(0.0, 1 - 4 * s) if dist > 0 else 0.0
            out[i][3] *= 1 + squash * near_ground
            out[i][4] *= 1 - squash * near_ground
    elif t == "bob":
        amp, period = val(m["amplitude"], ctx, 3), max(0.05, val(m["period"], ctx, 0.8))
        for i in range(len(out)):
            out[i][1] += amp * math.sin(2 * math.pi * (i / FPS) / period)
    elif t == "breathe":
        amount, period = val(m["amount"], ctx, 0.04), max(0.05, val(m["period"], ctx, 1.6))
        for i in range(len(out)):
            k = 1 + amount * math.sin(2 * math.pi * (i / FPS) / period)
            out[i][3] *= k
            out[i][4] *= k
    elif t == "face_motion":
        facing = -1 if frames[0][3] < 0 else 1
        for i in range(len(out)):
            if i:
                vx = frames[i][0] - frames[i - 1][0]
                if abs(vx) > 0.3:
                    facing = -1 if vx < 0 else 1
            out[i][3] = abs(out[i][3]) * facing
    elif t == "emit":
        every, rise, fade = max(0.2, val(m["every"], ctx, 0.8)), val(m["rise"], ctx, 40), val(m["fade"], ctx, 1.2)
        duration = (len(frames) - 1) / FPS
        k = 0
        while k * every < duration and k < 50:
            f = frames[min(len(frames) - 1, round(k * every * FPS))]
            events = events + [{"t": k * every, "glyph": m["glyph"][:3], "x": f[0], "y": f[1], "rise": rise, "fade": fade}]
            k += 1
    return out, events


def run(program: dict, start: dict, ctx: Ctx) -> dict:
    """Evaluate a behavior program for one actor. Returns frames, events, duration and end state."""
    s = [start["x"], start["y"], start.get("rot", 0.0), start.get("sx", 1.0), start.get("sy", 1.0), start.get("op", 1.0)]
    frames, events = evaluate(program, s, ctx)
    max_frames = int(MAX_CLIP_SECONDS * FPS) + 1
    if len(frames) > max_frames:
        ctx.clamps.append(f"clip truncated to {MAX_CLIP_SECONDS:.0f} s")
        frames = frames[:max_frames]
        events = [e for e in events if e["t"] <= MAX_CLIP_SECONDS]
    end = frames[-1]
    return {
        "frames": [[round(v, 2) for v in f] for f in frames],
        "events": events,
        "duration": (len(frames) - 1) / FPS,
        "end_state": {"x": end[0], "y": end[1], "rot": end[2], "sx": end[3], "sy": end[4], "op": end[5]},
    }


def resolve_params(specs: list[dict], given: dict[str, float], ctx_clamps: list[str]) -> dict[str, float]:
    """Defaults for missing values; clamp to declared ranges (and record clamps)."""
    out = {}
    for s in specs:
        v = given.get(s["name"], s["default"])
        lo, hi = min(s["min"], s["max"]), max(s["min"], s["max"])
        if not lo <= v <= hi:
            ctx_clamps.append(f"{s['name']} {v:g} clamped to [{lo:g}, {hi:g}]")
            v = max(lo, min(hi, v))
        out[s["name"]] = v
    return out
