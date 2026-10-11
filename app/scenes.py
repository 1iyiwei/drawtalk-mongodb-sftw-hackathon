"""Scene continuity: a scene starts where the previous one ends (plus its own additions/removals).

Starts are *derived*, not copied: when an earlier scene changes, later scenes are re-simulated from their new
start, clip by clip, with each clip's pinned behavior version and parameters. This keeps a long story
coherent as it is edited.
"""

import math

from app import db, dsl, geometry
from app.refine import retime

DEFAULT_STATE = {"rot": 0.0, "sx": 1.0, "sy": 1.0, "op": 1.0}


def end_states(start: dict, timeline: list[dict]) -> dict:
    states = {k: dict(v) for k, v in start.items()}
    for c in sorted(timeline, key=lambda c: c["start"] + c["duration"]):
        if c["actor"] in states:
            states[c["actor"]] = c["end_state"]
    return states


def _migrate(scene: dict, prev_end: dict | None) -> None:
    """Old scenes stored a copied start_state; split it into own additions."""
    if "added" in scene:
        return
    own = scene.get("start_state", {})
    scene["added"] = dict(own) if prev_end is None else {k: v for k, v in own.items() if k not in prev_end}
    scene["removed"] = []


def _same(a: dict, b: dict) -> bool:
    if set(a) != set(b):
        return False
    return all(math.hypot(a[k]["x"] - b[k]["x"], a[k]["y"] - b[k]["y"]) < 0.5
               and abs(a[k].get("rot", 0) - b[k].get("rot", 0)) < 0.5 for k in a)


def resimulate(timeline: list[dict], start: dict, entities: dict, behaviors: dict) -> list[dict]:
    """Re-run every clip from `start`, in time order. Clips of characters not in the scene are dropped."""
    states = {k: {**DEFAULT_STATE, **v} for k, v in start.items()}
    out = []
    for c in sorted(timeline, key=lambda c: c["start"]):
        if c["actor"] not in states:
            continue
        b = behaviors.get((c["behavior_id"], c["behavior_version"]))
        actor = entities.get(c["actor"])
        if not b or not actor:
            out.append(c)
            continue
        s = states[c["actor"]]
        pts = [tuple(p) for p in c["path"]["points"]]
        kind = c["path"]["kind"]
        path_default = path_stroke = None
        if kind == "stroke" and pts:
            path_stroke = geometry.stroke_path(s, pts)
        elif c.get("target") and c["target"] in states and c["target"] in entities:
            path_default = geometry.default_path(s, actor, geometry.entity_world_bbox(entities[c["target"]], states[c["target"]]))
        elif len(pts) > 1:  # a direction move: keep the same displacement, clamped to the canvas
            dx, dy = pts[-1][0] - pts[0][0], pts[-1][1] - pts[0][1]
            x0, y0, x1, y1 = actor["bbox"]
            ex = min(max(s["x"] + dx, geometry.CANVAS[0] - x0), geometry.CANVAS[2] - x1)
            ey = min(max(s["y"] + dy, geometry.CANVAS[1] - y0), geometry.CANVAS[3] - y1)
            path_default = [(s["x"], s["y"]), (ex, ey)]
        ctx = dsl.Ctx(params=c["params"], path_default=path_default, path_stroke=path_stroke)
        r = dsl.run(b["program"], s, ctx)
        c = {**c, "frames": r["frames"], "events": r["events"], "duration": r["duration"], "end_state": r["end_state"],
             "path": {"kind": kind, "points": [list(p) for p in (path_stroke or path_default or [])]}}
        states[c["actor"]] = r["end_state"]
        out.append(c)
    return retime(out)


async def resolve_project(project_id: str, dirty: set[str] | None = None) -> list[dict]:
    """Recompute every scene's start from the previous scene's end; re-simulate scenes whose start changed
    (or that are marked dirty). Persists changes and returns the scenes in order."""
    dirty = dirty or set()
    scenes = [s async for s in db.col("scenes").find({"project_id": project_id}).sort("order", 1)]
    entities = {e["_id"]: e async for e in db.col("entities").find({"project_id": project_id})}
    behaviors = None
    prev_end = None
    for sc in scenes:
        _migrate(sc, prev_end)
        base = dict(prev_end or {})
        start = {**base, **sc["added"]}
        for r in sc.get("removed", []):
            start.pop(r, None)
        start = {k: {**DEFAULT_STATE, **v} for k, v in start.items() if k in entities}
        changed = not _same(start, {k: {**DEFAULT_STATE, **v} for k, v in sc.get("start_state", {}).items()})
        if changed or sc["_id"] in dirty:
            if behaviors is None:
                behaviors = {(b["behavior_id"], b["version"]): b
                             async for b in db.col("behaviors").find({"project_id": project_id})}
            sc["timeline"] = resimulate(sc.get("timeline", []), start, entities, behaviors)
            sc["start_state"] = start
            await db.col("scenes").update_one({"_id": sc["_id"]}, {"$set": {
                "start_state": start, "timeline": sc["timeline"], "added": sc["added"], "removed": sc.get("removed", [])}})
            if changed:
                await db.log_event(project_id, "scene_resimulated", scene_id=sc["_id"], n_clips=len(sc["timeline"]),
                                   background=True)
        prev_end = end_states(start, sc["timeline"])
    return scenes
