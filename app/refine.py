"""Refinement: propose a new behavior version, diff it, regression-replay it, and apply it with a chosen scope."""

import math

from app import db, dsl

END_TOLERANCE_PX = 12.0  # a clip must still end where the story needs it (continuity)


# ---------------------------------------------------------------- diff


def _flatten(obj, prefix="") -> dict[str, object]:
    out = {}
    if isinstance(obj, dict):
        if set(obj) == {"param"}:
            return {prefix: f"${obj['param']}"}
        for k, v in obj.items():
            if k == "type" and prefix:
                continue
            key = f"{prefix}.{k}" if prefix else k
            if isinstance(v, (dict, list)):
                out.update(_flatten(v, key))
            else:
                out[key] = v
        if "type" in obj:
            out[f"{prefix}.type" if prefix else "type"] = obj["type"]
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            label = v.get("type", i) if isinstance(v, dict) else i
            out.update(_flatten(v, f"{prefix}[{label}]"))
    return out


def diff(old: dict, new: dict) -> list[str]:
    """Readable lines like 'program.mods[hop].height: 20 → 35' and 'params.speed.default: 60 → 90'."""
    def view(b):
        return {"program": b["program"], "params": {p["name"]: {k: v for k, v in p.items() if k != "name"} for p in b["params"]}}

    a, b = _flatten(view(old)), _flatten(view(new))
    lines = []
    for k in sorted(set(a) | set(b)):
        if a.get(k) != b.get(k):
            if k not in a:
                lines.append(f"+ {k}: {b[k]}")
            elif k not in b:
                lines.append(f"− {k}: {a[k]}")
            else:
                lines.append(f"{k}: {a[k]} → {b[k]}")
    return lines


# ---------------------------------------------------------------- replay


def scaled_overrides(clip: dict, old_params: list[dict], new_params: list[dict]) -> dict[str, float]:
    """A refined default shifts each clip's own value by the same ratio ("faster" → every clip a bit faster)."""
    old = {p["name"]: p["default"] for p in old_params}
    out = {}
    for p in new_params:
        o, v = old.get(p["name"]), clip["params"].get(p["name"])
        if o not in (None, 0) and v is not None and p["default"] != o:
            out[p["name"]] = v * p["default"] / o
    return out


def replay_clip(clip: dict, behavior: dict, param_overrides: dict | None = None) -> dict:
    """Re-evaluate a stored clip with another behavior version, using the clip's own start state and path."""
    f0 = clip["frames"][0]
    start = {"x": f0[0], "y": f0[1], "rot": f0[2], "sx": f0[3], "sy": f0[4], "op": f0[5]}
    pts = [tuple(p) for p in clip["path"]["points"]] or None
    given = {k: v for k, v in clip["params"].items() if k in {p["name"] for p in behavior["params"]}}
    given.update(param_overrides or {})
    clamps: list[str] = []
    params = dsl.resolve_params(behavior["params"], given, clamps)
    ctx = dsl.Ctx(
        params=params,
        path_default=pts if clip["path"]["kind"] != "stroke" else None,
        path_stroke=pts if clip["path"]["kind"] == "stroke" else None,
        clamps=clamps,
    )
    out = dsl.run(behavior["program"], start, ctx)
    out["params"] = params
    return out


def compare(clip: dict, new: dict) -> dict:
    old_end, new_end = clip["end_state"], new["end_state"]
    end_dev = math.hypot(old_end["x"] - new_end["x"], old_end["y"] - new_end["y"])
    return {
        "end_deviation_px": round(end_dev, 1),
        "duration_before": round(clip["duration"], 2),
        "duration_after": round(new["duration"], 2),
        "pass": end_dev <= END_TOLERANCE_PX,
    }


def retime(timeline: list[dict]) -> list[dict]:
    """Keep clip order and grouping; recompute start times after durations changed (groups = same start)."""
    groups: dict[float, list[dict]] = {}
    for c in sorted(timeline, key=lambda c: c["start"]):
        groups.setdefault(round(c["start"], 4), []).append(c)
    cursor, out = 0.0, []
    for _, clips in sorted(groups.items()):
        for c in clips:
            c["start"] = cursor
            out.append(c)
        cursor += max(c["duration"] for c in clips)
    return out


# ---------------------------------------------------------------- propose / apply


