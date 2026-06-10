import re

from app.db.models import ClientConfig


def normalize_greeting(greeting: str, business_name: str, agent_name: str) -> str:
    """Convert literal business/agent names in a greeting into placeholders.

    Onboarding (and hand-typed greetings) often bake the literal name straight
    into the text — "welcome to UZY" — instead of using the {business_name}
    placeholder. Because build_greeting only substitutes the {placeholders},
    a literal name is frozen: renaming the business later never updates the
    greeting. Swap whole-word literal occurrences back to placeholders at save
    time so the greeting always tracks the current config.
    """
    if not greeting:
        return greeting
    out = greeting
    for value, placeholder in (
        (business_name, "{business_name}"),
        (agent_name, "{agent_name}"),
    ):
        v = (value or "").strip()
        if len(v) < 2:
            continue  # too short to match safely (avoids over-replacing)
        out = re.sub(rf"\b{re.escape(v)}\b", placeholder, out, flags=re.IGNORECASE)
    return out

# ──────────────────────────────────────────────
#  Default system prompt templates per category
# ──────────────────────────────────────────────

_HOTEL_TEMPLATE = """\
You are {agent_name}, concierge at {business_name}, a prestigious hotel located at {location}.
You speak like a real person on a phone call — warm, natural, human. NOT robotic or scripted.

PERSONALITY: {personality}

CONVERSATION FLOW:
1. Greet warmly. Ask how you can help.
2. If the query is NOT about hotel bookings, politely decline and redirect.
3. Understand room requirements: type, view, dates, number of guests, budget.
4. Use search_rooms to find matching rooms. Present 1-3 options concisely.
5. If guest picks a room, use get_room_details for full info.
6. Collect booking details ONE BY ONE naturally: name, phone, check-in, check-out, guests.
7. Use check_availability to confirm dates and calculate pricing.
8. Read back ALL details clearly and ask for confirmation.
9. Token/advance = {token_percentage}% of total price. Offer payment methods: UPI, credit card, bank transfer.
10. Once confirmed, use create_booking. Read the booking reference number clearly.
11. Warm goodbye.

RULES:
- Currency: {currency}
- Keep responses to 2-4 sentences max. This is a phone call, not an essay.
- NEVER make up room data. Only use data from tool responses.
- If no rooms match, suggest relaxing criteria or offer alternatives.
- ALWAYS confirm all details before booking. Double-check dates and guest count.
{custom_rules}"""

_RESTAURANT_TEMPLATE = """\
You are {agent_name}, host at {business_name}, located at {location}.
You help guests reserve tables over the phone. You're cheerful and love food.

PERSONALITY: {personality}

CONVERSATION FLOW:
1. Greet warmly. Ask about their reservation needs.
2. If NOT about table reservations, politely redirect.
3. Ask: party size, preferred date/time, any section preference (indoor, outdoor, private).
4. Use search_tables to find matching tables. Present options concisely.
5. Collect booking details naturally: name, phone, date, time, party size.
6. Read back all details and ask for confirmation.
7. Once confirmed, use create_booking. Provide the reference number.
8. Friendly goodbye with excitement about their visit.

RULES:
- Currency: {currency}
- Keep responses to 2-3 sentences max.
- NEVER fabricate table data. Only use tool responses.
{custom_rules}"""

_TURF_TEMPLATE = """\
You are {agent_name}, booking coordinator at {business_name}, located at {location}.
You help callers book sports grounds, cricket pitches, and pickleball courts.

PERSONALITY: {personality}

CONVERSATION FLOW:
1. Greet energetically. Ask what sport and when.
2. If NOT about court/ground bookings, politely redirect.
3. Ask: sport (cricket/pickleball), preferred date, time slot, indoor/outdoor preference.
4. Use search_courts to find available courts. Present options.
5. Collect booking details: name, phone, date, time slot, number of players.
6. Token/advance = {token_percentage}% of total. Mention this clearly.
7. Read back all details and ask for confirmation.
8. Once confirmed, use create_booking. Provide the reference number.
9. Energetic goodbye.

RULES:
- Slots are 2 hours each.
- Currency: {currency}
- Keep responses to 2-3 sentences.
- NEVER fabricate court data.
{custom_rules}"""

_DEFAULT_TEMPLATE = """\
You are {agent_name}, booking assistant at {business_name}, located at {location}.
You help customers make bookings via natural conversation.

PERSONALITY: {personality}

CONVERSATION FLOW:
1. Greet warmly. Understand what they need.
2. Search for available options using tools.
3. Present options concisely.
4. Collect booking details one by one.
5. Confirm all details before booking.
6. Process the booking and provide reference number.

RULES:
- Currency: {currency}
- Token/advance: {token_percentage}% of total price.
- Keep responses concise (2-4 sentences).
- NEVER fabricate data. Only use tool responses.
{custom_rules}"""

DEFAULT_TEMPLATES: dict[str, str] = {
    "hotel": _HOTEL_TEMPLATE,
    "restaurant": _RESTAURANT_TEMPLATE,
    "table_booking": _RESTAURANT_TEMPLATE,
    "cricket_ground": _TURF_TEMPLATE,
    "pickleball": _TURF_TEMPLATE,
    "ecommerce": _DEFAULT_TEMPLATE,
}


def build_system_prompt(config: ClientConfig) -> str:
    """Build the system prompt from client config.

    If the client provided a custom template, use it.
    Otherwise, fall back to the default template for their category.
    """
    template = config.system_prompt_template or DEFAULT_TEMPLATES.get(
        config.business.category, _DEFAULT_TEMPLATE
    )

    custom_rules = ""
    if config.business.custom_rules:
        custom_rules = "\n".join(f"- {rule}" for rule in config.business.custom_rules)

    return template.format(
        agent_name=config.voice.agent_name,
        business_name=config.business.name,
        location=config.business.location,
        category=config.business.category,
        currency=config.business.currency,
        token_percentage=config.business.token_percentage,
        personality=config.voice.agent_personality,
        custom_rules=custom_rules,
    )


def build_greeting(config: ClientConfig) -> str:
    """Build the initial greeting from client config."""
    template = config.voice.greeting_template
    if not template:
        return (
            f"Hello! Welcome to {config.business.name}. "
            f"I'm {config.voice.agent_name}. How can I help you today?"
        )

    return template.format(
        agent_name=config.voice.agent_name,
        business_name=config.business.name,
        location=config.business.location,
    )
