# MADHACK x Orca — AI Agent Hackathon

Build **two AI agents** that communicate with each other and with the user through [Orca](https://orcaplatform.ai) — the orchestration layer for AI agents.

---

## The Challenge

Each team is assigned a **travel-related API** (hotels, restaurants, events, tours, car rental, etc.).

You must build:

| Agent | What it does | Port |
|-------|-------------|------|
| **Provider** | Connects to your assigned API. Handles search, booking, cancellation, listing — full CRUD. Responds to other agents. | 8000 |
| **Consumer** | A personal AI assistant. Takes user requests, delegates to provider agents, returns friendly responses. | 8001 |

At demo time, all consumer agents connect to **all** provider agents through Orca. Your consumer will talk to every team's provider.

---

## Quick Start

```bash
# 1. Clone this repo
git clone <repo-url> && cd <repo-name>

# 2. Install and run the provider agent
cd provider
pip install -r requirements.txt
python main.py
# → runs on http://localhost:8000

# 3. In another terminal, run the consumer agent
cd consumer
pip install -r requirements.txt
python main.py
# → runs on http://localhost:8001
```

Or with Docker:

```bash
cd provider && docker compose up --build
cd consumer && docker compose up --build
```

> **API keys** (OpenAI, your assigned API, etc.) are configured in the Orca admin panel and delivered to your agent in every request via `data.variables`. Use `Variables(data.variables).get("VARIABLE_NAME")` to read them — no environment variables needed.

---

## Project Structure

```
├── provider/
│   ├── main.py              ← Your provider agent (START HERE)
│   ├── requirements.txt
│   ├── Dockerfile
│   └── docker-compose.yml
├── consumer/
│   ├── main.py              ← Your consumer agent
│   ├── requirements.txt
│   ├── Dockerfile
│   └── docker-compose.yml
├── .gitignore
└── README.md
```

---

## What You Need to Build

### Provider Agent (the hard part)

Your provider agent receives questions from consumer agents and must:

1. **Understand the request** — use an LLM (OpenAI, Anthropic, etc.)
2. **Call your assigned API** — REST calls with authentication (`X-API-Key` header)
3. **Return structured results** — keep responses concise and data-rich

Think about: What API endpoints do you need? How do you map natural language to API calls? How do you handle errors? How do you keep token usage low?

### Consumer Agent (the creative part)

Your consumer agent talks to end users and must:

1. **Understand what the user wants** — parse intent from natural language
2. **Delegate to providers** — use `session.ask_agent()` to call the right provider
3. **Synthesize responses** — turn raw data into a friendly, helpful reply

Think about: What persona does your assistant have? How do you pick which provider to call? How do you handle multi-step tasks (search → compare → book)?

---

## Orca SDK Cheat Sheet

Install: `pip install orca-platform-sdk-ui`

### Agent Lifecycle

```python
from orca import create_agent_app, ChatMessage, OrcaHandler

async def process_message(data: ChatMessage):
    handler = OrcaHandler()
    session = handler.begin(data)

    # ... your logic ...

    session.stream("Your response text")
    session.close()

app, orca = create_agent_app(process_message_func=process_message)
```

### Reading Variables (API keys, config)

```python
from orca import Variables

variables = Variables(data.variables)
api_key = variables.get("OPENAI_API_KEY")
```

### Loading Indicators

```python
session.loading.start("thinking")
# ... do work ...
session.loading.end("thinking")
```

### Error Handling

```python
try:
    # your logic
except Exception as e:
    session.error("Something went wrong", exception=e)
```

### Agent-to-Agent Communication

```python
# See what provider agents are connected
for agent in session.available_agents:
    print(agent.slug, agent.name, agent.description)

# Ask a provider agent a question
response = session.ask_agent("hotel-agent", "Find rooms for 2 guests, March 15-17")

# Handle errors
try:
    response = session.ask_agent("hotel-agent", "your question")
except ValueError:
    # agent not connected
except RuntimeError:
    # agent unavailable or timeout
```

### Chat History

```python
from orca import ChatHistoryHelper

history = ChatHistoryHelper(data.chat_history)
recent_messages = history.get_last_n_messages(10)
```

### Usage Tracking

```python
session.usage.track(tokens=1500, token_type="total")
```

---

## How Agents Connect

```
                    ┌──────────────────┐
  User ──────────►  │  Consumer Agent   │
                    │  (your code)      │
                    └────────┬─────────┘
                             │
                   session.ask_agent()
                             │
                             ▼
                    ┌──────────────────┐
                    │    Orca Cloud     │
                    │  (orchestration)  │
                    └────────┬─────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
     ┌────────────┐ ┌────────────┐ ┌────────────┐
     │  Hotel      │ │ Restaurant │ │  Events    │
     │  Provider   │ │  Provider  │ │  Provider  │
     │ (Team A)    │ │ (Team B)   │ │ (Team C)   │
     └────────────┘ └────────────┘ └────────────┘
```

You develop locally. Orca handles the cloud orchestration and routing between agents.

---

## Judging Criteria

| Criteria | Description |
|----------|-------------|
| **Functionality** | Does it work? Rate the number of useful outputs (out of 10). |
| **API Integration** | Number and relevance of travel APIs used. |
| **Efficiency** | Optimization of prompts and tokens used per request. |

---

## Tips

- Start with the **provider agent** — get your API calls working first
- Use **function calling** (OpenAI) or **tool use** (Anthropic) to map user intent to API endpoints
- Keep provider responses **short and structured** — the consumer agent will format them
- Test your provider by running it and sending requests directly before connecting through Orca
- Add dependencies to `requirements.txt` as you go (`openai`, `httpx`, `anthropic`, etc.)
- Check your API documentation for available endpoints, auth method, and data formats

---

## Resources

- [Orca SDK on PyPI](https://pypi.org/project/orca-platform-sdk-ui/)
- [OpenAI Function Calling](https://platform.openai.com/docs/guides/function-calling)
- [Anthropic Tool Use](https://docs.anthropic.com/en/docs/build-with-claude/tool-use)

---

Good luck. Build fast, build smart.
