import json
import logging

from langchain_core.tools import tool

from app.db.models import ClientConfig
from app.db.repositories.resource_repo import ResourceRepository
from app.agent.tools.category_helpers import get_speech_formatter

logger = logging.getLogger(__name__)


def build_search_tool(config: ClientConfig, repo: ResourceRepository):
    """Factory: creates a search tool bound to the client's resource collection."""

    collection = config.db_mapping.resources_collection
    fields = config.db_mapping.searchable_fields
    fields_desc = ", ".join(fields) if fields else "any criteria"

    @tool
    async def search_resources(filters: dict = {}) -> str:
        """Search available resources based on preferences.

        Args:
            filters: Dictionary of search filters. Available filter fields vary by category.
        """
        try:
            safe_filters = {k: v for k, v in filters.items() if k in fields and v is not None}

            results = await repo.search(
                filters=safe_filters,
                searchable_fields=fields,
                sort_field=config.db_mapping.resource_price_field,
                availability_field=config.db_mapping.resource_availability_field,
                limit=3,
            )

            if not results:
                available_values = {}
                for f in fields:
                    vals = await repo.get_available_values(
                        f, config.db_mapping.resource_availability_field
                    )
                    if vals:
                        available_values[f] = vals

                return json.dumps({
                    "results": [],
                    "message": f"No {collection} match your criteria.",
                    "available_options": available_values,
                    "suggestion": "Try relaxing your search criteria.",
                })

            formatter = get_speech_formatter(config.business.category)
            formatted = [formatter(r, config) for r in results]

            return json.dumps({
                "results": results,
                "count": len(results),
                "speech_descriptions": formatted,
            })
        except Exception as e:
            logger.error("search_resources failed: %s", e)
            return json.dumps({"error": "I'm having trouble searching right now. Could you try again?"})

    search_resources.name = f"search_{collection}"
    search_resources.description = (
        f"Search available {collection}. Can filter by: {fields_desc}. "
        f"Returns up to 3 matching results sorted by price."
    )
    return search_resources
