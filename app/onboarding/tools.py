"""Onboarding tools — validate DB connection and save client config."""

import logging
import re
from datetime import datetime, timezone

from langchain_core.tools import tool
from motor.motor_asyncio import AsyncIOMotorClient

from app.db.models import (
    BusinessDetails,
    ClientConfig,
    ClientDatabase,
    ClientOwner,
    DatabaseMapping,
    VoiceSettings,
)
from app.db.repositories.client_repo import ClientRepository
from app.db.repositories.user_repo import UserRepository

logger = logging.getLogger(__name__)


@tool
async def validate_db_connection(uri: str, db_name: str) -> dict:
    """Validate a MongoDB connection URI by attempting to connect and ping.

    Args:
        uri: MongoDB connection URI (e.g., mongodb+srv://user:pass@cluster.mongodb.net)
        db_name: Database name to connect to

    Returns:
        dict with success, collections list, and error message if any.
    """
    if not uri or not db_name:
        return {"success": False, "collections": [], "error": "Both URI and database name are required."}

    try:
        client = AsyncIOMotorClient(
            uri,
            serverSelectionTimeoutMS=3000,
            connectTimeoutMS=3000,
        )
        await client.admin.command("ping")
        db = client[db_name]
        collections = await db.list_collection_names()
        client.close()
        return {
            "success": True,
            "collections": collections,
            "error": "",
        }
    except Exception as e:
        return {
            "success": False,
            "collections": [],
            "error": str(e),
        }


@tool
async def save_client_config(
    user_id: str,
    owner_name: str,
    owner_email: str,
    owner_phone: str,
    business_name: str,
    business_location: str,
    business_category: str,
    db_type: str,
    connection_uri: str,
    database_name: str,
    resources_collection: str,
    agent_name: str,
    agent_personality: str,
    greeting_template: str,
    tts_voice: str,
    resource_id_field: str,
    resource_name_field: str,
    resource_price_field: str,
    resource_availability_field: str,
    searchable_fields: list[str],
) -> dict:
    """Save the complete client configuration to MongoDB and mark user as onboarded.

    Call this ONLY when all required fields have been collected and confirmed by the user.

    Returns:
        dict with success status and client_id.
    """
    # Validate required fields
    required = {
        "business_name": business_name,
        "business_category": business_category,
        "resources_collection": resources_collection,
    }
    missing = [k for k, v in required.items() if not v]
    if missing:
        return {"success": False, "client_id": "", "error": f"Missing required fields: {', '.join(missing)}"}

    # Generate client_id from business name
    client_id = re.sub(r"[^a-z0-9]+", "-", business_name.lower()).strip("-")[:50]

    try:
        config = ClientConfig(
            client_id=client_id,
            owner=ClientOwner(
                name=owner_name or "",
                email=owner_email or "",
                phone=owner_phone or "",
            ),
            business=BusinessDetails(
                name=business_name,
                location=business_location or "",
                category=business_category,
            ),
            database=ClientDatabase(
                db_type=db_type or "mongodb",
                connection_uri=connection_uri or "",
                database_name=database_name or "",
            ),
            db_mapping=DatabaseMapping(
                resources_collection=resources_collection,
                resource_id_field=resource_id_field or "id",
                resource_name_field=resource_name_field or "name",
                resource_price_field=resource_price_field or "price_per_night",
                resource_availability_field=resource_availability_field or "available",
                searchable_fields=searchable_fields or [],
            ),
            voice=VoiceSettings(
                agent_name=agent_name or "Aria",
                agent_personality=agent_personality or "Warm, friendly, professional",
                greeting_template=greeting_template or "",
                tts_voice=tts_voice or "aura-asteria-en",
            ),
        )

        # Save to clients collection
        client_repo = ClientRepository()
        await client_repo.upsert(config)

        # Mark user as onboarded
        user_repo = UserRepository()
        await user_repo.set_onboarded(user_id, client_id)

        logger.info("Onboarding complete: user=%s, client=%s", user_id, client_id)
        return {"success": True, "client_id": client_id, "error": ""}

    except Exception as e:
        logger.error("Failed to save client config: %s", e)
        return {"success": False, "client_id": "", "error": str(e)}
