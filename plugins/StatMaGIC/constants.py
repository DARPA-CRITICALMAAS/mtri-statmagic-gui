""" This file defines global variables and a few color-related utilities. """


from rasterio.enums import Resampling



resampling_dict = {'nearest': Resampling.nearest, 'bilinear': Resampling.bilinear}
