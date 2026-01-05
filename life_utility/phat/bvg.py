#!/usr/bin/env python3
"""BVG API client for U-Bahn departure times."""

import time
from datetime import datetime
import requests

from config import BVG_STATION_ID, BVG_API_BASE

# Alexanderplatz - major hub to check all U-Bahn line delays
ALEXANDERPLATZ_ID = "900100003"


class BVGClient:
    """Fetches U-Bahn departure times from BVG API."""

    def __init__(self, station_id: str = BVG_STATION_ID):
        self.station_id = station_id
        self.base_url = BVG_API_BASE

    def get_northbound_departures(self, limit: int = 2) -> list[int]:
        """Fetch northbound U6 departures in minutes from now."""
        url = (
            f"{self.base_url}/stops/{self.station_id}/departures"
            f"?duration=30&subway=true&bus=false&tram=false"
            f"&ferry=false&express=false&regional=false"
        )

        # Retry up to 3 times with increasing timeout
        max_retries = 3
        last_error = None

        for attempt in range(max_retries):
            try:
                timeout = 15 + (attempt * 5)  # 15s, 20s, 25s
                response = requests.get(url, timeout=timeout)
                response.raise_for_status()
                data = response.json()
                departures = data.get("departures", [])

                # Filter northbound (Kurt-Schumacher-Platz = toward Alt-Tegel)
                northbound = [
                    d for d in departures
                    if "Kurt-Schumacher" in d.get("direction", "")
                    or "Alt-Tegel" in d.get("direction", "")
                ]

                # Convert to seconds from now
                results = []
                for dep in northbound[:limit]:
                    when = dep.get("when") or dep.get("plannedWhen")
                    if when:
                        dep_time = datetime.fromisoformat(when.replace("Z", "+00:00"))
                        now = datetime.now(dep_time.tzinfo)
                        secs = int((dep_time - now).total_seconds())
                        if secs >= 0:
                            results.append(secs)

                return results[:limit]

            except Exception as e:
                last_error = e
                print(f"BVG API attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)  # Wait before retry

        print(f"BVG API failed after {max_retries} attempts: {last_error}")
        return []

    def get_ubahn_delays(self, min_delay_mins: int = 2) -> dict[str, int]:
        """Fetch U-Bahn lines with significant delays.

        Returns dict of {line_name: delay_minutes} for lines delayed >= min_delay_mins.
        """
        url = (
            f"{self.base_url}/stops/{ALEXANDERPLATZ_ID}/departures"
            f"?duration=60&subway=true&bus=false&tram=false"
            f"&ferry=false&express=false&regional=false"
        )

        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            data = response.json()
            departures = data.get("departures", [])

            # Track max delay per line
            delays = {}
            for dep in departures:
                line = dep.get("line", {}).get("name", "")
                delay_secs = dep.get("delay", 0) or 0
                delay_mins = delay_secs // 60

                if delay_mins >= min_delay_mins:
                    if line not in delays or delay_mins > delays[line]:
                        delays[line] = delay_mins

            return delays

        except Exception as e:
            print(f"Error fetching U-Bahn delays: {e}")
            return {}
