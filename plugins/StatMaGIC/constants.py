""" This file defines global variables and a few color-related utilities. """


from rasterio.enums import Resampling



resampling_dict = {'nearest': Resampling.nearest, 'bilinear': Resampling.bilinear,
                   'cubic': Resampling.cubic, 'cubic_spline': Resampling.cubic_spline,
                   'lanczos': Resampling.lanczos, 'average': Resampling.average,
                   'mode': Resampling.mode, 'gauss': Resampling.gauss}

nationdata_raster_dict = {'Gravity: Geophysics HGM US Canada': 'https://d39ptu40l71xc2.cloudfront.net/pub/mrp-public-data/geophysics/gravity/GeophysicsGravity_HGM_USCanada_cog.tif',
                          'Gravity: Geophysics US Canada': 'https://d39ptu40l71xc2.cloudfront.net/pub/mrp-public-data/geophysics/gravity/GeophysicsGravity_USCanada_cog.tif',
                          'Gravity: Geophysics Up30km HGM US Canada': 'https://d39ptu40l71xc2.cloudfront.net/pub/mrp-public-data/geophysics/gravity/GeophysicsGravity_Up30km_HGM_USCanada_cog.tif',
                          'Gravity: Geophysics Up30km US Canada': 'https://d39ptu40l71xc2.cloudfront.net/pub/mrp-public-data/geophysics/gravity/GeophysicsGravity_Up30km_USCanada_cog.tif',
                          'Gravity: Geophysics ShapeIndex US Canada': 'https://d39ptu40l71xc2.cloudfront.net/pub/mrp-public-data/geophysics/gravity/GeophysicsSatelliteGravity_ShapeIndex_USCanada_cog.tif',
                          'Gravity: Geophysics Isostatic HGM US': 'https://d39ptu40l71xc2.cloudfront.net/pub/mrp-public-data/geophysics/gravity/US_IsostaticGravity_HGM_cog.tif',
                          'Gravity: Geophysics Isostatic US': 'https://d39ptu40l71xc2.cloudfront.net/pub/mrp-public-data/geophysics/gravity/US_IsostaticGravity_cog.tif',
                          'Magnetic: RTP Deep Sources': 'https://d39ptu40l71xc2.cloudfront.net/pub/mrp-public-data/geophysics/magnetic/GeophysicsMagRTP_DeepSources_cog.tif',
                          'Magnetic: RTP HGM Deep Sources': 'https://d39ptu40l71xc2.cloudfront.net/pub/mrp-public-data/geophysics/magnetic/GeophysicsMagRTP_HGMDeepSources_cog.tif',
                          'Magnetic: RTP HGM US Canada': 'https://d39ptu40l71xc2.cloudfront.net/pub/mrp-public-data/geophysics/magnetic/GeophysicsMag_RTP_HGM_USCanada_cog.tif',
                          'Magnetic: LOG Analytical Signal US Canada': 'https://d39ptu40l71xc2.cloudfront.net/pub/mrp-public-data/geophysics/magnetic/USCanadaMag_LOGAnalyticSignal_cog.tif.tif',
                          'Magnetic: RTP US Canada': 'https://d39ptu40l71xc2.cloudfront.net/pub/mrp-public-data/geophysics/magnetic/cog_Mag_RTP_UsCanada',
                          'Magnetotelluric: CONUS MT2023 15 km': 'https://d39ptu40l71xc2.cloudfront.net/pub/mrp-public-data/geophysics/magnetotelluric/CONUS_MT2023_15km_cog.tif',
                          'Magnetotelluric: CONUS MT2023 30 km': 'https://d39ptu40l71xc2.cloudfront.net/pub/mrp-public-data/geophysics/magnetotelluric/CONUS_MT2023_30km_cog.tif',
                          'Magnetotelluric: CONUS MT2023 48 km': 'https://d39ptu40l71xc2.cloudfront.net/pub/mrp-public-data/geophysics/magnetotelluric/CONUS_MT2023_48km_cog.tif',
                          'Magnetotelluric: CONUS MT2023 92 km': 'https://d39ptu40l71xc2.cloudfront.net/pub/mrp-public-data/geophysics/magnetotelluric/CONUS_MT2023_92km_cog.tif',
                          'Magnetotelluric: CONUS MT2023 9 km': 'https://d39ptu40l71xc2.cloudfront.net/pub/mrp-public-data/geophysics/magnetotelluric/CONUS_MT2023_9km_cog.tif',
                          'Magnetotelluric: CONUS Conductance 5-40 km': 'https://d39ptu40l71xc2.cloudfront.net/pub/mrp-public-data/geophysics/magnetotelluric/CONUS_conductance_5km_40km_cog.tif',
                          'Magnetotelluric: CONUS Conductance 125 km': 'https://d39ptu40l71xc2.cloudfront.net/pub/mrp-public-data/geophysics/magnetotelluric/CONUS_conductivity_125km_cog.tif',
                          'Magnetotelluric: CONUS Conductance 15 km': 'https://d39ptu40l71xc2.cloudfront.net/pub/mrp-public-data/geophysics/magnetotelluric/CONUS_conductivity_15km_cog.tif',
                          'Magnetotelluric: CONUS Conductance 2 km': 'https://d39ptu40l71xc2.cloudfront.net/pub/mrp-public-data/geophysics/magnetotelluric/CONUS_conductivity_2km_cog.tif',
                          'Magnetotelluric: CONUS Conductance 30 km': 'https://d39ptu40l71xc2.cloudfront.net/pub/mrp-public-data/geophysics/magnetotelluric/CONUS_conductivity_30km_cog.tif',
                          'Magnetotelluric: CONUS Conductance 60 km': 'https://d39ptu40l71xc2.cloudfront.net/pub/mrp-public-data/geophysics/magnetotelluric/CONUS_conductivity_60km_cog.tif',
                          'Radiometric: NAM Rad K': 'https://d39ptu40l71xc2.cloudfront.net/pub/mrp-public-data/geophysics/radiometric/NAMrad_K_COG.tif',
                          'Radiometric: NAM Rad Th': 'https://d39ptu40l71xc2.cloudfront.net/pub/mrp-public-data/geophysics/radiometric/NAMrad_Th_COG.tif',
                          'Radiometric: NAM Rad U': 'https://d39ptu40l71xc2.cloudfront.net/pub/mrp-public-data/geophysics/radiometric/NAMrad_U_COG.tif',
                          'Seismic: LAB US Canada': 'https://d39ptu40l71xc2.cloudfront.net/pub/mrp-public-data/geophysics/seismic/GeophysicsLAB_USCanada_cog.tif',
                          'Seismic: LAB HGM US Canada': 'https://d39ptu40l71xc2.cloudfront.net/pub/mrp-public-data/geophysics/seismic/Geophysics_LAB_HGM_USCanada_cog.tif',
                          'Seismic: Moho US Canada': 'https://d39ptu40l71xc2.cloudfront.net/pub/mrp-public-data/geophysics/seismic/USCanada_Moho_cog.tif'}

