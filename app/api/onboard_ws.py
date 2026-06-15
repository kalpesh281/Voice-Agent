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
from app.onboarding.agent import build_onboarding_graph, strip_meta, _clean_value, _clean_greeting, extract_text_content, extract_meta_json
from app.onboarding.tools import save_client_config
from app.utils.session import COOKIE_NAME, verify_session

logger = logging.getLogger(__name__)

# Fields that we try to extract from agent messages for the live preview
CONFIG_PREVIEW_FIELDS = [
    "business_name", "business_category", "business_location",
    "agent_name", "tts_voice", "greeting_template",
    "connection_uri", "database_name", "resources_collection",
    "owner_name", "owner_email", "owner_phone",
]


_PREVIEW_UPDATABLE = {
    "business_name", "business_category", "business_location",
    "agent_name", "tts_voice", "greeting_template",
    "connection_uri", "database_name", "resources_collection",
    "owner_name", "owner_email", "owner_phone", "resource_price_field",
}

_CATEGORIES = {"hotel", "restaurant", "table_booking", "cricket_ground", "pickleball", "ecommerce"}

_FIELD_LABEL_MAP = {
    "agent name": "agent_name",
    "tts voice": "tts_voice", "text-to-speech voice": "tts_voice",
    "resources collection": "resources_collection", "collection": "resources_collection",
    "price field": "resource_price_field",
    "business name": "business_name",
    "business location": "business_location", "location": "business_location",
    "business category": "business_category", "category": "business_category",
    "database name": "database_name", "db name": "database_name",
    "connection uri": "connection_uri", "mongodb uri": "connection_uri",
    "greeting template": "greeting_template", "greeting": "greeting_template",
    "owner name": "owner_name", "owner email": "owner_email", "owner phone": "owner_phone",
}


def _scan_meta_blocks(messages: list) -> dict:
    """Scan ALL AI messages for <meta> blocks and accumulate field updates.

    More reliable than regex on prose — covers cases where the LLM outputs
    meta correctly but doesn't use **Field:** formatting elsewhere.
    """
    config = {}
    for msg in messages:
        if not (hasattr(msg, "type") and msg.type == "ai" and msg.content):
            continue
        text_content = extract_text_content(msg.content)
        raw = extract_meta_json(text_content)
        if not raw:
            continue
        try:
            meta = json.loads(raw)
        except json.JSONDecodeError:
            # Lenient fallback: extract key:value pairs with regex even if JSON is malformed
            meta = {"updates": {}}
            for kv in re.finditer(r'["\']?(\w+)["\']?\s*:\s*["\']([^"\'}\n]+)["\']', raw):
                meta["updates"][kv.group(1)] = kv.group(2)
        for k, v in meta.get("updates", {}).items():
            if k in _PREVIEW_UPDATABLE and v:
                cleaner = _clean_greeting if k == "greeting_template" else _clean_value
                config[k] = cleaner(str(v))
    return config


def _scan_prose(messages: list) -> dict:
    """Fallback: extract config values from **Field:** value patterns and AI defaults suggestions."""
    config = {}
    for msg in messages:
        if not (hasattr(msg, "type") and msg.type == "ai" and msg.content):
            continue
        content = extract_text_content(msg.content).strip()
        lower = content.lower()

        # **Field:** value  or  - Field: value
        for m in re.finditer(r"(?:\*\*(.+?)\*\*|[-•]\s*(.+?)):\s*(.+?)(?:\n|$)", content):
            label = (m.group(1) or m.group(2) or "").strip().lower()
            value = m.group(3).strip().strip('"').strip("'").rstrip(".")
            if not value or len(value) > 200:
                continue
            for pattern, key in _FIELD_LABEL_MAP.items():
                if pattern in label:
                    if key == "tts_voice" and "aura" not in value.lower():
                        continue
                    config[key] = value
                    break

        # key=value defaults suggestions (e.g. agent_name=Aria, tts_voice=aura-asteria-en)
        for m in re.finditer(r'(\w+)\s*=\s*([^\s,\n]+)', content):
            k, v = m.group(1), m.group(2).strip()
            if k in _PREVIEW_UPDATABLE and v:
                cleaner = _clean_greeting if k == "greeting_template" else _clean_value
                config.setdefault(k, cleaner(v))

        # Aura voice model anywhere in AI message. Match the FULL id including the
        # trailing "-en" (and the optional "-2" generation segment) — the old
        # `aura-[\w]+-[\w]+` stopped at "aura-2-thalia", dropping "-en" and
        # producing an invalid model id that Deepgram rejects.
        aura_m = re.search(r'aura(?:-2)?-[a-z]+-en', lower)
        if aura_m:
            config.setdefault("tts_voice", aura_m.group(0))

        # Category mentions
        for cat in _CATEGORIES:
            if (f"category is {cat}" in lower or f"is a {cat.replace('_', ' ')}" in lower
                    or f"your business is a {cat.replace('_', ' ')}" in lower):
                config["business_category"] = cat
                break
    return config


