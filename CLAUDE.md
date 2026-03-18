# MADHACK — AI Agents Hackathon

## Overview
3-hour hackathon (18:00–21:00). Build two collaborative AI travel concierge agents on the Orca Agent Mesh Network.

## Architecture
- **Consumer Agent** (port 8001): User-facing travel assistant. Parses intent, delegates to providers via `session.ask_agent()`, synthesizes responses.
- **Provider Agent** (port 8000): Wraps a specific travel API. Receives natural language from consumers, maps to REST calls, returns structured data.

## Orca SDK Cheat Sheet
```python
from orca import create_agent_app, ChatMessage, OrcaHandler, Variables, ChatHistoryHelper

handler = OrcaHandler()
session = handler.begin(data)
variables = Variables(data.variables)          # Get config from Orca admin
session.available_agents                       # List connected agents (.slug, .name, .description)
session.ask_agent(slug, question, timeout=120) # Call another agent
session.stream(text)                           # Send response chunk
session.close()                                # Finalize
session.error(msg, exception=e)                # Error
session.loading.start(label) / .end(label)     # Loading indicator
```

## Travel APIs
Base URL: `https://hacketon-18march-api.orcaplatform.ai`
Auth: `X-API-Key` header or `?api_key=` query param.

| Service       | Instances                  | Default Key                    |
|---------------|----------------------------|--------------------------------|
| Hotel         | hotel-1, hotel-2           | hotel-1-key-abc123, hotel-2-key-def456 |
| Restaurant    | restaurant-1/2/3           | restaurant-{n}-key-{code}      |
| Flight        | flight-1                   | flight-1-key-pqr678           |
| Car Rental    | car-rental-1               | car-rental-1-key-stu901       |
| Tour Guide    | tour-guide-1               | tour-guide-1-key-vwx234       |
| Museum        | museum-1                   | museum-1-key-yza567           |

Each service has: `GET /api/schema` (self-describing), standard CRUD endpoints.

## Orca Admin Config (manual — requires browser)
- Endpoint: `https://hacketon-18march.orcapt.com/admin`
- API URL env: `export ORCA_API_URL="https://hacketon-18march-api.orcapt.com"`
- Variables to set: `ANTHROPIC_API_KEY`, `API_KEY`, `API_BASE_URL`
- Agents to register: Provider + Consumer, connect via ngrok URLs

## Boilerplate
- `hackathon-18march-boilerplate/provider/main.py` — Provider agent (port 8000)
- `hackathon-18march-boilerplate/consumer/main.py` — Consumer agent (port 8001)
- Both use FastAPI + uvicorn + orca-platform-sdk-ui

## Judging Criteria
1. Functionality (usefulness of outputs, 0-10)
2. API integration (number and relevance of APIs used)
3. Efficiency (token optimization per request)

## Dev Commands
```bash
# Provider
cd hackathon-18march-boilerplate/provider && pip install -r requirements.txt && python main.py

# Consumer
cd hackathon-18march-boilerplate/consumer && pip install -r requirements.txt && python main.py

# Expose to Orca
ngrok http 8000  # provider
ngrok http 8001  # consumer
```
