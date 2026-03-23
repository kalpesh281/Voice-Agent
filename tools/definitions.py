"""
OpenAI function tool definitions — shared by run.py and any other agent runner.
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_rooms",
            "description": "Search available hotel rooms by preferences.",
            "parameters": {
                "type": "object",
                "properties": {
                    "room_type": {
                        "type": "string",
                        "description": "deluxe, superior, suite, penthouse, or villa.",
                    },
                    "view": {
                        "type": "string",
                        "description": "sea, garden, city, pool, or mountain.",
                    },
                    "num_guests": {
                        "type": "integer",
                        "description": "Number of guests.",
                    },
                    "max_price_per_night": {
                        "type": "number",
                        "description": "Max budget per night in rupees.",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_room_details",
            "description": "Get full details about a specific hotel room.",
            "parameters": {
                "type": "object",
                "properties": {
                    "room_id": {
                        "type": "string",
                        "description": "e.g. room-001.",
                    },
                },
                "required": ["room_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_availability",
            "description": "Check room availability and calculate pricing.",
            "parameters": {
                "type": "object",
                "properties": {
                    "room_id": {"type": "string"},
                    "check_in": {"type": "string", "description": "YYYY-MM-DD"},
                    "check_out": {"type": "string", "description": "YYYY-MM-DD"},
                },
                "required": ["room_id", "check_in", "check_out"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_booking",
            "description": "Create confirmed booking after guest confirms and agrees to token.",
            "parameters": {
                "type": "object",
                "properties": {
                    "room_id": {"type": "string"},
                    "guest_name": {"type": "string"},
                    "guest_phone": {"type": "string"},
                    "check_in": {"type": "string", "description": "YYYY-MM-DD"},
                    "check_out": {"type": "string", "description": "YYYY-MM-DD"},
                    "num_guests": {"type": "integer"},
                    "payment_method": {"type": "string"},
                    "special_requests": {"type": "string"},
                },
                "required": ["room_id", "guest_name", "guest_phone", "check_in", "check_out", "num_guests"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_booking",
            "description": "Look up an existing booking by reference ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "booking_id": {"type": "string"},
                },
                "required": ["booking_id"],
            },
        },
    },
]