class InvisibleMotion(ValueError):
    pass


def keep_param_refs(old: object, new: object, params: list[dict], fixes: list[str], path: str = "program") -> object:
    """Guardrail: if a refinement replaced a {"param": x} with a literal number, restore the parameter and move
    the number into x's default. A literal would silently erase every clip's own value."""
    if isinstance(old, dict) and set(old) == {"param"} and isinstance(new, (int, float)) and not isinstance(new, bool):
        spec = next((p for p in params if p["name"] == old["param"]), None)
        if spec:
            spec["default"] = new
            spec["min"], spec["max"] = min(spec["min"], new), max(spec["max"], new)
            fixes.append(f"{path}: kept ${old['param']} (default → {new:g}) instead of a fixed {new:g}")
            return {"param": old["param"]}
        return new
    if isinstance(old, dict) and isinstance(new, dict) and old.get("type") == new.get("type"):
        return {k: keep_param_refs(old.get(k), v, params, fixes, f"{path}.{k}") for k, v in new.items()}
    if isinstance(old, list) and isinstance(new, list) and len(old) == len(new):
        return [keep_param_refs(o, n, params, fixes, f"{path}[{i}]") for i, (o, n) in enumerate(zip(old, new))]
    return new


async def propose(project_id: str, scene_id: str, text: str, current: dict, refine: dict, command_event: str,
                  entities: dict[str, dict]) -> dict:
    fixes: list[str] = []
    refine["program"] = keep_param_refs(current["program"], refine["program"], refine["params"], fixes)
    # a changed default shifts each clip by the same ratio, so widen the range by that ratio too (no clamping)
    old_defaults = {p["name"]: p for p in current["params"]}
    for spec in refine["params"]:
        o = old_defaults.get(spec["name"])
        if o and o["default"] and spec["default"] != o["default"]:
            r = spec["default"] / o["default"]
            lo, hi = sorted((o["min"] * r, o["max"] * r))
            if hi > spec["max"] or lo < spec["min"]:
                spec["min"], spec["max"] = round(min(spec["min"], lo), 2), round(max(spec["max"], hi), 2)
                fixes.append(f"{spec['name']} range widened to [{spec['min']:g}, {spec['max']:g}] to keep each clip's own value")
    names = {p["name"] for p in refine["params"]}
    dsl.validate(refine["program"], names)
    # self-check: the candidate must still visibly do something (catches e.g. a 1° "spin")
    params = dsl.resolve_params(refine["params"], {}, [])
    probe_start = {"x": 100.0, "y": 300.0}
    probe = dsl.run(refine["program"], probe_start, dsl.Ctx(params=params, path_default=[(100.0, 300.0), (400.0, 300.0)]))
    vis = dsl.visible_change(probe, probe_start)
    if not vis["visible"]:
        raise InvisibleMotion(f"{current['behavior_id']} v{current['version'] + 1} would move {vis['move_px']} px, "
                              f"rotate {vis['rotate_deg']}°, scale {vis['scale']}, fade {vis['fade']}")
    candidate = {
        "behavior_id": current["behavior_id"], "version": current["version"] + 1, "parent_version": current["version"],
        "description": refine["description"] or current["description"], "type_path": current["type_path"],
        "params": refine["params"], "program": refine["program"],
    }
    lines = diff(current, candidate)

    # regression replay over every clip that uses this behavior, in every scene of the project
    checks = []
    async for sc in db.col("scenes").find({"project_id": project_id}).sort("order", 1):
        for c in sc.get("timeline", []):
            if c["behavior_id"] != current["behavior_id"]:
                continue
            res = compare(c, replay_clip(c, candidate, scaled_overrides(c, current["params"], candidate["params"])))
            ex = await db.col("examples").find_one({"_id": c.get("example_id")}, {"outcome": 1})
            checks.append({
                "scene_id": sc["_id"], "scene": sc["title"], "clip_id": c["clip_id"],
                "actor": entities.get(c["actor"], {}).get("name", "?"), "version": c["behavior_version"],
                "outcome": (ex or {}).get("outcome", "?"), **res,
            })
    proposal = {
        "_id": db.new_id("prop"), "project_id": project_id, "scene_id": scene_id, "status": "pending",
        "text": text, "behavior_id": current["behavior_id"], "from_version": current["version"],
        "candidate": candidate, "old_params": current["params"], "diff": lines, "change_summary": refine["change_summary"],
        "scope_guess": refine["scope_guess"], "scope_reason": refine["scope_reason"], "actor": refine["actor"],
        "checks": checks, "guardrail_fixes": fixes, "command_event": command_event, "created": db.now(),
    }
    await db.col("proposals").insert_one(proposal)
    return proposal


