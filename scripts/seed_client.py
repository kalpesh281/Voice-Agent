"""Seed a client config into MongoDB.

Usage:
    poetry run python scripts/seed_client.py                 # seeds hotel (default)
    poetry run python scripts/seed_client.py --category restaurant
    poetry run python scripts/seed_client.py --category cricket_ground
    poetry run python scripts/seed_client.py --all
"""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings
from app.db.mongo import connect_platform, disconnect
from app.db.models import (
    BusinessDetails,
    ClientConfig,
    ClientDatabase,
    ClientOwner,
    DatabaseMapping,
    VoiceSettings,
)
from app.db.repositories.client_repo import ClientRepository


# ──────────────────────────────────────────────
#  Pre-defined client configs per category
# ──────────────────────────────────────────────

CLIENTS: dict[str, ClientConfig] = {
    "hotel": ClientConfig(
        client_id="grand-meridian-palace",
        owner=ClientOwner(
            name="Rajesh Sharma",
            email="rajesh@grandmeridian.com",
            phone="+91-9876543210",
            company="Grand Meridian Hotels Pvt. Ltd.",
        ),
        business=BusinessDetails(
            name="The Grand Meridian Palace",
            location="Marine Drive, Mumbai, India",
            category="hotel",
            currency="INR",
            token_percentage=20.0,
            custom_rules=[
                "Check-in time is 2:00 PM, check-out is 12:00 PM noon.",
                "Early check-in subject to availability at no extra charge.",
                "Complimentary airport pickup for suites and above.",
                "Pets are not allowed.",
            ],
        ),
        database=ClientDatabase(
            db_type="mongodb",
            connection_uri=settings.client_db_uri,
            database_name=settings.client_db_name,
        ),
        voice=VoiceSettings(
            agent_name="Aria",
            agent_personality=(
                "Warm, friendly Indian woman in her 30s. Speaks like a real "
                "person on a phone call — natural, NOT robotic. Uses fillers "
                'like "Oh lovely!", "Ji, bilkul!", "Wonderful choice!". '
                "2-4 sentences max per reply."
            ),
            greeting_template=(
                "Namaste and welcome to {business_name}! I'm {agent_name}, "
                "your personal concierge. How may I help you today?"
            ),
            language="en",
            tts_voice="aura-asteria-en",
        ),
        db_mapping=DatabaseMapping(
            resources_collection="rooms",
            bookings_collection="bookings",
            resource_id_field="id",
            resource_name_field="name",
            resource_price_field="price_per_night",
            resource_availability_field="available",
            searchable_fields=["type", "view", "max_guests", "bed_type"],
            display_fields=[
                "name", "type", "bed_type", "floor", "view",
                "max_guests", "price_per_night", "size_sqft",
            ],
            speech_fields=[
                "name", "type", "view", "bed_type", "floor",
                "max_guests", "price_per_night", "amenities", "description",
            ],
        ),
        tools_enabled=[
            "search_resources",
            "get_resource_details",
            "check_availability",
            "create_booking",
            "get_booking",
        ],
    ),
    "restaurant": ClientConfig(
        client_id="maharajas-kitchen",
        owner=ClientOwner(
            name="Anita Desai",
            email="anita@maharajaskitchen.com",
            phone="+91-9123456780",
            company="Maharaja's Kitchen LLP",
        ),
        business=BusinessDetails(
            name="Maharaja's Kitchen",
            location="Bandra West, Mumbai, India",
            category="restaurant",
            currency="INR",
            token_percentage=0.0,
            custom_rules=[
                "Reservations can be made up to 30 days in advance.",
                "Tables held for 15 minutes past reservation time.",
                "Free cancellation up to 2 hours before.",
                "Dress code: smart casual.",
            ],
        ),
        database=ClientDatabase(db_type="mongodb"),
        voice=VoiceSettings(
            agent_name="Priya",
            agent_personality=(
                "Cheerful, energetic young woman. Enthusiastic about food. "
                'Uses phrases like "Absolutely!", "That sounds wonderful!", '
                '"You\'re going to love it!". 2-3 sentences per reply.'
            ),
            greeting_template=(
                "Hello and welcome to {business_name}! I'm {agent_name}. "
                "Looking to reserve a table? I'd love to help!"
            ),
            language="en",
            tts_voice="aura-asteria-en",
        ),
        db_mapping=DatabaseMapping(
            resources_collection="tables",
            bookings_collection="bookings",
            resource_id_field="table_id",
            resource_name_field="name",
            resource_price_field="price_per_head",
            resource_availability_field="available",
            searchable_fields=["section", "max_guests", "outdoor"],
            display_fields=["name", "section", "max_guests", "outdoor", "description"],
            speech_fields=["name", "section", "max_guests", "description"],
        ),
        tools_enabled=[
            "search_resources",
            "get_resource_details",
            "check_availability",
            "create_booking",
        ],
    ),
    "cricket_ground": ClientConfig(
        client_id="mumbai-sports-arena",
        owner=ClientOwner(
            name="Vikram Singh",
            email="vikram@mumbaiarena.com",
            phone="+91-9988776655",
            company="Mumbai Sports Arena Pvt. Ltd.",
        ),
        business=BusinessDetails(
            name="Mumbai Sports Arena",
            location="Andheri East, Mumbai, India",
            category="cricket_ground",
            currency="INR",
            token_percentage=50.0,
            custom_rules=[
                "Slots are 2 hours each.",
                "Equipment rental available at additional cost.",
                "Cancellation free up to 24 hours before.",
                "Floodlights available for evening slots.",
            ],
        ),
        database=ClientDatabase(db_type="mongodb"),
        voice=VoiceSettings(
            agent_name="Raj",
            agent_personality=(
                "Energetic, sporty young man. Enthusiastic about sports. "
                'Uses phrases like "Great choice!", "That\'s a solid pick!". '
                "Keeps it brief and action-oriented. 2-3 sentences per reply."
            ),
            greeting_template=(
                "Hey! Welcome to {business_name}! I'm {agent_name}. "
                "Looking to book a ground or court? Let's get you sorted!"
            ),
            language="en",
            tts_voice="aura-asteria-en",
        ),
        db_mapping=DatabaseMapping(
            resources_collection="courts",
            bookings_collection="bookings",
            resource_id_field="court_id",
            resource_name_field="name",
            resource_price_field="price_per_slot",
            resource_availability_field="available",
            searchable_fields=["sport", "surface", "indoor", "floodlights"],
            display_fields=[
                "name", "sport", "surface", "capacity",
                "indoor", "floodlights", "price_per_slot",
            ],
            speech_fields=["name", "sport", "surface", "capacity", "price_per_slot", "description"],
        ),
        tools_enabled=[
            "search_resources",
            "get_resource_details",
            "check_availability",
            "create_booking",
        ],
    ),
}


async def main():
    parser = argparse.ArgumentParser(description="Seed client config into MongoDB")
    parser.add_argument(
        "--category",
        choices=list(CLIENTS.keys()),
        default="hotel",
        help="Category to seed (default: hotel)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Seed all categories",
    )
    args = parser.parse_args()

    await connect_platform(settings.mongodb_uri, settings.mongodb_database)
    repo = ClientRepository()

    categories = list(CLIENTS.keys()) if args.all else [args.category]

    for cat in categories:
        config = CLIENTS[cat]
        client_id = await repo.upsert(config)
        print(f"  Seeded client: {client_id} ({cat})")
        print(f"    Owner: {config.owner.name} ({config.owner.phone})")
        print(f"    Business: {config.business.name}")
        print(f"    DB type: {config.database.db_type}")

    await disconnect()
    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(main())
