#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import glob
import os
import random
import time
from datetime import datetime, timedelta, timezone
from typing import List, Tuple
import requests
import geocoder
import pytz
from PIL import Image, ImageDraw, ImageFont, ImageOps
from font_source_sans_pro import SourceSansProSemibold
from inky.auto import auto
from Box import Box
from utils import draw_grid

class WeatherData:
    def __init__(self, city, countrycode):
        self.city = city
        self.countrycode = countrycode
        self.api_key = "dd4e4011d95b7f9a60842291284c6569"
        self.address = f"{city}, {countrycode}"
        self.coords = self.get_coords()
        self.weather = self.get_weather()

    # Convert a city name and country code to latitude and longitude
    def get_coords(self):
        g = geocoder.arcgis(self.address)
        coords = g.latlng
        return coords

    # Query OpenWeatherMap to get current weather data
    def get_weather(self):
        weather = {"today": {}, "tomorrow": {}, "next_day": {}}
        today_url = f"https://api.openweathermap.org/data/2.5/weather?lat={self.coords[0]}&lon={self.coords[1]}&appid={self.api_key}&units=metric" 
        response = requests.get(today_url).json()
        weather["today"]["summary"] = response["weather"][0]["main"].lower()
        weather["today"]["temperature"] = response["main"]["temp"]
        forecast_url = f"https://api.openweathermap.org/data/2.5/forecast?lat={self.coords[0]}&lon={self.coords[1]}&appid={self.api_key}&units=metric"
        response = requests.get(forecast_url).json()
        days = self.group_by_day(response["list"])
        weather = self.get_min_max_for_each_day(days, weather)
        return weather

    def group_by_day(self, forecast_list):
        days = {}
        for item in forecast_list:
            day = datetime.fromtimestamp(item["dt"]).strftime("%Y-%m-%d")
            if day not in days:
                days[day] = []
            days[day].append(item)
        return days

    def get_min_max_for_each_day(self, days, weather):
        for day in days:
            temps = [item["main"]["temp"] for item in days[day]]
            weather[day] = {
                "summary": days[day][0]["weather"][0]["main"].lower(),
                "max": str(round(max(temps))),
                "min": str(round(min(temps)))
            }

        # set todays weather
        today = datetime.now().strftime("%Y-%m-%d")
        weather["today"] = weather[today]
        weather["today"]["temperature"] = weather["today"]["max"]
        
        # get tomorrow from days
        tomorrow = datetime.now() + timedelta(days=1)
        tomorrow = tomorrow.strftime("%Y-%m-%d")
        weather["tomorrow"] = weather[tomorrow]

        # get next day from days
        next_day = datetime.now() + timedelta(days=2)
        next_day = next_day.strftime("%Y-%m-%d")
        weather["next_day"] = weather[next_day]
        return weather


