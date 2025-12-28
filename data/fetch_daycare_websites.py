"""
One-time script to fetch daycare website URLs using Google Places API.

Usage:
    python3 data/fetch_daycare_websites.py

This will create/update data/daycare_supplementary.csv with website URLs.
"""

import json
import os
import time
from typing import Optional, Tuple

import pandas as pd
import googlemaps
from dotenv import load_dotenv

load_dotenv()


def parse_geometry(geometry_str: str) -> Optional[Tuple[float, float]]:
    """Extract lat/lon from GeoJSON geometry string."""
    try:
        geom = json.loads(geometry_str)
        if geom["type"] == "Point":
            lon, lat = geom["coordinates"]  # GeoJSON is [lon, lat]
            return (lat, lon)
    except (json.JSONDecodeError, KeyError, TypeError):
        pass
    return None

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(DATA_DIR, "daycare_supplementary.csv")


def get_latest_daycare_csv() -> str:
    """Find the most recent daycare data CSV file."""
    csv_files = [
        f for f in os.listdir(DATA_DIR)
        if f.startswith("daycare_list_") and f.endswith(".csv")
    ]
    if not csv_files:
        raise FileNotFoundError("No daycare_list_*.csv file found in data/")
    csv_files.sort(reverse=True)
    return os.path.join(DATA_DIR, csv_files[0])


def fetch_place_details(
    client: googlemaps.Client,
    name: str,
    address: str,
    postal_code: str,
    lat: Optional[float],
    lon: Optional[float],
) -> dict:
    """
    Search for a daycare using Google Places API and return all available details.

    Uses location bias and postal code to improve accuracy.
    Returns dict with all fetched fields (empty values if not found).
    """
    # Include postal code for more precise matching
    query = f"{name}, {address}, {postal_code}, Toronto, Ontario"

    empty_result = {
        "website": "",
        "google_rating": "",
        "google_reviews_count": "",
        "google_maps_url": "",
        "google_phone": "",
        "google_hours_mon": "",
        "google_hours_tue": "",
        "google_hours_wed": "",
        "google_hours_thu": "",
        "google_hours_fri": "",
        "google_hours_sat": "",
        "google_hours_sun": "",
        "google_photo_url": "",
        "google_place_id": "",
        "match_confidence": "",
    }

    try:
        # Build search params with location bias if coordinates available
        search_params = {"query": query, "type": "child_care"}
        if lat and lon:
            # Bias results toward the known location (500m radius)
            search_params["location"] = (lat, lon)
            search_params["radius"] = 500

        # Search for the place
        results = client.places(**search_params)

        if not results.get("results"):
            empty_result["match_confidence"] = "no_results"
            return empty_result

        # Get the top result
        top_result = results["results"][0]
        place_id = top_result["place_id"]

        # Check if the result is reasonably close to expected location
        if lat and lon:
            result_lat = top_result["geometry"]["location"]["lat"]
            result_lon = top_result["geometry"]["location"]["lng"]
            # Simple distance check (rough, not haversine)
            lat_diff = abs(result_lat - lat)
            lon_diff = abs(result_lon - lon)
            if lat_diff > 0.01 or lon_diff > 0.01:  # ~1km threshold
                empty_result["match_confidence"] = "location_mismatch"
                return empty_result

        # Get place details with all useful fields
        details = client.place(
            place_id,
            fields=[
                "website",
                "rating",
                "user_ratings_total",
                "url",
                "formatted_phone_number",
                "opening_hours",
                "photo",
            ]
        )

        result = details.get("result", {})

        # Parse opening hours into separate day columns
        hours = {}
        opening_hours = result.get("opening_hours", {})
        weekday_text = opening_hours.get("weekday_text", [])
        day_map = {
            "Monday": "mon", "Tuesday": "tue", "Wednesday": "wed",
            "Thursday": "thu", "Friday": "fri", "Saturday": "sat", "Sunday": "sun"
        }
        for day_hours in weekday_text:
            for day_name, day_key in day_map.items():
                if day_hours.startswith(day_name):
                    hours[f"google_hours_{day_key}"] = day_hours.replace(f"{day_name}: ", "")
                    break

        # Get first photo URL if available
        photos = result.get("photo", [])
        photo_url = ""
        if photos:
            photo_ref = photos[0].get("photo_reference") if isinstance(photos, list) else photos.get("photo_reference")
            if photo_ref:
                # Construct the photo URL (requires API key to access)
                photo_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photo_reference={photo_ref}&key={client.key}"

        return {
            "website": result.get("website", ""),
            "google_rating": result.get("rating", ""),
            "google_reviews_count": result.get("user_ratings_total", ""),
            "google_maps_url": result.get("url", ""),
            "google_phone": result.get("formatted_phone_number", ""),
            "google_hours_mon": hours.get("google_hours_mon", ""),
            "google_hours_tue": hours.get("google_hours_tue", ""),
            "google_hours_wed": hours.get("google_hours_wed", ""),
            "google_hours_thu": hours.get("google_hours_thu", ""),
            "google_hours_fri": hours.get("google_hours_fri", ""),
            "google_hours_sat": hours.get("google_hours_sat", ""),
            "google_hours_sun": hours.get("google_hours_sun", ""),
            "google_photo_url": photo_url,
            "google_place_id": place_id,
            "match_confidence": "high",
        }

    except Exception as e:
        print(f"  Error fetching {name}: {e}")
        empty_result["match_confidence"] = f"error: {e}"
        return empty_result


