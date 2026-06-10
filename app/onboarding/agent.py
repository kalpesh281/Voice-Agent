"""LangGraph onboarding agent — guides clients through setup via conversation.

Architecture:
    START → collect_info → (tool_calls?) → tools → collect_info → ... → END
"""

import json
import logging
import re

from langchain_core.messages import SystemMessage
from langchain_openrouter import ChatOpenRouter
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from app.config import Settings
from app.db.models import ClientUser
from app.onboarding.state import OnboardingState
from app.onboarding.tools import save_client_config, validate_db_connection

logger = logging.getLogger(__name__)

# Fields the <meta> block is allowed to update
_UPDATABLE_FIELDS = {
    "owner_name", "owner_email", "owner_phone",
    "business_name", "business_location", "business_category",
    "connection_uri", "database_name", "resources_collection",
    "agent_name", "tts_voice", "greeting_template",
    "resource_id_field", "resource_name_field",
    "resource_price_field", "resource_availability_field",
}

ONBOARDING_SYSTEM_PROMPT = """You are an expert business setup assistant for a voice booking agent platform.
Your job is to gather all the configuration needed to set up the client's AI voice booking agent.

The user has just signed up. Guide them through a friendly, conversational setup.

CURRENT STEP: {current_step}
ALREADY COLLECTED: {collected_summary}

STEP GUIDE:
1. intro: Brief welcome. Explain what you'll gather — their business info, database, and voice agent preferences.
   Their name is already known — do NOT ask for it. Jump straight to asking about their business.
2. business: Collect business name, location, category.
   Categories: hotel, restaurant, table_booking, cricket_ground, pickleball, ecommerce.
   Once you have category, IMMEDIATELY suggest smart defaults:
   - hotel: agent_name=Aria, tts_voice=aura-asteria-en, resources_collection=rooms, price_field=price_per_night
   - restaurant/table_booking: agent_name=Maya, tts_voice=aura-luna-en, resources_collection=tables, price_field=price_per_head
   - cricket_ground/pickleball: agent_name=Raj, tts_voice=aura-orion-en, resources_collection=courts, price_field=price_per_slot
   - ecommerce: agent_name=Aria, tts_voice=aura-asteria-en, resources_collection=products, price_field=price
3. database: Collect MongoDB URI and database name.
   - Call validate_db_connection() to verify the URI.
   - If validation succeeds, show available collections and ask which one has their resources.
   - If validation fails, explain the error clearly and ask them to try again.
   - If they say "use platform db" or "skip" or "test mode", accept empty URI and move on.
4. voice: Confirm or adjust agent name, personality, greeting template.
   - Suggest a greeting and KEEP the literal placeholders {business_name} and
     {agent_name} in the template — do NOT substitute the actual names. E.g.
     "Hello, welcome to {business_name}, I'm {agent_name}, how can I help today?"
     (They are filled in at call time, so the greeting stays correct after a rename.)
   - Ask if it sounds right or if they want to customize.
5. review: Read back ALL collected details in a clear format. Ask for final confirmation.
6. complete: Call save_client_config() with ALL collected fields. Celebrate — tell them their agent is ready!

RULES:
- Ask ONE thing at a time.
- Keep every message to 1-2 short sentences max. No exceptions.
- Write like a text message — casual, direct, no fluff. Never use bullet points or bold text in your replies.
- When you suggest defaults, just state them plainly. No need to explain unless asked.
- If a field is optional, mention it in one word ("optional:").
- At the review step, do NOT read back a long summary — just say something like "Here's everything we've got — review and edit if needed." The UI will show the actual details.
- When calling save_client_config, pass the user_id: {user_id}

META TRACKING (required after every response):
After your conversational message, on a new line, output this JSON block exactly as shown:
<meta>{{"next_step": "STEP", "updates": {{}}}}</meta>

- "next_step" = the step you are NOW in after this message
- "updates" = only fields confirmed in THIS turn (omit unchanged fields)
- Valid step names: intro, business, database, voice, review, complete
- Valid update keys: owner_name, owner_email, owner_phone, business_name, business_location,
  business_category, connection_uri, database_name, resources_collection, agent_name,
  tts_voice, greeting_template, resource_price_field

Example — user just confirmed business name and you moved to database step:
<meta>{{"next_step": "database", "updates": {{"business_name": "Seaside Hotel", "business_category": "hotel"}}}}</meta>

ALWAYS output this block, even if nothing changed (updates can be {{}}).
"""


