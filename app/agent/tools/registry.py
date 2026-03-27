"""Dynamic tool registry — builds LangChain tools from client config.

This is the core abstraction that makes multi-category work.
Each tool is a closure that captures the correct repository and config,
so a hotel client gets search_rooms while a turf client gets search_courts.
"""

import logging

from app.db.models import ClientConfig
from app.db.repositories.booking_repo import BookingRepository
from app.db.repositories.resource_repo import ResourceRepository
from app.agent.tools.search import build_search_tool
from app.agent.tools.details import build_details_tool
from app.agent.tools.availability import build_availability_tool
from app.agent.tools.booking import build_create_booking_tool, build_get_booking_tool

logger = logging.getLogger(__name__)


def build_tools(config: ClientConfig) -> list:
    """Build the tool list for a given client config.

    Returns a list of LangChain tool objects, each pre-bound to the
    correct MongoDB collection and field mappings.
    """
    resource_repo = ResourceRepository(config.db_mapping.resources_collection)
    booking_repo = BookingRepository(config.db_mapping.bookings_collection)

    tools = []
    enabled = set(config.tools_enabled)

    if "search_resources" in enabled:
        tools.append(build_search_tool(config, resource_repo))

    if "get_resource_details" in enabled:
        tools.append(build_details_tool(config, resource_repo))

    if "check_availability" in enabled:
        tools.append(build_availability_tool(config, resource_repo))

    if "create_booking" in enabled:
        tools.append(build_create_booking_tool(config, resource_repo, booking_repo))

    if "get_booking" in enabled:
        tools.append(build_get_booking_tool(booking_repo))

    logger.info(
        "Built %d tools for client '%s': %s",
        len(tools),
        config.client_id,
        [t.name for t in tools],
    )
    return tools
