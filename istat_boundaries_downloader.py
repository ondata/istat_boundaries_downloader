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

# Determina la versione di Qt
from qgis.PyQt.QtCore import QT_VERSION_STR
from qgis.core import Qgis, QgsMessageLog
QgsMessageLog.logMessage(f"ISTAT Boundaries Downloader: Usando Qt {QT_VERSION_STR}", "ISTAT Boundaries", Qgis.Info)

# Importazioni condizionali per compatibilità Qt5/Qt6
try:
    # Qt6
    from qgis.PyQt.QtGui import QAction
    from qgis.PyQt.QtCore import QSize, QTimer, Qt, QUrl
    USE_QT6 = True
except ImportError:
    # Qt5
    from qgis.PyQt.QtWidgets import QAction
    from qgis.PyQt.QtCore import QSize, QTimer, Qt, QUrl
    USE_QT6 = False

# Importazioni comuni
from qgis.PyQt.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, 
                              QLabel, QComboBox, QPushButton, 
                              QProgressBar, QMessageBox, QApplication,
                              QFileDialog, QCheckBox, QWidget, QLineEdit,
                              QFrame, QFormLayout, QGroupBox, QGridLayout)

from qgis.PyQt.QtGui import QIcon, QCursor
from qgis.core import QgsProject, QgsVectorLayer

# Funzioni helper per gestire le differenze Qt5/Qt6
def get_alignment(right=False, vcenter=False, hcenter=False, left=False):
    """Restituisce le costanti di allineamento appropriate per Qt5/Qt6"""
    if USE_QT6:
        # Qt6
        alignment = Qt.AlignmentFlag.AlignTop  # Valore predefinito
        if right:
            alignment |= Qt.AlignmentFlag.AlignRight
        if vcenter:
            alignment |= Qt.AlignmentFlag.AlignVCenter
        if hcenter:
            alignment |= Qt.AlignmentFlag.AlignHCenter
        if left:
            alignment |= Qt.AlignmentFlag.AlignLeft
        return alignment
    else:
        # Qt5
        alignment = Qt.AlignTop  # Valore predefinito
        if right:
            alignment |= Qt.AlignRight
        if vcenter:
            alignment |= Qt.AlignVCenter
        if hcenter:
            alignment |= Qt.AlignHCenter
        if left:
            alignment |= Qt.AlignLeft
        return alignment

def get_layout_direction(rtl=False):
    """Restituisce la direzione di layout appropriata per Qt5/Qt6"""
    if USE_QT6:
        return Qt.LayoutDirection.RightToLeft if rtl else Qt.LayoutDirection.LeftToRight
    else:
        return Qt.RightToLeft if rtl else Qt.LeftToRight

# Aggiungi queste funzioni helper per gestire le costanti di QFrame
def get_frame_shape(line_type="hline"):
    """Restituisce la costante appropriata per QFrame.setFrameShape"""
    if USE_QT6:
        # Qt6
        if line_type.lower() == "hline":
            return QFrame.Shape.HLine
        elif line_type.lower() == "vline":
            return QFrame.Shape.VLine
        else:
            return QFrame.Shape.NoFrame
    else:
        # Qt5
        if line_type.lower() == "hline":
            return QFrame.HLine
        elif line_type.lower() == "vline":
            return QFrame.VLine
        else:
            return QFrame.NoFrame

def get_frame_shadow(shadow_type="sunken"):
    """Restituisce la costante appropriata per QFrame.setFrameShadow"""
    if USE_QT6:
        # Qt6
        if shadow_type.lower() == "sunken":
            return QFrame.Shadow.Sunken
        elif shadow_type.lower() == "raised":
            return QFrame.Shadow.Raised
        else:
            return QFrame.Shadow.Plain
    else:
        # Qt5
        if shadow_type.lower() == "sunken":
            return QFrame.Sunken
        elif shadow_type.lower() == "raised":
            return QFrame.Raised
        else:
            return QFrame.Plain

