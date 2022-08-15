#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime, timedelta, timezone
import glob
import os
import random
import time
from resource import prlimit
from sys import exit
from typing import List, Tuple
import pytz
import geocoder
import requests
from bs4 import BeautifulSoup
from font_fredoka_one import FredokaOne
from font_source_sans_pro import SourceSansProSemibold
from inky.auto import auto
from PIL import Image, ImageDraw, ImageFont
from grid import Box

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
        weather["next_day"] = next_day_min_max
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
weather_icon = None

if weather:
    temperature = weather["temperature"]
    summary = weather["summary"]

    for icon in icon_map:
        if summary in icon_map[icon]:
            weather_icon = icon
            break

else:
    print("Warning, no weather information found!")


print(inky_display.resolution)
# Create a new canvas to draw on
img = Image.new("RGB", inky_display.resolution,
                'white').resize(inky_display.resolution)
draw = ImageDraw.Draw(img)

# Load our icon files and generate masks
for icon in glob.glob(os.path.join(PATH, "resources/icon-*.png")):
    icon_name = icon.split("icon-")[1].replace(".png", "")
    icon_image = Image.open(icon)
    icons[icon_name] = icon_image
    masks[icon_name] = create_mask(icon_image)


def get_kandinsky():
    # pick random image in file
    kandinskys = glob.glob(os.path.join(PATH, "resources/kandinsky/*"))
    # get random from array
    kandinsky = random.choice(kandinskys)
    image = Image.open(kandinsky, ).resize((200, 224))
    print(image)
    return {"mask": create_mask(image),
            "image": image}


font = ImageFont.truetype(SourceSansProSemibold, 40)

def draw_grid(width, height, number_of_grids_vertically, number_of_grids_horizontally, coordinates: Tuple[int, int]):
    grids = []
    starting_x, starting_y = coordinates
    for x in range(starting_x, width + starting_x, int(width/number_of_grids_vertically)):
        # iterate over height divided by 2
        for y in range(starting_y, height + starting_y, int(height/number_of_grids_horizontally) ):

            # draw lines around the grid
            draw.line((x, y, x + int(width/number_of_grids_vertically), y), 1)
            # calculate the bounding box of the grid
            bbox = (x, y, x + int(width/number_of_grids_vertically), y + int(height/2))
            # draw the border only of a rectangle
            draw.rectangle(bbox, fill=None, outline=inky_display.WHITE)
            # spread tuple into Box
            grids.append(Box(*bbox))
    
    return grids

main_grids: List[Box] = draw_grid(INKY_WIDTH, INKY_HEIGHT, 3, 2, (0,0))
last_main_grid_box = main_grids[5]
min_max_grids = draw_grid(last_main_grid_box.width(), last_main_grid_box.height(), 2, 2, (last_main_grid_box.x1, last_main_grid_box.y1))

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

# # Temperature
draw.text(main_grids[2].center(), u"{}°C".format(temperature), inky_display.WHITE if temperature <
          WARNING_TEMP else inky_display.BLUE, font=font, anchor="mm",)


# # Draw the current weather icon over the backdrop
if weather_icon is not None:
    print(icons[weather_icon], masks[weather_icon])
    icon_image = icons[weather_icon].resize((100, 100))
    img_w, img_h = icon_image.size

    # center the icon in grid[3]
    x = int(main_grids[3].center()[0] - img_w / 2)
    y = int(main_grids[3].center()[1] - img_h / 2)

    offset = (x, y)

    img.paste(icon_image, offset)

else:
    draw.text((28, 36), "?", inky_display.RED, font=font)



# Draw min-max temperature in box

kandinsky = get_kandinsky()
img.paste(kandinsky["image"], (main_grids[4].x1, main_grids[4].y1))

# minmax grid
print(weather)
max_temp = weather["tomorrow"]["max"]
# max_temp = weather["temperature"]["min"]
print(min_max_grids)
draw.text(min_max_grids[0].center(), u"tom:", inky_display.WHITE, font=font, anchor="mm")

tom_grid = draw_grid(min_max_grids[0].width(), min_max_grids[0].height(), 1, 2, (min_max_grids[2].x1, min_max_grids[2].y1))
draw.text(tom_grid[1].center(), weather["tomorrow"]["min"], inky_display.WHITE, font=font, anchor="mm")
draw.text(tom_grid[0].center(), weather["tomorrow"]["max"], inky_display.WHITE, font=font, anchor="mm")

draw.text(min_max_grids[1].center(), u"next:", inky_display.WHITE, font=font, anchor="mm")
next_grid = draw_grid(min_max_grids[3].width(), min_max_grids[3].height(), 1, 2, (min_max_grids[3].x1, min_max_grids[3].y1))

draw.text(next_grid[1].center(), weather["next_day"]["min"], inky_display.WHITE, font=font, anchor="mm")
draw.text(next_grid[0].center(), weather["next_day"]["max"], inky_display.WHITE, font=font, anchor="mm")


# Display the weather data on Inky pHAT
inky_display.set_image(img)
inky_display.show()
