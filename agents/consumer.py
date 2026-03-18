"""
Consumer agent — the travel concierge that orchestrates all providers.
Run with: python consumer.py
"""

import os
import json
import httpx
from openai import OpenAI
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from config import SERVICES
from bookings import add_booking, cancel_booking, get_all_bookings, get_summary

app = FastAPI(title="Travel Concierge — Consumer Agent")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

CONSUMER_PORT = 8001


class UserMessage(BaseModel):
    message: str
    history: list[dict] | None = None


def build_tools() -> list[dict]:
    tools = []
    # Provider tools
    for svc_id, svc in SERVICES.items():
        tools.append({
            "type": "function",
            "function": {
                "name": f"ask_{svc_id.replace('-', '_')}",
                "description": f"Query the {svc['name']} provider. {svc['description']}",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "question": {
                            "type": "string",
                            "description": "Natural language question. Be specific: include dates, guest count, location, budget.",
                        },
                    },
                    "required": ["question"],
                },
            },
        })

    # Booking management tools
    tools.append({
        "type": "function",
        "function": {
            "name": "save_booking",
            "description": "Save a confirmed booking to local memory. Call this EVERY TIME a provider confirms a booking/reservation/ticket.",
            "parameters": {
                "type": "object",
                "properties": {
                    "service": {
                        "type": "string",
                        "description": "Service name: hotel-1, museum-1, flight-1, restaurant-1, etc.",
                    },
                    "booking_id": {
                        "type": "string",
                        "description": "The booking/reservation/ticket ID returned by the provider API.",
                    },
                    "client_name": {
                        "type": "string",
                        "description": "Full name of the client this booking is for.",
                    },
                    "client_email": {
                        "type": "string",
                        "description": "Email of the client.",
                    },
                    "details": {
                        "type": "string",
                        "description": "Short human-readable summary, e.g. 'Flight SM101 NY→LA, Mar 10, 2 passengers, economy, $398'",
                    },
                },
                "required": ["service", "booking_id", "client_name", "client_email", "details"],
            },
        },
    })
    tools.append({
        "type": "function",
        "function": {
            "name": "view_bookings",
            "description": "View all active bookings. Use when the user asks to see their bookings, reservations, or trip plan.",
            "parameters": {
                "type": "object",
                "properties": {
                    "include_cancelled": {
                        "type": "boolean",
                        "description": "Whether to include cancelled bookings. Default false.",
                    },
                },
                "required": [],
            },
        },
    })
    tools.append({
        "type": "function",
        "function": {
            "name": "remove_booking",
            "description": "Cancel a booking locally AND via the provider. Use the local booking # (not the API ID).",
            "parameters": {
                "type": "object",
                "properties": {
                    "local_id": {
                        "type": "integer",
                        "description": "The local booking number (e.g. 1, 2, 3) as shown in view_bookings.",
                    },
                },
                "required": ["local_id"],
            },
        },
    })
    return tools


async def call_provider(service_id: str, question: str) -> str:
    svc = SERVICES[service_id]
    url = f"http://localhost:{svc['port']}/ask"
    async with httpx.AsyncClient() as client:
        r = await client.post(url, json={"message": question}, timeout=120)
        r.raise_for_status()
        return r.json().get("response", "No response")


def handle_local_tool(fn_name: str, fn_args: dict) -> str:
    """Handle booking management tools locally (no provider call needed)."""
    if fn_name == "save_booking":
        entry = add_booking(
            fn_args["service"], fn_args["booking_id"], fn_args["details"],
            client_name=fn_args.get("client_name", ""),
            client_email=fn_args.get("client_email", ""),
        )
        return f"Booking saved as #{entry['id']} for {entry['client_name']}: {entry['details']}"

    elif fn_name == "view_bookings":
        include = fn_args.get("include_cancelled", False)
        bookings = get_all_bookings(include_cancelled=include)
        if not bookings:
            return "No active bookings."
        lines = []
        for b in bookings:
            status = f" [CANCELLED]" if b["status"] == "cancelled" else ""
            client = f"{b.get('client_name', 'Unknown')} ({b.get('client_email', 'no email')})"
            lines.append(f"#{b['id']} [{b['service']}] Client: {client} — {b['details']} (API ID: {b['booking_id']}){status}")
        return "\n".join(lines)

    elif fn_name == "remove_booking":
        entry = cancel_booking(fn_args["local_id"])
        if entry:
            return f"Booking #{entry['id']} marked as cancelled locally. Service: {entry['service']}, API ID: {entry['booking_id']}. You should also cancel it via the provider."
        return f"Booking #{fn_args['local_id']} not found."

    return "Unknown tool."


