#!/usr/bin/env python3
"""Configuration constants for the weather display."""

# Location
CITY = "Berlin"
COUNTRY_CODE = "DE"
TIMEZONE = "Europe/Berlin"

# Weather API
OPENWEATHERMAP_API_KEY = "dd4e4011d95b7f9a60842291284c6569"

# BVG API
BVG_STATION_ID = "900068302"  # U Kaiserin-Augusta-Str
BVG_API_BASE = "https://v6.bvg.transport.rest"

# Display
WARNING_TEMP = 25.0

# Icon mapping
ICON_MAP = {
    "snow": ["snow", "sleet"],
    "rain": ["rain", "drizzle"],
    "cloud": ["fog", "cloudy", "partly-cloudy-day", "partly-cloudy-night", "clouds"],
    "sun": ["clear-day", "clear-night", "clear"],
    "storm": [],
    "wind": ["wind"],
}
