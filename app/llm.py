"""The only module that talks to an LLM. Model comes from OPENAI_MODEL (default gpt-5.4-mini)."""

import json
import os
import time

from openai import OpenAI

_client: OpenAI | None = None
MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")
TIMEOUT_S = float(os.getenv("LLM_TIMEOUT_S", "25"))


def client() -> OpenAI:
    global _client
    if _client is None:
        # LLM_BASE_URL lets any OpenAI-compatible server stand in, e.g. Ollama at http://localhost:11434/v1
        base = os.getenv("LLM_BASE_URL") or None
        _client = OpenAI(timeout=TIMEOUT_S, max_retries=1, base_url=base, api_key=os.getenv("OPENAI_API_KEY") or "ollama")
    return _client


def structured(system: str, user: str, schema_name: str, schema: dict) -> tuple[dict, dict]:
    """Call the model with a strict JSON schema. Returns (parsed_output, meta)."""
    t0 = time.time()
    kwargs = dict(
        model=MODEL,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        response_format={"type": "json_schema", "json_schema": {"name": schema_name, "strict": True, "schema": schema}},
    )
    effort = os.getenv("OPENAI_REASONING_EFFORT", "" if os.getenv("LLM_BASE_URL") else "low")
    try:
        r = client().chat.completions.create(**kwargs, **({"reasoning_effort": effort} if effort else {}))
    except Exception as e:  # some models reject reasoning/thinking options; retry without
        if not any(w in str(e).lower() for w in ("reasoning", "thinking")):
            raise
        r = client().chat.completions.create(**kwargs)
    msg = r.choices[0].message
    if getattr(msg, "refusal", None):
        raise RuntimeError(f"model refused: {msg.refusal}")
    meta = {
        "model": MODEL,
        "latency_ms": round((time.time() - t0) * 1000),
        "tokens_in": getattr(r.usage, "prompt_tokens", None),
        "tokens_out": getattr(r.usage, "completion_tokens", None),
    }
    return json.loads(msg.content), meta
