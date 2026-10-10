"""Smoke-test every external service in .env. Prints pass/fail only, never secret values.

Usage: uv run python scripts/check_setup.py [mongo|voyage|openai|anthropic|elevenlabs ...]
Re-run at the venue after adding its IP to the Atlas access list.
"""

import asyncio
import os
import subprocess
import sys
import tempfile
import time

import httpx
from dotenv import load_dotenv

load_dotenv(".env")

VOYAGE_MODELS = ["voyage-4-lite", "voyage-3.5-lite"]
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-haiku-5-5")
SCRIBE_MODELS = ["scribe_v2", "scribe_v1"]


def short(e: Exception) -> str:
    return f"{type(e).__name__}: {str(e).splitlines()[0][:200]}"


def embed(texts: list[str]) -> tuple[str, list[list[float]]]:
    import voyageai

    client = voyageai.Client()
    last = None
    for model in VOYAGE_MODELS:
        try:
            return model, client.embed(texts, model=model, input_type="document").embeddings
        except Exception as e:  # try the next model name
            last = e
    raise last


def check_voyage():
    model, vecs = embed(["a bird flies to a tree"])
    return f"{model}, dim={len(vecs[0])}"


async def check_mongo_async():
    from pymongo import AsyncMongoClient
    from pymongo.operations import SearchIndexModel

    client = AsyncMongoClient(os.environ["MONGODB_URI"], serverSelectionTimeoutMS=8000)
    try:
        await client.admin.command("ping")
        coll = client[os.environ.get("MONGODB_DB", "sketch_harness")]["_setup_check"]
        await coll.drop()

        texts = ["a bird flies to a tree", "a fish swims to a rock", "the cloud drifts slowly"]
        model, vecs = embed(texts)
        await coll.insert_many([{"text": t, "vec": v} for t, v in zip(texts, vecs)])

        await coll.create_search_index(
            SearchIndexModel(
                name="vec_idx",
                type="vectorSearch",
                definition={"fields": [{"type": "vector", "path": "vec", "numDimensions": len(vecs[0]), "similarity": "cosine"}]},
            )
        )
        t0 = time.time()
        while time.time() - t0 < 180:
            idx = [i async for i in await coll.list_search_indexes("vec_idx")]
            if idx and idx[0].get("queryable"):
                break
            await asyncio.sleep(3)
        else:
            return "ping+insert ok, but vector index not queryable after 180 s"

        _, (q,) = embed(["something with wings moving"])
        hits = await (await coll.aggregate([
            {"$vectorSearch": {"index": "vec_idx", "path": "vec", "queryVector": q, "numCandidates": 10, "limit": 1}},
            {"$project": {"_id": 0, "text": 1}},
        ])).to_list()
        await coll.drop()
        return f"ping, insert, vector index ({time.time() - t0:.0f} s), $vectorSearch top hit: {hits[0]['text']!r}"
    finally:
        await client.close()


def check_mongo():
    return asyncio.run(check_mongo_async())


def check_openai():
    from openai import OpenAI

    r = OpenAI().chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": 'Reply with JSON {"ok": true}'}],
        response_format={"type": "json_object"},
    )
    return f"{OPENAI_MODEL}: {r.choices[0].message.content.strip()}"


def check_anthropic():
    import anthropic

    r = anthropic.Anthropic().messages.create(
        model=ANTHROPIC_MODEL, max_tokens=20, messages=[{"role": "user", "content": "Say ok"}]
    )
    return f"{ANTHROPIC_MODEL}: {r.content[0].text.strip()}"


def check_elevenlabs():
    with tempfile.TemporaryDirectory() as d:
        aiff, wav = os.path.join(d, "t.aiff"), os.path.join(d, "t.wav")
        subprocess.run(["say", "-o", aiff, "this gesture means fly over there bouncing"], check=True)
        subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16@16000", aiff, wav], check=True)
        audio = open(wav, "rb").read()
    for model in SCRIBE_MODELS:
        r = httpx.post(
            "https://api.elevenlabs.io/v1/speech-to-text",
            headers={"xi-api-key": os.environ["ELEVENLABS_API_KEY"]},
            data={"model_id": model},
            files={"file": ("t.wav", audio, "audio/wav")},
            timeout=60,
        )
        if r.status_code == 200:
            return f"{model}: {r.json().get('text', '').strip()!r}"
        last = f"HTTP {r.status_code}: {r.text[:200]}"
    raise RuntimeError(last)


CHECKS = {
    "voyage": check_voyage,
    "mongo": check_mongo,
    "openai": check_openai,
    "anthropic": check_anthropic,
    "elevenlabs": check_elevenlabs,
}

if __name__ == "__main__":
    for name in sys.argv[1:] or CHECKS:
        try:
            print(f"PASS {name:10} {CHECKS[name]()}")
        except Exception as e:
            print(f"FAIL {name:10} {short(e)}")
