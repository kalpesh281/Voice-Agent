"""LangGraph onboarding agent — guides clients through setup via conversation.

Architecture:
    START → collect_info → (tool_calls?) → tools → collect_info → ... → END
"""

import logging

from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from app.config import Settings
from app.db.models import ClientUser
from app.onboarding.state import OnboardingState
from app.onboarding.tools import save_client_config, validate_db_connection

logger = logging.getLogger(__name__)

ONBOARDING_SYSTEM_PROMPT = """You are an expert business setup assistant for a voice booking agent platform.
Your job is to gather all the configuration needed to set up the client's AI voice booking agent.

The user has just signed up. Guide them through a friendly, conversational setup.

CURRENT STEP: {current_step}
ALREADY COLLECTED: {collected_summary}

STEP GUIDE:
1. intro: Brief welcome. Explain what you'll gather — their business info, database, and voice agent preferences. Ask for their name.
2. owner: Collect owner name, email, phone (phone is optional — say so).
3. business: Collect business name, location, category.
   Categories: hotel, restaurant, table_booking, cricket_ground, pickleball, ecommerce.
   Once you have category, IMMEDIATELY suggest smart defaults:
   - hotel: agent_name=Aria, tts_voice=aura-asteria-en, resources_collection=rooms, price_field=price_per_night
   - restaurant/table_booking: agent_name=Maya, tts_voice=aura-luna-en, resources_collection=tables, price_field=price_per_head
   - cricket_ground/pickleball: agent_name=Raj, tts_voice=aura-orion-en, resources_collection=courts, price_field=price_per_slot
   - ecommerce: agent_name=Aria, tts_voice=aura-asteria-en, resources_collection=products, price_field=price
4. database: Collect MongoDB URI and database name.
   - Call validate_db_connection() to verify the URI.
   - If validation succeeds, show available collections and ask which one has their resources.
   - If validation fails, explain the error clearly and ask them to try again.
   - If they say "use platform db" or "skip" or "test mode", accept empty URI and move on.
5. voice: Confirm or adjust agent name, personality, greeting template.
   - Suggest a greeting: "Hello, welcome to [business_name], I'm [agent_name]..."
   - Ask if it sounds right or if they want to customize.
6. review: Read back ALL collected details in a clear format. Ask for final confirmation.
7. complete: Call save_client_config() with ALL collected fields. Celebrate — tell them their agent is ready!

RULES:
- Ask ONE thing at a time. Do not dump multiple questions in one message.
- Be warm and encouraging. This is exciting — they're setting up their AI agent!
- When you suggest defaults, explain WHY briefly.
- If a field is optional (phone, personality), say so explicitly.
- Keep messages under 4 sentences unless reading back the full review.
- NEVER skip the review step — always read back details before saving.
- For the review step, format it nicely with each field on its own line.
- When calling save_client_config, pass the user_id: {user_id}
"""


def _build_collected_summary(state: OnboardingState) -> str:
    """Build a summary of already-collected fields for the system prompt."""
    fields = [
        ("Owner Name", state.get("owner_name")),
        ("Owner Email", state.get("owner_email")),
        ("Owner Phone", state.get("owner_phone")),
        ("Business Name", state.get("business_name")),
        ("Location", state.get("business_location")),
        ("Category", state.get("business_category")),
        ("DB URI", "***set***" if state.get("connection_uri") else ""),
        ("DB Name", state.get("database_name")),
        ("Resources Collection", state.get("resources_collection")),
        ("Agent Name", state.get("agent_name")),
        ("TTS Voice", state.get("tts_voice")),
        ("Greeting", state.get("greeting_template")),
    ]
    collected = [f"- {name}: {val}" for name, val in fields if val]
    return "\n".join(collected) if collected else "(nothing yet)"


def build_onboarding_graph(user: ClientUser, app_settings: Settings):
    """Build the onboarding LangGraph agent for a user."""

    tools = [validate_db_connection, save_client_config]

    llm = ChatOpenAI(
        model=app_settings.llm_model,
        temperature=0.7,
        api_key=app_settings.openai_api_key,
    )
    llm_with_tools = llm.bind_tools(tools)
    tool_node = ToolNode(tools)

    async def collect_info(state: OnboardingState) -> dict:
        """Main node: invoke LLM to guide the conversation."""
        current_step = state.get("current_step", "intro")
        collected = _build_collected_summary(state)
        prompt = ONBOARDING_SYSTEM_PROMPT.format(
            current_step=current_step,
            collected_summary=collected,
            user_id=state.get("user_id", ""),
        )
        messages = [SystemMessage(content=prompt)] + state["messages"]
        response = await llm_with_tools.ainvoke(messages)
        return {"messages": [response]}

    def should_use_tools(state: OnboardingState) -> str:
        last_message = state["messages"][-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        return END

    graph = StateGraph(OnboardingState)
    graph.add_node("collect_info", collect_info)
    graph.add_node("tools", tool_node)

    graph.set_entry_point("collect_info")
    graph.add_conditional_edges("collect_info", should_use_tools, {"tools": "tools", END: END})
    graph.add_edge("tools", "collect_info")

    # No checkpointer for onboarding — conversations are short-lived
    # and the WebSocket session maintains state in memory
    compiled = graph.compile()
    logger.info("Onboarding graph compiled for user '%s'", user.user_id)
    return compiled
