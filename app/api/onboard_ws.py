"""WebSocket endpoint for the onboarding chat agent.

Flow:
  Browser sends user messages → LangGraph onboarding agent processes → agent replies
  Progress updates and field extractions are sent as structured JSON.
"""

import asyncio
import json
import logging
import re

from fastapi import WebSocket, WebSocketDisconnect
from langchain_core.messages import AIMessage, HumanMessage

from app.config import settings
from app.db.repositories.user_repo import UserRepository
from app.onboarding.agent import build_onboarding_graph
from app.utils.session import COOKIE_NAME, verify_session

logger = logging.getLogger(__name__)

# Fields that we try to extract from agent messages for the live preview
CONFIG_PREVIEW_FIELDS = [
    "business_name", "business_category", "business_location",
    "agent_name", "tts_voice", "greeting_template",
    "connection_uri", "database_name", "resources_collection",
    "owner_name", "owner_email", "owner_phone",
]


def _extract_config_from_conversation(messages: list) -> dict:
    """Extract config values from the full conversation by scanning AI messages.

    Looks for the agent's summary/recap blocks which list fields like:
      - **Agent Name:** Maya
      - **Resources Collection:** rooms
    Also extracts from confirmation patterns.
    """
    import re
    config = {}
    categories = {"hotel", "restaurant", "table_booking", "cricket_ground", "pickleball", "ecommerce"}

    field_map = {
        "agent name": "agent_name",
        "tts voice": "tts_voice",
        "text-to-speech voice": "tts_voice",
        "voice": "tts_voice",
        "resources collection": "resources_collection",
        "collection": "resources_collection",
        "price field": "resource_price_field",
        "business name": "business_name",
        "business location": "business_location",
        "location": "business_location",
        "business category": "business_category",
        "category": "business_category",
        "database name": "database_name",
        "connection uri": "connection_uri",
        "greeting template": "greeting_template",
        "greeting": "greeting_template",
        "owner name": "owner_name",
        "owner email": "owner_email",
        "owner phone": "owner_phone",
    }

    for msg in messages:
        if not hasattr(msg, "content") or not msg.content:
            continue
        content = msg.content.strip()
        if not hasattr(msg, "type") or msg.type != "ai":
            continue

        # Match both "**Field:** value" and "- Field: value" patterns
        for match in re.finditer(
            r"(?:\*\*(.+?)\*\*|[-•]\s*(.+?)):\s*(.+?)(?:\n|$)", content
        ):
            label = (match.group(1) or match.group(2) or "").strip().lower()
            value = match.group(3).strip().strip('"').strip("'").rstrip(".")

            if not value or len(value) > 200:
                continue

            for key_pattern, config_key in field_map.items():
                if key_pattern in label:
                    # Don't overwrite tts_voice with agent name
                    if config_key == "tts_voice" and "aura" not in value.lower():
                        continue
                    config[config_key] = value
                    break

        # Extract category from mentions
        lower = content.lower()
        for cat in categories:
            cat_display = cat.replace("_", " ")
            if (f"category is {cat}" in lower or f"category: {cat}" in lower
                    or f"is a {cat_display}" in lower
                    or f"your business is a {cat_display}" in lower):
                config["business_category"] = cat
                break

    return config


async def _send_config_updates(websocket: WebSocket, result: dict):
    """Extract collected fields from conversation and send them for live preview."""
    messages = result.get("messages", [])
    config = _extract_config_from_conversation(messages)

    # Also check direct state fields
    for field in CONFIG_PREVIEW_FIELDS:
        value = result.get(field)
        if value and field not in config:
            config[field] = value

    for field, value in config.items():
        try:
            await websocket.send_json({
                "type": "config_update",
                "field": field,
                "value": value,
            })
        except Exception:
            pass


