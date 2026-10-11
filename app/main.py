"""FastAPI app: serves the static front end and the JSON API."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app import db, geometry, harness


@asynccontextmanager
async def lifespan(_app):
    await db.ensure_indexes()
    yield


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
            {"_id": db.new_id("scn"), "project_id": p["_id"], "order": 0, "title": "Scene 1", "start_state": {}, "timeline": []}
        )
        await db.log_event(p["_id"], "project_created")
    return p


@app.get("/api/state")
async def state(project: str = "rehearsal"):
    p = await _project(project)
    pid = p["_id"]
    scenes = [s async for s in db.col("scenes").find({"project_id": pid}).sort("order", 1)]
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
    await db.col("scenes").update_one(
        {"_id": body.scene_id}, {"$set": {f"start_state.{eid}": {"x": cx, "y": cy, **harness.DEFAULT_STATE}}}
    )
    await db.log_event(body.project_id, "entity_created", entity_id=eid, n_strokes=len(body.strokes))
    return {"entity": _clean(ent), "state": {"x": cx, "y": cy, **harness.DEFAULT_STATE}}


class CommandIn(BaseModel):
    project_id: str
    scene_id: str
    text: str = ""
    stroke: list[list[float]] | None = None


@app.post("/api/command")
async def command(body: CommandIn):
    if not body.text.strip() and not body.stroke:
        raise HTTPException(400, "empty command")
    try:
        return await harness.run_command(body.project_id, body.scene_id, body.text.strip(), body.stroke)
    except ValueError as e:
        raise HTTPException(404, str(e))


class SceneIn(BaseModel):
    project_id: str


@app.post("/api/scenes")
async def new_scene(body: SceneIn):
    """New scene continues from the previous scene's end state (continuity default)."""
    last = await db.col("scenes").find_one({"project_id": body.project_id}, sort=[("order", -1)])
    start = harness.current_states(last) if last else {}
    order = (last["order"] + 1) if last else 0
    scene = {"_id": db.new_id("scn"), "project_id": body.project_id, "order": order, "title": f"Scene {order + 1}",
             "start_state": start, "timeline": [], "continued_from": last["_id"] if last else None}
    await db.col("scenes").insert_one(scene)
    await db.log_event(body.project_id, "scene_created", scene_id=scene["_id"], n_carried=len(start))
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
    return {"ok": True}