nationdata_vector_dict = {'Gravity: Deep Bouger Worms US Canada': 'https://d39ptu40l71xc2.cloudfront.net/pub/mrp-public-data/geophysics/gravity/DeepBouguerGravity_Worms_USCanada.zip',
                          'Gravity: Isostatic Gravity Worms US': 'https://d39ptu40l71xc2.cloudfront.net/pub/mrp-public-data/geophysics/gravity/IsostaticGravityWorms.zip',
                          'Gravity: Shallow Bouguer Gravity Worms US Canada': 'https://d39ptu40l71xc2.cloudfront.net/pub/mrp-public-data/geophysics/gravity/ShallowBouguerGravity_Worms_USCanada.zip',
                          'Magnetic: Deep Mag Sources Worms US Canada': 'https://d39ptu40l71xc2.cloudfront.net/pub/mrp-public-data/geophysics/magnetic/DeepMagSources_Worms_USCanada.zip',
                          'Magnetic: Shallow Mag Sources Worms US Canada': 'https://d39ptu40l71xc2.cloudfront.net/pub/mrp-public-data/geophysics/magnetic/ShallowMagSources_Worms_USCanada.zip',
                          'Seismic: LAB worms': 'https://d39ptu40l71xc2.cloudfront.net/pub/mrp-public-data/geophysics/seismic/USCanada_LABWorms.zip'}