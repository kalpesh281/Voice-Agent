"""Onboarding agent state — tracks collected fields during the setup conversation."""

from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


class OnboardingState(TypedDict):
    messages: Annotated[list, add_messages]

    # Auth context
    user_id: str

    # Owner details
    owner_name: str
    owner_email: str
    owner_phone: str

    # Business details
    business_name: str
    business_location: str
    business_category: str  # hotel|restaurant|table_booking|cricket_ground|pickleball|ecommerce

    # Database
    db_type: str
    connection_uri: str
    database_name: str
    resources_collection: str

    # Voice settings
    agent_name: str
    agent_personality: str
    greeting_template: str
    tts_voice: str

    # DB mapping (auto-generated from category, user can override)
    resource_id_field: str
    resource_name_field: str
    resource_price_field: str
    resource_availability_field: str
    searchable_fields: list[str]

    # Status
    current_step: str  # intro|owner|business|database|voice|review|complete
    is_complete: bool
    errors: list[str]
