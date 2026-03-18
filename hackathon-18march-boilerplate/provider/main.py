import logging
import json
import os
import httpx
import anthropic
from orca import create_agent_app, ChatMessage, OrcaHandler, Variables

logger = logging.getLogger(__name__)

# --- Configuration via env vars (for multi-instance local dev) or Orca variables ---
SERVICE_NAME = os.environ.get("SERVICE_NAME", "museum-1")
SERVICE_API_KEY = os.environ.get("SERVICE_API_KEY", "")
SERVICE_PORT = int(os.environ.get("SERVICE_PORT", "8000"))

API_BASE = "https://hacketon-18march-api.orcaplatform.ai"

# All services and their default API keys
SERVICES = {
    "hotel-1":      "hotel-1-key-abc123",
    "hotel-2":      "hotel-2-key-def456",
    "restaurant-1": "restaurant-1-key-ghi789",
    "restaurant-2": "restaurant-2-key-jkl012",
    "restaurant-3": "restaurant-3-key-mno345",
    "flight-1":     "flight-1-key-pqr678",
    "car-rental-1": "car-rental-1-key-stu901",
    "tour-guide-1": "tour-guide-1-key-vwx234",
    "museum-1":     "museum-1-key-yza567",
}

# Cache the API schema per service
_schema_cache: dict | None = None


def get_service_config():
    """Get base URL and API key for the configured service."""
    api_key = SERVICE_API_KEY or SERVICES.get(SERVICE_NAME, "")
    base_url = f"{API_BASE}/{SERVICE_NAME}"
    return base_url, api_key


async def fetch_schema(base_url: str, api_key: str) -> dict:
    global _schema_cache
    if _schema_cache is not None:
        return _schema_cache
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{base_url}/api/schema",
            headers={"X-API-Key": api_key},
            timeout=10,
        )
        resp.raise_for_status()
        _schema_cache = resp.json()
    return _schema_cache


async def call_api(base_url: str, api_key: str, method: str, path: str,
                   params: dict | None = None, body: dict | None = None) -> dict:
    url = f"{base_url}{path}"
    headers = {"X-API-Key": api_key, "Content-Type": "application/json"}
    async with httpx.AsyncClient() as client:
        if method.upper() == "GET":
            resp = await client.get(url, headers=headers, params=params, timeout=15)
        elif method.upper() == "POST":
            resp = await client.post(url, headers=headers, json=body, timeout=15)
        elif method.upper() == "DELETE":
            resp = await client.delete(url, headers=headers, timeout=15)
        else:
            resp = await client.request(method.upper(), url, headers=headers,
                                        params=params, json=body, timeout=15)
        resp.raise_for_status()
        return resp.json()


def build_tools_from_schema(schema: dict) -> list[dict]:
    tools = []
    endpoints = schema.get("endpoints", [])
    for ep in endpoints:
        tool_name = (
            ep["method"].lower() + "_" +
            ep["path"].strip("/").replace("/", "_").replace("{", "").replace("}", "")
                .replace("-", "_").replace("api_", "")
        )
        properties = {}
        required = []
        raw_params = ep.get("parameters", {})
        # Handle both dict format {"name": "description"} and list format [{"name": ..}]
        if isinstance(raw_params, dict):
            for param_name, param_desc in raw_params.items():
                desc = str(param_desc)
                properties[param_name] = {"type": "string", "description": desc}
                if "required" in desc.lower():
                    required.append(param_name)
        elif isinstance(raw_params, list):
            for p in raw_params:
                properties[p["name"]] = {"type": "string", "description": p.get("description", p["name"])}
                if p.get("required", False):
                    required.append(p["name"])
        for field_name, field_info in ep.get("request_body", {}).items():
            prop = {"type": "string", "description": str(field_info)}
            properties[field_name] = prop
            required.append(field_name)

        tools.append({
            "name": tool_name,
            "description": f"{ep['method']} {ep['path']} — {ep.get('description', '')}",
            "input_schema": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        })

    if not tools:
        tools.append({
            "name": "call_travel_api",
            "description": "Make a REST call to the travel API.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "method": {"type": "string", "description": "HTTP method: GET, POST, DELETE"},
                    "path": {"type": "string", "description": "API path, e.g. /api/rooms/available"},
                    "params": {"type": "object", "description": "Query parameters"},
                    "body": {"type": "object", "description": "Request body for POST"},
                },
                "required": ["method", "path"],
            },
        })
    return tools


def find_endpoint_for_tool(tool_name: str, schema: dict) -> dict | None:
    for ep in schema.get("endpoints", []):
        candidate = (
            ep["method"].lower() + "_" +
            ep["path"].strip("/").replace("/", "_").replace("{", "").replace("}", "")
                .replace("-", "_").replace("api_", "")
        )
        if candidate == tool_name:
            return ep
    return None


