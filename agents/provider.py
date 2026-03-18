"""
Generic provider agent — wraps any travel API service.
Run with: SERVICE_NAME=museum-1 python provider.py
"""

import os
import json
import httpx
from openai import OpenAI
from fastapi import FastAPI
from pydantic import BaseModel
from config import SERVICES

SERVICE_NAME = os.environ.get("SERVICE_NAME", "museum-1")
svc = SERVICES[SERVICE_NAME]

app = FastAPI(title=f"Provider: {svc['name']}")

_schema: dict | None = None


class Query(BaseModel):
    message: str


async def get_schema() -> dict:
    global _schema
    if _schema:
        return _schema
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{svc['base_url']}/api/schema",
            headers={"X-API-Key": svc['api_key']},
            timeout=10,
        )
        r.raise_for_status()
        _schema = r.json()
    return _schema


async def call_api(method: str, path: str, params=None, body=None) -> dict:
    url = f"{svc['base_url']}{path}"
    headers = {"X-API-Key": svc['api_key'], "Content-Type": "application/json"}
    async with httpx.AsyncClient() as client:
        r = await client.request(
            method.upper(), url, headers=headers,
            params=params, json=body, timeout=15,
        )
        r.raise_for_status()
        return r.json()


def build_tools(schema: dict) -> list[dict]:
    tools = []
    for ep in schema.get("endpoints", []):
        name = (
            ep["method"].lower() + "_" +
            ep["path"].strip("/")
            .replace("/", "_").replace("{", "").replace("}", "")
            .replace("-", "_").replace("api_", "")
        )
        props = {}
        req = []
        raw = ep.get("parameters", {})
        if isinstance(raw, dict):
            for pname, pdesc in raw.items():
                props[pname] = {"type": "string", "description": str(pdesc)}
                if "required" in str(pdesc).lower():
                    req.append(pname)
        elif isinstance(raw, list):
            for p in raw:
                props[p["name"]] = {"type": "string", "description": p.get("description", "")}
                if p.get("required"):
                    req.append(p["name"])
        for fname, finfo in (ep.get("request_body") or ep.get("body") or {}).items():
            props[fname] = {"type": "string", "description": str(finfo)}
            req.append(fname)

        tools.append({
            "type": "function",
            "function": {
                "name": name,
                "description": f"{ep['method']} {ep['path']} — {ep.get('description', '')}",
                "parameters": {"type": "object", "properties": props, "required": req},
            },
        })
    return tools


def find_endpoint(tool_name: str, schema: dict) -> dict | None:
    for ep in schema.get("endpoints", []):
        candidate = (
            ep["method"].lower() + "_" +
            ep["path"].strip("/")
            .replace("/", "_").replace("{", "").replace("}", "")
            .replace("-", "_").replace("api_", "")
        )
        if candidate == tool_name:
            return ep
    return None


@app.get("/health")
async def health():
    return {"status": "ok", "service": SERVICE_NAME}


@app.post("/ask")
async def ask(query: Query):
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        return {"error": "OPENAI_API_KEY not set"}

    schema = await get_schema()
    tools = build_tools(schema)
    service_label = schema.get("service", svc["name"])

    system = f"""You are a provider agent for: {service_label}.
Your ONLY job is to call the travel API and return real data. Never make up information.

API Schema:
{json.dumps(schema, indent=2)[:3000]}

Rules:
- Use tools to get real data. Never fabricate.
- Return concise, structured responses: names, prices, dates, availability, IDs.
- Keep responses short and data-rich.
- CRITICAL: When booking/reserving, use the database "id" field (integer), NOT the room_number/table_number/name. For example, Room 201 might have id=3 — use room_id=3 in the booking request.
- Always include both the ID and the human-readable name/number in your responses so the consumer can display them."""

    client = OpenAI(api_key=api_key)
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": query.message},
    ]

    response = client.chat.completions.create(
        model="gpt-4o",
        max_tokens=1024,
        messages=messages,
        tools=tools if tools else None,
    )

    # Tool loop
    for _ in range(5):
        msg = response.choices[0].message
        if not msg.tool_calls:
            break

        messages.append(msg)
        for tc in msg.tool_calls:
            fn_name = tc.function.name
            fn_args = json.loads(tc.function.arguments)
            try:
                ep = find_endpoint(fn_name, schema)
                if ep:
                    method = ep["method"]
                    path = ep["path"]
                    args = dict(fn_args)
                    for k, v in list(args.items()):
                        if f"{{{k}}}" in path:
                            path = path.replace(f"{{{k}}}", str(v))
                            del args[k]
                    if method.upper() == "GET":
                        result = await call_api(method, path, params=args)
                    elif method.upper() == "POST":
                        result = await call_api(method, path, body=args)
                    elif method.upper() == "DELETE":
                        result = await call_api(method, path)
                    else:
                        result = await call_api(method, path, params=args)
                else:
                    result = {"error": f"Unknown tool: {fn_name}"}
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result)[:4000],
                })
            except Exception as e:
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": f"Error: {e}",
                })

        response = client.chat.completions.create(
            model="gpt-4o",
            max_tokens=1024,
            messages=messages,
            tools=tools if tools else None,
        )

    text = response.choices[0].message.content or "No results found."
    return {"response": text}


if __name__ == "__main__":
    import uvicorn
    print(f"Provider [{SERVICE_NAME}] on port {svc['port']}")
    uvicorn.run(app, host="0.0.0.0", port=svc["port"])
