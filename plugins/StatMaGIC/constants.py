""" This file defines global variables and a few color-related utilities. """


from rasterio.enums import Resampling



resampling_dict = {'nearest': Resampling.nearest, 'bilinear': Resampling.bilinear,
                   'cubic': Resampling.cubic, 'cubic_spline': Resampling.cubic_spline,
                   'lanczos': Resampling.lanczos, 'average': Resampling.average,
                   'mode': Resampling.mode, 'gauss': Resampling.gauss}