async def onboard_websocket_endpoint(websocket: WebSocket, session_id: str):
    """Handle an onboarding chat session over WebSocket."""
    await websocket.accept()

    # Authenticate via session cookie
    cookie = websocket.cookies.get(COOKIE_NAME)
    if not cookie:
        await websocket.send_json({"type": "error", "message": "Not authenticated"})
        await websocket.close()
        return

    user_id = verify_session(cookie)
    if not user_id:
        await websocket.send_json({"type": "error", "message": "Session expired"})
        await websocket.close()
        return

    user_repo = UserRepository()
    user = await user_repo.get_by_id(user_id)
    if not user:
        await websocket.send_json({"type": "error", "message": "User not found"})
        await websocket.close()
        return

    # Already onboarded? Tell the frontend
    if user.onboarding_complete:
        await websocket.send_json({"type": "complete", "client_id": user.client_id})
        await websocket.close()
        return

    # Build onboarding agent
    graph = build_onboarding_graph(user, settings)
    graph_config = {"configurable": {"thread_id": session_id}}

    # Send initial agent greeting
    try:
        initial_state = {
            "messages": [HumanMessage(content=f"Hi, my name is {user.full_name or 'there'}. I just signed up. Please welcome me, explain what we'll set up together (business info, database, voice agent), and then start by asking for my business details.")],
            "user_id": user.user_id,
            "owner_name": user.full_name,
            "owner_email": user.email,
            "owner_phone": "",
            "business_name": "",
            "business_location": "",
            "business_category": "",
            "db_type": "mongodb",
            "connection_uri": "",
            "database_name": "",
            "resources_collection": "",
            "agent_name": "",
            "agent_personality": "",
            "greeting_template": "",
            "tts_voice": "",
            "resource_id_field": "",
            "resource_name_field": "",
            "resource_price_field": "",
            "resource_availability_field": "",
            "searchable_fields": [],
            "current_step": "intro",
            "is_complete": False,
            "errors": [],
        }
        logger.info("Starting onboarding for user %s, session %s", user.user_id, session_id)
        result = await graph.ainvoke(initial_state, config=graph_config)
        last_msg = result["messages"][-1]
        if isinstance(last_msg, AIMessage) and last_msg.content:
            await websocket.send_json({
                "type": "agent_message",
                "text": last_msg.content,
                "field": None,
                "value": None,
            })
    except Exception as e:
        logger.error("Onboarding greeting error: %s", e)
        await websocket.send_json({"type": "error", "message": "Failed to start onboarding"})
        await websocket.close()
        return

    # Main chat loop
    while True:
        try:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "stop":
                break

            if msg_type == "message":
                user_text = data.get("text", "").strip()
                if not user_text:
                    continue

                # Invoke the onboarding agent
                try:
                    result = await graph.ainvoke(
                        {"messages": [HumanMessage(content=user_text)]},
                        config=graph_config,
                    )

                    # Process the response — extract field values for live preview
                    for msg in result.get("messages", []):
                        # Check tool results for completion
                        if hasattr(msg, "name") and msg.name == "save_client_config":
                            try:
                                tool_result = json.loads(msg.content)
                                if tool_result.get("success"):
                                    # Refresh user data
                                    updated_user = await user_repo.get_by_id(user_id)
                                    await websocket.send_json({
                                        "type": "complete",
                                        "client_id": tool_result.get("client_id", ""),
                                    })
                                    return
                            except (json.JSONDecodeError, AttributeError):
                                pass

                    # Send the last AI message
                    last_msg = result["messages"][-1]
                    if isinstance(last_msg, AIMessage) and last_msg.content:
                        await websocket.send_json({
                            "type": "agent_message",
                            "text": last_msg.content,
                            "field": None,
                            "value": None,
                        })

                    # Send config preview updates from graph state
                    await _send_config_updates(websocket, result)

                except Exception as e:
                    logger.error("Onboarding agent error: %s", e)
                    await websocket.send_json({
                        "type": "error",
                        "message": "Something went wrong. Please try again.",
                    })

        except WebSocketDisconnect:
            logger.info("Onboarding WS disconnected: session=%s", session_id)
            break
        except Exception as e:
            logger.error("Onboarding WS error: %s", e)
            break