class Display:
    def __init__(self, weather_data, inky_display):
        self.weather_data = weather_data
        self.inky_display = inky_display
        self.INKY_HEIGHT = inky_display.resolution[1]
        self.INKY_WIDTH = inky_display.resolution[0]
        self.font = ImageFont.truetype(SourceSansProSemibold, 40)
        self.img = Image.new("RGB", inky_display.resolution,
                'white').resize(inky_display.resolution)
        self.draw = ImageDraw.Draw(self.img)
        self.main_grids = draw_grid(self.INKY_WIDTH, self.INKY_HEIGHT, 3, 2, (0,0), self.draw, self.inky_display)
        self.last_main_grid_box = self.main_grids[5]
        self.min_max_grids = draw_grid(self.last_main_grid_box.width(), self.last_main_grid_box.height(), 2, 2, (self.last_main_grid_box.x1, self.last_main_grid_box.y1), self.draw, self.inky_display)
        self.icon_map = {
            "snow": ["snow", "sleet"],
            "rain": ["rain"],
            "cloud": ["fog", "cloudy", "partly-cloudy-day", "partly-cloudy-night", "clouds"],
            "sun": ["clear-day", "clear-night", "clear"],
            "storm": [],
            "wind": ["wind"]
        }
        self.icons = self.load_icons()
        self.kandinsky = self.get_kandinsky()

    def load_icons(self):
        PATH = os.path.dirname(__file__)
        icons = {}
        for icon in glob.glob(os.path.join(PATH, "resources/icon-*.jpg")):
            icon_name = icon.split("icon-")[1].replace(".jpg", "")
            icon_image = Image.open(icon)
            icon_image = ImageOps.invert(icon_image)
            icons[icon_name] = icon_image
        return icons

    def get_kandinsky(self):
        PATH = os.path.dirname(__file__)
        kandinskys = glob.glob(os.path.join(PATH, "resources/kandinsky/*"))
        kandinsky = random.choice(kandinskys)
        image = Image.open(kandinsky, ).resize((200, 224))
        return image

    def get_weather_icon(self, weather_condition, resize=(100, 100)):
        if weather_condition is None:
            raise Exception("Weather condition is None")

        # Find the icon name that corresponds to the weather condition
        for icon_name, conditions in self.icon_map.items():
            if weather_condition in conditions:
                weather_name = icon_name
                break
        else:
            raise Exception(f"No icon found for weather condition '{weather_condition}'")

        return self.icons[weather_name].resize(resize)

    def draw_weather(self):
        # Draw date and time
        today_date = datetime.now().strftime("%d/%m")
        now = time.strftime("%H:%M")
        day_of_week = time.strftime("%A")
        self.draw.text(self.main_grids[0].center(), f"{day_of_week}\n{today_date}", self.inky_display.WHITE, font=self.font, anchor="mm")
        self.draw.text(self.main_grids[1].center(), now, self.inky_display.WHITE, font=self.font, anchor="mm")

        # Draw temperature
        # temperature = self.weather_data["today"]["temperature"]
        # self.draw.text(self.main_grids[2].center(), u"{}°C".format(temperature), self.inky_display.WHITE if temperature < 25.0 else self.inky_display.BLUE, font=self.font, anchor="mm",)

    # Split the main_grids[2] into three sections
        temp_grid = draw_grid(self.main_grids[2].width(), self.main_grids[2].height(), 1, 3, (self.main_grids[2].x1, self.main_grids[2].y1), self.draw, self.inky_display)

        # Draw current temperature in the middle grid
        current_temp = self.weather_data["today"]["temperature"]
        self.draw.text(temp_grid[1].center(), u"{}°C".format(current_temp), self.inky_display.WHITE, font=self.font, anchor="mm")

        # Draw high temperature with up arrow icon
        high_temp = self.weather_data["today"]["max"]
        # high_temp_icon = self.get_weather_icon("up_arrow")
        self.draw.text(temp_grid[0].center(), u"{}°C".format(high_temp), self.inky_display.WHITE, font=self.font, anchor="mm")
        # self.img.paste(high_temp_icon, self.get_offset_for_weather_icon(temp_grid[0], high_temp_icon))





        # Draw weather icons
        today_icon_image = self.get_weather_icon(self.weather_data["today"]["summary"])
        tomorrow_icon_image = self.get_weather_icon(self.weather_data["tomorrow"]["summary"], resize=(50, 50))
        next_icon_image = self.get_weather_icon(self.weather_data["next_day"]["summary"], resize=(50, 50))

        self.img.paste(today_icon_image, self.get_offset_for_weather_icon(self.main_grids[3], today_icon_image))
        self.img.paste(tomorrow_icon_image, self.get_offset_for_weather_icon(self.main_grids[4], tomorrow_icon_image))
        self.img.paste(next_icon_image, self.get_offset_for_weather_icon(self.main_grids[5], next_icon_image))

        # Draw min-max temperature
        self.draw_min_max_grid()

        # Draw kandinsky
        self.img.paste(self.kandinsky, (self.main_grids[4].x1, self.main_grids[4].y1))

    def get_offset_for_weather_icon(self, box, icon):
        img_w, img_h = icon.size
        x = int(box.center()[0] - img_w / 2)
        y = int(box.center()[1] - img_h / 2)
        offset = (x, y)
        return offset

    def draw_min_max_grid(self):
        self.draw.text(self.min_max_grids[0].center(), u"tom:", self.inky_display.WHITE, font=self.font, anchor="mm")
        self.draw.text(self.min_max_grids[1].center(), u"next:", self.inky_display.WHITE, font=self.font, anchor="mm")

        tom_grid = draw_grid(self.min_max_grids[0].width(), self.min_max_grids[0].height(), 1, 2, (self.min_max_grids[2].x1, self.min_max_grids[2].y1), self.draw, self.inky_display)
        self.draw.text(tom_grid[1].center(), self.weather_data["tomorrow"]["min"], self.inky_display.WHITE, font=self.font, anchor="mm")
        self.draw.text(tom_grid[0].center(), self.weather_data["tomorrow"]["max"], self.inky_display.WHITE, font=self.font, anchor="mm")

        next_grid = draw_grid(self.min_max_grids[3].width(), self.min_max_grids[3].height(), 1, 2, (self.min_max_grids[3].x1, self.min_max_grids[3].y1), self.draw, self.inky_display)
        self.draw.text(next_grid[1].center(), self.weather_data["next_day"]["min"], self.inky_display.WHITE, font=self.font, anchor="mm")
        self.draw.text(next_grid[0].center(), self.weather_data["next_day"]["max"], self.inky_display.WHITE, font=self.font, anchor="mm")

    def show(self):
        self.inky_display.set_image(self.img, saturation=0.5)
        self.inky_display.show()


def main():
    # Set up the display
    inky_display = auto(ask_user=True, verbose=True)
    inky_display.set_border(inky_display.BLACK)

    # Get the weather data for the given location
    weather_data = WeatherData("Berlin", "DE").weather

    # Display the weather data on Inky pHAT
    display = Display(weather_data, inky_display)
    display.draw_weather()
    display.show()

if __name__ == "__main__":
    main()
