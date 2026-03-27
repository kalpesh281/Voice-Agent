from typing import Callable

from app.db.models import ClientConfig
from app.agent.tools.category_helpers.hotel import format_room_for_speech
from app.agent.tools.category_helpers.restaurant import format_table_for_speech
from app.agent.tools.category_helpers.turf import format_court_for_speech


def _default_formatter(resource: dict, config: ClientConfig) -> str:
    name = resource.get(config.db_mapping.resource_name_field, "Unknown")
    price = resource.get(config.db_mapping.resource_price_field, 0)
    return f"{name} — {price} {config.business.currency}"


_FORMATTERS: dict[str, Callable] = {
    "hotel": format_room_for_speech,
    "restaurant": format_table_for_speech,
    "table_booking": format_table_for_speech,
    "cricket_ground": format_court_for_speech,
    "pickleball": format_court_for_speech,
}


def get_speech_formatter(category: str) -> Callable:
    return _FORMATTERS.get(category, _default_formatter)
