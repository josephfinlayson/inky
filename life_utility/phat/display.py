#!/usr/bin/env python3
"""Display rendering for Inky pHAT e-ink display."""

import glob
import os
import time
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont, ImageOps
from font_source_sans_pro import SourceSansProSemibold

from config import ICON_MAP, WARNING_TEMP
from utils import Box, draw_grid

PATH = os.path.dirname(__file__)


class WeatherDisplay:
    """Renders weather and transit data to Inky pHAT display."""

    def __init__(self, inky_display):
        self.inky = inky_display
        self.width = inky_display.resolution[0]
        self.height = inky_display.resolution[1]

        # Fonts
        self.font_large = ImageFont.truetype(SourceSansProSemibold, 40)
        self.font_small = ImageFont.truetype(SourceSansProSemibold, 24)

        # Canvas
        self.img = Image.new("RGB", (self.width, self.height), "white")
        self.draw = ImageDraw.Draw(self.img)

        # Grid layout (3 cols x 2 rows)
        self.grids = draw_grid(
            self.width, self.height, 3, 2, (0, 0), self.draw, self.inky
        )

        # Load weather icons
        self.icons = self._load_icons()

    def _load_icons(self) -> dict:
        """Load and invert weather icon images."""
        icons = {}
        for path in glob.glob(os.path.join(PATH, "resources/icon-*.jpg")):
            name = path.split("icon-")[1].replace(".jpg", "")
            img = Image.open(path)
            icons[name] = ImageOps.invert(img)
        return icons

    def _get_icon_for_condition(self, condition: str, size: tuple = (100, 100)) -> Image:
        """Map weather condition to icon image."""
        for icon_name, conditions in ICON_MAP.items():
            if condition in conditions:
                return self.icons[icon_name].resize(size)
        return self.icons.get("smiley", self.icons["sun"]).resize(size)

    def _center_offset(self, box: Box, img: Image) -> tuple:
        """Calculate offset to center image in box."""
        img_w, img_h = img.size
        x = box.center()[0] - img_w // 2
        y = box.center()[1] - img_h // 2
        return (x, y)

    def draw_date_time(self):
        """Draw current date and time in top-left grids."""
        now = datetime.now()
        day_of_week = now.strftime("%A")
        date_str = now.strftime("%d/%m")
        time_str = now.strftime("%H:%M")

        # Draw day and date as separate centered lines
        box = self.grids[0]
        center_x = box.center()[0]
        center_y = box.center()[1]
        line_spacing = 25

        self.draw.text(
            (center_x, center_y - line_spacing),
            day_of_week,
            self.inky.WHITE,
            font=self.font_large,
            anchor="mm",
        )
        self.draw.text(
            (center_x, center_y + line_spacing),
            date_str,
            self.inky.WHITE,
            font=self.font_large,
            anchor="mm",
        )

        # Draw time in upper portion of grids[1]
        time_box = self.grids[1]
        time_y = time_box.y1 + time_box.height() // 3
        self.draw.text(
            (time_box.center()[0], time_y),
            time_str,
            self.inky.WHITE,
            font=self.font_large,
            anchor="mm",
        )

    def draw_sunrise_sunset(self, weather: dict):
        """Draw sunrise and sunset times with icons under the clock."""
        box = self.grids[1]
        sunrise = weather.get("sunrise", "--:--")
        sunset = weather.get("sunset", "--:--")

        # Position in lower portion of the time box - stacked vertically
        center_x = box.center()[0]
        icon_size = 20
        row_height = 28
        start_y = box.y1 + int(box.height() * 0.55)

        # Sunrise row: sun icon + time
        sunrise_y = start_y
        sun_icon = self.icons.get("sun")
        if sun_icon:
            small_sun = sun_icon.resize((icon_size, icon_size))
            icon_x = center_x - 55
            self.img.paste(small_sun, (icon_x, sunrise_y - icon_size // 2))
        self.draw.text(
            (center_x - 25, sunrise_y),
            sunrise,
            self.inky.WHITE,
            font=self.font_small,
            anchor="lm",
        )

        # Sunset row: moon icon + time
        sunset_y = start_y + row_height
        moon_x = center_x - 55
        self._draw_moon(moon_x + icon_size // 2, sunset_y, icon_size // 2)
        self.draw.text(
            (center_x - 25, sunset_y),
            sunset,
            self.inky.WHITE,
            font=self.font_small,
            anchor="lm",
        )

    def _draw_moon(self, x: int, y: int, radius: int):
        """Draw a crescent moon icon (black on white e-ink background)."""
        # Draw filled black circle
        self.draw.ellipse(
            [x - radius, y - radius, x + radius, y + radius],
            fill=self.inky.BLACK,
        )
        # Cut out with white circle offset to create crescent
        offset = int(radius * 0.6)
        self.draw.ellipse(
            [x - radius + offset, y - radius, x + radius + offset, y + radius],
            fill=self.inky.WHITE,
        )

    def draw_temperature(self, weather: dict):
        """Draw current temperature with precipitation graph below."""
        box = self.grids[2]
        temp = weather["today"]["temperature"]
        color = self.inky.WHITE if temp < WARNING_TEMP else self.inky.BLUE

        # Draw temperature in upper portion
        temp_y = box.y1 + box.height() // 3
        self.draw.text(
            (box.center()[0], temp_y),
            f"{temp:.0f}°C",
            color,
            font=self.font_large,
            anchor="mm",
        )

        # Draw precipitation graph in lower portion
        precip_data = weather.get("precipitation", [])
        self._draw_precipitation_graph(box, precip_data)

    def _draw_precipitation_graph(self, box: Box, precip_data: list):
        """Draw a 24-hour precipitation probability bar graph with current time marker."""
        # Graph area: lower 40% of the box with padding
        padding = 8
        graph_height = 40
        graph_width = box.width() - (padding * 2)
        graph_x = box.x1 + padding
        graph_y = box.y2 - graph_height - padding

        # Draw baseline
        self.draw.line(
            [(graph_x, graph_y + graph_height), (graph_x + graph_width, graph_y + graph_height)],
            fill=self.inky.WHITE,
            width=1,
        )

        # Bar width for 24 hours (or 8 x 3-hour blocks from API)
        if not precip_data:
            return

        # OpenWeatherMap gives 3-hour blocks, typically 8 per day
        num_bars = len(precip_data)
        bar_width = max(1, graph_width // max(num_bars, 1))
        bar_gap = 2

        for i, data in enumerate(precip_data):
            pop = data["pop"]  # 0-1
            bar_height = int(pop * (graph_height - 5))

            if bar_height > 0:
                x = graph_x + i * (bar_width + bar_gap)
                y = graph_y + graph_height - bar_height

                self.draw.rectangle(
                    [x, y, x + bar_width, graph_y + graph_height],
                    fill=self.inky.BLUE,
                    outline=self.inky.WHITE,
                )

        # Draw vertical line for current time position
        now = datetime.now()
        current_hour = now.hour + now.minute / 60

        # Map current hour to graph position (assuming data spans today)
        if precip_data:
            first_hour = precip_data[0]["hour"]
            last_hour = precip_data[-1]["hour"] + 3  # 3-hour blocks
            hour_range = last_hour - first_hour

            if hour_range > 0 and first_hour <= current_hour <= last_hour:
                time_ratio = (current_hour - first_hour) / hour_range
                marker_x = graph_x + int(time_ratio * graph_width)

                # Draw vertical marker line
                self.draw.line(
                    [(marker_x, graph_y), (marker_x, graph_y + graph_height)],
                    fill=self.inky.RED,
                    width=2,
                )

    def draw_weather_icons(self, weather: dict):
        """Draw weather icons for today, tomorrow, and next day."""
        # Today's icon (larger)
        today_icon = self._get_icon_for_condition(
            weather["today"]["summary"], (100, 100)
        )

        # Build sub-grid for weather icon area
        icon_box = self.grids[3]
        icon_grids = draw_grid(
            icon_box.width(), icon_box.height(), 1, 2,
            (icon_box.x1, icon_box.y1), self.draw, self.inky
        )

        self.img.paste(today_icon, self._center_offset(icon_grids[0], today_icon))

        # Tomorrow and next day (smaller, side by side)
        tomorrow_icon = self._get_icon_for_condition(
            weather["tomorrow"]["summary"], (50, 50)
        )
        next_icon = self._get_icon_for_condition(
            weather["next_day"]["summary"], (50, 50)
        )

        forecast_box = icon_grids[1]
        forecast_grids = draw_grid(
            forecast_box.width(), forecast_box.height(), 2, 1,
            (forecast_box.x1, forecast_box.y1), self.draw, self.inky
        )

        self.img.paste(tomorrow_icon, self._center_offset(forecast_grids[0], tomorrow_icon))
        self.img.paste(next_icon, self._center_offset(forecast_grids[1], next_icon))

    def draw_u6_departures(self, departures: list):
        """Draw U6 departure times in bottom-left grid."""
        box = self.grids[4]
        width = box.width()

        # Header
        self.draw.text(
            (box.x1 + width // 2, box.y1 + 10),
            "U6 Nord",
            self.inky.BLUE,
            font=self.font_small,
            anchor="mt",
        )

        # Departure times
        if departures:
            y_start = box.y1 + 50
            y_spacing = 45

            for i, secs in enumerate(departures[:4]):
                y = y_start + i * y_spacing
                mins = secs // 60
                remaining_secs = secs % 60

                if secs < 60:
                    text = "jetzt"
                elif mins < 60:
                    text = f"{mins}:{remaining_secs:02d}"
                else:
                    hours = mins // 60
                    remaining_mins = mins % 60
                    if remaining_mins == 0:
                        text = f"{hours}h"
                    else:
                        text = f"{hours}h {remaining_mins}m"

                self.draw.text(
                    (box.x1 + width // 2, y),
                    text,
                    self.inky.WHITE,
                    font=self.font_large,
                    anchor="mt",
                )
        else:
            self.draw.text(
                box.center(),
                "No data",
                self.inky.WHITE,
                font=self.font_small,
                anchor="mm",
            )

    def draw_min_max(self, weather: dict):
        """Draw min/max temperatures for tomorrow and next day."""
        last_box = self.grids[5]
        min_max_grids = draw_grid(
            last_box.width(), last_box.height(), 2, 2,
            (last_box.x1, last_box.y1), self.draw, self.inky
        )

        # Tomorrow
        self.draw.text(
            min_max_grids[0].center(), "tom:",
            self.inky.WHITE, font=self.font_large, anchor="mm"
        )
        tom_grid = draw_grid(
            min_max_grids[0].width(), min_max_grids[0].height(), 1, 2,
            (min_max_grids[2].x1, min_max_grids[2].y1), self.draw, self.inky
        )
        self.draw.text(
            tom_grid[0].center(), weather["tomorrow"]["max"],
            self.inky.WHITE, font=self.font_large, anchor="mm"
        )
        self.draw.text(
            tom_grid[1].center(), weather["tomorrow"]["min"],
            self.inky.WHITE, font=self.font_large, anchor="mm"
        )

        # Next day
        self.draw.text(
            min_max_grids[1].center(), "next:",
            self.inky.WHITE, font=self.font_large, anchor="mm"
        )
        next_grid = draw_grid(
            min_max_grids[3].width(), min_max_grids[3].height(), 1, 2,
            (min_max_grids[3].x1, min_max_grids[3].y1), self.draw, self.inky
        )
        self.draw.text(
            next_grid[0].center(), weather["next_day"]["max"],
            self.inky.WHITE, font=self.font_large, anchor="mm"
        )
        self.draw.text(
            next_grid[1].center(), weather["next_day"]["min"],
            self.inky.WHITE, font=self.font_large, anchor="mm"
        )

    def render(self, weather: dict, departures: list):
        """Render all components to the display."""
        self.draw_date_time()
        self.draw_sunrise_sunset(weather)
        self.draw_temperature(weather)
        self.draw_weather_icons(weather)
        self.draw_u6_departures(departures)
        self.draw_min_max(weather)

    def show(self):
        """Push image to the e-ink display."""
        self.inky.set_image(self.img, saturation=0.5)
        self.inky.show()
