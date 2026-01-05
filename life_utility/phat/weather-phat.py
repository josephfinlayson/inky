#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import glob
import os
import random
import time
from utils import draw_grid
from datetime import datetime, timedelta, timezone
from typing import List, Tuple

import geocoder
import pytz
import requests
from font_source_sans_pro import SourceSansProSemibold
from inky.auto import auto
from PIL import Image, ImageDraw, ImageFont, ImageOps

from Box import Box

# Get the current path
PATH = os.path.dirname(__file__)

# Set up the display
inky_display = auto(ask_user=True, verbose=True)

inky_display.set_border(inky_display.BLACK)


INKY_HEIGHT = inky_display.resolution[1]
INKY_WIDTH = inky_display.resolution[0]
# Details to customise your weather display

CITY = "Berlin"
COUNTRYCODE = "DE"
WARNING_TEMP = 25.0
# Placeholder variables
temperature = 0
today_weather_name = None
tomorrow_weather_name = None
next_weather_name = None

# Convert a city name and country code to latitude and longitude
def get_coords(address):
    g = geocoder.arcgis(address)
    coords = g.latlng
    return coords


def get_min_max(el):
    return {
        "max": el.findAll('span', "maxTemp")[0].text,
        "min": el.findAll('span', "minTemp")[0].text
    }
# Query Dark Sky (https://darksky.net/) to scrape current weather data


def get_weather(address):
    coords = get_coords(address)
    weather = {"today": {}, "tomorrow": {
        "summary": "",
        "max": "",
        "min": ""
    }, "next_day": {
        "summary": "",
        "max": "",
        "min": ""
    }}
    api_key = "dd4e4011d95b7f9a60842291284c6569"
    today_url = f"https://api.openweathermap.org/data/2.5/weather?lat={coords[0]}&lon={coords[1]}&appid={api_key}&units=metric" 
    response = requests.get(today_url).json()
    weather["today"]["summary"] = response["weather"][0]["main"].lower()
    weather["today"]["temperature"] = response["main"]["temp"]

    forecast_url = f"https://api.openweathermap.org/data/2.5/forecast?lat={coords[0]}&lon={coords[1]}&appid={api_key}&units=metric"

    response = requests.get(forecast_url).json()
    # group by day
    days = {}
    for item in response["list"]:
        day = datetime.fromtimestamp(item["dt"]).strftime("%Y-%m-%d")
        if day not in days:
            days[day] = []
        days[day].append(item)
    
    # get min and max for each day
    for day in days:
        temps = [item["main"]["temp"] for item in days[day]]
        weather[day] = {
            "summary": days[day][0]["weather"][0]["main"].lower(),
            "max": str(round(max(temps))),
            "min": str(round(min(temps)))
        }
    # get tomorrow from days
    tomorrow = datetime.now() + timedelta(days=1)
    tomorrow = tomorrow.strftime("%Y-%m-%d")
    weather["tomorrow"] = weather[tomorrow]

    # get next day from days
    next_day = datetime.now() + timedelta(days=2)
    next_day = next_day.strftime("%Y-%m-%d")
    weather["next_day"] = weather[next_day]
    print(weather["next_day"])

    return weather


def create_mask(source, mask=(inky_display.WHITE,
                              inky_display.BLACK,
                              inky_display.RED,
                              inky_display.BLUE,
                              inky_display.YELLOW,
                              inky_display.GREEN,
                              inky_display.ORANGE,
                              )):
    """Create a transparency mask.

    Takes a paletized source image and converts it into a mask
    permitting all the colours supported by Inky pHAT (0, 1, 2)
    or an optional list of allowed colours.

    :param mask: Optional list of Inky pHAT colours to allow.

    """
    mask_image = Image.new("1", source.size)
    w, h = source.size
    for x in range(w):
        for y in range(h):
            p = source.getpixel((x, y))
            if p in mask:
                mask_image.putpixel((x, y), 255)

    return mask_image


# Dictionaries to store our icons and icon masks in
icons = {}
masks = {}

# Get the weather data for the given location
location_string = "{city}, {countrycode}".format(
    city=CITY, countrycode=COUNTRYCODE)
weather = get_weather(location_string)

# to the appropriate weather icons
icon_map = {
    "snow": ["snow", "sleet"],
    "rain": ["rain", "drizzle"],
    "cloud": ["fog", "cloudy", "partly-cloudy-day", "partly-cloudy-night", "clouds"],
    "sun": ["clear-day", "clear-night", "clear"],
    "storm": [],
    "wind": ["wind"]
}

