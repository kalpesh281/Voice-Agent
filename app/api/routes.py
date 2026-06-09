"""API routes for client onboarding and management."""

import logging
import re
from uuid import uuid4

import httpx
from fastapi import APIRouter, HTTPException, Query
from livekit import api as lk_api
from fastapi.responses import StreamingResponse

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
from app.config import settings
from app.db.repositories.client_repo import ClientRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["clients"])


@router.get("/livekit/token")
async def livekit_token(
    client_id: str = Query(...),
    identity: str = Query(...),
):
    """Mint a short-lived LiveKit access token for a browser to join its room.

    The room is named "voice-<client_id>"; the agent worker (app/livekit_agent)
    is dispatched into that room and reads the client_id back from the name.
    """
    if not (settings.livekit_url and settings.livekit_api_key and settings.livekit_api_secret):
        raise HTTPException(status_code=503, detail="LiveKit not configured")

    # Verify the client exists so we don't hand out tokens for unknown rooms.
    config = await ClientRepository().get_by_id(client_id)
    if config is None:
        raise HTTPException(status_code=404, detail=f"Client '{client_id}' not found")

    # UNIQUE room per call. A token's RoomConfiguration (the agent dispatch) is
    # only honored when the room is CREATED. A fixed room name persists on the
    # cloud between calls, so the 2nd+ call joins an existing room and the
    # dispatch is silently ignored — the agent never joins ("stuck connecting").
    # A fresh room name every time guarantees a creation event, so the agent is
    # always dispatched. The worker parses client_id back out of the room name.
    room = f"voice-{client_id}-{uuid4().hex[:8]}"
    token = (
        lk_api.AccessToken(settings.livekit_api_key, settings.livekit_api_secret)
        .with_identity(identity)
        .with_name(identity)
        .with_grants(
            lk_api.VideoGrants(
                room_join=True,
                room=room,
                can_publish=True,
                can_subscribe=True,
            )
        )
        # Explicitly dispatch the named agent worker into this room when the
        # browser joins. Without this we relied on auto-dispatch, which only
        # fires on room *creation* — so the 2nd call onward (room already exists)
        # hung on "connecting" with the agent never joining. AGENT_NAME must
        # match the worker's @server.rtc_session(agent_name=...).
        .with_room_config(
            lk_api.RoomConfiguration(
                agents=[lk_api.RoomAgentDispatch(agent_name="booking-agent")]
            )
        )
        .to_jwt()
    )
    return {"url": settings.livekit_url, "token": token, "room": room}


@router.get("/tts-preview")
async def tts_preview(
    text: str = Query(..., max_length=500),
    voice: str = Query(default="aura-asteria-en"),
):
    """Generate a TTS audio preview using Deepgram. Returns audio/mpeg stream."""
    if not settings.deepgram_api_key:
        raise HTTPException(status_code=503, detail="Deepgram not configured")

    async def stream_audio():
        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream(
                "POST",
                f"https://api.deepgram.com/v1/speak?model={voice}",
                json={"text": text},
                headers={
                    "Authorization": f"Token {settings.deepgram_api_key}",
                    "Content-Type": "application/json",
                },
            ) as resp:
                if resp.status_code != 200:
                    raise HTTPException(status_code=502, detail="TTS generation failed")
                async for chunk in resp.aiter_bytes(chunk_size=4096):
                    yield chunk

    return StreamingResponse(stream_audio(), media_type="audio/mpeg")


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
        system_prompt_template=req.system_prompt_template or "",
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
        system_prompt_template=req.system_prompt_template if req.system_prompt_template else existing.system_prompt_template,
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
