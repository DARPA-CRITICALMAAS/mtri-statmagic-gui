""" This file defines global variables and a few color-related utilities. """

import numpy as np
from pathlib import Path
from rasterio.enums import Resampling

plugdir = Path(__file__).parent
clsmap = np.loadtxt(Path(plugdir / 'stock_color_map.clr'))
covmap = np.loadtxt(Path(plugdir / 'classCoversClrmap.clr'))
intmap = np.loadtxt(Path(plugdir / 'interClrmap.clr'))


resampling_dict = {'nearest': Resampling.nearest, 'bilinear': Resampling.bilinear}

def returnColorMap(colorProfile):
    if colorProfile == "Classes":
        return clsmap
    if colorProfile == "Coverage":
        return covmap
    if colorProfile == "Intersection":
        return intmap


def getRGBvals(classid, clrmap):
    # print(f'classid is {classid}')
    try:
        # print('Trying first method')
        lookupID = classid -1
        # print("IN THE LOOKUPTABLE getRGB")
        # print(f'lookupID {lookupID}')
        # print(clrmap)
        red = clrmap[lookupID][1]
        green = clrmap[lookupID][2]
        blue = clrmap[lookupID][3]
        # print(f'red {red}, green {green}, blue {blue}')
    except IndexError:
        print('didnt work, trying second')
        lookupID = np.where(clrmap[:, 0] == classid)[0][0]
        print(f'lookupID is {lookupID}')
        red = clrmap[lookupID][1]
        green = clrmap[lookupID][2]
        blue = clrmap[lookupID][3]
    return int(red), int(green), int(blue)
