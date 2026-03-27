from app.db.models import ClientConfig


def format_court_for_speech(court: dict, config: ClientConfig) -> str:
    """Format a sports court/ground document into natural speech."""
    name = court.get("name", "")
    sport = court.get("sport", "")
    surface = court.get("surface", "").replace("_", " ")
    capacity = court.get("capacity", 0)
    indoor = "indoor" if court.get("indoor") else "outdoor"
    lights = "with floodlights" if court.get("floodlights") else "daytime only"
    price = court.get("price_per_slot", 0)
    currency = config.business.currency

    return (
        f"{name} is an {indoor} {sport} {surface} ground "
        f"for up to {capacity} players, {lights}. "
        f"The rate is {price:,} {currency} per 2-hour slot."
    )