def _build_collected_summary(state: OnboardingState) -> str:
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


def _clean_value(value: str) -> str:
    """Strip markdown formatting and trailing descriptions from short identifier values."""
    value = re.sub(r'\*+', '', value)   # remove ** bold markers
    value = value.replace('`', '')       # remove backticks
    for sep in [' — ', ' - ']:          # only strip after em/en dash (not comma or period)
        if sep in value:
            value = value.split(sep)[0]
    return value.strip()


def _clean_greeting(value: str) -> str:
    """Strip markdown artifacts from greeting sentences while keeping full text."""
    value = re.sub(r'^[\s>]+', '', value)   # strip leading > blockquote markers
    value = re.sub(r'\*+', '', value)        # strip * and ** bold/italic markers
    value = value.strip().strip('"').strip("'")  # strip surrounding quotes
    return value.strip()


def _parse_meta(content: str) -> tuple[str | None, dict]:
    """Extract <meta> block from LLM response. Returns (next_step, updates)."""
    match = re.search(r'<meta>\s*(\{.*?\})\s*</meta>', content, re.DOTALL)
    if not match:
        return None, {}
    raw = match.group(1)
    try:
        meta = json.loads(raw)
    except json.JSONDecodeError:
        # Lenient fallback: extract key:value pairs even if JSON is malformed
        meta = {"updates": {}}
        step_m = re.search(r'["\']?next_step["\']?\s*:\s*["\'](\w+)["\']', raw)
        if step_m:
            meta["next_step"] = step_m.group(1)
        for kv in re.finditer(r'["\']?(\w+)["\']?\s*:\s*["\']([^"\'}\n]+)["\']', raw):
            if kv.group(1) != "next_step":
                meta["updates"][kv.group(1)] = kv.group(2)
    next_step = meta.get("next_step")
    updates = {}
    for k, v in meta.get("updates", {}).items():
        if k in _UPDATABLE_FIELDS and v:
            updates[k] = _clean_greeting(str(v)) if k == "greeting_template" else _clean_value(str(v))
    return next_step, updates


def strip_meta(text: str) -> str:
    """Remove <meta>...</meta> block from text for frontend display."""
    return re.sub(r'\s*<meta>.*?</meta>', '', text, flags=re.DOTALL).strip()


def build_onboarding_graph(user: ClientUser, app_settings: Settings):
    """Build the onboarding LangGraph agent for a user."""

    tools = [validate_db_connection, save_client_config]

    llm = ChatOpenRouter(
        model=app_settings.llm_model,
        temperature=0.7,
        api_key=app_settings.openrouter_api_key,
    )
    llm_with_tools = llm.bind_tools(tools)
    tool_node = ToolNode(tools)

    async def collect_info(state: OnboardingState) -> dict:
        current_step = state.get("current_step", "intro")
        collected = _build_collected_summary(state)
        prompt = ONBOARDING_SYSTEM_PROMPT.format(
            current_step=current_step,
            collected_summary=collected,
            user_id=state.get("user_id", ""),
        )
        messages = [SystemMessage(content=prompt)] + state["messages"]
        response = await llm_with_tools.ainvoke(messages)

        result: dict = {"messages": [response]}

        # Only parse meta on plain text responses (not tool calls)
        if not (getattr(response, "tool_calls", None)):
            next_step, updates = _parse_meta(response.content or "")
            if next_step:
                result["current_step"] = next_step
            result.update(updates)

        return result

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

    # MemorySaver keeps state alive across invocations within the same WebSocket session
    compiled = graph.compile(checkpointer=MemorySaver())
    logger.info("Onboarding graph compiled for user '%s'", user.user_id)
    return compiled
