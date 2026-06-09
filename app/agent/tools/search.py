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
    name_field = config.db_mapping.resource_name_field
    # `amenities` (a list of feature phrases) is searchable by keyword, so a
    # caller can shop by feature ("a room with a jacuzzi") without knowing names.
    # Driven off speech_fields so it's only enabled when the category has it.
    feature_fields = [f for f in (config.db_mapping.speech_fields or []) if f == "amenities"]
    # The name is searchable too, with fuzzy word-matching — so a caller naming a
    # specific room finds it even if they pair it with the wrong descriptor.
    allowed = list(dict.fromkeys([*fields, name_field, *feature_fields]))
    fields_desc = ", ".join(allowed) if allowed else "any criteria"

    @tool
    async def search_resources(filters: dict = {}) -> str:
        """Search available resources based on preferences.

        Args:
            filters: Dictionary of search filters. Available filter fields vary by category.
        """
        try:
            safe_filters = {k: v for k, v in filters.items() if k in allowed and v is not None}

            results = await repo.search(
                filters=safe_filters,
                searchable_fields=allowed,
                sort_field=config.db_mapping.resource_price_field,
                availability_field=config.db_mapping.resource_availability_field,
                limit=3,
                fuzzy_fields=[name_field],
                array_fields=feature_fields,
            )

            # Self-correct when the LLM misfiles a room name into the wrong field
            # (e.g. type="Maharaja Deluxe King"). Constrained fields are
            # exact-match, so a proper name there yields nothing. Retry by
            # OR-matching every string value the LLM provided against the name
            # field, which is fuzzy — so the named room still surfaces.
            if not results:
                string_vals = [
                    str(v) for k, v in safe_filters.items()
                    if isinstance(v, str) and k != name_field and k not in feature_fields
                ]
                if string_vals:
                    retry = await repo.search(
                        filters={name_field: " ".join(string_vals)},
                        searchable_fields=[name_field],
                        sort_field=config.db_mapping.resource_price_field,
                        availability_field=config.db_mapping.resource_availability_field,
                        limit=3,
                        fuzzy_fields=[name_field],
                    )
                    if retry:
                        results = retry

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
            logger.error("search_%s FAILED: %s", collection, e, exc_info=True)
            return json.dumps({"error": "I'm having trouble searching right now. Could you try again?"})

    search_resources.name = f"search_{collection}"
    # Steer the model to the right field: a specific/proper resource name (what a
    # caller says, e.g. "Maharaja Deluxe King") belongs in `name`, NOT in the
    # constrained category fields. The constrained fields only accept their known
    # values; stuffing a proper name into them matches nothing.
    constrained = ", ".join(f for f in fields if f != name_field)
    amenity_hint = (
        " To shop by feature when the caller doesn't know room names, put feature "
        "keywords in 'amenities' (e.g. {\"amenities\": \"private pool jacuzzi\"}) — "
        "each keyword must be present."
        if feature_fields else ""
    )
    search_resources.description = (
        f"Search available {collection}. Filter fields: {fields_desc}. "
        f"Put a specific room/resource name the caller mentions (e.g. a proper "
        f"name) in '{name_field}' — it matches fuzzily. Use {constrained} only "
        f"for their category values, never for a proper name.{amenity_hint} "
        f"Returns up to 3 matches sorted by price."
    )
    return search_resources
