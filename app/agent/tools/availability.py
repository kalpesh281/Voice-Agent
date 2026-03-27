import json
import logging
from datetime import datetime

from langchain_core.tools import tool

from app.db.models import ClientConfig
from app.db.repositories.resource_repo import ResourceRepository

logger = logging.getLogger(__name__)


def build_availability_tool(config: ClientConfig, repo: ResourceRepository):
    """Factory: creates an availability check tool."""

    id_field = config.db_mapping.resource_id_field
    name_field = config.db_mapping.resource_name_field
    price_field = config.db_mapping.resource_price_field
    currency = config.business.currency
    token_pct = config.business.token_percentage

    @tool
    async def check_availability(
        resource_id: str, start_date: str, end_date: str = ""
    ) -> str:
        """Check availability and calculate pricing for a resource.

        Args:
            resource_id: The unique identifier of the resource.
            start_date: Start/check-in date in YYYY-MM-DD format.
            end_date: End/check-out date in YYYY-MM-DD format (optional for single-slot bookings).
        """
        try:
            resource = await repo.get_by_resource_id(resource_id, id_field)
            if not resource:
                return json.dumps({"error": f"Resource {resource_id} not found."})

            if not resource.get(config.db_mapping.resource_availability_field, False):
                return json.dumps({
                    "available": False,
                    "message": f"{resource.get(name_field, 'This resource')} is currently fully booked.",
                })

            # Parse dates
            try:
                start = datetime.strptime(start_date, "%Y-%m-%d")
            except ValueError:
                return json.dumps({"error": f"Invalid start date format: {start_date}. Use YYYY-MM-DD."})

            price_per_unit = resource.get(price_field, 0)
            units = 1
            unit_label = "slot"

            if end_date:
                try:
                    end = datetime.strptime(end_date, "%Y-%m-%d")
                except ValueError:
                    return json.dumps({"error": f"Invalid end date format: {end_date}. Use YYYY-MM-DD."})

                if end <= start:
                    return json.dumps({"error": "End date must be after start date."})

                units = (end - start).days
                unit_label = "night" if units == 1 else "nights"

            total_price = price_per_unit * units
            token_amount = int(total_price * token_pct / 100)

            return json.dumps({
                "available": True,
                "resource_id": resource_id,
                "resource_name": resource.get(name_field, ""),
                "start_date": start_date,
                "end_date": end_date,
                "units": units,
                "unit_label": unit_label,
                "price_per_unit": price_per_unit,
                "total_price": total_price,
                "token_amount": token_amount,
                "token_percentage": token_pct,
                "currency": currency,
            })
        except Exception as e:
            logger.error("check_availability failed: %s", e)
            return json.dumps({"error": "I'm having trouble checking availability. One moment please."})

    check_availability.name = "check_availability"
    check_availability.description = (
        "Check if a resource is available for the given dates and calculate total pricing "
        "including the advance token amount."
    )
    return check_availability
