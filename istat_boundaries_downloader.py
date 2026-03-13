# -*- coding: utf-8 -*-
"""
/***************************************************************************
 ISTAT Boundaries Downloader

 This plugin allows you to download Italian administrative boundaries from the onData API.
 It supports various boundary types (regions, provinces, municipalities) at different dates.
                              -------------------
        begin                : 2025-03-02
        git sha              : $Format:%H$
        email                : pigrecoinfinito@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import os

from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtGui import QIcon

from .istat_boundaries_downloader_dialog import DownloaderDialog


class IstatBoundariesDownloader:
    """QGIS Plugin to download Italian administrative boundaries from onData API"""

    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)

        # Set up the base URL for API requests
        self.base_url = "https://www.confini-amministrativi.it/api/v2/it/"

        # Define available boundary types
        self.boundary_types = {
            "Regioni": "regioni",
            "Unità Territoriali Sovracomunali (Province)": "unita-territoriali-sovracomunali",
            "Comuni": "comuni",
            "Ripartizioni Geografiche": "ripartizioni-geografiche"
        }

        # Define available formats
        self.formats = {
            "Shapefile (.zip)": "zip",
            "GeoPackage (.gpkg)": "gpkg",
            "CSV (.csv)": "csv",
            "KML (.kml)": "kml",
            "KMZ (.kmz)": "kmz"
        }

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI"""
        icon_path = os.path.join(self.plugin_dir, "icon.svg")
        self.action = QAction(
            QIcon(icon_path),
            "ISTAT Boundaries Downloader",
            self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu("ISTAT Boundaries Downloader", self.action)

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI"""
        self.iface.removePluginMenu("ISTAT Boundaries Downloader", self.action)
        self.iface.removeToolBarIcon(self.action)

    def run(self):
        """Run method that performs all the real work"""
        dlg = DownloaderDialog(self.boundary_types, self.formats, self.base_url, self.iface, self.plugin_dir)
        dlg.exec()
