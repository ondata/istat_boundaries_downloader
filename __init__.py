# -*- coding: utf-8 -*-
"""
/***************************************************************************
 ISTAT Boundaries Downloader
                              -------------------
        begin                : 2025-03-02
        git sha              : $Format:%H$
        copyright            : (C) 2025
        email                : support@example.com
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


def classFactory(iface):
    """Load the plugin class.
    
    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    from .istat_boundaries_downloader import IstatBoundariesDownloader
    return IstatBoundariesDownloader(iface)