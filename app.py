import json
import os
from datetime import datetime
from typing import List, Optional, Tuple

from flask import Flask, render_template, request
import pandas as pd
from dotenv import load_dotenv

from utils.geocoding import geocode_address
from utils.distance import haversine_distance
from utils.age_mapper import get_age_group, calculate_age_in_months
from utils.travel_time import get_all_travel_times

load_dotenv()

app = Flask(__name__)

SEARCH_RADIUS_KM = 5.0
DATA_DIR = "data"


def load_daycare_data() -> pd.DataFrame:
    """Load the most recent daycare CSV file."""
    csv_files = [f for f in os.listdir(DATA_DIR) if f.endswith(".csv")]
    if not csv_files:
        raise FileNotFoundError("No daycare data file found")

    csv_files.sort(reverse=True)
    latest_file = os.path.join(DATA_DIR, csv_files[0])

    return pd.read_csv(latest_file)


def parse_geometry(geometry_str: str) -> Optional[Tuple[float, float]]:
    """Extract lat/long from GeoJSON geometry string."""
    try:
        geom = json.loads(geometry_str)
        if geom["type"] == "Point":
            lon, lat = geom["coordinates"]  # GeoJSON is [lon, lat]
            return (lat, lon)
    except (json.JSONDecodeError, KeyError, TypeError):
        pass
    return None


def find_nearby_daycares(
    user_lat: float, user_lon: float, birthday: datetime, df: pd.DataFrame
) -> List[dict]:
    """Find daycares within radius that have capacity for the child's age group."""
    age_group = get_age_group(birthday.date())
    capacity_column = age_group["column"]

    results = []

    for _, row in df.iterrows():
        coords = parse_geometry(row["geometry"])
        if coords is None:
            continue

        daycare_lat, daycare_lon = coords

        distance = haversine_distance(user_lat, user_lon, daycare_lat, daycare_lon)

        if distance > SEARCH_RADIUS_KM:
            continue

        capacity = row.get(capacity_column, 0)
        if pd.isna(capacity) or int(capacity) <= 0:
            continue

        results.append(
            {
                "name": row["LOC_NAME"],
                "address": row["ADDRESS"],
                "postal_code": row["PCODE"],
                "phone": row["PHONE"],
                "distance_km": round(distance, 2),
                "capacity": int(capacity),
                "total_spaces": int(row["TOTSPACE"]),
                "subsidy": row["subsidy"] == "Y",
                "cwelcc": row["cwelcc_flag"] == "Y",
                "age_group_label": age_group["label"],
                "lat": daycare_lat,
                "lon": daycare_lon,
                "infant_spaces": int(row["IGSPACE"]) if not pd.isna(row["IGSPACE"]) else 0,
                "toddler_spaces": int(row["TGSPACE"]) if not pd.isna(row["TGSPACE"]) else 0,
                "preschool_spaces": int(row["PGSPACE"]) if not pd.isna(row["PGSPACE"]) else 0,
                "kindergarten_spaces": int(row["KGSPACE"]) if not pd.isna(row["KGSPACE"]) else 0,
                "schoolage_spaces": int(row["SGSPACE"]) if not pd.isna(row["SGSPACE"]) else 0,
            }
        )

    results.sort(key=lambda x: x["distance_km"])

    return results


def parse_walk_time(walk_time_str: str) -> Optional[int]:
    """Parse walk time string like '15 mins' or '1 hour 5 mins' to minutes."""
    if not walk_time_str or walk_time_str == "N/A":
        return None
    try:
        total_minutes = 0
        # Handle hours
        if "hour" in walk_time_str:
            parts = walk_time_str.split("hour")
            hours = int(parts[0].strip())
            total_minutes += hours * 60
            walk_time_str = parts[1] if len(parts) > 1 else ""
        # Handle minutes
        if "min" in walk_time_str:
            min_part = walk_time_str.split("min")[0].strip()
            # Get just the number (last word before "min")
            min_num = min_part.split()[-1] if min_part else "0"
            total_minutes += int(min_num)
        return total_minutes if total_minutes > 0 else None
    except (ValueError, AttributeError, IndexError):
        return None


def calculate_stats(results: List[dict]) -> dict:
    """Calculate summary statistics for search results."""
    if not results:
        return {}

    total = len(results)

    # Walking distance (15 min or less)
    walking_distance = 0
    for r in results:
        minutes = parse_walk_time(r.get("walk_time"))
        if minutes is not None and minutes <= 15:
            walking_distance += 1

    # CWELCC count
    cwelcc_count = sum(1 for r in results if r.get("cwelcc"))

    # Subsidy count
    subsidy_count = sum(1 for r in results if r.get("subsidy"))

    # Total spaces for the age group
    total_spaces = sum(r.get("capacity", 0) for r in results)

    return {
        "total": total,
        "walking_distance": walking_distance,
        "cwelcc_count": cwelcc_count,
        "cwelcc_percent": round(cwelcc_count / total * 100) if total > 0 else 0,
        "subsidy_count": subsidy_count,
        "subsidy_percent": round(subsidy_count / total * 100) if total > 0 else 0,
        "total_spaces": total_spaces,
    }


@app.route("/", methods=["GET", "POST"])
def index():
    """Main search page."""
    if request.method == "POST":
        address = request.form.get("address", "").strip()
        birthday_str = request.form.get("birthday", "").strip()

        errors = []

        if not address:
            errors.append("Please enter an address")

        if not birthday_str:
            errors.append("Please enter your child's birthday")

        birthday = None
        if birthday_str:
            try:
                birthday = datetime.strptime(birthday_str, "%Y-%m-%d")
            except ValueError:
                errors.append("Invalid date format")

        if errors:
            return render_template(
                "index.html", errors=errors, address=address, birthday=birthday_str
            )

        coords = geocode_address(address)
        if coords is None:
            errors.append(
                "Could not find that address. Please try a more specific address."
            )
            return render_template(
                "index.html", errors=errors, address=address, birthday=birthday_str
            )

        user_lat, user_lon = coords

        try:
            df = load_daycare_data()
            results = find_nearby_daycares(user_lat, user_lon, birthday, df)

            # Get travel times for all results
            if results:
                destinations = [(r["lat"], r["lon"]) for r in results]
                travel_times = get_all_travel_times((user_lat, user_lon), destinations)
                for i, result in enumerate(results):
                    result["walk_time"] = travel_times[i]["walk"]
                    result["transit_time"] = travel_times[i]["transit"]
                    result["drive_time"] = travel_times[i]["drive"]

            # Calculate summary stats
            stats = calculate_stats(results)
        except Exception as e:
            errors.append(f"Error searching daycares: {str(e)}")
            return render_template(
                "index.html", errors=errors, address=address, birthday=birthday_str
            )

        age_months = calculate_age_in_months(birthday.date())
        if age_months >= 12:
            age_display = f"{age_months // 12} years, {age_months % 12} months"
        else:
            age_display = f"{age_months} months"

        return render_template(
            "results.html",
            results=results,
            address=address,
            age_display=age_display,
            radius_km=SEARCH_RADIUS_KM,
            user_lat=user_lat,
            user_lon=user_lon,
            stats=stats,
        )

    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5001)
