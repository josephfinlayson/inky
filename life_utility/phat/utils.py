#!/usr/bin/env python3
"""Utility classes and functions for the display."""

from typing import List, Tuple
from PIL import Image, ImageDraw


class Box:
    """Represents a rectangular region on the display."""

    def __init__(self, x1: int, y1: int, x2: int, y2: int):
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2

    def __repr__(self):
        return f"Box({self.x1}, {self.y1}, {self.x2}, {self.y2})"

    def center(self) -> Tuple[int, int]:
        return (self.x1 + self.x2) // 2, (self.y1 + self.y2) // 2

    def width(self) -> int:
        return self.x2 - self.x1

    def height(self) -> int:
        return self.y2 - self.y1


def draw_grid(
    width: int,
    height: int,
    cols: int,
    rows: int,
    origin: Tuple[int, int],
    draw: ImageDraw,
    inky_display,
) -> List[Box]:
    """Create a grid of Box regions and draw borders."""
    grids = []
    start_x, start_y = origin
    cell_w = width // cols
    cell_h = height // rows

    for col in range(cols):
        for row in range(rows):
            x = start_x + col * cell_w
            y = start_y + row * cell_h
            bbox = (x, y, x + cell_w, y + cell_h)
            draw.rectangle(bbox, fill=None, outline=inky_display.WHITE)
            grids.append(Box(*bbox))

    return grids


def create_mask(source: Image, allowed_colors: tuple) -> Image:
    """Create a transparency mask for e-ink color palette.

    Args:
        source: Paletized source image
        allowed_colors: Tuple of allowed Inky color indices

    Returns:
        Binary mask image where allowed colors are white (255)
    """
    mask = Image.new("1", source.size)
    w, h = source.size

    for x in range(w):
        for y in range(h):
            if source.getpixel((x, y)) in allowed_colors:
                mask.putpixel((x, y), 255)

    return mask