if weather:
    temperature = weather["today"]["temperature"]
    summary = weather["today"]["summary"]
    tomorrow_summary = weather["tomorrow"]["summary"]
    next_summary = weather["next_day"]["summary"]
    for icon in icon_map:
        if summary in icon_map[icon]:
            today_weather_name = icon
        if tomorrow_summary in icon_map[icon]:
            tomorrow_weather_name = icon
        if next_summary in icon_map[icon]:
            next_weather_name = icon

else:
    print("Warning, no weather information found!")

# Create a new canvas to draw on
img = Image.new("RGB", inky_display.resolution,
                'white').resize(inky_display.resolution)
draw = ImageDraw.Draw(img)

# Load our icon files and generate masks
for icon in glob.glob(os.path.join(PATH, "resources/icon-*.jpg")):
    icon_name = icon.split("icon-")[1].replace(".jpg", "")
    icon_image = Image.open(icon)
    # invert image color
    icon_image = ImageOps.invert(icon_image)
    icons[icon_name] = icon_image
    masks[icon_name] = create_mask(icon_image)


def get_kandinsky():
    # pick random image in file
    kandinskys = glob.glob(os.path.join(PATH, "resources/kandinsky/*"))
    # get random from array
    kandinsky = random.choice(kandinskys)
    image = Image.open(kandinsky, ).resize((200, 224))
    return {"mask": create_mask(image),
            "image": image}


def get_u6_departures():
    """Fetch northbound U6 departures from Kaiserin-Augusta-Str."""
    station_id = "900068302"
    url = f"https://v6.bvg.transport.rest/stops/{station_id}/departures?duration=30&subway=true&bus=false&tram=false&ferry=false&express=false&regional=false"

    try:
        response = requests.get(url, timeout=10).json()
        departures = response.get("departures", [])

        # Filter for northbound only (Kurt-Schumacher-Platz direction = toward Alt-Tegel)
        northbound = [d for d in departures if "Kurt-Schumacher" in d.get("direction", "") or "Alt-Tegel" in d.get("direction", "")]

        # Get next 4 departures
        results = []
        for dep in northbound[:4]:
            when = dep.get("when") or dep.get("plannedWhen")
            if when:
                # Parse ISO time and convert to minutes from now
                dep_time = datetime.fromisoformat(when.replace("Z", "+00:00"))
                now = datetime.now(dep_time.tzinfo)
                mins = int((dep_time - now).total_seconds() / 60)
                if mins >= 0:
                    results.append(mins)

        return results[:4]
    except Exception as e:
        print(f"Error fetching U6 departures: {e}")
        return []


