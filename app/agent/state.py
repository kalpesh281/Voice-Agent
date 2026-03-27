from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """State flowing through the LangGraph voice booking agent."""

    messages: Annotated[list, add_messages]
    client_id: str
    client_config: dict
    pending_booking: dict | None
