#!/usr/bin/env python3
"""Main entrypoint for the Inky pHAT weather display."""

from inky.auto import auto

from config import CITY, COUNTRY_CODE
from weather import WeatherClient
from bvg import BVGClient
from display import WeatherDisplay


def main():
    """Fetch data and render to display."""
    # Initialize display hardware
    inky_display = auto(ask_user=True, verbose=True)
    inky_display.set_border(inky_display.BLACK)

    # Fetch weather data
    weather_client = WeatherClient(CITY, COUNTRY_CODE)
    weather = weather_client.fetch()

    # Fetch U6 departures
    bvg_client = BVGClient()
    departures = bvg_client.get_northbound_departures()

    # Render to display
    display = WeatherDisplay(inky_display)
    display.render(weather, departures)
    display.show()


if __name__ == "__main__":
    main()
