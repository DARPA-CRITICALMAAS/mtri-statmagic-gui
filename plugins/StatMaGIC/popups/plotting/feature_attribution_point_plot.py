from qgis.PyQt.QtWidgets import QDialog, QCheckBox
from qgis.gui import QgsMapLayerComboBox
from PyQt5.QtWidgets import QFormLayout, QLabel, QVBoxLayout, QGridLayout, QHBoxLayout
from qgis.core import QgsMapLayerProxyModel, QgsRaster, QgsPointXY
import pyqtgraph as pg
from PyQt5.QtCore import Qt
# from qgis.gui import QgsMapToolEmitPoint
# from ..point_tool import PointTool
from ..point_tool import pointTool



class featAttPlot(QDialog):
    def __init__(self, parent):
        self.parent = parent
        self.iface = parent.iface
        super(featAttPlot, self).__init__(parent)
        QDialog.setWindowTitle(self, 'Feature Attribution Plotter')

        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setGeometry(100, 100, 600, 500)
        self.bargraph = pg.BarGraphItem(x=[], height=[], width=0.5)

        raster_label = QLabel('Raster Layer')
        self.raster_selection_box = QgsMapLayerComboBox(self)
        self.raster_selection_box.setShowCrs(True)
        self.raster_selection_box.setFilters(QgsMapLayerProxyModel.RasterLayer)

        self.sort_box = QCheckBox(self)
        self.sort_box.setText('Sort Values')
        self.sort_box.setChecked(True)
        self.sort_box.setToolTip('Checked: Values will be sorted in descending order and band names will be arranged acccordingly \n'
                                 'Unchecked: Band Values will stay in the order and values will not be sorted')

        self.remove_weak = QCheckBox(self)
        self.remove_weak.setText('Remove weak contributors')
        self.remove_weak.setChecked(True)
        self.remove_weak.setToolTip('Checked: Features with values +/- 0.001 from 0 will be dropped \n'
                                 'Unchecked: All features will be included. \n'
                                 'With numerous features plots may be more readable by removing some features')


        self.layout = QVBoxLayout(self)

        self.raster_select_layout = QFormLayout(self)
        innerLayout = QHBoxLayout(self)
        innerLayout.addWidget(self.raster_selection_box)
        innerLayout.addWidget(self.sort_box)
        innerLayout.addWidget(self.remove_weak)
        self.raster_select_layout.addRow(raster_label, innerLayout)

        explanation_text = QLabel('Interpretation: Positive values indicate the evidence reinforces the prediction and '
                                  'negative values indicate the evidence contradicts the prediction. The magnitude of '
                                  'the value is indicative of the level of reinforcement or contradiction')
        explanation_text.setWordWrap(True)

        self.layout.addLayout(self.raster_select_layout)
        self.layout.addWidget(self.plot_widget)
        self.layout.addWidget(explanation_text)

        self.setLayout(self.layout)

        self.canvas = self.parent.canvas
        self.pointTool = pointTool(self.canvas)
        self.canvas.setMapTool(self.pointTool)
        self.pointTool.canvasClicked.connect(self.extract_values)
        # If time look at the other stackoverflow for hover plotting
        # https://gis.stackexchange.com/questions/245280/display-raster-value-as-a-tooltip


    def extract_values(self):
        # Need to clear the bar graph here
        self.plot_widget.removeItem(self.bargraph)
        point = self.pointTool.get_point()
        raster = self.raster_selection_box.currentLayer()
        do_sort = self.sort_box.isChecked()
        drop_weak = self.remove_weak.isChecked()

        provider = raster.dataProvider()
        # extent = raster.extent()
        # xSize = raster.rasterUnitsPerPixelX()
        # ySize = raster.rasterUnitsPerPixelY()

        x = point.x()
        y = point.y()

        # xmin, ymin, xmax, ymax = extent.toRectF().getCoords()
        # row = int((ymax - y) / ySize)
        # col = int((x - xmin) / xSize)

        value_dict = provider.identify(QgsPointXY(x, y),
                                  QgsRaster.IdentifyFormatValue).results()

        band_list = []
        for b in range(raster.bandCount()):
            band_list.append(raster.bandName(b + 1))
        print(band_list)
        x_pos, y, ticks = merge_band_list_and_value_dict(band_list, value_dict, do_sort=do_sort, drop_weak=drop_weak)
        #
        # print('############ Unsorted ###################')
        # for a, b in zip(band_list, list(value_dict.values())):
        #     print(f"{a}: {b}")
        #
        # print('----------Sorted Values--------------------------')
        # for a, b in zip(x_pos, y):
        #     print(f'xpos: {a}, y: {b}')
        #
        # # print(f"x_pos: {x_pos}")
        # # print(f"y: {y}")
        #
        # for a, b in ticks[0]:
        #     print(f"{a}, {b}")
        # # print(f"ticks: {ticks}")
        self.update_plot(x_pos, y, ticks)

    def update_plot(self, x_pos, y, ticks):
        self.bargraph = pg.BarGraphItem(x0=0, y=x_pos, height=0.5, width=y)
        self.plot_widget.addItem(self.bargraph)
        line = pg.InfiniteLine(pos=0, angle=90,  movable=False, pen=pg.mkPen('g', width=2, style=Qt.DashLine))
        self.plot_widget.addItem(line)
        ax = self.plot_widget.getAxis('left')
        ax.setTicks(ticks)

    def close(self):
        self.pointTool.deactivate()
        self.canvas.unsetMapTool(self.pointTool)



