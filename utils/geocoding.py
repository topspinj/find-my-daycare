import os
from typing import Optional, Tuple

import googlemaps
from dotenv import load_dotenv

load_dotenv()


def get_maps_client() -> googlemaps.Client:
    """Get a Google Maps client instance."""
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_MAPS_API_KEY not found in environment variables")
    return googlemaps.Client(key=api_key)


def geocode_address(address: str) -> Optional[Tuple[float, float]]:
    """
    Convert a Toronto-area address to latitude/longitude coordinates.

    Args:
        address: Street address string (e.g., "100 Queen St W, Toronto")

    Returns:
        Tuple of (latitude, longitude) or None if geocoding fails
    """
    # Append Toronto if not present for better accuracy
    if "toronto" not in address.lower():
        address = f"{address}, Toronto, Ontario, Canada"

    try:
        client = get_maps_client()
        results = client.geocode(address)

        if results:
            location = results[0]["geometry"]["location"]
            return (location["lat"], location["lng"])
        return None
    except Exception:
        return None
