"""MongoDB access. One async client per process; collections are named in one place."""

import os
import secrets
from datetime import datetime, timezone

from dotenv import load_dotenv
from pymongo import AsyncMongoClient

load_dotenv(".env")

_client: AsyncMongoClient | None = None


def client() -> AsyncMongoClient:
    global _client
    if _client is None:
        _client = AsyncMongoClient(os.environ["MONGODB_URI"], serverSelectionTimeoutMS=8000, appname="drawtalk-harness")
    return _client


def db():
    return client()[os.environ.get("MONGODB_DB", "sketch_harness")]


def col(name: str):
    """Collections: projects, entities, scenes, behaviors, examples, events, harness_config."""
    return db()[name]


def new_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(5)}"


def now() -> datetime:
    return datetime.now(timezone.utc)


async def ensure_indexes():
    await col("entities").create_index([("project_id", 1)])
    await col("scenes").create_index([("project_id", 1), ("order", 1)])
    await col("behaviors").create_index([("project_id", 1), ("behavior_id", 1), ("version", -1)], unique=True)
    await col("examples").create_index([("project_id", 1), ("created", -1)])
    await col("events").create_index([("project_id", 1), ("ts", 1)])


async def log_event(project_id: str, type_: str, **data) -> str:
    """Append to the events log (the source of truth for metrics and the why trace)."""
    eid = new_id("evt")
    await col("events").insert_one({"_id": eid, "project_id": project_id, "type": type_, "ts": now(), **data})
    return eid