async def process_message(data: ChatMessage):
    handler = OrcaHandler()
    session = handler.begin(data)

    try:
        # Config: prefer Orca variables, fall back to env vars
        variables = Variables(data.variables)
        anthropic_key = variables.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_API_KEY", "")
        base_url, api_key = get_service_config()
        # Allow Orca variable overrides
        orca_base = variables.get("API_BASE_URL")
        orca_key = variables.get("API_KEY")
        if orca_base:
            base_url = orca_base
        if orca_key:
            api_key = orca_key

        if not anthropic_key:
            session.stream("Missing ANTHROPIC_API_KEY.")
            session.close()
            return

        session.loading.start("Fetching API schema")
        schema = await fetch_schema(base_url, api_key)
        session.loading.end("Fetching API schema")

        tools = build_tools_from_schema(schema)
        service_label = schema.get("service_name", SERVICE_NAME)

        system_prompt = f"""You are a provider agent for: {service_label}.

Your ONLY job is to answer questions by calling the travel API. You have tools for each endpoint.

API Schema:
{json.dumps(schema, indent=2)[:3000]}

Rules:
- Always use the tools to get real data. Never make up information.
- Return concise, structured responses with key data points.
- Include: names, prices, dates, availability, IDs.
- Keep responses short and data-rich — the consumer agent formats for the user.
- If the request is unclear, ask for clarification.
- For bookings, confirm all required fields before calling the API."""

        client = anthropic.Anthropic(api_key=anthropic_key)
        messages = [{"role": "user", "content": data.message}]

        session.loading.start("Thinking")
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=system_prompt,
            tools=tools,
            messages=messages,
        )
        session.loading.end("Thinking")

        # Tool use loop
        max_iterations = 5
        iteration = 0
        while response.stop_reason == "tool_use" and iteration < max_iterations:
            iteration += 1
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    tool_name = block.name
                    tool_input = block.input

                    session.loading.start(f"Calling API: {tool_name}")
                    try:
                        if tool_name == "call_travel_api":
                            result = await call_api(
                                base_url, api_key,
                                tool_input.get("method", "GET"),
                                tool_input.get("path", ""),
                                params=tool_input.get("params"),
                                body=tool_input.get("body"),
                            )
                        else:
                            ep = find_endpoint_for_tool(tool_name, schema)
                            if ep:
                                method = ep["method"]
                                path = ep["path"]
                                for key, val in tool_input.items():
                                    if f"{{{key}}}" in path:
                                        path = path.replace(f"{{{key}}}", str(val))
                                path_params = {k for k in tool_input if f"{{{k}}}" in ep.get("path", "")}
                                remaining = {k: v for k, v in tool_input.items() if k not in path_params}
                                if method.upper() == "GET":
                                    result = await call_api(base_url, api_key, method, path, params=remaining)
                                elif method.upper() == "POST":
                                    result = await call_api(base_url, api_key, method, path, body=remaining)
                                elif method.upper() == "DELETE":
                                    result = await call_api(base_url, api_key, method, path)
                                else:
                                    result = await call_api(base_url, api_key, method, path,
                                                           params=remaining, body=remaining)
                            else:
                                result = {"error": f"Unknown tool: {tool_name}"}

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(result)[:4000],
                        })
                    except httpx.HTTPStatusError as e:
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": f"API error {e.response.status_code}: {e.response.text[:500]}",
                            "is_error": True,
                        })
                    except Exception as e:
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": f"Error: {str(e)}",
                            "is_error": True,
                        })
                    finally:
                        session.loading.end(f"Calling API: {tool_name}")

            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})

            session.loading.start("Analyzing results")
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                system=system_prompt,
                tools=tools,
                messages=messages,
            )
            session.loading.end("Analyzing results")

        final_text = ""
        for block in response.content:
            if hasattr(block, "text"):
                final_text += block.text

        if not final_text:
            final_text = "No results found for your query."

        session.stream(final_text)
        session.close()

    except Exception as e:
        logger.exception("Error processing message")
        session.error("Something went wrong.", exception=e)


app, orca = create_agent_app(
    process_message_func=process_message,
    title=f"Provider Agent — {SERVICE_NAME}",
    description=f"Travel API provider for {SERVICE_NAME}",
)

if __name__ == "__main__":
    import uvicorn
    print(f"Starting provider for {SERVICE_NAME} on port {SERVICE_PORT}")
    uvicorn.run(app, host="0.0.0.0", port=SERVICE_PORT)
