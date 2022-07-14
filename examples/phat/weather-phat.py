#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from resource import prlimit
import geocoder
import random
from bs4 import BeautifulSoup
import glob
import os
import time
from sys import exit
import requests

from font_fredoka_one import FredokaOne
from inky.auto import auto
from PIL import Image, ImageDraw, ImageFont


# Get the current path
PATH = os.path.dirname(__file__)

# Set up the display
try:
    inky_display = auto(ask_user=True, verbose=True)
except TypeError:
    raise TypeError("You need to update the Inky library to >= v1.1.0")

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


# Query Dark Sky (https://darksky.net/) to scrape current weather data
def get_weather(address):
    coords = get_coords(address)
    weather = {}
    res = requests.get(
        "https://darksky.net/forecast/{}/uk212/en".format(",".join([str(c) for c in coords])))
    if res.status_code == 200:
        soup = BeautifulSoup(res.content, "lxml")
        curr = soup.find_all("span", "currently")
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
    kandinskys = glob.glob(os.path.join(PATH, "resources/kandinsky/*.png"))
    # get random from array
    kandinsky = random.choice(kandinskys)
    image = Image.open(kandinsky, ).resize((200, 224))
    print(image)
    return {"mask": create_mask(image),
     "image": image}


# Load the FredokaOne font
font = ImageFont.truetype(FredokaOne, 22)

# Draw lines to frame the weather data
draw.line((INKY_WIDTH/3, 0, INKY_WIDTH/3, INKY_HEIGHT),
          1)       # Vertical line
draw.line((INKY_WIDTH-INKY_WIDTH, INKY_HEIGHT/2, INKY_WIDTH,
          INKY_HEIGHT/2), 1)      # Horizontal top line
draw.line((INKY_WIDTH/3*2, 0, INKY_WIDTH/3*2,
          INKY_HEIGHT), 1)       # Vertical line

# Write text with weather values to the canvas
today_date = time.strftime("%d/%m")
now = time.strftime("%H:%M")


draw.text((30, 12), f"Thursday {today_date}", inky_display.WHITE, font=font)

# Time
draw.text((36, 120), f"{now}", inky_display.WHITE, font=font)

# Temperature
draw.text((70, 45), u"{}°C".format(temperature), inky_display.WHITE if temperature <
          WARNING_TEMP else inky_display.RED, font=font)

# Draw the current weather icon over the backdrop
if weather_icon is not None:
    print(icons[weather_icon], masks[weather_icon])
    img.paste(icons[weather_icon], (28, 36), masks[weather_icon])
else:
    draw.text((28, 36), "?", inky_display.RED, font=font)


kandinsky = get_kandinsky()
img.paste(kandinsky["image"], (400,0))

# Display the weather data on Inky pHAT
inky_display.set_image(img)
inky_display.show()
