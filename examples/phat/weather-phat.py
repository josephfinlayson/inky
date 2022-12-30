#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import glob
import os
import random
import time
from utils import draw_grid
from datetime import datetime, timezone
from typing import List, Tuple

import geocoder
import pytz
import requests
from bs4 import BeautifulSoup
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
    weather = {}
    res = requests.get(
        "https://darksky.net/forecast/{}/uk212/en".format(",".join([str(c) for c in coords])))


    # https://darksky.net/forecast/52.516,13.3769/uk212/en
    if res.status_code == 200:
        soup = BeautifulSoup(res.content, "lxml")
        curr = soup.find_all("span", "currently")
        tomorrow = soup.find_all("a", attrs={"data-day":"1"})
        next_day = soup.find_all("a", attrs={"data-day":"2"})
        tomorrow_min_max = get_min_max(tomorrow[0])
        next_day_min_max = get_min_max(next_day[0])
        weather["tomorrow"] = tomorrow_min_max
        weather["tomorrow"]["summary"] = tomorrow[0].img["alt"].split()[0]
        weather["next_day"] = next_day_min_max
        weather["next_day"]["summary"] = next_day[0].img["alt"].split()[0]
        weather["summary"] = curr[0].img["alt"].split()[0]
        weather["temperature"] = int(curr[0].find(
            "span", "summary").text.split()[0][:-1])
        return weather
    else:
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

# This maps the weather summary from Dark Sky
# to the appropriate weather icons
icon_map = {
    "snow": ["snow", "sleet"],
    "rain": ["rain"],
    "cloud": ["fog", "cloudy", "partly-cloudy-day", "partly-cloudy-night"],
    "sun": ["clear-day", "clear-night"],
    "storm": [],
    "wind": ["wind"]
}

# Placeholder variables
temperature = 0
today_weather_name = None
tomorrow_weather_name = None
next_weather_name = None

if weather:
    temperature = weather["temperature"]
    summary = weather["summary"]
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
for icon in glob.glob(os.path.join(PATH, "resources/icon-*.png")):
    icon_name = icon.split("icon-")[1].replace(".png", "")
    icon_image = Image.open(icon).convert("RGBA")
    # convert transparent pixels to white
    new_image = Image.new("RGBA", icon_image.size, "WHITE") # Create a white rgba background
    new_image.paste(icon_image, (0, 0), icon_image)              # Paste the image on the background. Go to the links given below for details.
    new_image.convert('RGB').save(icon + 'test.jpg', "JPEG")  # Save as JPEG
    # invert image color
    # icon_image = ImageOps.invert(icon_image)
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

draw.text(main_grids[0].center(), f"""{day_of_week}
{today_date}""", inky_display.WHITE, font=font, anchor="mm")

draw.text(main_grids[1].center(), now, inky_display.WHITE, font=font, anchor="mm")


def get_weather_icon(weather_name, resize=(100, 100)):
    if weather_name is None:
        return None
    return icons[weather_name].resize(resize)

def get_offset_for_weather_icon(box, icon):
    img_w, img_h = icon.size

    x = int(box.center()[0] - img_w / 2)
    y = int(box.center()[1] - img_h / 2)
    offset = (x, y)
    return offset


# # Temperature
draw.text(main_grids[2].center(), u"{}°C".format(temperature), inky_display.WHITE if temperature <
          WARNING_TEMP else inky_display.BLUE, font=font, anchor="mm",)


# # Draw the current weather icon over the backdrop
if today_weather_name is not None:
    print('today_weather_name: ', today_weather_name)
    today_icon_image = get_weather_icon(today_weather_name)
    tomorrow_icon_image = get_weather_icon(tomorrow_weather_name, resize=(50, 50))
    next_icon_image = get_weather_icon(next_weather_name, resize=(50, 50))

    weather_icon_grid = main_grids[3]
    weather_icon_vertical_grid = draw_grid(weather_icon_grid.width(), weather_icon_grid.height(), 1, 2, (weather_icon_grid.x1, weather_icon_grid.y1), draw, inky_display)    

    todays_weather_box = weather_icon_vertical_grid[0]
    today_offset = get_offset_for_weather_icon(todays_weather_box, today_icon_image)
    
    # tomorrow and next weather grid
    tomorrow_weather_box = weather_icon_vertical_grid[1]
    tomorrow_weather_box_grid = draw_grid(tomorrow_weather_box.width(), tomorrow_weather_box.height() * 2, 2, 1, (tomorrow_weather_box.x1, tomorrow_weather_box.y1), draw, inky_display)
    
    tomorrow_offset = get_offset_for_weather_icon(tomorrow_weather_box_grid[0], tomorrow_icon_image)
    next_offset = get_offset_for_weather_icon(tomorrow_weather_box_grid[1], next_icon_image)

    img.paste(today_icon_image, today_offset)
    img.paste(tomorrow_icon_image, tomorrow_offset)
    img.paste(next_icon_image, next_offset)

else:
    draw.text((28, 36), "?", inky_display.RED, font=font)


def draw_text(location: tuple, text_content: str, color):
    draw.text(location, text_content, color or inky_display.RED, font=font)




# Draw min-max temperature in box

kandinsky = get_kandinsky()
img.paste(kandinsky["image"], (main_grids[4].x1, main_grids[4].y1))

# minmax grid
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


# Display the weather data on Inky pHAT
inky_display.set_image(img)
inky_display.show()
