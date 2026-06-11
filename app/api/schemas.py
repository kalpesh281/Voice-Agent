"""API request/response schemas for client onboarding."""

from typing import Literal

from pydantic import BaseModel, Field


# ──────────────────────────────────────────────
#  Client Onboarding — Request
# ──────────────────────────────────────────────


class ClientOnboardRequest(BaseModel):
    """What the client fills in the onboarding form."""

    # Owner / contact details
    owner_name: str = Field(..., min_length=2, examples=["Rajesh Sharma"])
    owner_email: str = Field("", examples=["rajesh@grandmeridian.com"])
    owner_phone: str = Field(..., min_length=10, examples=["+91-9876543210"])
    owner_company: str = Field("", examples=["Grand Meridian Hotels Pvt. Ltd."])

    # Business details
    business_name: str = Field(..., min_length=2, examples=["The Grand Meridian Palace"])
    business_location: str = Field("", examples=["Marine Drive, Mumbai, India"])
    business_category: Literal[
        "hotel",
        "restaurant",
        "table_booking",
        "cricket_ground",
        "pickleball",
        "ecommerce",
    ] = Field(..., examples=["hotel"])
    currency: str = Field("INR", examples=["INR", "USD"])
    token_percentage: float = Field(20.0, ge=0, le=100, examples=[20.0])
    custom_rules: list[str] = Field(
        default=[],
        examples=[["Check-in 2PM", "No pets"]],
    )

    # Client's database details
    db_type: Literal["mongodb", "postgresql", "mysql"] = Field(
        "mongodb", examples=["mongodb"]
    )
    db_connection_uri: str = Field(
        "",
        examples=["mongodb+srv://user:pass@cluster.mongodb.net/"],
        description="Client's database connection URI. Empty = use platform DB.",
    )
    db_name: str = Field(
        "",
        examples=["hotel_data"],
        description="Client's database name. Empty = use platform DB.",
    )

    # Database mapping — how their data maps to our tools
    resources_collection: str = Field(..., examples=["rooms"])
    resource_id_field: str = Field("id", examples=["id", "room_id", "table_id"])
    resource_name_field: str = Field("name", examples=["name"])
    resource_price_field: str = Field(
        "price_per_night",
        examples=["price_per_night", "price_per_slot", "price_per_head"],
    )
    resource_availability_field: str = Field("available", examples=["available"])
    searchable_fields: list[str] = Field(
        default=[],
        examples=[["type", "view", "max_guests", "bed_type"]],
    )
    display_fields: list[str] = Field(default=[])
    speech_fields: list[str] = Field(default=[])

    # Voice agent customization (optional)
    agent_name: str = Field("Aria", examples=["Aria", "Priya", "Raj"])
    agent_personality: str = Field(
        "",
        examples=["Warm, friendly Indian woman. Natural phone conversation style."],
    )
    greeting_template: str = Field("", examples=["Namaste! Welcome to {business_name}!"])
    tts_voice: str = Field("aura-2-thalia-en", examples=["aura-2-thalia-en"])

    # Custom system prompt (if empty, uses default template for the category)
    system_prompt_template: str = Field("", description="Custom system prompt override. Leave empty for default.")


class ClientUpdateRequest(ClientOnboardRequest):
    """Schema for editing an EXISTING client (PUT).

    Same shape as onboarding, but the strict input gates are relaxed: a Settings
    save re-sends every field, so onboarding-only minimums (e.g. phone length)
    must not reject an edit to an unrelated field like the business name.
    """

    owner_name: str = Field("")
    owner_phone: str = Field("")
    business_name: str = Field(..., min_length=2)
    resources_collection: str = Field("")


# ──────────────────────────────────────────────
#  Client Onboarding — Response
# ──────────────────────────────────────────────


class ClientOnboardResponse(BaseModel):
    success: bool
    client_id: str
    message: str


class ClientListItem(BaseModel):
    client_id: str
    business_name: str
    category: str
    owner_name: str
    owner_phone: str
    is_active: bool


class ClientDetailResponse(BaseModel):
    success: bool
    client: dict
