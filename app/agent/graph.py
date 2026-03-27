"""LangGraph StateGraph for the voice booking agent.

Architecture:
    START → respond → (tool_calls?) → tools → respond → ... → END
"""

import logging

from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
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

    llm = ChatOpenAI(
        model=app_settings.llm_model,
        temperature=app_settings.llm_temperature,
        api_key=app_settings.openai_api_key,
        streaming=True,
    )
    llm_with_tools = llm.bind_tools(tools)

    tool_node = ToolNode(tools)

    # ── Graph nodes ──

    async def respond(state: AgentState) -> dict:
        """Invoke the LLM with the conversation history and tools."""
        messages = [SystemMessage(content=system_prompt)] + state["messages"]
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
