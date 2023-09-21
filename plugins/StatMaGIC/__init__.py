from .statmagicplugin import StatMaGICPlugin

def classFactory(iface):
    return StatMaGICPlugin(iface)