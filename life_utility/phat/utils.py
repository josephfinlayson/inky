
from typing import List, Tuple
from PIL import Image, ImageDraw, ImageFont
from Box import Box
def draw_grid(width, height, number_of_grids_vertically, number_of_grids_horizontally, coordinates: Tuple[int, int], draw: ImageDraw, inky_display):
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
