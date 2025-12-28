# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Find My Daycare is a Flask web application that helps Toronto parents find licensed daycares near their address, filtered by their child's age group. It uses Toronto Open Data for daycare information and Google Maps API for geocoding and travel times.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run development server (port 5001)
python3 app.py

# Production server
gunicorn app:app
```

## Environment Variables

Requires `GOOGLE_MAPS_API_KEY` in `.env` file for geocoding and distance matrix API calls.

## Architecture

**Request Flow:**
1. User submits address + child's birthday on homepage
2. `geocode_address()` converts address to lat/lon via Google Maps
3. `load_daycare_data()` reads the most recent CSV from `data/` directory
4. `find_nearby_daycares()` filters daycares within 5km radius with capacity for child's age group
5. `get_all_travel_times()` fetches walk/transit/drive times via Google Distance Matrix API
6. Results rendered with Leaflet.js map

**Key Modules:**
- `utils/age_mapper.py` - Maps child's age to Toronto daycare age groups (Infant, Toddler, Preschool, Kindergarten, School Age)
- `utils/geocoding.py` - Google Maps geocoding wrapper
- `utils/travel_time.py` - Batch travel time calculations (25 destinations per API call)
- `utils/distance.py` - Haversine distance calculation

**Data:**
- Daycare data is a CSV from Toronto Open Data stored in `data/`
- CSV contains GeoJSON geometry, capacity columns (IGSPACE, TGSPACE, PGSPACE, KGSPACE, SGSPACE), and program flags (subsidy, cwelcc_flag)
- `data/fetch_daycare_data.py` can refresh the data

**Frontend:**
- Jinja2 templates with Leaflet.js for maps
- Flatpickr for date picker
- Client-side filtering by walking distance and CWELCC status

## Deployment

Configured for Render with `.python-version` (3.11.7) and gunicorn in requirements.txt.
