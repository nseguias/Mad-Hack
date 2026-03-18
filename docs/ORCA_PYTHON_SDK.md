# Orca SDK Developer Guide

Official guide for building agents with `orca-platform-sdk-ui` (`import orca`).

## Install

```bash
pip install orca-platform-sdk-ui
```

Optional extras:

```bash
pip install "orca-platform-sdk-ui[web]"
pip install "orca-platform-sdk-ui[dev]"
```

## Quick Start

```python
from orca import ChatMessage, OrcaHandler, create_agent_app

async def process_message(data: ChatMessage):
    handler = OrcaHandler()
    session = handler.begin(data)
    try:
        session.loading.start("thinking")
        session.stream(f"Echo: {data.message}")
        session.loading.end("thinking")
        session.close()
    except Exception as e:
        session.error("Failed to process message", exception=e)

app, handler = create_agent_app(process_message)
```

## Core Concepts

- `OrcaHandler` orchestrates streaming + backend callbacks
- `Session` is the primary API you use inside each request
- `ChatMessage` carries request metadata, variables, routing, and mode flags
- `create_agent_app` and `create_hybrid_handler` provide production-ready bootstrap

## Session API (recommended)

```python
session = handler.begin(data)
session.stream("chunk")
session.close()
```

### Main operations

```python
session.loading.start("thinking")
session.loading.end("thinking")

session.image.send("https://example.com/image.jpg")
session.video.send("https://example.com/video.mp4")
session.video.youtube("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
session.location.send_coordinates(35.6892, 51.3890)
session.card.send([{"header": "Card", "text": "Details"}])
session.audio.send_single("https://example.com/audio.mp3", label="Track")

session.html.send("<div>Custom widget</div>")
session.html.send_figure(plt)
session.html.send_plotly(fig)

session.tracing.begin("Planning", visibility="all")
session.tracing.append("Step complete")
session.tracing.end("Done")

session.usage.track(tokens=1000, token_type="total", cost="0.01", label="inference")
```

## Variables and Memory

```python
from orca import Variables, MemoryHelper

vars = Variables(data.variables)
openai_key = vars.get("OPENAI_API_KEY")

memory = MemoryHelper(data.memory)
if memory.has_name():
    session.stream(f"Welcome back {memory.get_name()}!")
```

`Variable` uses `name` / `value` fields (not `key`).

## Response and Streaming Modes

`ChatMessage` supports per-request behavior controls:

- `response_mode="async"` + `stream_mode=True` (default): background + live streaming
- `response_mode="sync"` + `stream_mode=False`: return full response content directly
- `response_mode="async"` + `stream_mode=False`: background processing, no token streaming

These modes are consumed by the standard endpoint flow in `orca.web.endpoints`.

## Agent-to-Agent Calls

```python
# Available connected agents are in request payload
for agent in session.available_agents:
    print(agent.slug, agent.name)

try:
    answer = session.ask_agent("legal-advisor", "Check this clause", timeout=120)
    session.stream(answer)
except ValueError:
    session.stream("Agent not connected.")
except RuntimeError:
    session.stream("Agent is unavailable.")
```

Internal API route used by SDK:
- `POST /api/internal/v1/agents/{slug}/ask`

## Conversation SDK

```python
from orca import OrcaConversation

# Inside agent
conv = OrcaConversation(data=data)
conv.rename(thread_id=data.thread_id, title="New title")

# Standalone
conv = OrcaConversation(token="workspace-token", base_url="https://api.example.com/v1/external")
created = conv.create(
    project_uuid="project-uuid",
    title="Support chat",
    model="gpt-4",
    user_id_external="ext-user-1",
    content="Hello",
)
conv.send_message(
    thread_id=created["data"]["thread_id"],
    model="gpt-4",
    content="Follow-up question",
)
```

For current `orca-v1-api`, the core supported external routes are:
- `POST /v1/external/projects/{project_uuid}/conversations`
- `PUT /v1/external/conversations/{thread_id}`
- `GET /v1/external/conversations/{thread_id}/messages`
- `POST /v1/external/conversations/{thread_id}/messages`

## FastAPI Factory APIs

### `create_agent_app`

Returns:
- `(app, orca_handler)`

```python
app, orca = create_agent_app(process_message)
```

### `create_orca_app` + `add_standard_endpoints`

Available for explicit FastAPI wiring:

```python
from orca import OrcaHandler, create_orca_app, add_standard_endpoints

orca = OrcaHandler()
app = create_orca_app(title="My Agent", debug=True)
add_standard_endpoints(app, orca_handler=orca, process_message_func=process_message)
```

## Lambda Deployment Entry Point

```python
from orca import create_hybrid_handler

handler = create_hybrid_handler(process_message_func=process_message)
```

The hybrid handler auto-routes HTTP, SQS, and cron-shaped events.

## Troubleshooting

- Import error for `orca`: confirm `pip show orca-platform-sdk-ui`
- No streaming in local dev: set `ORCA_DEV_MODE=true`
- Missing API key: inspect `Variables(data.variables).list_names()`
- Agent-to-agent failures: verify connection in admin (`connected_agent_ids`)

## Versioning

Current SDK version in repository: `1.0.16`.
