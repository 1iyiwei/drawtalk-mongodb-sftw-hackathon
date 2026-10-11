"""FastAPI app: serves the static front end and the JSON API."""

import os
from contextlib import asynccontextmanager

import raindrop.analytics as raindrop

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app import db, geometry, harness, memory, refine, scenes as scene_logic


@asynccontextmanager
async def lifespan(_app):
    await db.ensure_indexes()
    await memory.ensure_vector_index()
    raindrop.init(os.getenv("RAINDROP_WRITE_KEY"))
    raindrop.set_debug_logs(os.getenv("RAINDROP_DEBUG") == "1")
    yield
    raindrop.flush()
    raindrop.shutdown()


app = FastAPI(title="DrawTalk Harness", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def index():
    return FileResponse("static/index.html")


def _clean(doc: dict) -> dict:
    return {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in doc.items()}


async def _project(name: str) -> dict:
    p = await db.col("projects").find_one({"name": name})
    if not p:
        p = {"_id": db.new_id("prj"), "name": name, "created": db.now()}
        await db.col("projects").insert_one(p)
        await db.col("scenes").insert_one(
            {"_id": db.new_id("scn"), "project_id": p["_id"], "order": 0, "title": "Scene 1", "start_state": {},
             "added": {}, "removed": [], "timeline": []}
        )
        await db.log_event(p["_id"], "project_created")
    return p


@app.get("/api/state")
async def state(project: str = "rehearsal"):
    p = await _project(project)
    pid = p["_id"]
    scenes = await scene_logic.resolve_project(pid)
    entities = [_clean(e) async for e in db.col("entities").find({"project_id": pid})]
    behaviors = [_clean(b) for b in (await harness.latest_behaviors(pid)).values()]
    return {"project": _clean(p), "scenes": scenes, "entities": entities, "behaviors": behaviors}


class EntityIn(BaseModel):
    project_id: str
    scene_id: str
    name: str
    strokes: list[list[list[float]]]  # world coords: strokes → points → [x, y, t]


@app.post("/api/entities")
async def create_entity(body: EntityIn):
    pts = [(p[0], p[1]) for s in body.strokes for p in s]
    if not pts:
        raise HTTPException(400, "no strokes")
    x0, y0, x1, y1 = geometry.bbox(pts)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    name = body.name.strip().lower()
    eid = db.new_id("ent")
    ent = {
        "_id": eid, "project_id": body.project_id, "name": name,
        "strokes": [[[round(p[0] - cx, 1), round(p[1] - cy, 1)] for p in s] for s in body.strokes],
        "bbox": [x0 - cx, y0 - cy, x1 - cx, y1 - cy], "traits": [], "created": db.now(),
    }
    await db.col("entities").insert_one(ent)
    await scene_logic.resolve_project(body.project_id)  # make sure `added` exists (migrates old scenes)
    await db.col("scenes").update_one(
        {"_id": body.scene_id}, {"$set": {f"added.{eid}": {"x": cx, "y": cy, **harness.DEFAULT_STATE}}}
    )
    await scene_logic.resolve_project(body.project_id)
    await db.log_event(body.project_id, "entity_created", entity_id=eid, n_strokes=len(body.strokes), background=True)
    return {"entity": _clean(ent), "state": {"x": cx, "y": cy, **harness.DEFAULT_STATE}}


class CommandIn(BaseModel):
    project_id: str
    scene_id: str
    text: str = ""
    stroke: list[list[float]] | None = None
    gesture: list[list[float]] | None = None


@app.post("/api/command")
async def command(body: CommandIn):
    if not body.text.strip() and not body.stroke and not body.gesture:
        raise HTTPException(400, "empty command")
    try:
        res = await harness.run_command(body.project_id, body.scene_id, body.text.strip(), body.stroke, body.gesture)
        if res["clips"]:
            await scene_logic.resolve_project(body.project_id)  # later scenes start where this one now ends
        return res
    except ValueError as e:
        raise HTTPException(404, str(e))


class SceneIn(BaseModel):
    project_id: str


@app.post("/api/scenes")
async def new_scene(body: SceneIn):
    """New scene continues from the previous scene's end state (continuity default)."""
    last = await db.col("scenes").find_one({"project_id": body.project_id}, sort=[("order", -1)])
    order = (last["order"] + 1) if last else 0
    scene = {"_id": db.new_id("scn"), "project_id": body.project_id, "order": order, "title": f"Scene {order + 1}",
             "start_state": {}, "added": {}, "removed": [], "timeline": [], "continued_from": last["_id"] if last else None}
    await db.col("scenes").insert_one(scene)
    resolved = await scene_logic.resolve_project(body.project_id)
    scene = next(s for s in resolved if s["_id"] == scene["_id"])
    await db.log_event(body.project_id, "scene_created", scene_id=scene["_id"], n_carried=len(scene["start_state"]),
                       background=True)
    return scene


class ClipDeleteIn(BaseModel):
    project_id: str
    scene_id: str
    clip_id: str


@app.post("/api/clips/delete")
async def delete_clip(body: ClipDeleteIn):
    """Remove a clip. Its example is marked 'undone' (a negative signal for the harness)."""
    scene = await db.col("scenes").find_one({"_id": body.scene_id, "project_id": body.project_id})
    clip = next((c for c in (scene or {}).get("timeline", []) if c["clip_id"] == body.clip_id), None)
    if not clip:
        raise HTTPException(404, "clip not found")
    await db.col("scenes").update_one({"_id": body.scene_id}, {"$pull": {"timeline": {"clip_id": body.clip_id}}})
    await db.col("examples").update_one({"_id": clip["example_id"]}, {"$set": {"outcome": "undone"}})
    await db.col("behaviors").update_one(
        {"project_id": body.project_id, "behavior_id": clip["behavior_id"], "version": clip["behavior_version"]},
        {"$inc": {"stats.corrected": 1}},
    )
    await db.log_event(body.project_id, "clip_deleted", scene_id=body.scene_id, clip_id=body.clip_id,
                       behavior_id=clip["behavior_id"], example_id=clip["example_id"])
    ex = await db.col("examples").find_one({"_id": clip["example_id"]}, {"command_event": 1})
    if ex and ex.get("command_event"):
        raindrop.track_signal(event_id=ex["command_event"], name="clip_undone", sentiment="NEGATIVE",
                              properties={"behavior": clip["behavior_id"], "version": clip["behavior_version"],
                                          "route": clip.get("route") or "llm"})
    if clip.get("route") == "fast":
        await memory.penalize_fast_guess(body.project_id, clip["example_id"], clip["behavior_id"])
    await scene_logic.resolve_project(body.project_id, dirty={body.scene_id})
    return {"ok": True}


class SceneOpIn(BaseModel):
    project_id: str
    scene_id: str
    entity_id: str | None = None


@app.post("/api/scenes/clear")
async def clear_scene(body: SceneOpIn):
    """Remove all clips from a scene (characters stay where the scene starts)."""
    r = await db.col("scenes").update_one({"_id": body.scene_id, "project_id": body.project_id}, {"$set": {"timeline": []}})
    if not r.matched_count:
        raise HTTPException(404, "scene not found")
    await db.log_event(body.project_id, "scene_cleared", scene_id=body.scene_id, background=True)
    await scene_logic.resolve_project(body.project_id, dirty={body.scene_id})
    return {"ok": True}


@app.post("/api/scenes/remove-entity")
async def remove_entity(body: SceneOpIn):
    """Take a character out of a scene, with the clips that move it. The entity doc is kept (history)."""
    await scene_logic.resolve_project(body.project_id)
    sc = await db.col("scenes").find_one({"_id": body.scene_id, "project_id": body.project_id})
    if not sc:
        raise HTTPException(404, "scene not found")
    update = {"$pull": {"timeline": {"actor": body.entity_id}}}
    if body.entity_id in sc.get("added", {}):
        update["$unset"] = {f"added.{body.entity_id}": ""}  # introduced here: un-introduce it
    else:
        update["$addToSet"] = {"removed": body.entity_id}  # carried in from earlier: remove from here on
    await db.col("scenes").update_one({"_id": body.scene_id}, update)
    await scene_logic.resolve_project(body.project_id, dirty={body.scene_id})
    await db.log_event(body.project_id, "entity_removed", scene_id=body.scene_id, entity_id=body.entity_id, background=True)
    return {"ok": True}


class EraseIn(BaseModel):
    project_id: str
    entity_id: str
    stroke_indices: list[int]


@app.post("/api/entities/erase-strokes")
async def erase_strokes(body: EraseIn):
    """Delete some strokes of a character (all scenes share it). The pivot stays; the bbox is recomputed."""
    ent = await db.col("entities").find_one({"_id": body.entity_id, "project_id": body.project_id})
    if not ent:
        raise HTTPException(404, "entity not found")
    drop = set(body.stroke_indices)
    keep = [s for i, s in enumerate(ent["strokes"]) if i not in drop]
    if not keep:
        raise HTTPException(400, "would erase every stroke; remove the character instead")
    x0, y0, x1, y1 = geometry.bbox([(p[0], p[1]) for s in keep for p in s])
    await db.col("entities").update_one({"_id": body.entity_id}, {"$set": {"strokes": keep, "bbox": [x0, y0, x1, y1]}})
    await db.log_event(body.project_id, "strokes_erased", entity_id=body.entity_id, n_erased=len(drop), n_left=len(keep))
    return {"strokes": keep, "bbox": [x0, y0, x1, y1]}


class RefineIn(BaseModel):
    proposal_id: str
    scope: str  # behavior | instance | cancel


@app.post("/api/refine/confirm")
async def refine_confirm(body: RefineIn):
    if body.scope not in ("behavior", "instance", "cancel"):
        raise HTTPException(400, "bad scope")
    try:
        return await refine.apply(body.proposal_id, body.scope)
    except ValueError as e:
        raise HTTPException(404, str(e))


@app.get("/api/config")
async def config(project_id: str):
    cur = await memory.get_config(project_id)
    history = [ _clean(d) async for d in db.col("harness_config").find({"project_id": project_id}).sort("version", 1)]
    return {"current": _clean(cur) if "_id" in cur else cur, "history": history}


@app.get("/api/metrics")
async def metrics(project_id: str, window: int = 5):
    """Learning curve from hard signals: per command, did it need the LLM, and was its result undone?"""
    cmds = [e async for e in db.col("events").find({"project_id": project_id, "type": "command"}).sort("ts", 1)]
    outcomes: dict[str, list[str]] = {}
    async for ex in db.col("examples").find({"project_id": project_id}, {"command_event": 1, "outcome": 1}):
        outcomes.setdefault(ex.get("command_event"), []).append(ex["outcome"])
    points = []
    for i, c in enumerate(cmds):
        lo = max(0, i - window + 1)
        win = cmds[lo:i + 1]
        outs = [o for w in win for o in outcomes.get(w["_id"], [])]
        points.append({
            "i": i + 1, "text": c.get("text") or ("(gesture/path)" if c.get("has_stroke") else ""),
            "route": c.get("route"), "intent": c.get("intent"), "latency_ms": c.get("latency_ms"),
            "llm_share": sum(w.get("route") == "llm" for w in win) / len(win),
            "correction_share": (sum(o == "undone" for o in outs) / len(outs)) if outs else 0.0,
        })
    history = []
    async for b in db.col("behaviors").find({"project_id": project_id}, {"behavior_id": 1, "version": 1, "reason": 1,
                                                                          "change_summary": 1, "created": 1}):
        history.append({"ts": b["created"], "kind": "behavior", "what": f"{b['behavior_id']} v{b['version']}",
                        "why": b.get("change_summary") or b.get("reason")})
    async for c in db.col("harness_config").find({"project_id": project_id}):
        history.append({"ts": c["created"], "kind": "routing", "what": f"routing v{c['version']} (threshold {c['fast_path']['min_score']})",
                        "why": c.get("reason")})
    history.sort(key=lambda h: h["ts"], reverse=True)
    lat = [p["latency_ms"] for p in points if p["latency_ms"] is not None]
    return {
        "points": points, "window": window,
        "history": [{**h, "ts": h["ts"].isoformat()} for h in history[:30]],
        "summary": {
            "commands": len(points),
            "no_llm": sum(p["route"] in ("fast", "ask") for p in points),
            "latency_first": round(sum(lat[:5]) / len(lat[:5])) if lat else None,
            "latency_last": round(sum(lat[-5:]) / len(lat[-5:])) if lat else None,
            "behaviors": len({h["what"].split(" v")[0] for h in history if h["kind"] == "behavior"}),
            "versions": sum(h["kind"] == "behavior" for h in history),
        },
    }


class TimingIn(BaseModel):
    project_id: str
    scene_id: str
    clip_id: str
    mode: str  # "with_previous" | "after_previous"


@app.post("/api/clips/timing")
async def clip_timing(body: TimingIn):
    """Make a clip run together with the previous clip group, or after it. Then re-simulate."""
    sc = await db.col("scenes").find_one({"_id": body.scene_id, "project_id": body.project_id})
    if not sc:
        raise HTTPException(404, "scene not found")
    tl = sorted(sc.get("timeline", []), key=lambda c: c["start"])
    idx = next((i for i, c in enumerate(tl) if c["clip_id"] == body.clip_id), None)
    if idx is None or idx == 0:
        raise HTTPException(400, "the first clip has nothing before it")
    clip, prev = tl[idx], tl[idx - 1]
    if body.mode == "with_previous":
        clip["start"] = prev["start"]
    else:  # its own group right after the previous group
        clip["start"] = prev["start"] + 1e-3
        for c in tl[idx + 1:]:
            c["start"] += 2e-3  # keep later groups after it
    await db.col("scenes").update_one({"_id": body.scene_id}, {"$set": {"timeline": tl}})
    await scene_logic.resolve_project(body.project_id, dirty={body.scene_id})
    await db.log_event(body.project_id, "clip_retimed", scene_id=body.scene_id, clip_id=body.clip_id, mode=body.mode,
                       background=True)
    return {"ok": True}


@app.get("/api/projects")
async def projects():
    """Projects with activity counts, newest first (for the project switcher)."""
    out = []
    async for p in db.col("projects").find({}, {"name": 1, "created": 1}).sort("created", -1):
        n = await db.col("events").count_documents({"project_id": p["_id"], "type": "command"})
        out.append({"name": p["name"], "commands": n})
    return out



@app.post("/api/scenes/delete")
async def delete_scene(body: SceneOpIn):
    """Delete a scene; later scenes renumber and continue from the scene before it."""
    sc = await db.col("scenes").find_one({"_id": body.scene_id, "project_id": body.project_id})
    if not sc:
        raise HTTPException(404, "scene not found")
    if await db.col("scenes").count_documents({"project_id": body.project_id}) <= 1:
        raise HTTPException(400, "a story needs at least one scene")
    await db.col("scenes").delete_one({"_id": body.scene_id})
    async for later in db.col("scenes").find({"project_id": body.project_id, "order": {"$gt": sc["order"]}}).sort("order", 1):
        o = later["order"] - 1
        await db.col("scenes").update_one({"_id": later["_id"]}, {"$set": {"order": o, "title": f"Scene {o + 1}"}})
    # characters introduced in the deleted scene are carried into the next one, so nothing disappears silently
    nxt = await db.col("scenes").find_one({"project_id": body.project_id, "order": sc["order"]})
    if nxt and sc.get("added"):
        await db.col("scenes").update_one({"_id": nxt["_id"]}, {"$set": {f"added.{k}": v for k, v in sc["added"].items()}})
    await scene_logic.resolve_project(body.project_id)
    await db.log_event(body.project_id, "scene_deleted", scene_id=body.scene_id, n_clips=len(sc.get("timeline", [])),
                       background=True)
    return {"ok": True}