def _extract_from_exchange(messages: list) -> dict:
    """Correlate user replies with the preceding AI question to extract field values.

    Doesn't rely on any LLM formatting — works with plain casual language.
    Iterates every human message and checks what the AI just asked about.
    """
    config = {}
    indexed = list(messages)

    for i, msg in enumerate(indexed):
        if not (hasattr(msg, "type") and msg.type == "human" and msg.content):
            continue

        reply = extract_text_content(msg.content).strip().strip('"').strip("'")
        if not reply or len(reply) > 400:
            continue

        # Find the immediately preceding AI message
        prev_ai = ""
        for j in range(i - 1, -1, -1):
            m = indexed[j]
            if hasattr(m, "type") and m.type == "ai" and m.content:
                prev_ai = strip_meta(m.content).lower()
                break

        if not prev_ai:
            continue

        low_reply = reply.lower()

        # Business name
        if any(p in prev_ai for p in ["business name", "your business called", "name of your business"]):
            config.setdefault("business_name", reply)

        # Location
        if any(p in prev_ai for p in ["located", "location", "city", "where is your business", "where are you based"]):
            config.setdefault("business_location", reply)

        # Category
        if any(p in prev_ai for p in ["category", "what type", "what kind of business"]):
            for cat in ["table_booking", "cricket_ground", "hotel", "restaurant", "pickleball", "ecommerce"]:
                if cat.replace("_", " ") in low_reply or cat in low_reply:
                    config.setdefault("business_category", cat)
                    break

        # Agent name
        if any(p in prev_ai for p in ["agent name", "call your agent", "name your agent", "agent's name"]):
            if len(reply) < 50:
                config.setdefault("agent_name", reply)

        # Greeting
        if any(p in prev_ai for p in ["greeting", "how should your agent greet", "sound right"]):
            config.setdefault("greeting_template", _clean_greeting(reply))

        # Database name
        if any(p in prev_ai for p in ["database name", "db name", "name of the database"]):
            if len(reply) < 100:
                config.setdefault("database_name", reply)

        # Resources collection
        if any(p in prev_ai for p in ["collection", "which collection", "resources live"]):
            if len(reply) < 60:
                config.setdefault("resources_collection", reply)

        # MongoDB URI (user provides it or says skip)
        if any(p in prev_ai for p in ["mongodb uri", "connection uri", "connection string", "mongodb+srv"]):
            if "mongodb" in low_reply:
                config.setdefault("connection_uri", reply)

    return config


