"""LangGraph StateGraph for the voice booking agent.

Architecture:
    START → respond → (tool_calls?) → tools → respond → ... → END
"""

import logging

from langchain_core.messages import SystemMessage, trim_messages
from langchain_openrouter import ChatOpenRouter
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode
from pymongo import MongoClient

from app.agent.state import AgentState
from app.agent.tools.registry import build_tools
from app.config import Settings
from app.db.models import ClientConfig
from app.utils.prompt_builder import build_system_prompt

logger = logging.getLogger(__name__)


def build_graph(config: ClientConfig, app_settings: Settings):
    """Build and compile the LangGraph agent for a given client config.

    Returns a compiled graph that takes AgentState and returns AgentState.
    """
    tools = build_tools(config)
    system_prompt = build_system_prompt(config)

    llm = ChatOpenRouter(
        model=app_settings.llm_model,
        temperature=app_settings.llm_temperature,
        api_key=app_settings.openrouter_api_key,
    )
    # Retry transient provider failures. OpenRouter intermittently returns a JSON
    # error body ("Provider returned error", 502) instead of a completion, which
    # raises mid-turn and — over LiveKit — leaves the agent stuck after only its
    # preamble ("Absolutely! Let me search..."), the reply never arriving. A few
    # exponential-backoff retries turn those blips into a brief pause, not a dead
    # turn. (Genuine errors still surface after the attempts are exhausted.)
    llm_with_tools = llm.bind_tools(tools).with_retry(
        stop_after_attempt=3,
        wait_exponential_jitter=True,
    )

    tool_node = ToolNode(tools)

    # ── Graph nodes ──

    async def respond(state: AgentState) -> dict:
        """Invoke the LLM with the conversation history and tools.

        On long calls the checkpointer keeps growing the message history, which
        would slowly inflate latency and token cost on every turn. We feed the
        LLM only a rolling window of the most recent messages (the system prompt
        carries the durable context), keeping per-turn cost flat no matter how
        long the conversation runs. Full history is still persisted by the
        checkpointer; we just don't resend all of it each turn.
        """
        history = trim_messages(
            state["messages"],
            strategy="last",
            token_counter=len,        # count messages, not tokens — cheap & predictable
            max_tokens=24,            # keep the last ~12 exchanges
            start_on="human",         # never start on an orphaned tool/ai message
            end_on=("human", "tool", "ai"),
            include_system=False,
            allow_partial=False,
        )
        messages = [SystemMessage(content=system_prompt)] + history
        response = await llm_with_tools.ainvoke(messages)
        return {"messages": [response]}

    # ── Routing logic ──

    def should_use_tools(state: AgentState) -> str:
        """Route to tools node if the LLM made tool calls, else end."""
        last_message = state["messages"][-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        return END

    # ── Build the graph ──

    graph = StateGraph(AgentState)
    graph.add_node("respond", respond)
    graph.add_node("tools", tool_node)

    graph.set_entry_point("respond")
    graph.add_conditional_edges("respond", should_use_tools, {"tools": "tools", END: END})
    graph.add_edge("tools", "respond")

    # ── Checkpointer (MongoDB) ──

    checkpointer = None
    try:
        from langgraph.checkpoint.mongodb import MongoDBSaver

        sync_client = MongoClient(
            app_settings.mongodb_uri,
            maxPoolSize=5,
            serverSelectionTimeoutMS=3000,
        )
        checkpointer = MongoDBSaver(
            client=sync_client,
            db_name=app_settings.mongodb_database,
        )
        logger.info("MongoDB checkpointer initialized")
    except Exception as e:
        logger.warning("Failed to initialize MongoDB checkpointer: %s. Running without state persistence.", e)

    compiled = graph.compile(checkpointer=checkpointer)
    logger.info("Agent graph compiled for client '%s'", config.client_id)
    return compiled