# Per aprire URL esterni
def open_web_url(self, url):
    """Apre un URL nel browser predefinito"""
    if USE_QT6:
        from qgis.PyQt.QtGui import QDesktopServices
    else:
        from qgis.PyQt.QtCore import QDesktopServices
    
    QDesktopServices.openUrl(QUrl(url))

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
        separator.setFrameShape(get_frame_shape("hline"))
        separator.setFrameShadow(get_frame_shadow("sunken"))
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
        date_label.setAlignment(get_alignment(right=True, vcenter=True))
        self.date_combo = QComboBox()
        
        # Aggiunge date in gruppi logici
        date_recenti = ["20250101", "20240101", "20230101", "20220101", "20210101", "20200101"]
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
        type_label.setAlignment(get_alignment(right=True, vcenter=True))
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
        
        # Checkbox per attivare filtro per singola regione (riga 0)
        self.region_filter_check = QCheckBox("Filtra per singola regione")
        self.region_filter_check.setChecked(False)  # Default: NON selezionato (scarica tutta Italia)
        self.region_filter_check.setLayoutDirection(get_layout_direction(rtl=True))
        region_grid.addWidget(self.region_filter_check, 0, 1, 1, 1, get_alignment(left=True))
        
        # Selezione regione (riga 1)
        region_label = QLabel("Filtro regione:")
        region_label.setAlignment(get_alignment(right=True, vcenter=True))
        self.region_combo = QComboBox()
        self.region_combo.setMinimumWidth(300)
        region_grid.addWidget(region_label, 1, 0)
        region_grid.addWidget(self.region_combo, 1, 1)
        
        # Selezione tipo dati regione (riga 2)
        region_data_label = QLabel("Scarica:")
        region_data_label.setAlignment(get_alignment(right=True, vcenter=True))
        self.region_data_combo = QComboBox()
        self.region_data_combo.setMinimumWidth(300)
        self.region_data_combo.addItem("Province della regione")
        self.region_data_combo.addItem("Comuni della regione")
        region_grid.addWidget(region_data_label, 2, 0)
        region_grid.addWidget(self.region_data_combo, 2, 1)
        
        # Connessione per aggiornare lo stato di abilitazione del combo regione
        self.region_filter_check.toggled.connect(self.update_region_filter_state)
        
        # Nascondi il filtro regione inizialmente
        self.region_filter_container.setVisible(False)
        form_grid.addWidget(self.region_filter_container, 2, 0, 1, 2)
        
        # 4. Selezione formato (riga 4)
        format_label = QLabel("Formato disponibile:")
        format_label.setAlignment(get_alignment(right=True, vcenter=True))
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

        # Nota KML/KMZ (riga 6)
        self.kml_note = QLabel("Nota: i formati KML/KMZ sono visualizzabili in Google Earth e altri visualizzatori GIS.")
        self.kml_note.setStyleSheet("color: #2196F3; font-style: italic;")
        self.kml_note.setVisible(False)
        form_grid.addWidget(self.kml_note, 6, 1)
        
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
        save_path_label.setAlignment(get_alignment(right=True, vcenter=True))
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
        
        # Layout orizzontale per l'URL e il pulsante di copia
        url_row_layout = QHBoxLayout()
        
        self.url_preview = QLabel()
        self.url_preview.setStyleSheet("font-family: monospace; padding: 8px; background-color: #f8f8f8; border: 1px solid #ddd; border-radius: 4px;")
        self.url_preview.setWordWrap(True)
        url_row_layout.addWidget(self.url_preview)
        
        # Pulsante per copiare l'URL negli appunti
        self.copy_url_button = QPushButton()
        self.copy_url_button.setIcon(QIcon(":/images/themes/default/mActionEditCopy.svg"))
        self.copy_url_button.setToolTip("Copia URL negli appunti")
        self.copy_url_button.setFixedSize(36, 36)
        self.copy_url_button.setStyleSheet("""
            QPushButton {
                background-color: #e3f2fd; 
                border: 1px solid #90caf9; 
                border-radius: 4px;
                padding: 4px;
            }
            QPushButton:hover {
                background-color: #bbdefb;
            }
            QPushButton:pressed {
                background-color: #64b5f6;
            }
        """)
        self.copy_url_button.clicked.connect(self.copy_url_to_clipboard)
        url_row_layout.addWidget(self.copy_url_button)
        
        url_layout.addLayout(url_row_layout)
        
        # Etichetta per feedback sulla copia
        self.copy_feedback = QLabel()
        self.copy_feedback.setAlignment(Qt.AlignRight)
        self.copy_feedback.setStyleSheet("color: #4CAF50; font-style: italic; font-size: 11px;")
        self.copy_feedback.setVisible(False)
        url_layout.addWidget(self.copy_feedback)
        
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
        
        # Aggiungi le connessioni per il checkbox
        self.region_filter_check.toggled.connect(self.update_region_filter_state)
        self.region_filter_check.toggled.connect(self.update_url_preview)
        
        # Connessione ai segnali in modo compatibile
        if USE_QT6:
            # Qt6
            self.copy_url_button.clicked.connect(self.copy_url_to_clipboard)
            self.browse_button.clicked.connect(self.browse_folder)
        else:
            # Qt5 (stesso comportamento, ma è buona pratica essere espliciti)
            self.copy_url_button.clicked.connect(self.copy_url_to_clipboard)
            self.browse_button.clicked.connect(self.browse_folder)
        
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
                self.region_filter_check.isChecked() and  # Verifica se il filtro è attivato
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
            elif file_format == "kml":
                # Per KML, copialo direttamente
                dest_kml_path = os.path.join(self.download_path, f"{file_name}.kml")
                shutil.copyfile(temp_file_path, dest_kml_path)
                qgis_file_path = dest_kml_path
            elif file_format == "kmz":
                # Per KMZ, copialo direttamente
                dest_kmz_path = os.path.join(self.download_path, f"{file_name}.kmz")
                shutil.copyfile(temp_file_path, dest_kmz_path)
                
                # Per visualizzazione in QGIS, estrai il contenuto KML
                if not save_only:
                    try:
                        with zipfile.ZipFile(temp_file_path, 'r') as kmz:
                            # Estrai il file KML dal KMZ (di solito è doc.kml)
                            kml_file = None
                            for file in kmz.namelist():
                                if file.endswith('.kml'):
                                    kml_file = file
                                    break
                            
                            if kml_file:
                                kmz.extract(kml_file, temp_dir)
                                qgis_file_path = os.path.join(temp_dir, kml_file)
                            else:
                                # Se non troviamo un file KML, usa il KMZ direttamente
                                qgis_file_path = dest_kmz_path
                    except zipfile.BadZipFile:
                        QApplication.restoreOverrideCursor()
                        QMessageBox.critical(self, "Error", "Il file KMZ scaricato non è valido.")
                        return
                else:
                    qgis_file_path = dest_kmz_path
            else:
                # Per GeoPackage (.gpkg) e altri formati, copialo direttamente
                dest_path = os.path.join(self.download_path, f"{file_name}.{file_format}")
                shutil.copyfile(temp_file_path, dest_path)
                qgis_file_path = dest_path
            
            self.progress_bar.setValue(80)
            
            # Carica il layer in QGIS solo se l'utente non ha scelto "solo salvataggio"
            if not save_only:
                layer_name = f"ISTAT_{boundary_type}_{date_str}"
                
                if file_format == "csv":
                    # Per i CSV, utilizziamo un gestore specifico per dati non geografici
                    vector_layer = QgsVectorLayer(uri, layer_name, "delimitedtext")
                elif file_format in ["kml", "kmz"]:
                    # Per KML e KMZ, utilizziamo OGR
                    vector_layer = QgsVectorLayer(qgis_file_path, layer_name, "ogr")
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
        self.kml_note.setVisible("KML" in format_text or "KMZ" in format_text)
            
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
            
            # Imposta lo stato iniziale delle opzioni del filtro regione
            self.update_region_filter_state(self.region_filter_check.isChecked())
            
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
                self.region_filter_check.isChecked() and  # Verifica se il filtro è attivato
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
            
            # Salva l'URL corrente come attributo della classe
            self.current_url = url
            
            # Aggiorna l'etichetta di anteprima con URL formattato
            self.url_preview.setText(url)
            
        except Exception as e:
            self.url_preview.setText(f"Errore nell'aggiornare l'URL: {str(e)}")
            self.current_url = ""

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
        search_label.setAlignment(get_alignment(right=True, vcenter=True))
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
        province_label.setAlignment(get_alignment(right=True, vcenter=True))
        province_label.setFixedWidth(200)
        
        # MODIFICA: Configurazione provincia combo uniforme
        self.province_combo = QComboBox()
        self.province_combo.setMinimumWidth(300)
        self.province_combo.setMaximumWidth(300)
        self.province_combo.setMaxVisibleItems(15)  # Aumenta il numero di elementi visibili
        # Opzionalmente aggiungi uno stile per evidenziare la presenza di scrollbar
        self.province_combo.setStyleSheet("QComboBox { combobox-popup: 0; padding: 5px; }")
        
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
        
        # Se il testo è vuoto e abbiamo tutte le province memorizzate, ripristina l'elenco completo
        if not text and hasattr(self, 'all_provinces') and self.all_provinces:
            self.province_combo.blockSignals(True)
            self.province_combo.clear()
            
            for province in self.all_provinces:
                self.province_combo.addItem(province['text'], province['data'])
                
            # Ripristina la selezione precedente se possibile
            if current_data is not None:
                for i in range(self.province_combo.count()):
                    if self.province_combo.itemData(i) == current_data:
                        self.province_combo.setCurrentIndex(i)
                        break
                        
            self.province_combo.blockSignals(False)
            self.update_url_preview()
            return
        
        # Solo se il testo non è vuoto, effettua il filtraggio
        if text:
            # Blocca segnali per evitare di attivare callback durante l'aggiornamento
            self.province_combo.blockSignals(True)
            self.province_combo.clear()
            
            # Aggiungi le province che corrispondono al criterio di ricerca
            search_text = text.lower()
            found_provinces = []
            
            if hasattr(self, 'all_provinces') and self.all_provinces:
                for province in self.all_provinces:
                    if search_text in province['text'].lower():
                        found_provinces.append(province)
            
                # Mantieni l'ordine originale in cui le province erano nella lista
                for province in found_provinces:
                    self.province_combo.addItem(province['text'], province['data'])
            
            # Sblocca i segnali
            self.province_combo.blockSignals(False)
            
            # Se c'è solo una corrispondenza, selezionala automaticamente
            if self.province_combo.count() == 1:
                self.province_combo.setCurrentIndex(0)
            
            # Aggiorna l'anteprima dell'URL in base alla nuova selezione
            self.update_url_preview()
    
    def populate_province_combo(self):
        """Popola il combo box delle province direttamente dai dati dell'API"""
        # Svuota prima il combo
        self.province_combo.clear()
        
        # Pulisci anche la cache delle province
        self.all_provinces = []
        
        # Svuota il campo di ricerca
        if hasattr(self, 'province_search'):
            self.province_search.clear()
        
        # Imposta un placeholder mentre carica
        self.province_combo.addItem("Caricamento province...")
        QApplication.processEvents()
        
        try:
            # Ottieni la data corrente selezionata
            date_str = self.date_combo.currentText()
            
            # URL per ottenere l'elenco delle province
            provinces_url = f"{self.base_url}{date_str}/unita-territoriali-sovracomunali.csv"
            url_disponibile = self.check_url_exists(provinces_url)
            
            if not url_disponibile:
                # Se l'URL non è disponibile, mostra un messaggio
                QgsMessageLog.logMessage(f"URL province non disponibile: {provinces_url}", "ISTAT Downloader", Qgis.Warning)
                self.province_combo.clear()
                self.province_combo.addItem("Dati non disponibili per questa data")
                return
            
            # Scarica e leggi il CSV direttamente
            province_from_api = []  # Lista per memorizzare le province dal CSV
            
            try:
                temp_file, _ = urllib.request.urlretrieve(provinces_url)
                
                with open(temp_file, 'r', encoding='utf-8') as f:
                    # Salta l'intestazione
                    header_line = next(f)
                    header = header_line.strip().split(',')
                    
                    # Identifica gli indici delle colonne rilevanti
                    col_indices = {}
                    for i, col in enumerate(header):
                        col_clean = col.strip('"')
                        # Mappatura delle varie possibili denominazioni di colonne
                        if col_clean in ['cod_prov', 'cod_ut', 'cod_provincia']:
                            col_indices['cod_prov'] = i
                        elif col_clean in ['den_prov', 'den_uts', 'den_provincia']:
                            col_indices['den_prov'] = i
                        elif col_clean in ['den_pcm', 'den_ita']:
                            col_indices['den_pcm'] = i
                        elif col_clean in ['sigla_prov', 'sigla', 'sigla_provincia']:
                            col_indices['sigla'] = i
                    
                    # Se non troviamo il codice provincia, usa il primo campo
                    if 'cod_prov' not in col_indices:
                        col_indices['cod_prov'] = 0
                    
                    # Leggi tutte le righe e memorizza le province
                    for line in f:
                        parts = line.strip().split(',')
                        if len(parts) <= col_indices['cod_prov']:
                            continue  # Salta righe troppo corte
                        
                        cod_prov = parts[col_indices['cod_prov']].strip('"')
                        
                        # Cerca il nome della provincia nelle varie colonne possibili
                        nome_prov = None
                        
                        # Prima prova den_prov
                        if 'den_prov' in col_indices and len(parts) > col_indices['den_prov']:
                            nome_temp = parts[col_indices['den_prov']].strip('"')
                            if nome_temp and nome_temp != "-":
                                nome_prov = nome_temp
                        
                        # Se non trovato o è solo "-", prova den_pcm
                        if (nome_prov is None or nome_prov == "-") and 'den_pcm' in col_indices and len(parts) > col_indices['den_pcm']:
                            nome_temp = parts[col_indices['den_pcm']].strip('"')
                            if nome_temp and nome_temp != "-":
                                nome_prov = nome_temp
                        
                        # Se ancora non trovato, prova con la sigla
                        if (nome_prov is None or nome_prov == "-") and 'sigla' in col_indices and len(parts) > col_indices['sigla']:
                            nome_temp = parts[col_indices['sigla']].strip('"')
                            if nome_temp and nome_temp != "-":
                                nome_prov = nome_temp
                        
                        # Se ancora non abbiamo un nome valido, usa un valore di fallback
                        if nome_prov is None or nome_prov == "-":
                            nome_prov = f"Provincia {cod_prov}"
                        
                        # Formatta in modo chiaro e leggibile
                        display_text = f"{cod_prov}-{nome_prov}"
                        province_from_api.append((display_text, cod_prov))
                
                # Se abbiamo trovato province, usa quelle
                if province_from_api:
                    self.province_combo.clear()
                    
                    # Ordina le province per codice numerico
                    province_from_api.sort(key=lambda x: int(x[1]) if x[1].isdigit() else float('inf'))
                    
                    # Aggiungi le province dal CSV
                    for display_text, cod_prov in province_from_api:
                        self.province_combo.addItem(display_text, cod_prov)
                else:
                    self.province_combo.clear()
                    self.province_combo.addItem("Nessuna provincia trovata per questa data")
            
            except Exception as e:
                # In caso di errore, mostra un messaggio
                QgsMessageLog.logMessage(f"Errore nel processare CSV province: {str(e)}", "ISTAT Downloader", Qgis.Critical)
                self.province_combo.clear()
                self.province_combo.addItem(f"Errore: {str(e)}")
        
        except Exception as e:
            QgsMessageLog.logMessage(f"Errore generale nel caricare le province: {str(e)}", "ISTAT Downloader", Qgis.Critical)
            self.province_combo.clear()
            self.province_combo.addItem("Errore nel caricare le province")
        
        # Aggiungi connessioni per aggiornare l'URL
        self.province_combo.currentIndexChanged.connect(self.update_url_preview)
        self.province_comuni_check.toggled.connect(self.update_url_preview)
        
        # Salva tutte le province per uso futuro nella funzione di filtro
        self.all_provinces = []
        for i in range(self.province_combo.count()):
            item_text = self.province_combo.itemText(i)
            if item_text not in ["Caricamento province...", "Dati non disponibili per questa data", 
                                "Nessuna provincia trovata per questa data"]:
                self.all_provinces.append({
                    'text': item_text,
                    'data': self.province_combo.itemData(i)
                })
    
    def update_filters_on_date_change(self):
        """Aggiorna i filtri quando cambia la data"""
        # Aggiorna il filtro regioni se è visibile
        if self.region_filter_container.isVisible():
            self.populate_region_combo()
        
        # Aggiorna il filtro province se è visibile
        if hasattr(self, 'province_filter_container') and self.province_filter_container.isVisible():
            self.populate_province_combo()
    
    def copy_url_to_clipboard(self):
        """Copia l'URL corrente negli appunti del sistema"""
        if hasattr(self, 'current_url') and self.current_url:
            # Copia negli appunti
            clipboard = QApplication.clipboard()
            clipboard.setText(self.current_url)
            
            # Mostra feedback all'utente
            self.copy_feedback.setText("URL copiato negli appunti!")
            self.copy_feedback.setVisible(True)
            
            # Nascondi il messaggio dopo 2 secondi
            QTimer.singleShot(2000, lambda: self.copy_feedback.setVisible(False))
        else:
            # Nessun URL valido disponibile
            self.copy_feedback.setText("Nessun URL valido disponibile")
            self.copy_feedback.setStyleSheet("color: #F44336; font-style: italic; font-size: 11px;")
            self.copy_feedback.setVisible(True)
            
            # Nascondi il messaggio dopo 2 secondi
            QTimer.singleShot(2000, lambda: self.copy_feedback.setVisible(False))
    
    def update_region_filter_state(self, checked):
        """Aggiorna lo stato del filtro regioni in base alla checkbox"""
        # Abilita il combo delle regioni e il combo del tipo di dati solo se il filtro è attivato
        self.region_combo.setEnabled(checked)
        self.region_data_combo.setEnabled(checked)
        
        # Se il filtro è disabilitato, i campi di selezione regione diventano grigi
        if not checked:
            self.region_combo.setStyleSheet("color: #999999;")
            self.region_data_combo.setStyleSheet("color: #999999;")
        else:
            self.region_combo.setStyleSheet("")
            self.region_data_combo.setStyleSheet("")
        
        # Aggiorna l'URL preview
        self.update_url_preview()
    
# Required methods for QGIS plugin
def classFactory(iface):
    return IstatBoundariesDownloader(iface)