def merge_band_list_and_value_dict(band_list, value_dict, do_sort=True, drop_weak=False):
    x_labs = []
    for band in band_list:
        if len(band) > 6 and band[7] == ":":
            band_split = band.split(':')
            if band_split[0][0:4] == 'Band':
                # There's always a space before the first character
                x_labs.append(band_split[1][1:])
            else:
                x_labs.append(band)
        else:
            x_labs.append(band)

    y = list(value_dict.values())

    if drop_weak:
        for i, val in enumerate(y):
            if -0.005 < val < 0.005:
                y.pop(i)
                x_labs.pop(i)

    if do_sort:
        dict_to_sort = {x_labs[i]: y[i] for i in range(len(x_labs))}
        sorted_dict = {k: v for k, v in sorted(dict_to_sort.items(), key=lambda item: item[1])}
        y = list(sorted_dict.values())
        x_labs = list(sorted_dict.keys())

    x_pos = list(range(1, len(x_labs) + 1))
    ticks = []
    for i, item in enumerate(x_labs):
        ticks.append((x_pos[i], item))
    ticks = [ticks]
    return x_pos, y, ticks

#
# #
# value_dict = {1: 0.0015344728017225862, 2: 8.931876072892919e-05, 3: 0.0001621908158995211, 4: -0.002270624041557312, 5: -0.003053442109376192, 6: -0.0009642420336604118, 7: 0.0004031291464343667, 8: 0.0002492135390639305, 9: 0.005374161060899496, 10: -0.0049675083719193935, 11: -0.0007970089209266007, 12: -0.003808047389611602, 13: -0.0002019825333263725, 14: -0.0033749134745448828, 15: -0.0036229423712939024, 16: 0.000789787620306015, 17: 0.00012501147284638137, 18: -6.360213592415676e-05, 19: 3.8295049307635054e-05, 20: -0.0007799595477990806, 21: 0.0014319088077172637, 22: -0.0017671260284259915, 23: -0.0020169871859252453, 24: 0.0012369239702820778, 25: -0.005648343823850155}
# band_list = ['Band 01: Geophysics_Gravity_Bouguer_HGM_Worms', 'Band 02: Geophysics_Gravity_Bouguer_HGM', 'Band 03: Geophysics_Gravity_Bouguer_Up30km_HGM_Worms', 'Band 04: Geophysics_Gravity_Bouguer_Up30km_HGM', 'Band 05: Geophysics_Gravity_Bouguer_Up30km', 'Band 06: Geophysics_Gravity_Bouguer', 'Band 07: Geophysics_Gravity_Isostatic_HGM_Worms', 'Band 08: Geophysics_Gravity_Isostatic_HGM', 'Band 09: Geophysics_Gravity_Isostatic', 'Band 10: Geophysics_LAB_HGM_Worms', 'Band 11: Geophysics_LAB_HGM', 'Band 12: Geophysics_LAB', 'Band 13: Geophysics_Mag_RTP_HGM_smidcont', 'Band 14: Geophysics_Mag_RTP_HGM_Worms', 'Band 15: Geophysics_Mag_RTP_Long-Wavelength_HGM_Worms', 'Band 16: Geophysics_Mag_RTP_Long-Wavelength_HGM', 'Band 17: Geophysics_Mag_RTP_Long-Wavelength', 'Band 18: Geophysics_Mag_RTP_smidcont', 'Band 19: Geophysics_Moho', 'Band 20: Geophysics_MT2023_9km', 'Band 21: Geophysics_MT2023_15km', 'Band 22: Geophysics_MT2023_30km', 'Band 23: Geophysics_MT2023_48km', 'Band 24: Geophysics_MT2023_92km', 'Band 25: Geophysics_Satellite_Gravity']
# # band_list = ['Band 1']
# do_sort = True
# drop_weak = True
#
# x_labs = []
# for band in band_list:
#     if band[6] == ":":
#         band_split = band.split(':')
#         if band_split[0][0:4] == 'Band':
#             # There's always a space before the first character
#             x_labs.append(band_split[1][1:])
#         else:
#             x_labs.append(band)
#     else:
#         x_labs.append(band)
#
# y = list(value_dict.values())
# if drop_weak:
#     for i, val in enumerate(y):
#         print(val)
#         print(x_labs[i])
#         if -0.0001 < val < 0.0001:
#             print('remove')
#             y.pop(i)
#             x_labs.pop(i)
#
# if do_sort:
#     dict_to_sort = {x_labs[i]: y[i] for i in range(len(x_labs))}
#     sorted_dict = {k: v for k, v in sorted(dict_to_sort.items(), key=lambda item: -item[1])}
#     y = list(sorted_dict.values())
#     x_labs = list(sorted_dict.keys())
#
# x_pos = list(range(1, len(x_labs) + 1))
# ticks = []
# for i, item in enumerate(x_labs):
#     ticks.append((x_pos[i], item))
# ticks = [ticks]