import json
import logging

from langchain_core.tools import tool

from app.db.models import ClientConfig
from app.db.repositories.resource_repo import ResourceRepository
from app.agent.tools.category_helpers import get_speech_formatter

logger = logging.getLogger(__name__)


def build_details_tool(config: ClientConfig, repo: ResourceRepository):
    """Factory: creates a resource details tool."""

    collection = config.db_mapping.resources_collection
    id_field = config.db_mapping.resource_id_field

    @tool
    async def get_resource_details(resource_id: str) -> str:
        """Get full details of a specific resource by its ID.

        Args:
            resource_id: The unique identifier of the resource.
        """
        try:
            resource = await repo.get_by_resource_id(resource_id, id_field)
            if not resource:
                return json.dumps({"error": f"No {collection[:-1]} found with ID {resource_id}."})

            formatter = get_speech_formatter(config.business.category)
            speech = formatter(resource, config)

            return json.dumps({
                "resource": resource,
                "speech_description": speech,
            })
        except Exception as e:
            logger.error("get_resource_details failed: %s", e)
            return json.dumps({"error": "I'm having trouble getting those details. One moment please."})

    get_resource_details.name = f"get_{collection[:-1]}_details"
    get_resource_details.description = (
        f"Get full details of a specific {collection[:-1]} by ID, "
        f"including amenities, description, and pricing."
    )
    return get_resource_details
