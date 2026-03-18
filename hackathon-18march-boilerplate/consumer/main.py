import logging
import json
import anthropic
from orca import create_agent_app, ChatMessage, OrcaHandler, Variables, ChatHistoryHelper

logger = logging.getLogger(__name__)


def build_agent_tools(available_agents: list) -> tuple[list[dict], str]:
    """Build tool definitions for querying provider agents + presenting results."""
    agent_descriptions = []
    for agent in available_agents:
        agent_descriptions.append(f"- **{agent.slug}**: {agent.name} — {agent.description}")

    agents_list = "\n".join(agent_descriptions) if agent_descriptions else "No providers connected yet."

    tools = [
        {
            "name": "ask_provider",
            "description": (
                "Query a provider agent on the Orca mesh network. Each provider wraps a specific "
                "travel API (hotels, flights, restaurants, car rentals, tours, museums). "
                "Send a natural language question and get structured travel data back."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "agent_slug": {
                        "type": "string",
                        "description": "The slug of the provider agent to query",
                    },
                    "question": {
                        "type": "string",
                        "description": (
                            "Natural language question for the provider. Be specific: "
                            "include dates, number of guests, location, budget, etc."
                        ),
                    },
                },
                "required": ["agent_slug", "question"],
            },
        },
        {
            "name": "present_travel_plan",
            "description": (
                "Present the final travel plan or response to the user. Use this once you've "
                "gathered all needed information from providers. Format it nicely."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "response": {
                        "type": "string",
                        "description": "The formatted travel plan or response for the user",
                    },
                },
                "required": ["response"],
            },
        },
    ]

    return tools, agents_list


async def process_message(data: ChatMessage):
    handler = OrcaHandler()
    session = handler.begin(data)

    try:
        variables = Variables(data.variables)
        anthropic_key = variables.get("ANTHROPIC_API_KEY")

        if not anthropic_key:
            session.stream("Missing ANTHROPIC_API_KEY in Orca variables.")
            session.close()
            return

        # Get conversation history for context
        history = ChatHistoryHelper(data.chat_history)
        recent_messages = history.get_last_n_messages(10)

        # Discover all connected provider agents
        tools, agents_list = build_agent_tools(session.available_agents)

        system_prompt = f"""You are a personal AI travel concierge — friendly, efficient, and knowledgeable.

## Your role
You help users plan trips by coordinating with specialized travel provider agents. You don't have travel data yourself — you MUST query providers to get real information.

## Available provider agents
{agents_list}

## How to work
1. When a user asks about travel, figure out which provider(s) you need.
2. Use `ask_provider` to query the relevant agents. Be specific in your questions — include dates, guest counts, locations, budgets.
3. You can query MULTIPLE providers in sequence to build a complete trip plan.
4. Once you have all the info, use `present_travel_plan` to give the user a clear, well-formatted response.

## Guidelines
- Always query providers for real data. Never make up prices, availability, or details.
- If multiple providers are relevant (e.g., flights + hotels + restaurants for a trip), query all of them.
- Compare options when possible — give the user choices with prices.
- Be conversational and helpful. Summarize data clearly.
- If a provider is unavailable or errors out, tell the user and suggest alternatives.
- For bookings, confirm details with the user before proceeding.
- Keep it practical — prioritize actionable information (prices, dates, availability)."""

        client = anthropic.Anthropic(api_key=anthropic_key)

        # Build message history for context
        messages = []
        for msg in recent_messages:
            role = "user" if msg.get("role") == "user" else "assistant"
            content = msg.get("content", "")
            if content:
                messages.append({"role": role, "content": content})

        # Ensure the current message is included
        if not messages or messages[-1].get("content") != data.message:
            messages.append({"role": "user", "content": data.message})

        # Ensure messages alternate roles (Anthropic requirement)
        cleaned = []
        for msg in messages:
            if cleaned and cleaned[-1]["role"] == msg["role"]:
                cleaned[-1]["content"] += "\n" + msg["content"]
            else:
                cleaned.append(msg)
        messages = cleaned

        # Ensure first message is from user
        if messages and messages[0]["role"] != "user":
            messages = messages[1:]
        if not messages:
            messages = [{"role": "user", "content": data.message}]

        session.loading.start("Planning")
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            system=system_prompt,
            tools=tools,
            messages=messages,
        )
        session.loading.end("Planning")

        # Tool use loop
        max_iterations = 10  # Consumer may need multiple provider calls
        iteration = 0
        while response.stop_reason == "tool_use" and iteration < max_iterations:
            iteration += 1
            tool_results = []

            for block in response.content:
                if block.type == "tool_use":
                    tool_name = block.name
                    tool_input = block.input

                    if tool_name == "ask_provider":
                        slug = tool_input["agent_slug"]
                        question = tool_input["question"]
                        session.loading.start(f"Asking {slug}")
                        try:
                            provider_response = session.ask_agent(slug, question, timeout=120)
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": str(provider_response)[:4000],
                            })
                        except ValueError:
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": f"Agent '{slug}' is not connected. Available agents: "
                                           f"{', '.join(a.slug for a in session.available_agents)}",
                                "is_error": True,
                            })
                        except RuntimeError as e:
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": f"Agent '{slug}' is unavailable: {str(e)}",
                                "is_error": True,
                            })
                        finally:
                            session.loading.end(f"Asking {slug}")

                    elif tool_name == "present_travel_plan":
                        # Stream the final response to the user
                        session.stream(tool_input["response"])
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": "Response sent to user.",
                        })

            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})

            # Check if we already presented to the user
            presented = any(
                b.type == "tool_use" and b.name == "present_travel_plan"
                for b in response.content
            )
            if presented:
                break

            session.loading.start("Thinking")
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2048,
                system=system_prompt,
                tools=tools,
                messages=messages,
            )
            session.loading.end("Thinking")

        # If we exited without presenting, extract any text
        if response.stop_reason != "tool_use":
            final_text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    final_text += block.text
            if final_text:
                session.stream(final_text)

        session.close()

    except Exception as e:
        logger.exception("Error processing message")
        session.error("Something went wrong.", exception=e)


app, orca = create_agent_app(
    process_message_func=process_message,
    title="Consumer Agent",
    description="Personal AI travel concierge — coordinates with provider agents to plan trips",
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
