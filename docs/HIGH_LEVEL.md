# MADHACK — Architecture Overview

## System Architecture

```
                         http://localhost:8001
                                  │
                          ┌───────┴───────┐
                          │   CONSUMER    │
                          │   (GPT-4o)    │
                          │  Port 8001    │
                          └───────┬───────┘
                                  │
                    "Which providers do I need?"
                    GPT-4o decides via tool_use
                                  │
          ┌──────┬──────┬─────────┼─────────┬──────┬──────┐
          ▼      ▼      ▼         ▼         ▼      ▼      ▼
       hotel-1 hotel-2 rest-1  flight-1  car-1  tour-1 museum-1
       :8010   :8011   :8012    :8015    :8016   :8017   :8018
          │      │      │         │         │      │      │
          └──────┴──────┴─────────┼─────────┴──────┴──────┘
                                  │
                    Each provider has its own GPT-4o
                    that maps questions → API calls
                                  │
                                  ▼
                   hacketon-18march-api.orcaplatform.ai
                     (real hotel/flight/museum/... data)
```

## The 3 Layers

### 1. UI (`ui.html`)
Simple dark-themed chat page served at `localhost:8001`. Sends user messages as `POST /chat` to the consumer. Shows a health status dot that polls `/health` every 10 seconds. Maintains conversation history client-side and sends it with each request for context.

### 2. Consumer Agent (`consumer.py`, port 8001)
The orchestration brain. Receives the user's message, sends it to GPT-4o with 9 tools — one per provider service (`ask_hotel_1`, `ask_flight_1`, `ask_museum_1`, etc.). GPT-4o decides which providers to call and what to ask them. It can call multiple providers in a loop (up to 10 iterations), then synthesizes everything into one formatted response.

Key responsibilities:
- Parse user intent via GPT-4o
- Decide which provider(s) to query
- Call providers via HTTP (`POST localhost:{port}/ask`)
- Synthesize multiple provider responses into a single user-friendly answer
- Serve the web UI at `/`
- CORS enabled for browser access

### 3. Provider Agents (`provider.py` × 9 instances)
Each provider is the same generic code, configured with a different `SERVICE_NAME` env var. On startup, each:
1. Fetches the API schema from its assigned travel service (`GET /api/schema`)
2. Converts each API endpoint into a GPT-4o function-calling tool
3. Listens for questions on its assigned port

When queried, the provider:
1. Sends the question to GPT-4o with the API endpoint tools
2. GPT-4o picks the right endpoint and parameters
3. Provider makes the real REST API call
4. Returns structured data back to the consumer

## Example Flow: "Book museum tickets for 2 adults March 19"

1. **User** types in the UI → `POST /chat {"message": "..."}`
2. **Consumer** sends to GPT-4o with 9 provider tools
3. GPT-4o returns: `call ask_museum_1("tickets for 2 adults on 2026-03-19")`
4. **Consumer** does `POST localhost:8018/ask` with that question
5. **Museum provider** sends to its own GPT-4o with API endpoint tools
6. GPT-4o returns: `call get_availability(date="2026-03-19", visitors="2")`
7. **Provider** calls the real API: `GET hacketon-18march-api.../museum-1/api/availability?date=2026-03-19&visitors=2`
8. Real data comes back → provider's GPT-4o formats it → returns to consumer
9. **Consumer's** GPT-4o synthesizes → sends to UI

## Services & Ports

| Service       | Port  | API Key                    |
|---------------|-------|----------------------------|
| hotel-1       | 8010  | hotel-1-key-abc123         |
| hotel-2       | 8011  | hotel-2-key-def456         |
| restaurant-1  | 8012  | restaurant-1-key-ghi789    |
| restaurant-2  | 8013  | restaurant-2-key-jkl012    |
| restaurant-3  | 8014  | restaurant-3-key-mno345    |
| flight-1      | 8015  | flight-1-key-pqr678        |
| car-rental-1  | 8016  | car-rental-1-key-stu901    |
| tour-guide-1  | 8017  | tour-guide-1-key-vwx234    |
| museum-1      | 8018  | museum-1-key-yza567        |
| **consumer**  | 8001  | —                          |

## File Structure

```
agents/
├── .env               # OPENAI_API_KEY (gitignored)
├── .gitignore
├── config.py           # All 9 services: URLs, API keys, ports
├── provider.py         # Generic provider — runs as 9 instances via SERVICE_NAME
├── consumer.py         # Orchestrator + serves the web UI
├── ui.html             # Chat interface
├── launch_all.py       # Starts all 10 processes, loads .env
└── requirements.txt    # fastapi, uvicorn, httpx, openai
```

## Running

```bash
cd agents
export OPENAI_API_KEY="sk-..."   # or use .env file
python3.11 launch_all.py
# Open http://localhost:8001
```

## LLM Usage

- **Model**: GPT-4o (via OpenAI API)
- **Consumer**: 1 GPT-4o call per user message + 1 per tool loop iteration
- **Provider**: 1 GPT-4o call per question + 1 per API tool loop iteration
- **Total per query**: ~2-6 LLM calls depending on complexity

## Travel APIs

Base URL: `https://hacketon-18march-api.orcaplatform.ai`
Auth: `X-API-Key` header or `?api_key=` query param.

Each service exposes:
- `GET /api/schema` — self-describing endpoint list
- Standard CRUD: list, search/available, pricing, create booking, list bookings, get booking, cancel booking
