"""Long-term memory: Voyage embeddings + Atlas Vector Search over examples, and the versioned harness config."""

import asyncio
import logging

import voyageai
from pymongo.operations import SearchIndexModel

from app import db

log = logging.getLogger("memory")
EMBED_MODEL = "voyage-4-lite"
DIMS = 1024
VECTOR_INDEX = "examples_text_vec"
_vo: voyageai.Client | None = None


def _client() -> voyageai.Client:
    global _vo
    if _vo is None:
        _vo = voyageai.Client()
    return _vo


async def embed(text: str, kind: str = "document") -> list[float] | None:
    try:
        r = await asyncio.to_thread(_client().embed, [text], model=EMBED_MODEL, input_type=kind)
        return r.embeddings[0]
    except Exception as e:  # memory is best-effort; the harness still works without it
        log.warning("embed failed: %s", type(e).__name__)
        return None


async def ensure_vector_index():
    coll = db.col("examples")
    existing = [i["name"] async for i in await coll.list_search_indexes()]
    if VECTOR_INDEX not in existing:
        await coll.create_search_index(SearchIndexModel(name=VECTOR_INDEX, type="vectorSearch", definition={
            "fields": [
                {"type": "vector", "path": "text_vec", "numDimensions": DIMS, "similarity": "cosine"},
                {"type": "filter", "path": "project_id"},
                {"type": "filter", "path": "outcome"},
            ]
        }))


async def similar_examples(project_id: str, vec: list[float] | None, k: int = 4) -> list[dict]:
    """Accepted past examples whose command text means something similar (Atlas $vectorSearch).

    The caller embeds the command text once and reuses that vector when it stores the new examples
    (one Voyage call per command keeps us under free-tier rate limits)."""
    if not vec:
        return []
    try:
        cur = await db.col("examples").aggregate([
            {"$vectorSearch": {"index": VECTOR_INDEX, "path": "text_vec", "queryVector": vec, "numCandidates": 60,
                               "limit": k, "filter": {"project_id": project_id, "outcome": "accepted"}}},
            {"$project": {"_id": 1, "text": 1, "actor_name": 1, "target_name": 1, "behavior_id": 1,
                          "behavior_version": 1, "params": 1, "score": {"$meta": "vectorSearchScore"}}},
        ])
        return [d async for d in cur]
    except Exception as e:  # index still building, etc.
        log.warning("vector search failed: %s", type(e).__name__)
        return []


# ---------------------------------------------------------------- harness config (versioned, self-modifying)

DEFAULT_CONFIG = {"fast_path": {"min_score": 0.8, "min_examples": 2, "accepted_since_change": 0,
                                 "gesture_min_score": 0.5, "gesture_margin": 0.1}}


async def get_config(project_id: str) -> dict:
    doc = await db.col("harness_config").find_one({"project_id": project_id}, sort=[("version", -1)])
    if doc:  # older versions predate newer keys
        doc["fast_path"] = {**DEFAULT_CONFIG["fast_path"], **doc["fast_path"]}
    return doc or {"project_id": project_id, "version": 0, **DEFAULT_CONFIG}


async def update_config(project_id: str, changes: dict, reason: str, evidence: list[str]) -> dict:
    """Write a NEW version (never overwrite): the harness rewriting its own routing policy."""
    cur = await get_config(project_id)
    fp = {**cur["fast_path"], **changes}
    doc = {"_id": db.new_id("cfg"), "project_id": project_id, "version": cur["version"] + 1,
           "parent_version": cur["version"], "fast_path": fp, "reason": reason, "evidence": evidence,
           "created": db.now()}
    await db.col("harness_config").insert_one(doc)
    await db.log_event(project_id, "config_changed", version=doc["version"], changes=changes, reason=reason)
    if ("min_score" in changes or "gesture_min_score" in changes) and evidence:  # a real policy change
        ex = await db.col("examples").find_one({"_id": evidence[-1]}, {"command_event": 1})
        if ex and ex.get("command_event"):
            import raindrop.analytics as raindrop
            raindrop.track_signal(event_id=ex["command_event"], name="routing_policy_changed",
                                  properties={"version": doc["version"], "min_score": fp["min_score"],
                                              "gesture_min_score": fp["gesture_min_score"], "reason": reason})
    return doc


async def count_fast_accepted(project_id: str, n: int, evidence: list[str]):
    """Accepted fast-path guesses build trust; every 3 in a row relax the threshold a little (bounded)."""
    cfg = await get_config(project_id)
    since = cfg["fast_path"]["accepted_since_change"] + n
    if since >= 3 and cfg["fast_path"]["min_score"] > 0.72:
        await update_config(project_id, {"min_score": round(cfg["fast_path"]["min_score"] - 0.02, 2), "accepted_since_change": 0},
                            f"{since} fast-path guesses accepted in a row: trust stroke matches a bit more", evidence)
    elif cfg["version"] == 0:
        await update_config(project_id, {"accepted_since_change": since}, "baseline routing policy", evidence)
    else:  # a running counter, not a policy change: update the current version in place
        await db.col("harness_config").update_one({"_id": cfg["_id"]}, {"$set": {"fast_path.accepted_since_change": since}})


async def penalize_fast_guess(project_id: str, example_id: str, behavior_id: str):
    """The user undid a fast-path guess: require a closer stroke match from now on (new policy version)."""
    cfg = await get_config(project_id)
    new = round(min(0.95, cfg["fast_path"]["min_score"] + 0.05), 2)
    await update_config(project_id, {"min_score": new, "accepted_since_change": 0},
                        f"fast-path guess '{behavior_id}' was undone: require closer stroke matches", [example_id])


async def learn_from_missed_gesture(project_id: str, behavior_id: str, example_id: str):
    """A gesture was just taught with words. If a recent unrecognized gesture almost matched that same behavior,
    the threshold was too strict for this user's drawing: lower it to just below the missed score."""
    import datetime as dt
    since = db.now() - dt.timedelta(minutes=3)
    miss = await db.col("events").find_one({"project_id": project_id, "type": "gesture_unknown", "ts": {"$gte": since}},
                                           sort=[("ts", -1)])
    if not miss or not miss.get("candidates"):
        return None
    top = miss["candidates"][0]
    cfg = (await get_config(project_id))["fast_path"]
    if top["behavior"] != behavior_id or top["score"] >= cfg["gesture_min_score"]:
        return None
    new = round(max(0.4, top["score"] - 0.03), 2)
    await update_config(project_id, {"gesture_min_score": new},
                        f"gesture for '{behavior_id}' was missed at {top['score']:.2f}; you confirmed it means "
                        f"'{behavior_id}': accept gestures from {new}", [example_id])
    return new
