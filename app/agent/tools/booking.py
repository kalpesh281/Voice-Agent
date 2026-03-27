import json
import logging

from langchain_core.tools import tool

from app.db.models import Booking, ClientConfig
from app.db.repositories.booking_repo import BookingRepository
from app.db.repositories.resource_repo import ResourceRepository

logger = logging.getLogger(__name__)


def build_create_booking_tool(
    config: ClientConfig,
    resource_repo: ResourceRepository,
    booking_repo: BookingRepository,
):
    """Factory: creates a booking creation tool."""

    id_field = config.db_mapping.resource_id_field
    name_field = config.db_mapping.resource_name_field
    price_field = config.db_mapping.resource_price_field
    currency = config.business.currency
    token_pct = config.business.token_percentage

    @tool
    async def create_booking(
        resource_id: str,
        customer_name: str,
        customer_phone: str,
        start_date: str,
        end_date: str = "",
        num_guests: int = 1,
        payment_method: str = "",
        special_requests: str = "",
    ) -> str:
        """Create a confirmed booking after the customer has agreed to all details.

        IMPORTANT: Only call this AFTER reading back all details and getting explicit confirmation.

        Args:
            resource_id: The resource to book.
            customer_name: Guest/customer name.
            customer_phone: Guest/customer phone number.
            start_date: Check-in/booking date (YYYY-MM-DD).
            end_date: Check-out date (YYYY-MM-DD), empty for single-slot bookings.
            num_guests: Number of guests/players.
            payment_method: Payment method (UPI, credit card, bank transfer).
            special_requests: Any special requests.
        """
        try:
            # Verify resource exists and is available
            resource = await resource_repo.get_by_resource_id(resource_id, id_field)
            if not resource:
                return json.dumps({"error": f"Resource {resource_id} not found."})

            if not resource.get(config.db_mapping.resource_availability_field, False):
                return json.dumps({"error": f"{resource.get(name_field, 'Resource')} is no longer available."})

            # Calculate pricing
            from datetime import datetime

            price_per_unit = resource.get(price_field, 0)
            units = 1
            if end_date:
                try:
                    start = datetime.strptime(start_date, "%Y-%m-%d")
                    end = datetime.strptime(end_date, "%Y-%m-%d")
                    units = max((end - start).days, 1)
                except ValueError:
                    pass

            total_price = price_per_unit * units
            token_amount = int(total_price * token_pct / 100)

            booking = Booking(
                client_id=config.client_id,
                resource_id=resource_id,
                resource_name=resource.get(name_field, ""),
                customer_name=customer_name,
                customer_phone=customer_phone,
                start_date=start_date,
                end_date=end_date,
                num_guests=num_guests,
                total_price=total_price,
                token_amount=token_amount,
                payment_method=payment_method,
                currency=currency,
                special_requests=special_requests,
                status="confirmed",
            )

            booking_id = await booking_repo.save_booking(booking)

            return json.dumps({
                "success": True,
                "booking_id": booking_id,
                "resource_name": resource.get(name_field, ""),
                "customer_name": customer_name,
                "start_date": start_date,
                "end_date": end_date,
                "num_guests": num_guests,
                "total_price": total_price,
                "token_amount": token_amount,
                "currency": currency,
                "payment_method": payment_method,
                "status": "confirmed",
            })
        except Exception as e:
            logger.error("create_booking failed: %s", e)
            return json.dumps({"error": "I'm sorry, there was an issue creating your booking. Please try again."})

    create_booking.name = "create_booking"
    create_booking.description = (
        "Create a confirmed booking. ONLY call this after reading back all details "
        "to the customer and getting their explicit confirmation."
    )
    return create_booking


def build_get_booking_tool(booking_repo: BookingRepository):
    """Factory: creates a booking lookup tool."""

    @tool
    async def get_booking(booking_id: str) -> str:
        """Look up an existing booking by its reference ID.

        Args:
            booking_id: The booking reference (e.g., BK-20260328-001).
        """
        try:
            booking = await booking_repo.get_booking(booking_id)
            if not booking:
                return json.dumps({"error": f"No booking found with ID {booking_id}."})
            return json.dumps(booking.model_dump(mode="json"))
        except Exception as e:
            logger.error("get_booking failed: %s", e)
            return json.dumps({"error": "I'm having trouble looking up that booking."})

    get_booking.name = "get_booking"
    get_booking.description = "Look up an existing booking by its reference ID."
    return get_booking
