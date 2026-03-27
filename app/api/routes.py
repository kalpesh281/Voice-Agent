"""API routes for client onboarding and management."""

import logging
import re

from fastapi import APIRouter, HTTPException

from app.api.schemas import (
    ClientDetailResponse,
    ClientListItem,
    ClientOnboardRequest,
    ClientOnboardResponse,
)
from app.db.models import (
    BusinessDetails,
    ClientConfig,
    ClientDatabase,
    ClientOwner,
    DatabaseMapping,
    VoiceSettings,
)
from app.db.repositories.client_repo import ClientRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["clients"])


def _generate_client_id(business_name: str) -> str:
    """Generate a URL-safe client ID from business name."""
    slug = re.sub(r"[^a-z0-9]+", "-", business_name.lower()).strip("-")
    return slug[:50]


@router.post("/clients", response_model=ClientOnboardResponse)
async def onboard_client(req: ClientOnboardRequest):
    """Register a new client (business owner) via the onboarding form.

    This creates a ClientConfig in the platform DB with all the details
    needed for the voice agent to serve this client's customers.
    """
    repo = ClientRepository()
    client_id = _generate_client_id(req.business_name)

    # Check if client already exists
    existing = await repo.get_by_id(client_id)
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Client '{client_id}' already exists. Use PUT to update.",
        )

    # Build the ClientConfig from form data
    config = ClientConfig(
        client_id=client_id,
        owner=ClientOwner(
            name=req.owner_name,
            email=req.owner_email,
            phone=req.owner_phone,
            company=req.owner_company,
        ),
        business=BusinessDetails(
            name=req.business_name,
            location=req.business_location,
            category=req.business_category,
            currency=req.currency,
            token_percentage=req.token_percentage,
            custom_rules=req.custom_rules,
        ),
        database=ClientDatabase(
            db_type=req.db_type,
            connection_uri=req.db_connection_uri,
            database_name=req.db_name,
        ),
        db_mapping=DatabaseMapping(
            resources_collection=req.resources_collection,
            resource_id_field=req.resource_id_field,
            resource_name_field=req.resource_name_field,
            resource_price_field=req.resource_price_field,
            resource_availability_field=req.resource_availability_field,
            searchable_fields=req.searchable_fields,
            display_fields=req.display_fields,
            speech_fields=req.speech_fields,
        ),
        voice=VoiceSettings(
            agent_name=req.agent_name,
            agent_personality=req.agent_personality or (
                "Warm, friendly, professional — speaks like a real person on a phone call"
            ),
            greeting_template=req.greeting_template,
            tts_voice=req.tts_voice,
        ),
    )

    await repo.upsert(config)
    logger.info("Client onboarded: %s (%s)", client_id, req.business_name)

    return ClientOnboardResponse(
        success=True,
        client_id=client_id,
        message=f"Client '{req.business_name}' registered successfully.",
    )


@router.get("/clients", response_model=list[ClientListItem])
async def list_clients():
    """List all registered clients."""
    repo = ClientRepository()
    docs = await repo.find_many({}, limit=100)
    return [
        ClientListItem(
            client_id=d.get("client_id", ""),
            business_name=d.get("business", {}).get("name", ""),
            category=d.get("business", {}).get("category", ""),
            owner_name=d.get("owner", {}).get("name", ""),
            owner_phone=d.get("owner", {}).get("phone", ""),
            is_active=d.get("is_active", True),
        )
        for d in docs
    ]


@router.get("/clients/{client_id}", response_model=ClientDetailResponse)
async def get_client(client_id: str):
    """Get full details of a specific client."""
    repo = ClientRepository()
    config = await repo.get_by_id(client_id)
    if not config:
        raise HTTPException(status_code=404, detail=f"Client '{client_id}' not found.")
    return ClientDetailResponse(success=True, client=config.model_dump(mode="json"))


@router.put("/clients/{client_id}", response_model=ClientOnboardResponse)
async def update_client(client_id: str, req: ClientOnboardRequest):
    """Update an existing client's configuration."""
    repo = ClientRepository()
    existing = await repo.get_by_id(client_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Client '{client_id}' not found.")

    # Rebuild config with updated data (keep same client_id)
    config = ClientConfig(
        client_id=client_id,
        owner=ClientOwner(
            name=req.owner_name,
            email=req.owner_email,
            phone=req.owner_phone,
            company=req.owner_company,
        ),
        business=BusinessDetails(
            name=req.business_name,
            location=req.business_location,
            category=req.business_category,
            currency=req.currency,
            token_percentage=req.token_percentage,
            custom_rules=req.custom_rules,
        ),
        database=ClientDatabase(
            db_type=req.db_type,
            connection_uri=req.db_connection_uri,
            database_name=req.db_name,
        ),
        db_mapping=DatabaseMapping(
            resources_collection=req.resources_collection,
            resource_id_field=req.resource_id_field,
            resource_name_field=req.resource_name_field,
            resource_price_field=req.resource_price_field,
            resource_availability_field=req.resource_availability_field,
            searchable_fields=req.searchable_fields,
            display_fields=req.display_fields,
            speech_fields=req.speech_fields,
        ),
        voice=VoiceSettings(
            agent_name=req.agent_name,
            agent_personality=req.agent_personality or existing.voice.agent_personality,
            greeting_template=req.greeting_template or existing.voice.greeting_template,
            tts_voice=req.tts_voice,
        ),
        created_at=existing.created_at,
    )

    await repo.upsert(config)
    logger.info("Client updated: %s", client_id)

    return ClientOnboardResponse(
        success=True,
        client_id=client_id,
        message=f"Client '{req.business_name}' updated successfully.",
    )


@router.delete("/clients/{client_id}")
async def deactivate_client(client_id: str):
    """Deactivate a client (soft delete)."""
    repo = ClientRepository()
    existing = await repo.get_by_id(client_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Client '{client_id}' not found.")

    await repo.update_one(
        {"client_id": client_id},
        {"is_active": False},
    )
    return {"success": True, "message": f"Client '{client_id}' deactivated."}