LOCAL_TOOLS = {"save_booking", "view_bookings", "remove_booking"}


@app.get("/")
async def serve_ui():
    return FileResponse(os.path.join(os.path.dirname(__file__), "ui.html"))


@app.get("/health")
async def health():
    return {"status": "ok", "role": "consumer"}


@app.get("/bookings")
async def api_bookings():
    return get_all_bookings(include_cancelled=True)


@app.post("/chat")
async def chat(msg: UserMessage):
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        return {"error": "OPENAI_API_KEY not set"}

    # Include current bookings in system prompt so the LLM knows what's booked
    current_bookings = get_summary()

    provider_list = "\n".join(
        f"- **ask_{sid.replace('-', '_')}**: {s['name']} — {s['description']}"
        for sid, s in SERVICES.items()
    )

    system = f"""You are a personal AI travel concierge — friendly, efficient, and knowledgeable.
You are a travel agency serving multiple clients. Always track who each booking is for.

## IMPORTANT: The current date is 2026-03-18. If the user says a date without a year, assume 2026.

## Available travel providers (use these tools to get real data)
{provider_list}

## Booking management tools
- **save_booking**: Save a booking after a provider confirms it. ALWAYS call this after a successful booking.
- **view_bookings**: Show the user their current bookings.
- **remove_booking**: Cancel a booking (marks it locally, then you should also cancel via the provider).

## Current bookings
{current_bookings}

## How to work
1. Analyze what the user needs.
2. Call the relevant provider tool(s) with specific questions (include dates, guest counts, etc.).
3. You can call MULTIPLE providers to build a complete trip plan.
4. Synthesize all responses into a clear, well-formatted answer.
5. After ANY successful booking, ALWAYS call save_booking to record it.
6. When cancelling, call remove_booking AND ask the provider to cancel via the API.

## Booking rules
- Before making ANY booking, you MUST have: full name and email of the client.
- If the user hasn't provided name/email, ASK for them before proceeding.
- When saving a booking, include the client name, email, and all details in the "details" field.
- When a provider confirms a booking with an ID, immediately call save_booking.
- When the user asks to see bookings, show: client name, email, service, dates, price, status.

## Rules
- ALWAYS call providers for real data. Never make up prices or availability.
- Compare options when possible — give choices with prices.
- Be conversational and helpful.
- If a provider errors, tell the user and suggest alternatives.
- Always use year 2026 for dates unless the user explicitly specifies another year.
- When booking flights, use the flight ID (integer) not the flight number. Always pass passenger_name, passenger_email, num_passengers, and seat_class."""

    client = OpenAI(api_key=api_key)
    tools = build_tools()

    messages = [{"role": "system", "content": system}]
    if msg.history:
        for h in msg.history:
            messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": msg.message})

    response = client.chat.completions.create(
        model="gpt-4o",
        max_tokens=2048,
        messages=messages,
        tools=tools,
    )

    # Tool loop
    for _ in range(10):
        choice = response.choices[0].message
        if not choice.tool_calls:
            break

        messages.append(choice)
        for tc in choice.tool_calls:
            fn_name = tc.function.name
            fn_args = json.loads(tc.function.arguments)

            if fn_name in LOCAL_TOOLS:
                # Handle locally — no provider call
                result = handle_local_tool(fn_name, fn_args)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })
            else:
                # Provider call
                svc_id = fn_name.replace("ask_", "").replace("_", "-")
                try:
                    result = await call_provider(svc_id, fn_args["question"])
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result[:4000],
                    })
                except Exception as e:
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": f"Provider unavailable: {e}",
                    })

        response = client.chat.completions.create(
            model="gpt-4o",
            max_tokens=2048,
            messages=messages,
            tools=tools,
        )

    text = response.choices[0].message.content or "I couldn't get results. Please try again."
    return {"response": text}


if __name__ == "__main__":
    import uvicorn
    print(f"Consumer agent on port {CONSUMER_PORT}")
    uvicorn.run(app, host="0.0.0.0", port=CONSUMER_PORT)
