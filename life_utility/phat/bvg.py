#!/usr/bin/env python3
"""BVG API client for U-Bahn departure times."""

from datetime import datetime
import requests

from config import BVG_STATION_ID, BVG_API_BASE


class BVGClient:
    """Fetches U-Bahn departure times from BVG API."""

    def __init__(self, station_id: str = BVG_STATION_ID):
        self.station_id = station_id
        self.base_url = BVG_API_BASE

    def get_northbound_departures(self, limit: int = 4) -> list[int]:
        """Fetch northbound U6 departures in minutes from now."""
        url = (
            f"{self.base_url}/stops/{self.station_id}/departures"
            f"?duration=30&subway=true&bus=false&tram=false"
            f"&ferry=false&express=false&regional=false"
        )

        try:
            response = requests.get(url, timeout=10).json()
            departures = response.get("departures", [])

            # Filter northbound (Kurt-Schumacher-Platz = toward Alt-Tegel)
            northbound = [
                d for d in departures
                if "Kurt-Schumacher" in d.get("direction", "")
                or "Alt-Tegel" in d.get("direction", "")
            ]

            # Convert to minutes from now
            results = []
            for dep in northbound[:limit]:
                when = dep.get("when") or dep.get("plannedWhen")
                if when:
                    dep_time = datetime.fromisoformat(when.replace("Z", "+00:00"))
                    now = datetime.now(dep_time.tzinfo)
                    mins = int((dep_time - now).total_seconds() / 60)
                    if mins >= 0:
                        results.append(mins)

            return results[:limit]

        except Exception as e:
            print(f"Error fetching U6 departures: {e}")
            return []
