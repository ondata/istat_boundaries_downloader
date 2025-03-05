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
                               QFileDialog, QCheckBox, QWidget, QLineEdit,
                               QFrame, QFormLayout, QGroupBox, QGridLayout)  # Aggiunto QLineEdit
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
        
        # Imposta un ridimensionamento minimo iniziale
        self.resize(550, 580)
        # Impedisce il ridimensionamento orizzontale e verticale eccessivo
        self.setMinimumWidth(550)
        self.setMinimumHeight(580)

    def setup_ui(self):
        """Configura l'interfaccia utente del dialogo con una migliore organizzazione e allineamento"""
        # Layout principale
        layout = QVBoxLayout()
        layout.setSpacing(12)  # Spaziatura costante tra tutti gli elementi
        layout.setContentsMargins(15, 15, 15, 15)  # Aggiunge un po' di padding su tutti i bordi
        
        # ===== SEZIONE INTESTAZIONE =====
        header_layout = self.create_header_section()
        layout.addLayout(header_layout)
        
        # Aggiunge un separatore dopo l'intestazione
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("background-color: #E0E0E0; max-height: 1px;")
        layout.addWidget(separator)
        layout.addSpacing(5)  # Aggiunge un po' di spazio extra dopo il separatore
        
        # ===== MODULO IMPOSTAZIONI PRINCIPALI =====
        # Creiamo un contenitore con un layout a griglia per un allineamento migliore
        form_container = QWidget()
        form_grid = QGridLayout(form_container)
        form_grid.setVerticalSpacing(10)
        form_grid.setHorizontalSpacing(10)
        form_grid.setContentsMargins(5, 0, 5, 0)
        
        # 1. Selezione data (riga 0)
        date_label = QLabel("Data di riferimento (>=1991):")
        date_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.date_combo = QComboBox()
        
        # Aggiunge date in gruppi logici
        date_recenti = ["20240101", "20230101", "20220101", "20210101", "20200101"]
        date_medie = ["20190101", "20180101", "20170101", "20160101", "20150101", 
                     "20140101", "20130101", "20120101", "20111009", "20100101"]
        date_vecchie = ["20060101", "20050101", "20040101", "20030101", "20020101", 
                       "20011021", "19911020"]
        
        # Aggiunge date recenti
        for date in date_recenti:
            self.date_combo.addItem(date)
        
        # Aggiunge date medie
        for date in date_medie:
            self.date_combo.addItem(date)
        
        # Aggiunge date vecchie
        for date in date_vecchie:
            self.date_combo.addItem(date)
        
        self.date_combo.setMinimumWidth(300)
        form_grid.addWidget(date_label, 0, 0)
        form_grid.addWidget(self.date_combo, 0, 1)
        
        # 2. Selezione tipo di confine (riga 1)
        type_label = QLabel("Tipo di confine amministrativo:")
        type_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.type_combo = QComboBox()
        tipi_confine_ordinati = [
            "Ripartizioni Geografiche",
            "Regioni",
            "Unità Territoriali Sovracomunali (Province)",
            "Comuni"
        ]
        
        for label in tipi_confine_ordinati:
            if label in self.boundary_types:
                self.type_combo.addItem(label)
        
        self.type_combo.setMinimumWidth(300)
        form_grid.addWidget(type_label, 1, 0)
        form_grid.addWidget(self.type_combo, 1, 1)
        
        # 3. Filtro regione (righe 2-3)
        self.region_filter_container = QWidget()
        region_grid = QGridLayout(self.region_filter_container)
        region_grid.setContentsMargins(0, 0, 0, 0)
        region_grid.setSpacing(10)
        
        # Selezione regione (riga 2)
        region_label = QLabel("Filtro regione:")
        region_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.region_combo = QComboBox()
        self.region_combo.setMinimumWidth(300)
        region_grid.addWidget(region_label, 0, 0)
        region_grid.addWidget(self.region_combo, 0, 1)
        
        # Selezione tipo dati regione (riga 3)
        region_data_label = QLabel("Scarica:")
        region_data_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.region_data_combo = QComboBox()
        self.region_data_combo.setMinimumWidth(300)
        self.region_data_combo.addItem("Province della regione")
        self.region_data_combo.addItem("Comuni della regione")
        region_grid.addWidget(region_data_label, 1, 0)
        region_grid.addWidget(self.region_data_combo, 1, 1)
        
        # Nascondi il filtro regione inizialmente
        self.region_filter_container.setVisible(False)
        form_grid.addWidget(self.region_filter_container, 2, 0, 1, 2)
        
        # 4. Selezione formato (riga 4)
        format_label = QLabel("Formato disponibile:")
        format_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.format_combo = QComboBox()
        for label in self.formats.keys():
            self.format_combo.addItem(label)
        self.format_combo.setMinimumWidth(300)
        form_grid.addWidget(format_label, 4, 0)
        form_grid.addWidget(self.format_combo, 4, 1)
        
        # Nota CSV (riga 5)
        self.csv_note = QLabel("Nota: il formato CSV non contiene geometrie, solo dati tabellari.")
        self.csv_note.setStyleSheet("color: #FF5722; font-style: italic;")
        self.csv_note.setVisible(False)
        form_grid.addWidget(self.csv_note, 5, 1)
        
        # Imposta la larghezza delle colonne
        form_grid.setColumnStretch(0, 0)  # Prima colonna (labels) non si espande
        form_grid.setColumnStretch(1, 1)  # Seconda colonna (combobox) si espande
        
        # Aggiungi il container del form al layout principale
        layout.addWidget(form_container)
        
        # Crea il filtro province
        self.create_province_filter()
        
        # Aggiungi il filtro province al form_grid
        form_grid.addWidget(self.province_filter_container, 3, 0, 1, 2)
        
        # ===== SEZIONE OPZIONI DI SALVATAGGIO =====
        save_section = QGroupBox("Opzioni di Salvataggio")
        save_section.setStyleSheet("QGroupBox { font-weight: bold; }")
        save_layout = QGridLayout(save_section)
        save_layout.setVerticalSpacing(10)
        
        # Selezione percorso di salvataggio
        save_path_label = QLabel("Salva in:")
        save_path_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.save_path_edit = QLabel("Seleziona una cartella di destinazione...")
        self.save_path_edit.setStyleSheet("font-family: monospace; padding: 8px; background-color: #f8f8f8; border: 1px solid #ddd; border-radius: 4px;")
        self.save_path_edit.setWordWrap(True)
        
        self.browse_button = QPushButton("Sfoglia")
        self.browse_button.setIcon(QIcon(":/qt-project.org/styles/commonstyle/images/diropen-16.png"))
        self.browse_button.setStyleSheet("background-color: #8BC34A; color: Black; font-weight: bold; padding: 5px 10px; border-radius: 4px;")
        self.browse_button.clicked.connect(self.browse_folder)
        
        save_layout.addWidget(save_path_label, 0, 0)
        save_layout.addWidget(self.save_path_edit, 0, 1)
        save_layout.addWidget(self.browse_button, 0, 2)
        
        # Checkbox salvataggio solo locale
        self.save_only_check = QCheckBox("Solo salvataggio locale (non caricare in QGIS)")
        save_layout.addWidget(self.save_only_check, 1, 1, 1, 2)
        
        # Imposta le proporzioni delle colonne
        save_layout.setColumnStretch(0, 0)  # Etichetta
        save_layout.setColumnStretch(1, 1)  # Campo di testo
        save_layout.setColumnStretch(2, 0)  # Pulsante
        
        layout.addWidget(save_section)
        
        # ===== SEZIONE ANTEPRIMA URL =====
        url_section = QGroupBox("URL di Download")
        url_section.setStyleSheet("QGroupBox { font-weight: bold; }")
        url_layout = QVBoxLayout(url_section)
        
        self.url_preview = QLabel()
        self.url_preview.setStyleSheet("font-family: monospace; padding: 8px; background-color: #f8f8f8; border: 1px solid #ddd; border-radius: 4px;")
        self.url_preview.setWordWrap(True)
        url_layout.addWidget(self.url_preview)
        
        layout.addWidget(url_section)
        
        # ===== BARRA DI AVANZAMENTO =====
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("QProgressBar { border: 1px solid #bdbdbd; border-radius: 4px; text-align: center; } "
                                       "QProgressBar::chunk { background-color: #4CAF50; }")
        layout.addWidget(self.progress_bar)
        
        # ===== PULSANTI =====
        buttons_layout = QHBoxLayout()
        
        # Pulsante Chiudi
        self.close_button = QPushButton("Chiudi")
        self.close_button.setIcon(QIcon(":/qt-project.org/styles/commonstyle/images/standardbutton-closetab-16.png"))
        self.close_button.setStyleSheet("padding: 8px 15px;")
        self.close_button.clicked.connect(self.reject)
        buttons_layout.addWidget(self.close_button)
        
        # Aggiunge spaziatore
        buttons_layout.addStretch(1)
        
        # Pulsante Scarica
        self.download_button = QPushButton("Scarica")
        download_icon = QIcon(":/images/themes/default/downloading_svg.svg")
        self.download_button.setIcon(download_icon)
        self.download_button.setIconSize(QSize(24, 24))
        self.download_button.setStyleSheet("background-color: #4CAF50; color: white; font-size: 14px; "
                                          "font-weight: bold; padding: 10px 20px; border-radius: 4px;")
        self.download_button.setMinimumWidth(150)
        self.download_button.setMinimumHeight(40)
        self.download_button.clicked.connect(self.download_boundaries)
        buttons_layout.addWidget(self.download_button)
        
        layout.addLayout(buttons_layout)
        
        # Configura connessioni per aggiornare l'anteprima URL
        self.date_combo.currentIndexChanged.connect(self.update_url_preview)
        self.type_combo.currentIndexChanged.connect(self.update_url_preview)
        self.format_combo.currentIndexChanged.connect(self.update_url_preview)
        self.format_combo.currentIndexChanged.connect(self.update_format_notes)
        self.type_combo.currentIndexChanged.connect(self.update_region_filter_visibility)
        
        # Inizializza anteprima URL
        self.update_url_preview()
        
        # Dopo aver creato il form_container e impostato il layout principale
        # ma prima di completare la configurazione, crea il filtro province
        # self.create_province_filter()
        form_grid.addWidget(self.province_filter_container, 3, 0, 1, 2)
        
        # Aggiorna la visibilità dei filtri in base alla selezione iniziale
        self.update_region_filter_visibility()
        
        # Imposta il layout del dialogo
        self.setLayout(layout)
        
        # Inizializza il percorso di salvataggio alla cartella Documenti dell'utente
        self.download_path = os.path.join(os.path.expanduser('~'), 'Documents')
        self.save_path_edit.setText(self.download_path)
        
        # Imposta dimensione minima dialogo
        self.setMinimumWidth(550)
        self.setMinimumHeight(580)

    def create_header_section(self):
        """Crea la sezione intestazione con logo e titolo"""
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 10)
        
        # Logo
        icon_label = QLabel()
        icon_pixmap = QIcon(os.path.join(self.plugin_dir, "icon.png")).pixmap(88, 88)
        icon_label.setPixmap(icon_pixmap)
        
        # Titolo e descrizione
        text_layout = QVBoxLayout()
        
        # Titolo principale
        title_label = QLabel("ISTAT Boundaries Downloader (EPSG:4326)")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #2E7D32;")
        
        # Descrizione con collegamento ipertestuale
        description_layout = QHBoxLayout()
        description_layout.setContentsMargins(0, 5, 0, 0)
        info_text = QLabel("Scarica confini amministrativi italiani ISTAT usando le ")
        info_text.setStyleSheet("font-size: 13px;")
        
        link_label = QLabel("<a href='https://www.confini-amministrativi.it/'>API onData</a>")
        link_label.setOpenExternalLinks(True)
        link_label.setStyleSheet("font-size: 13px;")
        
        description_layout.addWidget(info_text)
        description_layout.addWidget(link_label)
        description_layout.addStretch(1)
        
        text_layout.addWidget(title_label)
        text_layout.addLayout(description_layout)
        
        # Aggiunge al layout intestazione
        header_layout.addWidget(icon_label)
        header_layout.addLayout(text_layout, 1)
        
        return header_layout

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
            QMessageBox.critical(
                self, 
                "API non disponibile", 
                f"Il servizio API non è disponibile per questa richiesta.\n\nURL: {url}\n\n"
                "Il problema potrebbe essere temporaneo o la combinazione di data e confini richiesta non è supportata dalle API."
            )

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
            selected_type = self.type_combo.currentText()
            boundary_type = self.boundary_types[selected_type]
            file_format = self.formats[self.format_combo.currentText()]
            save_only = self.save_only_check.isChecked()
            
            # Gestione URL con filtro regione
            if (selected_type == "Regioni" and 
                self.region_filter_container.isVisible() and 
                self.region_combo.count() > 0 and 
                self.region_combo.currentText() != "Caricamento regioni..." and
                self.region_combo.currentText() != "Errore nel caricare le regioni"):
                
                # Ottieni il codice della regione selezionata
                region_code = self.region_combo.currentData()
                region_name = self.region_combo.currentText()
                
                # Determina quale tipo di dati scaricare (province o comuni)
                if self.region_data_combo.currentText() == "Province della regione":
                    # URL per le province della regione selezionata
                    boundary_type = f"regioni/{region_code}/unita-territoriali-sovracomunali"
                    display_type = f"province della regione {region_name}"
                else:
                    # URL per i comuni della regione selezionata
                    boundary_type = f"regioni/{region_code}/comuni"
                    display_type = f"comuni della regione {region_name}"
            
            # Gestione URL con filtro provincia
            elif (selected_type == "Unità Territoriali Sovracomunali (Province)" and
                hasattr(self, 'province_filter_container') and
                self.province_filter_container.isVisible() and 
                self.province_combo.count() > 0 and 
                self.province_combo.currentText() != "Caricamento province..." and
                self.province_combo.currentText() != "Errore nel caricare le province" and
                self.province_comuni_check.isChecked()):
                
                # Ottieni il codice e il nome della provincia selezionata
                province_code = self.province_combo.currentData()
                province_name = self.province_combo.currentText().split('-', 1)[1] if '-' in self.province_combo.currentText() else self.province_combo.currentText()
                
                # URL per i comuni della provincia selezionata
                boundary_type = f"unita-territoriali-sovracomunali/{province_code}/comuni"
                display_type = f"comuni della provincia di {province_name}"
            else:
                display_type = boundary_type
            
            # Verifica che la cartella di destinazione esista
            if not os.path.exists(self.download_path):
                os.makedirs(self.download_path)
            
            # Construct the URL
            url = f"{self.base_url}{date_str}/{boundary_type}.{file_format}"
            
            # First check if the URL exists
            if not self.check_url_exists(url):
                QApplication.restoreOverrideCursor()
                self.progress_bar.setVisible(False)
                QMessageBox.critical(
                    self, 
                    "API non disponibile", 
                    f"Il servizio API non è disponibile per questa richiesta.\n\nURL: {url}\n\n"
                    "Il problema potrebbe essere temporaneo o la combinazione di data e confini richiesta non è supportata dalle API."
                )
                return
            
            self.progress_bar.setValue(20)
            
            # Create a temporary directory for extraction and processing
            temp_dir = tempfile.mkdtemp()
            
            # Crea un nome di file temporaneo sicuro, che non contenga slash
            # Sostituisci gli slash nel boundary_type con underscore per il percorso locale
            safe_boundary_name = boundary_type.replace('/', '_')
            temp_file_path = os.path.join(temp_dir, f"{safe_boundary_name}.{file_format}")
            
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
            
            # Crea nome file di destinazione (utilizzando il nome sicuro)
            file_name = f"ISTAT_{safe_boundary_name}_{date_str}"
            
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
                
                if (selected_type == "Unità Territoriali Sovracomunali (Province)" and
                    hasattr(self, 'province_filter_container') and
                    self.province_filter_container.isVisible() and 
                    self.province_combo.count() > 0 and 
                    self.province_combo.currentText() != "Caricamento province..." and
                    self.province_combo.currentText() != "Errore nel caricare le province" and
                    self.province_comuni_check.isChecked()):
                
                    # Ottieni il codice e il nome della provincia selezionata
                    province_code = self.province_combo.currentData()
                    province_name = self.province_combo.currentText().split('-', 1)[1] if '-' in self.province_combo.currentText() else self.province_combo.currentText()
                    
                    # URL per i comuni della provincia selezionata
                    boundary_type = f"unita-territoriali-sovracomunali/{province_code}/comuni"
                    display_type = f"comuni della provincia di {province_name}"
                else:
                    display_type = boundary_type
                
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
            
    def update_region_filter_visibility(self):
        """Mostra/nascondi il filtro regione o provincia in base al tipo di confine selezionato"""
        current_type = self.type_combo.currentText()
        
        # Determina quale tipo di filtro mostrare
        show_region_filter = (current_type == "Regioni")
        show_province_filter = (current_type == "Unità Territoriali Sovracomunali (Province)")
        
        # Gestisci il filtro regione
        self.region_filter_container.setVisible(show_region_filter)
        
        # Gestisci il filtro provincia (da implementare)
        if hasattr(self, 'province_filter_container'):
            self.province_filter_container.setVisible(show_province_filter)
        else:
            # Prima volta - creazione del container per il filtro provincia
            self.create_province_filter()
            self.province_filter_container.setVisible(show_province_filter)
        
        # Se stiamo mostrando il filtro regione, popolalo con i dati
        if show_region_filter:
            self.populate_region_combo()
        
        # Se stiamo mostrando il filtro provincia, popolalo con i dati
        if show_province_filter:
            self.populate_province_combo()
        
        # Aggiorna l'URL preview
        self.update_url_preview()
        
        # Ridimensiona automaticamente il dialogo per adattarsi al contenuto
        self.adjustSize()
        
        # Imposta un'altezza minima per evitare ridimensionamenti troppo piccoli
        if show_region_filter or show_province_filter:
            self.setMinimumHeight(580) # Altezza con filtri visibili
        else:
            self.setMinimumHeight(480) # Altezza con filtri nascosti
    
    def populate_region_combo(self):
        """Popola il combo box delle regioni"""
        # Svuota prima il combo
        self.region_combo.clear()
        
        try:
            # Mappa statica delle regioni italiane (rispecchia la struttura dell'ISTAT)
            regioni_istat = {
                '1': 'Piemonte',
                '2': 'Valle d\'Aosta',
                '3': 'Lombardia',
                '4': 'Trentino-Alto Adige',
                '5': 'Veneto',
                '6': 'Friuli-Venezia Giulia',
                '7': 'Liguria',
                '8': 'Emilia-Romagna',
                '9': 'Toscana',
                '10': 'Umbria',
                '11': 'Marche',
                '12': 'Lazio',
                '13': 'Abruzzo',
                '14': 'Molise',
                '15': 'Campania',
                '16': 'Puglia',
                '17': 'Basilicata',
                '18': 'Calabria',
                '19': 'Sicilia',
                '20': 'Sardegna'
            }
            
            # Ottieni la data corrente selezionata
            date_str = self.date_combo.currentText()
            
            # Imposta un placeholder mentre carica
            self.region_combo.addItem("Caricamento regioni...")
            QApplication.processEvents()
            
            # Verifica se l'URL delle regioni è disponibile
            regions_url = f"{self.base_url}{date_str}/regioni.csv"
            url_disponibile = self.check_url_exists(regions_url)
            
            if url_disponibile:
                # Scarica e leggi il CSV per verificare quali regioni sono disponibili
                temp_file, _ = urllib.request.urlretrieve(regions_url)
                available_regions = set()  # Set per tenere traccia dei codici regione disponibili
                
                with open(temp_file, 'r', encoding='utf-8') as f:
                    # Salta l'intestazione
                    next(f)
                    for line in f:
                        parts = line.strip().split(',')
                        if len(parts) >= 2:
                            # Assume che il formato sia: cod_reg,nome_reg,...
                            cod_reg = parts[0].strip('"')
                            available_regions.add(cod_reg)
                
                # Svuota il combo
                self.region_combo.clear()
                
                # Aggiungi le regioni in ordine numerico di codice regione
                for cod_reg in sorted(regioni_istat.keys(), key=int):
                    # Verifica se questa regione è disponibile nel dataset
                    if cod_reg in available_regions or not available_regions:  # se non ci sono regioni disponibili, mostra tutte
                        nome_reg = regioni_istat[cod_reg]
                        # Formatta in modo chiaro e leggibile
                        self.region_combo.addItem(f"{nome_reg}", cod_reg)
            else:
                # Se il CSV non è disponibile, usa direttamente la mappa statica
                self.region_combo.clear()
                for cod_reg, nome_reg in sorted(regioni_istat.items(), key=lambda x: int(x[0])):
                    self.region_combo.addItem(f"{nome_reg}", cod_reg)
            
            # Aggiungi connessione per aggiornare l'URL quando cambia regione
            self.region_combo.currentIndexChanged.connect(self.update_url_preview)
            self.region_data_combo.currentIndexChanged.connect(self.update_url_preview)
            
        except Exception as e:
            QgsMessageLog.logMessage(f"Errore nel caricare le regioni: {str(e)}", "ISTAT Downloader", Qgis.Critical)
            self.region_combo.clear()
            self.region_combo.addItem("Errore nel caricare le regioni")
    
    def update_url_preview(self):
        """Aggiorna l'anteprima URL in base alle opzioni selezionate"""
        try:
            date_str = self.date_combo.currentText()
            selected_type = self.type_combo.currentText()
            boundary_type = self.boundary_types[selected_type]
            file_format = self.formats[self.format_combo.currentText()]
            
            # Gestione URL con filtro regione
            if (selected_type == "Regioni" and 
                self.region_filter_container.isVisible() and 
                self.region_combo.count() > 0 and 
                self.region_combo.currentText() != "Caricamento regioni..." and
                self.region_combo.currentText() != "Errore nel caricare le regioni"):
                
                # Ottieni il codice della regione selezionata
                region_code = self.region_combo.currentData()
                
                # Determina quale tipo di dati scaricare (province o comuni)
                if self.region_data_combo.currentText() == "Province della regione":
                    # URL per le province della regione selezionata
                    boundary_type = f"regioni/{region_code}/unita-territoriali-sovracomunali"
                else:
                    # URL per i comuni della regione selezionata
                    boundary_type = f"regioni/{region_code}/comuni"
            
            # Gestione URL con filtro provincia
            elif (selected_type == "Unità Territoriali Sovracomunali (Province)" and 
                hasattr(self, 'province_filter_container') and
                self.province_filter_container.isVisible() and 
                self.province_combo.count() > 0 and 
                self.province_combo.currentText() != "Caricamento province..." and
                self.province_combo.currentText() != "Errore nel caricare le province" and
                self.province_comuni_check.isChecked()):
                
                # Ottieni il codice della provincia selezionata
                province_code = self.province_combo.currentData()
                
                # URL per i comuni della provincia selezionata
                boundary_type = f"unita-territoriali-sovracomunali/{province_code}/comuni"
            
            # Costruisce l'URL completo
            url = f"{self.base_url}{date_str}/{boundary_type}.{file_format}"
            
            # Aggiorna l'etichetta di anteprima con URL formattato
            self.url_preview.setText(url)
            
        except Exception as e:
            self.url_preview.setText(f"Errore nell'aggiornare l'URL: {str(e)}")
    
    def create_province_filter(self):
        """Crea e configura il container per il filtro province"""
        # Container per filtro province
        self.province_filter_container = QWidget()
        province_grid = QGridLayout(self.province_filter_container)
        province_grid.setContentsMargins(0, 0, 0, 0)
        province_grid.setSpacing(10)
        # Aggiungi controllo specifico sull'espansione
        province_grid.setColumnMinimumWidth(1, 300)
        # province_grid.setColumnMaximumWidth(1, 300)

        # Campo di ricerca provincia
        search_label = QLabel("Cerca provincia:")
        search_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        search_label.setFixedWidth(200)
        
        # Nuova configurazione con dimensione esplicita
        self.province_search = QLineEdit()
        self.province_search.setPlaceholderText("Digita per cercare una provincia...")
        self.province_search.setClearButtonEnabled(True)  # Aggiunge un pulsante X per cancellare
        self.province_search.textChanged.connect(self.filter_provinces)
        
        # MODIFICA: Imposta la larghezza minima identica al combobox regioni
        self.province_search.setMinimumWidth(300)
        self.province_search.setMaximumWidth(300)
        
        province_grid.addWidget(search_label, 0, 0)
        province_grid.addWidget(self.province_search, 0, 1)
        
        # Selezione provincia
        province_label = QLabel("Filtro provincia:")
        province_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        province_label.setFixedWidth(200)
        
        # MODIFICA: Configurazione provincia combo uniforme
        self.province_combo = QComboBox()
        self.province_combo.setMinimumWidth(300)
        self.province_combo.setMaximumWidth(300)
        
        province_grid.addWidget(province_label, 1, 0)
        province_grid.addWidget(self.province_combo, 1, 1)
        
        # Checkbox per mostrare solo i comuni della provincia
        self.province_comuni_check = QCheckBox("Scarica solo comuni di questa provincia")
        self.province_comuni_check.setChecked(False)  # Default: non selezionato
        province_grid.addWidget(self.province_comuni_check, 2, 1)
        
        # Nascondi il container all'inizio
        self.province_filter_container.setVisible(False)
        
        # MODIFICA: Imposta le proporzioni delle colonne in modo uniforme
        province_grid.setColumnStretch(0, 0)  # Prima colonna (labels) non si espande
        province_grid.setColumnStretch(1, 1)  # Seconda colonna (inputs) si espande
        
        # Aggiungi le connessioni per aggiornare l'URL
        self.province_combo.currentIndexChanged.connect(self.update_url_preview)
        self.province_comuni_check.toggled.connect(self.update_url_preview)

    def filter_provinces(self, text):
        """Filtra le province in base al testo di ricerca"""
        # Memorizza la selezione corrente (se presente)
        current_data = self.province_combo.currentData() if self.province_combo.currentIndex() >= 0 else None
        
        # Memorizza tutte le province in un attributo di classe se non esiste già
        if not hasattr(self, 'all_provinces') or not self.all_provinces:
            self.all_provinces = []
            for i in range(self.province_combo.count()):
                self.all_provinces.append({
                    'text': self.province_combo.itemText(i),
                    'data': self.province_combo.itemData(i)
                })
        
        # Blocca segnali per evitare di attivare callback durante l'aggiornamento
        self.province_combo.blockSignals(True)
        self.province_combo.clear()
        
        # Aggiungi le province che corrispondono al criterio di ricerca
        search_text = text.lower()
        found_provinces = []
        for province in self.all_provinces:
            if search_text in province['text'].lower():
                found_provinces.append(province)
        
        # Ordina le province trovate per numero di provincia
        for province in sorted(found_provinces, key=lambda x: int(x['text'].split('-')[0]) if x['text'][0].isdigit() else 999):
            self.province_combo.addItem(province['text'], province['data'])
        
        # Ripristina la selezione precedente se possibile
        if current_data is not None:
            for i in range(self.province_combo.count()):
                if self.province_combo.itemData(i) == current_data:
                    self.province_combo.setCurrentIndex(i)
                    break
        
        # Sblocca i segnali
        self.province_combo.blockSignals(False)
        
        # Se c'è solo una corrispondenza, selezionala automaticamente
        if self.province_combo.count() == 1:
            self.province_combo.setCurrentIndex(0)
        
        # Aggiorna l'anteprima dell'URL in base alla nuova selezione
        self.update_url_preview()
    
    def populate_province_combo(self):
        """Popola il combo box delle province"""
        # Svuota prima il combo
        self.province_combo.clear()
        
        # Pulisci anche la cache delle province
        self.all_provinces = []
        
        # Svuota il campo di ricerca
        if hasattr(self, 'province_search'):
            self.province_search.clear()
        
        # Mappa statica delle province italiane con formato "Codice-Nome"
        province_predefinite = [
            '1-Torino', '2-Vercelli', '3-Novara', '4-Cuneo', '5-Asti', '6-Alessandria', '7-Aosta', '8-Imperia', 
            '9-Savona', '10-Genova', '11-La Spezia', '12-Varese', '13-Como', '14-Sondrio', '15-Milano', '16-Bergamo', 
            '17-Brescia', '18-Pavia', '19-Cremona', '20-Mantova', '21-Bolzano', '22-Trento', '23-Verona', '24-Vicenza', 
            '25-Belluno', '26-Treviso', '27-Venezia', '28-Padova', '29-Rovigo', '30-Udine', '31-Gorizia', '32-Trieste', 
            '33-Piacenza', '34-Parma', '35-Reggio nell\'Emilia', '36-Modena', '37-Bologna', '38-Ferrara', '39-Ravenna', 
            '40-Forlì-Cesena', '41-Pesaro e Urbino', '42-Ancona', '43-Macerata', '44-Ascoli Piceno', '45-Massa Carrara',
            '46-Lucca', '47-Pistoia', '48-Firenze', '49-Livorno', '50-Pisa', '51-Arezzo', '52-Siena', '53-Grosseto', 
            '54-Perugia', '55-Terni', '56-Viterbo', '57-Rieti', '58-Roma', '59-Latina', '60-Frosinone', '61-Caserta',
            '62-Benevento', '63-Napoli', '64-Avellino', '65-Salerno', '66-L\'Aquila', '67-Teramo', '68-Pescara', 
            '69-Chieti', '70-Campobasso', '71-Foggia', '72-Bari', '73-Taranto', '74-Brindisi', '75-Lecce', '76-Potenza', 
            '77-Matera', '78-Cosenza', '79-Catanzaro', '80-Reggio di Calabria', '81-Trapani', '82-Palermo', '83-Messina', 
            '84-Agrigento', '85-Caltanissetta', '86-Enna', '87-Catania', '88-Ragusa', '89-Siracusa', '90-Sassari', 
            '91-Nuoro', '92-Cagliari', '93-Pordenone', '94-Isernia', '95-Oristano', '96-Biella', '97-Lecco', '98-Lodi', 
            '99-Rimini', '100-Prato', '101-Crotone', '102-Vibo Valentia', '103-Verbano-Cusio-Ossola', '108-Monza e della Brianza', 
            '109-Fermo', '110-Barletta-Andria-Trani', '111-Sud Sardegna'
        ]
        
        # Crea un dizionario per lookup veloce
        province_dict = {}
        for prov in province_predefinite:
            parts = prov.split('-', 1)
            if len(parts) == 2:
                cod_prov = parts[0]
                nome_prov = parts[1]
                province_dict[cod_prov] = nome_prov
        
        # Imposta un placeholder mentre carica
        self.province_combo.addItem("Caricamento province...")
        QApplication.processEvents()
        
        try:
            # Ottieni la data corrente selezionata
            date_str = self.date_combo.currentText()
            
            # Verifica se l'URL delle province è disponibile
            provinces_url = f"{self.base_url}{date_str}/unita-territoriali-sovracomunali.csv"
            url_disponibile = self.check_url_exists(provinces_url)
            
            # Usa sempre la lista predefinita che è più leggibile
            self.province_combo.clear()
            
            # Se l'URL esiste, carica solo i codici e poi usa il dizionario per i nomi
            province_attive = set()  # Set per monitorare quali province sono attive sul server
            if url_disponibile:
                try:
                    # Scarica e leggi il CSV solo per conoscere quali province sono attualmente disponibili nell'API
                    temp_file, _ = urllib.request.urlretrieve(provinces_url)
                    
                    with open(temp_file, 'r', encoding='utf-8') as f:
                        # Salta l'intestazione
                        next(f)
                        for line in f:
                            parts = line.strip().split(',')
                            if len(parts) >= 1:
                                cod_prov = parts[0].strip('"')
                                province_attive.add(cod_prov)
                except:
                    # Se c'è un errore nel processare il CSV, usa tutte le province
                    pass
            
            # Aggiungi le province in ordine dalla lista predefinita
            for prov in sorted(province_predefinite, key=lambda x: int(x.split('-')[0])):
                parts = prov.split('-', 1)
                if len(parts) == 2:
                    cod_prov = parts[0]
                    nome_prov = parts[1]
                    
                    # Se stiamo filtrando in base alle province attive e questa provincia non è attiva, salta
                    if url_disponibile and len(province_attive) > 0 and cod_prov not in province_attive:
                        continue
                        
                    # Formatta in modo chiaro e leggibile
                    self.province_combo.addItem(f"{cod_prov}-{nome_prov}", cod_prov)
        
        except Exception as e:
            QgsMessageLog.logMessage(f"Errore nel caricare le province: {str(e)}", "ISTAT Downloader", Qgis.Critical)
            
            # In caso di errore, mostra comunque la lista predefinita
            self.province_combo.clear()
            for prov in sorted(province_predefinite, key=lambda x: int(x.split('-')[0])):
                parts = prov.split('-', 1)
                if len(parts) == 2:
                    cod_prov = parts[0]
                    nome_prov = parts[1]
                    self.province_combo.addItem(f"{cod_prov}-{nome_prov}", cod_prov)
        
        # Aggiungi connessioni per aggiornare l'URL
        self.province_combo.currentIndexChanged.connect(self.update_url_preview)
        self.province_comuni_check.toggled.connect(self.update_url_preview)
        
        # Alla fine del metodo, dopo aver popolato il combobox:
        # Salva tutte le province per uso futuro nella funzione di filtro
        self.all_provinces = []
        for i in range(self.province_combo.count()):
            self.all_provinces.append({
                'text': self.province_combo.itemText(i),
                'data': self.province_combo.itemData(i)
            })
    
# Required methods for QGIS plugin
def classFactory(iface):
    return IstatBoundariesDownloader(iface)