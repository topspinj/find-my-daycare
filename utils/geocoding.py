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

        if not results:
            return None

        result = results[0]
        geometry = result.get("geometry", {})
        location = geometry.get("location")

        if not location:
            return None

        # Reject vague matches - only accept precise addresses
        # ROOFTOP = exact address, RANGE_INTERPOLATED = interpolated street number
        location_type = geometry.get("location_type", "")
        if location_type not in ("ROOFTOP", "RANGE_INTERPOLATED"):
            return None

        # Check that result is in Toronto area
        address_components = result.get("address_components", [])
        is_toronto = False
        has_street = False

        for component in address_components:
            types = component.get("types", [])
            name = component.get("long_name", "").lower()

            # Check for Toronto
            if "locality" in types and "toronto" in name:
                is_toronto = True

            # Check for street-level address
            if "street_number" in types or "route" in types:
                has_street = True

        # Must be in Toronto and have a street address
        if not is_toronto or not has_street:
            return None

        return (location["lat"], location["lng"])
    except Exception:
        return None