def main():
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_MAPS_API_KEY not found in environment variables")

    client = googlemaps.Client(key=api_key)

    # Load daycare data
    csv_path = get_latest_daycare_csv()
    print(f"Loading daycares from: {csv_path}")
    df = pd.read_csv(csv_path)

    print(f"Found {len(df)} daycares")

    # Load existing supplementary data if it exists (to preserve manual entries)
    existing_data = {}
    if os.path.exists(OUTPUT_FILE):
        existing_df = pd.read_csv(OUTPUT_FILE)
        for _, row in existing_df.iterrows():
            existing_data[row["LOC_ID"]] = row.to_dict()
        print(f"Found {len(existing_df)} existing entries")

    # Fetch details for each daycare
    results = []

    for idx, row in df.iterrows():
        loc_id = row["LOC_ID"]
        name = row["LOC_NAME"]
        address = row["ADDRESS"]
        postal_code = row.get("PCODE", "")

        # Parse coordinates from geometry
        coords = parse_geometry(row.get("geometry", ""))
        lat, lon = coords if coords else (None, None)

        # Skip if we already have data for this daycare (preserve all existing data)
        if loc_id in existing_data and existing_data[loc_id].get("match_confidence") == "high":
            print(f"[{idx + 1}/{len(df)}] Skipping {name} (already fetched)")
            results.append(existing_data[loc_id])
            continue

        print(f"[{idx + 1}/{len(df)}] Fetching: {name}...")

        place_details = fetch_place_details(client, name, address, postal_code, lat, lon)

        confidence = place_details.get("match_confidence", "")
        if confidence == "high":
            if place_details["website"]:
                print(f"  Website: {place_details['website']}")
            if place_details["google_rating"]:
                print(f"  Rating: {place_details['google_rating']} ({place_details['google_reviews_count']} reviews)")
        else:
            print(f"  No match ({confidence})")

        # Combine fetched data with manual fields (preserve existing manual entries if any)
        existing = existing_data.get(loc_id, {})
        result_row = {
            "LOC_ID": loc_id,
            **place_details,
            # Manual fields - preserve existing or leave empty
            "food_info": existing.get("food_info", ""),
            "surveillance_cameras": existing.get("surveillance_cameras", ""),
            "religious_affiliation": existing.get("religious_affiliation", ""),
        }
        results.append(result_row)

        # Small delay to avoid rate limiting
        time.sleep(0.1)

    # Save results
    results_df = pd.DataFrame(results)
    results_df.to_csv(OUTPUT_FILE, index=False)

    # Print summary
    high_confidence = sum(1 for r in results if r.get("match_confidence") == "high")
    websites_found = sum(1 for r in results if r.get("website"))
    ratings_found = sum(1 for r in results if r.get("google_rating"))
    no_results = sum(1 for r in results if r.get("match_confidence") == "no_results")
    location_mismatch = sum(1 for r in results if r.get("match_confidence") == "location_mismatch")

    print(f"\nDone! Saved to {OUTPUT_FILE}")
    print(f"High confidence matches: {high_confidence}/{len(results)}")
    print(f"Websites found: {websites_found}/{len(results)}")
    print(f"Ratings found: {ratings_found}/{len(results)}")
    print(f"No results: {no_results}")
    print(f"Location mismatch (rejected): {location_mismatch}")


if __name__ == "__main__":
    main()
