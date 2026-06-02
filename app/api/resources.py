"""Client resource endpoints — read-only access to client's own DB resources.

Also includes test-db endpoint for Profile > Database tab.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient

from app.api.deps import get_current_user
from app.db.models import ClientUser
from app.db.repositories.client_repo import ClientRepository

logger = logging.getLogger(__name__)

resources_router = APIRouter(prefix="/api/v1/clients", tags=["resources"])


@resources_router.post("/{client_id}/test-db")
async def test_db_connection(
    client_id: str,
    user: ClientUser = Depends(get_current_user),
):
    """Test the client's database connection."""
    if user.client_id != client_id:
        raise HTTPException(status_code=403, detail="Not your client")

    repo = ClientRepository()
    config = await repo.get_by_id(client_id)
    if not config:
        raise HTTPException(status_code=404, detail="Client not found")

    uri = config.database.connection_uri
    db_name = config.database.database_name

    if not uri or not db_name:
        return {"success": True, "message": "Using platform database", "collections": []}

    try:
        client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=3000, connectTimeoutMS=3000)
        await client.admin.command("ping")
        db = client[db_name]
        collections = await db.list_collection_names()
        client.close()
        return {"success": True, "message": "Connected successfully", "collections": collections}
    except Exception as e:
        return {"success": False, "message": str(e), "collections": []}


@resources_router.get("/{client_id}/resources")
async def list_resources(
    client_id: str,
    user: ClientUser = Depends(get_current_user),
    limit: int = 50,
):
    """List resources from the client's own database (read-only)."""
    if user.client_id != client_id:
        raise HTTPException(status_code=403, detail="Not your client")

    repo = ClientRepository()
    config = await repo.get_by_id(client_id)
    if not config:
        raise HTTPException(status_code=404, detail="Client not found")

    uri = config.database.connection_uri
    db_name = config.database.database_name
    collection_name = config.db_mapping.resources_collection

    if not uri or not db_name:
        return {"resources": [], "collection": collection_name, "message": "No external database configured"}

    try:
        client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=3000, connectTimeoutMS=3000)
        db = client[db_name]
        cursor = db[collection_name].find({}, {"_id": 0}).limit(limit)
        resources = await cursor.to_list(length=limit)
        client.close()
        return {"resources": resources, "collection": collection_name, "count": len(resources)}
    except Exception as e:
        logger.error("Failed to read resources for client %s: %s", client_id, e)
        raise HTTPException(status_code=500, detail=f"Failed to read resources: {e}")