async def _send_config_updates(websocket: WebSocket, result: dict):
    """Send collected field updates to the frontend for live preview."""
    config = {}

    # Layer 1 — state fields written by collect_info via <meta> parsing
    for field in CONFIG_PREVIEW_FIELDS:
        value = result.get(field)
        if value:
            config[field] = value

    messages = result.get("messages", [])

    # Layer 2 — scan <meta> blocks accumulated across full conversation
    for field, value in _scan_meta_blocks(messages).items():
        if field not in config:
            config[field] = value

    # Layer 3 — prose regex fallback (**Field:** value patterns + key=value defaults)
    for field, value in _scan_prose(messages).items():
        if field not in config:
            config[field] = value

    # Layer 4 — conversation-flow extraction (AI question → user answer mapping)
    for field, value in _extract_from_exchange(messages).items():
        if field not in config:
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

    # Send greeting immediately — no LLM call, instant delivery
    try:
        name = (user.full_name or "").split()[0] if user.full_name else "there"
        greeting = (
            f"Hey {name}! I'll help you set up your AI voice booking agent. "
            "We'll go through your business details, database, and voice settings — "
            "should only take a few minutes. What's your business name?"
        )

        # Prime the checkpoint so LLM has full context from the first user message
        initial_state = {
            "messages": [AIMessage(content=greeting)],
            "user_id": user.user_id,
            "owner_name": user.full_name or "",
            "owner_email": user.email or "",
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
            "current_step": "business",
            "is_complete": False,
            "errors": [],
        }
        logger.info("Starting onboarding for user %s, session %s", user.user_id, session_id)
        await graph.aupdate_state(graph_config, initial_state)

        await websocket.send_json({
            "type": "agent_message",
            "text": greeting,
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

            if msg_type == "confirm":
                # User confirmed (possibly with edits) from the review card — save directly
                cfg = data.get("config", {})
                try:
                    # Merge graph state under cfg so user edits always win,
                    # but any field the frontend missed is filled from LangGraph state.
                    try:
                        snapshot = await graph.aget_state(graph_config)
                        state_vals = snapshot.values if snapshot else {}
                        cfg = {**state_vals, **cfg}
                    except Exception:
                        pass

                    # Timeout guards against a hung DB write leaving the
                    # frontend stuck on "Launching your agent…" forever.
                    tool_result = await asyncio.wait_for(
                        save_client_config.ainvoke({
                            "user_id": user_id,
                            "owner_name": cfg.get("owner_name", ""),
                            "owner_email": cfg.get("owner_email", user.email or ""),
                            "owner_phone": cfg.get("owner_phone", ""),
                            "business_name": cfg.get("business_name", ""),
                            "business_location": cfg.get("business_location", ""),
                            "business_category": cfg.get("business_category", ""),
                            "db_type": cfg.get("db_type", "mongodb"),
                            "connection_uri": cfg.get("connection_uri", ""),
                            "database_name": cfg.get("database_name", ""),
                            "resources_collection": cfg.get("resources_collection", ""),
                            "agent_name": cfg.get("agent_name", "Aria"),
                            "agent_personality": cfg.get("agent_personality", "Warm, friendly, professional"),
                            "greeting_template": cfg.get("greeting_template", ""),
                            "tts_voice": cfg.get("tts_voice", "aura-2-thalia-en"),
                            "resource_id_field": cfg.get("resource_id_field", "id"),
                            "resource_name_field": cfg.get("resource_name_field", "name"),
                            "resource_price_field": cfg.get("resource_price_field", "price"),
                            "resource_availability_field": cfg.get("resource_availability_field", "available"),
                            "searchable_fields": cfg.get("searchable_fields", []),
                        }),
                        timeout=15.0,
                    )
                    if tool_result.get("success"):
                        await websocket.send_json({
                            "type": "complete",
                            "client_id": tool_result.get("client_id", ""),
                        })
                        return
                    else:
                        err = tool_result.get("error", "Save failed. Please try again.")
                        logger.error("save_client_config returned failure: %s", err)
                        await websocket.send_json({"type": "confirm_error", "message": err})
                except asyncio.TimeoutError:
                    logger.error("Confirm save timed out for session %s", session_id)
                    await websocket.send_json({
                        "type": "confirm_error",
                        "message": "Saving timed out — check your database connection and try again.",
                    })
                except Exception as e:
                    import traceback
                    logger.error("Confirm save error: %s\n%s", e, traceback.format_exc())
                    await websocket.send_json({"type": "confirm_error", "message": "Save failed. Please try again."})

            elif msg_type == "message":
                user_text = data.get("text", "").strip()
                if not user_text:
                    continue

                # Invoke the onboarding agent (30s timeout guards against hung LLM calls)
                try:
                    result = await asyncio.wait_for(
                        graph.ainvoke(
                            {"messages": [HumanMessage(content=user_text)]},
                            config=graph_config,
                        ),
                        timeout=30.0,
                    )

                    is_review = result.get("current_step") == "review"

                    if is_review:
                        # Replace the agent's verbose summary with a single handoff line
                        await websocket.send_json({
                            "type": "agent_message",
                            "text": "Here's everything we've collected — review and edit anything below before going live.",
                            "field": None,
                            "value": None,
                        })
                    else:
                        last_msg = result["messages"][-1]
                        if isinstance(last_msg, AIMessage) and last_msg.content:
                            await websocket.send_json({
                                "type": "agent_message",
                                "text": strip_meta(last_msg.content),
                                "field": None,
                                "value": None,
                            })

                    # Send config preview updates from graph state
                    await _send_config_updates(websocket, result)

                    if is_review:
                        await websocket.send_json({"type": "review_card"})

                    # Check for successful save — scan from most recent message only
                    messages = result.get("messages", [])
                    for msg in reversed(messages):
                        if hasattr(msg, "name") and msg.name == "save_client_config":
                            try:
                                if isinstance(msg.content, str):
                                    tool_result = json.loads(msg.content)
                                elif isinstance(msg.content, dict):
                                    tool_result = msg.content
                                else:
                                    tool_result = {}
                                if tool_result.get("success"):
                                    await websocket.send_json({
                                        "type": "complete",
                                        "client_id": tool_result.get("client_id", ""),
                                    })
                                    return
                            except Exception:
                                pass
                            break  # Only check the most recent save attempt

                except Exception as e:
                    import traceback
                    logger.error("Onboarding agent error: %s\n%s", e, traceback.format_exc())
                    # Send a recoverable agent message so the frontend isn't left waiting
                    await websocket.send_json({
                        "type": "agent_message",
                        "text": "Sorry, I ran into a small hiccup. Could you repeat that?",
                        "field": None,
                        "value": None,
                    })

        except WebSocketDisconnect:
            logger.info("Onboarding WS disconnected: session=%s", session_id)
            break
        except Exception as e:
            logger.error("Onboarding WS error: %s", e)
            break
