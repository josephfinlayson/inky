#!/usr/bin/env python3
"""Weather API client for OpenWeatherMap."""

from datetime import datetime, timedelta
import geocoder
import requests

from config import OPENWEATHERMAP_API_KEY


class WeatherClient:
    """Fetches weather data from OpenWeatherMap API."""

    def __init__(self, city: str, country_code: str):
        self.city = city
        self.country_code = country_code
        self.api_key = OPENWEATHERMAP_API_KEY
        self.coords = self._get_coords()

    def _get_coords(self) -> tuple:
        """Convert city name to lat/lon coordinates."""
        address = f"{self.city}, {self.country_code}"
        g = geocoder.arcgis(address)
        return g.latlng

    def fetch(self) -> dict:
        """Fetch current weather and forecast data."""
        weather = {"today": {}, "tomorrow": {}, "next_day": {}}

        # Current weather
        current_url = (
            f"https://api.openweathermap.org/data/2.5/weather"
            f"?lat={self.coords[0]}&lon={self.coords[1]}"
            f"&appid={self.api_key}&units=metric"
        )
        response = requests.get(current_url, timeout=10).json()
        weather["today"]["summary"] = response["weather"][0]["main"].lower()
        weather["today"]["temperature"] = response["main"]["temp"]

        # Sunrise/sunset times
        weather["sunrise"] = datetime.fromtimestamp(response["sys"]["sunrise"]).strftime("%H:%M")
        weather["sunset"] = datetime.fromtimestamp(response["sys"]["sunset"]).strftime("%H:%M")

        # Forecast
        forecast_url = (
            f"https://api.openweathermap.org/data/2.5/forecast"
            f"?lat={self.coords[0]}&lon={self.coords[1]}"
            f"&appid={self.api_key}&units=metric"
        )
        response = requests.get(forecast_url, timeout=10).json()

        # Group forecast by day
        days = {}
        for item in response["list"]:
            day = datetime.fromtimestamp(item["dt"]).strftime("%Y-%m-%d")
            if day not in days:
                days[day] = []
            days[day].append(item)

        # Extract min/max for each day
        for day, items in days.items():
            temps = [item["main"]["temp"] for item in items]
            weather[day] = {
                "summary": items[0]["weather"][0]["main"].lower(),
                "max": str(round(max(temps))),
                "min": str(round(min(temps))),
            }

        # Map tomorrow and next_day
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        next_day = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
        weather["tomorrow"] = weather.get(tomorrow, {})
        weather["next_day"] = weather.get(next_day, {})

        # Extract hourly precipitation for today (24h from midnight)
        weather["precipitation"] = self._extract_precipitation(response["list"])

        return weather

    def _extract_precipitation(self, forecast_list: list) -> list:
        """Extract precipitation probability for today's 24 hours.

        Returns list of (hour, pop) tuples for 00:00-23:59 today.
        """
        today = datetime.now().strftime("%Y-%m-%d")
        precip = []

        for item in forecast_list:
            dt = datetime.fromtimestamp(item["dt"])
            if dt.strftime("%Y-%m-%d") == today:
                hour = dt.hour
                pop = item.get("pop", 0)  # 0-1 probability
                precip.append({"hour": hour, "pop": pop})

        return precip