def draw_u6_departures(draw, box, inky_display, font_large, font_small):
    """Draw U6 departure times in the given box."""
    departures = get_u6_departures()

    # Create image for the departure display
    width = box.width()
    height = box.height()

    # Header
    header_y = 10
    draw.text((box.x1 + width // 2, box.y1 + header_y), "U6 Nord", inky_display.BLUE, font=font_small, anchor="mt")

    # Departure times
    if departures:
        y_start = box.y1 + 50
        y_spacing = 45

        for i, mins in enumerate(departures[:4]):
            y = y_start + (i * y_spacing)
            if mins == 0:
                time_text = "jetzt"
            elif mins == 1:
                time_text = "1 min"
            else:
                time_text = f"{mins} min"

            draw.text((box.x1 + width // 2, y), time_text, inky_display.WHITE, font=font_large, anchor="mt")
    else:
        draw.text((box.x1 + width // 2, box.y1 + height // 2), "No data", inky_display.WHITE, font=font_small, anchor="mm")


font = ImageFont.truetype(SourceSansProSemibold, 40)

main_grids: List[Box] = draw_grid(INKY_WIDTH, INKY_HEIGHT, 3, 2, (0,0), draw, inky_display)
last_main_grid_box = main_grids[5]
min_max_grids = draw_grid(last_main_grid_box.width(), last_main_grid_box.height(), 2, 2, (last_main_grid_box.x1, last_main_grid_box.y1), draw, inky_display)

# Main grids
# Write text with weather values to the canvas
today_date = time.strftime("%d/%m")
# convert to CEST tz
today_date = datetime.strptime(today_date, "%d/%m").replace(
    tzinfo=timezone(pytz.timezone('UTC').utcoffset(datetime.now()))).astimezone(timezone(pytz.timezone('Europe/Berlin').utcoffset(datetime.now()))).strftime("%d/%m")


now = time.strftime("%H:%M")
# get day of week
day_of_week = time.strftime("%A")

draw.text(main_grids[0].center(), f"""
    {day_of_week}
          {today_date}
""", inky_display.WHITE, font=font, anchor="mm")

draw.text(main_grids[1].center(), now, inky_display.WHITE, font=font, anchor="mm")


def get_weather_icon(weather_name, resize=(100, 100)):
    print(weather_name)
    if weather_name is None:
        raise Exception("Weather name is None")
    return icons[weather_name].resize(resize)

def get_offset_for_weather_icon(box, icon):
    if icon:
        img_w, img_h = icon.size

        x = int(box.center()[0] - img_w / 2)
        y = int(box.center()[1] - img_h / 2)
        offset = (x, y)
        return offset
    return (0, 0)

# # Temperature
draw.text(main_grids[2].center(), u"{}°C".format(temperature), inky_display.WHITE if temperature <
          WARNING_TEMP else inky_display.BLUE, font=font, anchor="mm",)

# Draw the current weather icon over the backdrop
try:
    today_icon_image = get_weather_icon(today_weather_name)
except Exception:
    print(f"Missing weather icon for today's Icon:  {today_weather_name}, {weather}")
    today_icon_image = get_weather_icon("smiley")
    # write the name of the missing weather

try:
    tomorrow_icon_image = get_weather_icon(tomorrow_weather_name, resize=(50, 50))
except Exception:
    tomorrow_icon_image = get_weather_icon("smiley")
    print(f"Missing weather icon for tommorrows:  {tomorrow_weather_name}, {weather}")

try:
    next_icon_image = get_weather_icon(next_weather_name, resize=(50, 50))
except Exception:
    print(f"Missing weather icon for next weather Icon:  { next_weather_name} {weather}")
    next_icon_image = get_weather_icon("smiley")

# This is the grid of the weather icon
weather_icon_grid = main_grids[3]

# Draw a grid inside the weather icon grid
weather_icon_vertical_grid = draw_grid(weather_icon_grid.width(), weather_icon_grid.height(), 1, 2, (weather_icon_grid.x1, weather_icon_grid.y1), draw, inky_display)    

# This is the top box in the weather icon grid
todays_weather_box = weather_icon_vertical_grid[0]
# This is the top left corner of the weather icon grid
today_offset = get_offset_for_weather_icon(todays_weather_box, today_icon_image)

# This is the bottom box in the weather icon grid
tomorrow_weather_box = weather_icon_vertical_grid[1]
# Draw a grid inside the bottom box
tomorrow_weather_box_grid = draw_grid(tomorrow_weather_box.width(), tomorrow_weather_box.height() * 2, 2, 1, (tomorrow_weather_box.x1, tomorrow_weather_box.y1), draw, inky_display)

# This is the top left corner of the top box in the bottom box
tomorrow_offset = get_offset_for_weather_icon(tomorrow_weather_box_grid[0], tomorrow_icon_image)
# This is the top left corner of the bottom box in the bottom box
next_offset = get_offset_for_weather_icon(tomorrow_weather_box_grid[1], next_icon_image)

try: 
    # Paste the weather icons onto the image
    img.paste(today_icon_image, today_offset)
    img.paste(tomorrow_icon_image, tomorrow_offset)
    img.paste(next_icon_image, next_offset)
except:
    print('weather icon not found')

# Draw min-max temperature in box

# Draw U6 departure times instead of kandinsky art
font_small = ImageFont.truetype(SourceSansProSemibold, 24)
draw_u6_departures(draw, main_grids[4], inky_display, font, font_small)

# minmax grid

def draw_min_max_grid():
    max_temp = weather["tomorrow"]["max"]
    # max_temp = weather["temperature"]["min"]
    draw.text(min_max_grids[0].center(), u"tom:", inky_display.WHITE, font=font, anchor="mm")

    tom_grid = draw_grid(min_max_grids[0].width(), min_max_grids[0].height(), 1, 2, (min_max_grids[2].x1, min_max_grids[2].y1), draw, inky_display)
    draw.text(tom_grid[1].center(), weather["tomorrow"]["min"], inky_display.WHITE, font=font, anchor="mm")
    draw.text(tom_grid[0].center(), weather["tomorrow"]["max"], inky_display.WHITE, font=font, anchor="mm")

    draw.text(min_max_grids[1].center(), u"next:", inky_display.WHITE, font=font, anchor="mm")
    next_grid = draw_grid(min_max_grids[3].width(), min_max_grids[3].height(), 1, 2, (min_max_grids[3].x1, min_max_grids[3].y1), draw, inky_display)

    draw.text(next_grid[1].center(), weather["next_day"]["min"], inky_display.WHITE, font=font, anchor="mm")
    draw.text(next_grid[0].center(), weather["next_day"]["max"], inky_display.WHITE, font=font, anchor="mm")

draw_min_max_grid()
# Display the weather data on Inky pHAT
inky_display.set_image(img, saturation=0.5)
inky_display.show()
