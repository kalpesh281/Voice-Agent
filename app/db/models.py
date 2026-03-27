"""Data models for the three-tier voice booking platform.

Tier 1 — Agent (Platform): Managed via app/config.py (Settings).
         The platform itself, infrastructure, AI orchestration.

Tier 2 — Client (Business Owner): ClientConfig model.
         Hotel owner, restaurant owner, turf owner.
         Registers via onboarding form with business details + DB access.
         Stored in MongoDB `clients` collection.

Tier 3 — End User (Customer): The person who calls the voice agent.
         Their info is captured during conversation and stored in Booking.
         No account needed — identified by phone number per conversation.
"""

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


# ──────────────────────────────────────────────
#  Tier 2: Client (Business Owner) Models
# ──────────────────────────────────────────────


class ClientOwner(BaseModel):
    """Client's personal / contact details — the business owner themselves."""

    name: str                       # "Kalpesh Patel"
    email: str = ""                 # "kalpesh@grandmeridian.com"
    phone: str = ""                 # "+91-9313497508"
    company: str = ""               # Company / org name if different from business


class BusinessDetails(BaseModel):
    """Client's business information — provided during onboarding form."""

    name: str                       # "The Grand Meridian Palace"
    location: str = ""              # "Marine Drive, Mumbai, India"
    category: Literal[
        "hotel",
        "restaurant",
        "table_booking",
        "cricket_ground",
        "pickleball",
        "ecommerce",
    ]
    currency: str = "INR"
    token_percentage: float = 20.0  # advance payment %
    custom_rules: list[str] = []    # business-specific rules injected into agent prompt


class ClientDatabase(BaseModel):
    """Client's database connection details — provided during onboarding.

    For now: only NoSQL (MongoDB). Later: SQL support added.
    The client tells us where their data lives and we connect to read it.
    """

    db_type: Literal["mongodb", "postgresql", "mysql"] = "mongodb"
    connection_uri: str = ""        # client's DB URI (if separate from platform DB)
    database_name: str = ""         # client's DB name (if separate)
    # If empty, we use the platform's MongoDB (same DB for everything)


class DatabaseMapping(BaseModel):
    """Maps client's DB collections/tables and field names to our generic tools.

    This is the key abstraction — the agent tools are generic (search, book, etc.)
    but each client's data lives in different collections with different field names.
    This mapping tells the tools where to look and what to call things.
    """

    resources_collection: str                       # "rooms", "tables", "courts"
    bookings_collection: str = "bookings"
    resource_id_field: str = "id"                   # field name for resource ID
    resource_name_field: str = "name"               # field name for resource name
    resource_price_field: str = "price_per_night"   # "price_per_night", "price_per_slot"
    resource_availability_field: str = "available"  # field name for availability flag
    searchable_fields: list[str] = []               # fields the search tool can filter on
    display_fields: list[str] = []                  # fields shown in summaries
    speech_fields: list[str] = []                   # fields read aloud by TTS


class VoiceSettings(BaseModel):
    """How the voice agent sounds and behaves for this client."""

    agent_name: str = "Aria"
    agent_personality: str = "Warm, friendly, professional — speaks like a real person on a phone call"
    greeting_template: str = ""
    language: str = "en"
    tts_voice: str = "aura-asteria-en"


class ClientConfig(BaseModel):
    """Full configuration for a client (business owner).

    Created when a client registers via the onboarding form.
    Stored in MongoDB `clients` collection (our data, not client's).

    The voice agent loads this at startup to know:
    - Who the client is (owner details)
    - What business it represents (hotel, restaurant, etc.)
    - Where the client's data lives (DB connection)
    - How to map their data to our generic tools
    - How the voice agent should sound and behave
    """

    client_id: str

    # Client owner (the person who registered)
    owner: ClientOwner

    # Business details
    business: BusinessDetails

    # Client's database access
    database: ClientDatabase = ClientDatabase()

    # How their DB maps to our tools
    db_mapping: DatabaseMapping

    # Voice agent configuration
    voice: VoiceSettings = VoiceSettings()

    # Which tools the agent can use for this client
    tools_enabled: list[str] = [
        "search_resources",
        "get_resource_details",
        "check_availability",
        "create_booking",
        "get_booking",
    ]

    # Custom system prompt (if empty, uses default template for the category)
    system_prompt_template: str = ""

    # Status
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ──────────────────────────────────────────────
#  Tier 3: End User (Customer) Models
# ──────────────────────────────────────────────


class Booking(BaseModel):
    """A booking made by an end user through the voice agent.

    Links to:
    - client_id: which business this booking belongs to (Tier 2)
    - customer_*: the end user's info, captured during voice conversation (Tier 3)
    - resource_*: what was booked (room, table, court — from client's DB)
    """

    booking_id: str = ""
    client_id: str = ""

    # Resource (what was booked)
    resource_id: str = ""
    resource_name: str = ""

    # End user / customer info (captured via voice conversation)
    customer_name: str = ""
    customer_phone: str = ""
    customer_email: str = ""

    # Booking details
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

    # Category-specific fields (e.g., time_slot for restaurant, sport for turf)
    extra: dict = {}
