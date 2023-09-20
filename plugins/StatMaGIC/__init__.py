from .statmagic import StatMaGICPlugin

def classFactory(iface):
    return StatMaGICPlugin(iface)