async def apply(proposal_id: str, scope: str) -> dict:
    p = await db.col("proposals").find_one({"_id": proposal_id, "status": "pending"})
    if not p:
        raise ValueError("proposal not found or already decided")
    project_id = p["project_id"]
    if scope == "cancel":
        await db.col("proposals").update_one({"_id": proposal_id}, {"$set": {"status": "cancelled"}})
        await db.log_event(project_id, "refine_cancelled", proposal_id=proposal_id, behavior_id=p["behavior_id"])
        return {"status": "cancelled", "upgraded": []}

    cand = p["candidate"]
    upgraded = []
    if scope == "behavior":
        tests = [d["_id"] async for d in db.col("examples").find(
            {"project_id": project_id, "behavior_id": p["behavior_id"], "outcome": "accepted"}, {"_id": 1})]
        doc = {
            "_id": db.new_id("beh"), "project_id": project_id, **cand,
            "reason": f"user: {p['text']!r}", "change_summary": p["change_summary"], "diff": p["diff"],
            "evidence": [p["command_event"]], "tests": tests, "regression": p["checks"],
            "stats": {"uses": 0, "accepted": 0, "corrected": 0}, "created": db.now(),
        }
        await db.col("behaviors").insert_one(doc)
        # propagate: upgrade clips whose regression check passed; keep failing ones pinned (user sees why)
        passed = {c["clip_id"] for c in p["checks"] if c["pass"]}
        targets = passed
    else:  # instance: only the latest clip of this behavior in the current scene
        sc = await db.col("scenes").find_one({"_id": p["scene_id"]})
        mine = [c for c in sc.get("timeline", []) if c["behavior_id"] == p["behavior_id"]]
        if not mine:
            raise ValueError(f"no {p['behavior_id']} clip in this scene to change; try 'everywhere' instead")
        targets = {max(mine, key=lambda c: c["start"])["clip_id"]}

    async for sc in db.col("scenes").find({"project_id": project_id}):
        changed = False
        for c in sc.get("timeline", []):
            if c["clip_id"] not in targets:
                continue
            new = replay_clip(c, cand, scaled_overrides(c, p.get("old_params", cand["params"]), cand["params"]))
            c.update(frames=new["frames"], events=new["events"], duration=new["duration"], end_state=new["end_state"],
                     params=new["params"])
            if scope == "behavior":
                c["behavior_version"] = cand["version"]
            else:
                c["override"] = {"from_proposal": proposal_id, "diff": p["diff"]}
            upgraded.append({"scene_id": sc["_id"], "scene": sc["title"], "clip_id": c["clip_id"]})
            changed = True
        if changed:
            await db.col("scenes").update_one({"_id": sc["_id"]}, {"$set": {"timeline": retime(sc["timeline"])}})

    from app.scenes import resolve_project
    await resolve_project(project_id)  # durations/ends changed: later scenes follow
    import raindrop.analytics as raindrop
    raindrop.track_signal(event_id=p["command_event"], name="refinement_applied", sentiment="POSITIVE",
                          properties={"behavior": p["behavior_id"], "scope": scope, "version": cand["version"] if scope == "behavior" else 0,
                                      "regression_pass": sum(c["pass"] for c in p["checks"]), "regression_total": len(p["checks"]),
                                      "clips_upgraded": len(upgraded), "diff": "; ".join(p["diff"])})
    await db.col("proposals").update_one({"_id": proposal_id}, {"$set": {"status": f"applied:{scope}"}})
    await db.log_event(project_id, "refine_applied", proposal_id=proposal_id, behavior_id=p["behavior_id"], scope=scope,
                       version=cand["version"] if scope == "behavior" else None, n_upgraded=len(upgraded),
                       n_kept=len(p["checks"]) - len(upgraded) if scope == "behavior" else None)
    return {"status": f"applied:{scope}", "upgraded": upgraded, "version": cand["version"] if scope == "behavior" else None}
