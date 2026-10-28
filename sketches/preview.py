"""Assemble the six exported PNGs without reducing their resolution."""

from pathlib import Path

from matplotlib.image import imread, imsave
import numpy as np


def save_preview(paths, output_path):
    """Place Q2, Q3, and Q4 in rows, with their two views side by side."""
    if len(paths) != 6:
        raise ValueError("The preview requires exactly six PNGs")
    images = [np.rint(imread(path) * 255).astype(np.uint8) for path in paths]
    widths = [max(image.shape[1] for image in images[column::2]) for column in range(2)]
    heights = [max(image.shape[0] for image in images[row:row + 2]) for row in (0, 2, 4)]
    gap = 24
    canvas = np.full((sum(heights) + gap * 4, sum(widths) + gap * 3, 4), 255, dtype=np.uint8)
    y = gap
    for row, height in enumerate(heights):
        x = gap
        for column, width in enumerate(widths):
            image = images[row * 2 + column]
            top, left = y + (height - image.shape[0]) // 2, x + (width - image.shape[1]) // 2
            canvas[top:top + image.shape[0], left:left + image.shape[1], :image.shape[2]] = image
            x += width + gap
        y += height + gap
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    imsave(output_path, canvas, format="png")
    return output_path
