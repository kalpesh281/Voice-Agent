from app.db.models import ClientConfig


def format_table_for_speech(table: dict, config: ClientConfig) -> str:
    """Format a restaurant table document into natural speech."""
    name = table.get("name", "")
    section = table.get("section", "main")
    guests = table.get("max_guests", 2)
    outdoor = "outdoor" if table.get("outdoor") else "indoor"
    description = table.get("description", "")
    price = table.get("price_per_head", 0)
    currency = config.business.currency

    text = f"{name} seats up to {guests} guests in our {section} section ({outdoor})."
    if description:
        text += f" {description}"
    if price:
        text += f" Starting at {price:,} {currency} per head."
    return text
