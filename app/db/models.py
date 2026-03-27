from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


class VoiceSettings(BaseModel):
    agent_name: str = "Aria"
    agent_personality: str = "Warm, friendly, professional — speaks like a real person on a phone call"
    greeting_template: str = ""
    language: str = "en"
    tts_voice: str = "aura-asteria-en"


class BusinessDetails(BaseModel):
    name: str
    location: str = ""
    category: Literal[
        "hotel",
        "restaurant",
        "table_booking",
        "cricket_ground",
        "pickleball",
        "ecommerce",
    ]
    currency: str = "INR"
    token_percentage: float = 20.0
    custom_rules: list[str] = []


class DatabaseMapping(BaseModel):
    resources_collection: str
    bookings_collection: str = "bookings"
    resource_id_field: str = "id"
    resource_name_field: str = "name"
    resource_price_field: str = "price_per_night"
    resource_availability_field: str = "available"
    searchable_fields: list[str] = []
    display_fields: list[str] = []
    speech_fields: list[str] = []


class ClientConfig(BaseModel):
    client_id: str
    business: BusinessDetails
    voice: VoiceSettings = VoiceSettings()
    db_mapping: DatabaseMapping
    tools_enabled: list[str] = [
        "search_resources",
        "get_resource_details",
        "check_availability",
        "create_booking",
        "get_booking",
    ]
    system_prompt_template: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Booking(BaseModel):
    booking_id: str = ""
    client_id: str = ""
    resource_id: str = ""
    resource_name: str = ""
    customer_name: str = ""
    customer_phone: str = ""
    customer_email: str = ""
    start_date: str = ""
    end_date: str = ""
    num_guests: int = 1
    total_price: float = 0.0
    token_amount: float = 0.0
    payment_method: str = ""
    currency: str = "INR"
    special_requests: str = ""
    status: str = "confirmed"
    booked_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    extra: dict = {}
