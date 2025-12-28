import os
from typing import Dict, List, Tuple

import googlemaps
from dotenv import load_dotenv

load_dotenv()


def get_maps_client() -> googlemaps.Client:
    """Get a Google Maps client instance."""
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_MAPS_API_KEY not found in environment variables")
    return googlemaps.Client(key=api_key)


def get_travel_times_for_mode(
    client: googlemaps.Client,
    origin: Tuple[float, float],
    destinations: List[Tuple[float, float]],
    mode: str,
) -> List[Dict]:
    """Get travel times for a specific mode."""
    results = []
    batch_size = 25

    for i in range(0, len(destinations), batch_size):
        batch = destinations[i : i + batch_size]

        try:
            response = client.distance_matrix(
                origins=[origin],
                destinations=batch,
                mode=mode,
                units="metric",
            )

            for element in response["rows"][0]["elements"]:
                if element["status"] == "OK":
                    results.append(element["duration"]["text"])
                else:
                    results.append("N/A")
        except Exception:
            for _ in batch:
                results.append("N/A")

    return results


def get_all_travel_times(
    origin: Tuple[float, float], destinations: List[Tuple[float, float]]
) -> List[Dict]:
    """
    Get walking, transit, and driving times from origin to destinations.

    Returns:
        List of dicts with 'walk', 'transit', and 'drive' keys
    """
    if not destinations:
        return []

    client = get_maps_client()

    walk_times = get_travel_times_for_mode(client, origin, destinations, "walking")
    transit_times = get_travel_times_for_mode(client, origin, destinations, "transit")
    drive_times = get_travel_times_for_mode(client, origin, destinations, "driving")

    results = []
    for i in range(len(destinations)):
        results.append(
            {
                "walk": walk_times[i],
                "transit": transit_times[i],
                "drive": drive_times[i],
            }
        )

    return results
