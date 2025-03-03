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
import urllib.request
import urllib.error
import zipfile
import tempfile
import http.client
from datetime import datetime
import shutil  # Aggiungi importazione per operazioni sui file

from qgis.PyQt.QtCore import Qt, QUrl
from qgis.PyQt.QtWidgets import (QAction, QDialog, QVBoxLayout, QHBoxLayout, 
                               QLabel, QComboBox, QPushButton, 
                               QProgressBar, QMessageBox, QApplication,
                               QFileDialog, QCheckBox)  # Aggiungi QFileDialog e QCheckBox
from qgis.PyQt.QtGui import QIcon, QCursor, QDesktopServices
from qgis.core import QgsProject, QgsVectorLayer, Qgis, QgsMessageLog
from qgis.PyQt.QtCore import QSize

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
            "CSV (.csv)": "csv"
        }

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI"""
        icon_path = os.path.join(self.plugin_dir, "icon.png")
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
        # Create and show the dialog
        dlg = DownloaderDialog(self.boundary_types, self.formats, self.base_url, self.iface, self.plugin_dir)
        # Show the dialog
        dlg.exec_()


class DownloaderDialog(QDialog):
    def __init__(self, boundary_types, formats, base_url, iface, plugin_dir, parent=None):
        super(DownloaderDialog, self).__init__(parent)
        self.boundary_types = boundary_types
        self.formats = formats
        self.base_url = base_url
        self.iface = iface
        self.plugin_dir = plugin_dir
        self.setWindowTitle("ISTAT Boundaries Downloader")
        self.setup_ui()

    def setup_ui(self):
        """Set up the user interface for the dialog"""
        # Create layout
        layout = QVBoxLayout()
        
        # Add logo/icon
        icon_layout = QHBoxLayout()
        icon_label = QLabel()
        icon_pixmap = QIcon(os.path.join(self.plugin_dir, "icon.png")).pixmap(88, 88)
        icon_label.setPixmap(icon_pixmap)
        
        title_label = QLabel("ISTAT Boundaries Downloader (EPSG:4326)")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        
        icon_layout.addWidget(icon_label)
        icon_layout.addWidget(title_label)
        icon_layout.addStretch()
        layout.addLayout(icon_layout)
        
        # Info label with hyperlink in a single line
        info_layout = QHBoxLayout()
        
        # Create a single line text with hyperlink
        info_text = QLabel("Scarica confini amministrativi italiani ISTAT usando le ")
        info_text.setStyleSheet("font-size: 14px; font-weight: bold;")
        
        link_label = QLabel("<a href='https://www.confini-amministrativi.it/'>API onData</a>")
        link_label.setOpenExternalLinks(True)
        link_label.setStyleSheet("font-size: 14px;")
        
        info_layout.addWidget(info_text)
        info_layout.addWidget(link_label)
        info_layout.addStretch(1)
        
        layout.addLayout(info_layout)
        
        # Aggiungi linea separatrice
        separator = QLabel()
        separator.setStyleSheet("border-top: 1px solid #ddd; margin-top: 10px; margin-bottom: 10px;")
        layout.addWidget(separator)
        
        # Date selection
        date_layout = QHBoxLayout()
        date_label = QLabel("Data di riferimento (>=1991):")
        
        # Replace DateEdit with ComboBox for predefined dates
        self.date_combo = QComboBox()
        
        # Add dates from screenshots
        # Primo gruppo (più recenti)
        self.date_combo.addItem("20240101")
        self.date_combo.addItem("20230101")
        self.date_combo.addItem("20220101")
        self.date_combo.addItem("20210101")
        self.date_combo.addItem("20200101")
        self.date_combo.addItem("20190101")
        self.date_combo.addItem("20180101")
        
        # Secondo gruppo
        self.date_combo.addItem("20170101")
        self.date_combo.addItem("20160101")
        self.date_combo.addItem("20150101")
        self.date_combo.addItem("20140101")
        self.date_combo.addItem("20130101")
        self.date_combo.addItem("20120101")
        self.date_combo.addItem("20111009")
        self.date_combo.addItem("20100101")
        
        # Terzo gruppo (più vecchi)
        self.date_combo.addItem("20060101")
        self.date_combo.addItem("20050101")
        self.date_combo.addItem("20040101")
        self.date_combo.addItem("20030101")
        self.date_combo.addItem("20020101")
        self.date_combo.addItem("20011021")
        self.date_combo.addItem("19911020")
        
        date_layout.addWidget(date_label)
        date_layout.addWidget(self.date_combo)
        layout.addLayout(date_layout)
        
        # Boundary type selection
        type_layout = QHBoxLayout()
        type_label = QLabel("Tipo di confine amministrativo:")
        self.type_combo = QComboBox()
        for label in self.boundary_types.keys():
            self.type_combo.addItem(label)
        
        type_layout.addWidget(type_label)
        type_layout.addWidget(self.type_combo)
        layout.addLayout(type_layout)
        
        # Format selection
        format_layout = QHBoxLayout()
        format_label = QLabel("Formato disponibile:")
        self.format_combo = QComboBox()
        for label in self.formats.keys():
            self.format_combo.addItem(label)
        
        format_layout.addWidget(format_label)
        format_layout.addWidget(self.format_combo)
        layout.addLayout(format_layout)
        
        # Aggiungi nota sul formato CSV
        self.csv_note = QLabel("Nota: il formato CSV non contiene geometrie, solo dati tabellari.")
        self.csv_note.setStyleSheet("color: #FF5722; font-style: italic;")
        self.csv_note.setVisible(False)  # Inizialmente nascosto
        layout.addWidget(self.csv_note)
        
        # Mostra/nascondi la nota quando il formato selezionato cambia
        self.format_combo.currentIndexChanged.connect(self.update_format_notes)
        
        # Prima del layout URL preview, aggiungi il selettore del percorso di salvataggio
        save_path_layout = QHBoxLayout()
        save_path_label = QLabel("Salva in:")
        self.save_path_edit = QLabel("Seleziona una cartella di destinazione...")
        self.save_path_edit.setStyleSheet("font-family: monospace; padding: 5px; background-color: #f5f5f5; border: 1px solid #ddd;")
        self.save_path_edit.setWordWrap(True)
        
        self.browse_button = QPushButton("Sfoglia")
        self.browse_button.setIcon(QIcon(":/qt-project.org/styles/commonstyle/images/diropen-16.png"))
        self.browse_button.setStyleSheet("background-color: #8BC34A; color: Black; font-weight: bold;")
        self.browse_button.clicked.connect(self.browse_folder)
        
        save_path_layout.addWidget(save_path_label)
        save_path_layout.addWidget(self.save_path_edit, 1)
        save_path_layout.addWidget(self.browse_button)
        layout.addLayout(save_path_layout)
        
        # Aggiungi opzione per salvare solo localmente (senza caricare in QGIS)
        save_only_layout = QHBoxLayout()
        self.save_only_check = QCheckBox("Solo salvataggio locale (non caricare in QGIS)")
        save_only_layout.addWidget(self.save_only_check)
        layout.addLayout(save_only_layout)
        
        # URL preview
        url_layout = QVBoxLayout()
        url_label = QLabel("URL di download:")
        self.url_preview = QLabel()
        self.url_preview.setStyleSheet("font-family: monospace; padding: 5px; background-color: #f5f5f5; border: 1px solid #ddd;")
        self.url_preview.setWordWrap(True)
        
        # Update URL preview when selections change
        self.date_combo.currentIndexChanged.connect(self.update_url_preview)
        self.type_combo.currentIndexChanged.connect(self.update_url_preview)
        self.format_combo.currentIndexChanged.connect(self.update_url_preview)
        
        url_layout.addWidget(url_label)
        url_layout.addWidget(self.url_preview)
        layout.addLayout(url_layout)
        
        # Progress bar (hidden initially)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Buttons layout
        buttons_layout = QHBoxLayout()
        
        # Chiudi button
        self.close_button = QPushButton("Chiudi")
        self.close_button.setIcon(QIcon(":/qt-project.org/styles/commonstyle/images/standardbutton-closetab-16.png"))
        self.close_button.setIconSize(QSize(24, 24))  # Imposta una dimensione adeguata per l'icona
        self.close_button.clicked.connect(self.reject)
        buttons_layout.addWidget(self.close_button)
        
        # Aggiungi spazio tra i pulsanti
        buttons_layout.addStretch(1)
        
        # Download button - con dimensione raddoppiata
        self.download_button = QPushButton("Scarica")
        download_icon = QIcon(":/images/themes/default/downloading_svg.svg")
        # Crea un'icona più grande (raddoppiata)
        self.download_button.setIconSize(QSize(32, 32))  # Dimensione dell'icona raddoppiata
        self.download_button.setIcon(download_icon)
        self.download_button.setStyleSheet("background-color: #4CAF50; color: white; font-size: 14px; font-weight: bold;")
        # Imposta una dimensione più grande
        download_size_policy = self.download_button.sizePolicy()
        download_size_policy.setHorizontalStretch(2) 
        self.download_button.setSizePolicy(download_size_policy)
        # Imposta altezza minima maggiore
        self.download_button.setMinimumHeight(40)
        self.download_button.clicked.connect(self.download_boundaries)
        buttons_layout.addWidget(self.download_button)
        
        layout.addLayout(buttons_layout)
        
        # Initialize URL preview
        self.update_url_preview()
        
        self.setLayout(layout)
        self.resize(500, 300)
        
        # Initialize save path to user's documents folder
        self.download_path = os.path.join(os.path.expanduser('~'), 'Documents')
        self.save_path_edit.setText(self.download_path)
        
    def update_url_preview(self):
        """Update the URL preview based on current selections"""
        date_str = self.date_combo.currentText()
        boundary_type = self.boundary_types[self.type_combo.currentText()]
        file_format = self.formats[self.format_combo.currentText()]
        url = f"{self.base_url}{date_str}/{boundary_type}.{file_format}"
        self.url_preview.setText(url)
        
    def check_availability(self):
        """Check if the selected resource is available"""
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        
        date_str = self.date_combo.currentText()
        boundary_type = self.boundary_types[self.type_combo.currentText()]
        file_format = self.formats[self.format_combo.currentText()]
        url = f"{self.base_url}{date_str}/{boundary_type}.{file_format}"
        
        if self.check_url_exists(url):
            QApplication.restoreOverrideCursor()
            QMessageBox.information(self, "Disponibilità", f"La risorsa è disponibile!\n\n{url}")
        else:
            QApplication.restoreOverrideCursor()
            response = QMessageBox.question(
                self, 
                "Risorsa non disponibile", 
                f"L'URL richiesto non è disponibile:\n{url}\n\nVuoi vedere date alternative suggerite?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if response == QMessageBox.Yes:
                self.show_suggestions_dialog(url)
    
    def check_url_exists(self, url):
        """Check if a URL exists without downloading the full content"""
        try:
            # Just open the URL without retrieving data
            request = urllib.request.Request(url, method='HEAD')
            urllib.request.urlopen(request)
            return True
        except urllib.error.HTTPError as e:
            QgsMessageLog.logMessage(f"URL check failed: {url} - {str(e)}", "ISTAT Downloader", Qgis.Critical)
            return False
        except Exception as e:
            QgsMessageLog.logMessage(f"URL check error: {str(e)}", "ISTAT Downloader", Qgis.Critical)
            return False
    
    def get_suggested_dates(self):
        """Return a list of suggested dates that are likely to work"""
        # Usiamo direttamente le date predefinite che sono nel combobox
        suggested_dates = []
        for i in range(self.date_combo.count()):
            suggested_dates.append(self.date_combo.itemText(i))
        return suggested_dates
    
    def show_suggestions_dialog(self, failed_url):
        """Show a dialog with suggested dates and URLs"""
        # Use the predefined dates instead of generating them
        suggestions = [
            "20240101", "20230101", "20220101", "20210101", "20200101",
            "20190101", "20180101", "20170101", "20160101", "20150101"
        ]
        boundary_type = self.boundary_types[self.type_combo.currentText()]
        file_format = self.formats[self.format_combo.currentText()]
        
        message = f"L'URL richiesto non è disponibile:\n{failed_url}\n\nProva con queste date disponibili:"
        
        # Add suggested dates to the message
        for date in suggestions:
            suggested_url = f"{self.base_url}{date}/{boundary_type}.{file_format}"
            # Only suggest URLs that exist
            if self.check_url_exists(suggested_url):
                message += f"\n- {date} (01/01/{date[:4]})"
        
        QMessageBox.information(self, "Suggerimenti", message)
    
    def download_boundaries(self):
        """Download and load the selected boundaries"""
        try:
            # Change cursor to wait cursor
            QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
            
            # Show progress
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(10)
            
            # Get selected options
            date_str = self.date_combo.currentText()
            boundary_type = self.boundary_types[self.type_combo.currentText()]
            file_format = self.formats[self.format_combo.currentText()]
            save_only = self.save_only_check.isChecked()
            
            # Verifica che la cartella di destinazione esista
            if not os.path.exists(self.download_path):
                os.makedirs(self.download_path)
            
            # Construct the URL
            url = f"{self.base_url}{date_str}/{boundary_type}.{file_format}"
            
            # First check if the URL exists
            if not self.check_url_exists(url):
                QApplication.restoreOverrideCursor()
                self.progress_bar.setVisible(False)
                response = QMessageBox.question(
                    self, 
                    "Risorsa non disponibile", 
                    f"L'URL richiesto non è disponibile:\n{url}\n\nVuoi vedere date alternative suggerite?",
                    QMessageBox.Yes | QMessageBox.No
                )
                
                if response == QMessageBox.Yes:
                    self.show_suggestions_dialog(url)
                return
            
            self.progress_bar.setValue(20)
            
            # Create a temporary directory for extraction and processing
            temp_dir = tempfile.mkdtemp()
            temp_file_path = os.path.join(temp_dir, f"{boundary_type}.{file_format}")
            
            # Download the file with proper error handling
            try:
                urllib.request.urlretrieve(url, temp_file_path)
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    QApplication.restoreOverrideCursor()
                    QMessageBox.critical(self, "Error", f"Risorsa non trovata (HTTP 404). L'URL non esiste: {url}")
                    return
                else:
                    raise
            
            self.progress_bar.setValue(50)
            
            # Crea nome file di destinazione
            file_name = f"ISTAT_{boundary_type}_{date_str}"
            
            # Gestione diversa in base al formato
            if file_format == "zip":
                # Copia nella destinazione specificata dall'utente
                dest_zip_path = os.path.join(self.download_path, f"{file_name}.zip")
                shutil.copyfile(temp_file_path, dest_zip_path)
                
                # Extract the file if it's a ZIP for processing and viewing in QGIS
                try:
                    with zipfile.ZipFile(temp_file_path, 'r') as zip_ref:
                        zip_ref.extractall(temp_dir)
                    
                    # Find the shapefile
                    shp_files = [f for f in os.listdir(temp_dir) if f.endswith('.shp')]
                    
                    if not shp_files:
                        QApplication.restoreOverrideCursor()
                        QMessageBox.critical(self, "Error", "Nessun shapefile trovato nell'archivio zip.")
                        return
                        
                    # Path per QGIS
                    qgis_file_path = os.path.join(temp_dir, shp_files[0])
                    
                    # Se l'utente vuole estrarre nella cartella di destinazione
                    dest_dir = os.path.join(self.download_path, file_name)
                    if not os.path.exists(dest_dir):
                        os.makedirs(dest_dir)
                    
                    # Estrai tutti i file nella cartella di destinazione
                    with zipfile.ZipFile(dest_zip_path, 'r') as zip_ref:
                        zip_ref.extractall(dest_dir)
                    
                except zipfile.BadZipFile:
                    QApplication.restoreOverrideCursor()
                    QMessageBox.critical(self, "Error", "Il file scaricato non è un archivio ZIP valido.")
                    return
            elif file_format == "csv":
                # Per CSV, copialo direttamente
                dest_csv_path = os.path.join(self.download_path, f"{file_name}.csv")
                shutil.copyfile(temp_file_path, dest_csv_path)
                
                # Per il CSV, potrebbe essere necessario specificare il delimitatore e la geometria
                if not save_only:
                    # Imposta URI per caricare il CSV come layer (senza geometria)
                    uri = f"file:///{dest_csv_path}?delimiter=,"
                    qgis_file_path = uri
                else:
                    qgis_file_path = dest_csv_path
            else:
                # Per GeoPackage (.gpkg), copialo direttamente
                dest_gpkg_path = os.path.join(self.download_path, f"{file_name}.gpkg")
                shutil.copyfile(temp_file_path, dest_gpkg_path)
                qgis_file_path = dest_gpkg_path
            
            self.progress_bar.setValue(80)
            
            # Carica il layer in QGIS solo se l'utente non ha scelto "solo salvataggio"
            if not save_only:
                layer_name = f"ISTAT_{boundary_type}_{date_str}"
                
                if file_format == "csv":
                    # Per i CSV, utilizziamo un gestore specifico per dati non geografici
                    vector_layer = QgsVectorLayer(uri, layer_name, "delimitedtext")
                else:
                    # Per shapefile e geopackage, utilizziamo ogr
                    if file_format == "zip":
                        # Per shapefile, usa il percorso al file .shp nella cartella estratta
                        extracted_shp = os.path.join(dest_dir, shp_files[0])
                        vector_layer = QgsVectorLayer(extracted_shp, layer_name, "ogr")
                    else:
                        vector_layer = QgsVectorLayer(qgis_file_path, layer_name, "ogr")
                
                if vector_layer.isValid():
                    # Add the layer to the map
                    QgsProject.instance().addMapLayer(vector_layer)
                    QgsMessageLog.logMessage(f"Dati caricati con successo: {layer_name}", "ISTAT Downloader", Qgis.Info)
                else:
                    QMessageBox.critical(self, "Error", f"Il file {file_format} scaricato non è valido.")
                    self.progress_bar.setVisible(False)
                    QApplication.restoreOverrideCursor()
                    return
            
            self.progress_bar.setValue(100)
            
            # Messaggio di successo
            if save_only:
                message = f"Dati {boundary_type} del {date_str[:4]}-{date_str[4:6]}-{date_str[6:]} scaricati con successo in:\n{self.download_path}"
            else:
                message = f"Dati {boundary_type} del {date_str[:4]}-{date_str[4:6]}-{date_str[6:]} scaricati con successo in:\n{self.download_path}\n\ne caricati nel progetto QGIS."
                
            QMessageBox.information(self, "Operazione completata", message)
                
        except Exception as e:
            QgsMessageLog.logMessage(f"Errore: {str(e)}", "ISTAT Downloader", Qgis.Critical)
            QMessageBox.critical(self, "Error", f"Si è verificato un errore: {str(e)}")
        
        finally:
            # Pulisci la directory temporanea
            try:
                shutil.rmtree(temp_dir)
            except:
                pass
            
            self.progress_bar.setVisible(False)
            QApplication.restoreOverrideCursor()
            
    def browse_folder(self):
        """Browse for a folder to save the downloaded files"""
        folder = QFileDialog.getExistingDirectory(self, "Seleziona cartella di destinazione", self.download_path)
        if folder:
            self.download_path = folder
            self.save_path_edit.setText(folder)
            
    def update_format_notes(self):
        """Mostra/nascondi note sui formati quando cambiano le selezioni"""
        format_text = self.format_combo.currentText()
        self.csv_note.setVisible("CSV" in format_text)
            
# Required methods for QGIS plugin
def classFactory(iface):
    return IstatBoundariesDownloader(iface)