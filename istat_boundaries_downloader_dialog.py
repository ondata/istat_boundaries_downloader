# -*- coding: utf-8 -*-
"""
/***************************************************************************
 ISTAT Boundaries Downloader - Dialog

 This module contains the dialog UI for the ISTAT Boundaries Downloader plugin.
                              -------------------
        begin                : 2025-03-02
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
import shutil

from qgis.PyQt.QtCore import Qt, QUrl, QSize, QTimer
from qgis.PyQt.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout,
                               QLabel, QComboBox, QPushButton,
                               QProgressBar, QMessageBox, QApplication,
                               QFileDialog, QCheckBox, QWidget, QLineEdit,
                               QFrame, QFormLayout, QGroupBox, QGridLayout)
from qgis.PyQt.QtGui import QIcon, QCursor, QDesktopServices
from qgis.core import QgsProject, QgsVectorLayer, Qgis, QgsMessageLog


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
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
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
        date_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.date_combo = QComboBox()

        # Aggiunge date in gruppi logici
        date_recenti = ["20250101", "20240101", "20230101", "20220101", "20210101", "20200101"]
        date_medie = ["20190101", "20180101", "20170101", "20160101", "20150101",
                     "20140101", "20130101", "20120101", "20111009", "20100101"]
        date_vecchie = ["20060101", "20050101", "20040101", "20030101", "20020101",
                       "20011021", "19911020"]

        for date in date_recenti:
            self.date_combo.addItem(date)
        for date in date_medie:
            self.date_combo.addItem(date)
        for date in date_vecchie:
            self.date_combo.addItem(date)

        self.date_combo.setMinimumWidth(300)
        form_grid.addWidget(date_label, 0, 0)
        form_grid.addWidget(self.date_combo, 0, 1)

        # 2. Selezione tipo di confine (riga 1)
        type_label = QLabel("Tipo di confine amministrativo:")
        type_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
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
        self.region_filter_check.setLayoutDirection(Qt.LayoutDirection.RightToLeft)  # Allinea a destra
        region_grid.addWidget(self.region_filter_check, 0, 1, 1, 1, Qt.AlignmentFlag.AlignLeft)  # Allineato a sinistra

        # Selezione regione (riga 1)
        region_label = QLabel("Filtro regione:")
        region_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.region_combo = QComboBox()
        self.region_combo.setMinimumWidth(300)
        region_grid.addWidget(region_label, 1, 0)
        region_grid.addWidget(self.region_combo, 1, 1)

        # Selezione tipo dati regione (riga 2)
        region_data_label = QLabel("Scarica:")
        region_data_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
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
        format_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
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
        save_path_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
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
        self.copy_feedback.setAlignment(Qt.AlignmentFlag.AlignRight)
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

        # Inizializza anteprima URL
        self.update_url_preview()

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
        icon_pixmap = QIcon(os.path.join(self.plugin_dir, "icon.svg")).pixmap(88, 88)
        icon_label.setPixmap(icon_pixmap)

        # Titolo e descrizione
        text_layout = QVBoxLayout()

        # Titolo principale
        title_label = QLabel("ISTAT Boundaries Downloader (EPSG:4326)")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #2E7D32;")

        # Descrizione con collegamento ipertestuale
        description_layout = QHBoxLayout()
        description_layout.setContentsMargins(0, 5, 0, 0)
        info_text = QLabel("Scarica confini amministrativi italiani<br>usando le <a href='https://www.confini-amministrativi.it/'>API onData</a> (basate su dati <a href='https://www.istat.it/it/archivio/222527'>ISTAT</a>)")
        info_text.setOpenExternalLinks(True)
        info_text.setStyleSheet("font-size: 13px;")

        description_layout.addWidget(info_text)
        description_layout.addStretch(1)

        text_layout.addWidget(title_label)
        text_layout.addLayout(description_layout)

        # Aggiunge al layout intestazione
        header_layout.addWidget(icon_label)
        header_layout.addLayout(text_layout, 1)

        return header_layout

    def check_availability(self):
        """Check if the selected resource is available"""
        QApplication.setOverrideCursor(QCursor(Qt.CursorShape.WaitCursor))

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
            request = urllib.request.Request(url, method='HEAD')
            urllib.request.urlopen(request)
            return True
        except urllib.error.HTTPError as e:
            QgsMessageLog.logMessage(f"URL check failed: {url} - {str(e)}", "ISTAT Downloader", Qgis.MessageLevel.Critical)
            return False
        except Exception as e:
            QgsMessageLog.logMessage(f"URL check error: {str(e)}", "ISTAT Downloader", Qgis.MessageLevel.Critical)
            return False

    def download_boundaries(self):
        """Download and load the selected boundaries"""
        try:
            # Change cursor to wait cursor
            QApplication.setOverrideCursor(QCursor(Qt.CursorShape.WaitCursor))

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
                self.region_filter_check.isChecked() and
                self.region_combo.currentText() != "Caricamento regioni..." and
                self.region_combo.currentText() != "Errore nel caricare le regioni"):

                region_code = self.region_combo.currentData()
                region_name = self.region_combo.currentText()

                if self.region_data_combo.currentText() == "Province della regione":
                    boundary_type = f"regioni/{region_code}/unita-territoriali-sovracomunali"
                    display_type = f"province della regione {region_name}"
                else:
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

                province_code = self.province_combo.currentData()
                province_name = self.province_combo.currentText().split('-', 1)[1] if '-' in self.province_combo.currentText() else self.province_combo.currentText()
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

            temp_dir = tempfile.mkdtemp()
            safe_boundary_name = boundary_type.replace('/', '_')
            temp_file_path = os.path.join(temp_dir, f"{safe_boundary_name}.{file_format}")

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

            file_name = f"ISTAT_{safe_boundary_name}_{date_str}"

            if file_format == "zip":
                dest_zip_path = os.path.join(self.download_path, f"{file_name}.zip")
                shutil.copyfile(temp_file_path, dest_zip_path)

                try:
                    with zipfile.ZipFile(temp_file_path, 'r') as zip_ref:
                        zip_ref.extractall(temp_dir)

                    shp_files = [f for f in os.listdir(temp_dir) if f.endswith('.shp')]

                    if not shp_files:
                        QApplication.restoreOverrideCursor()
                        QMessageBox.critical(self, "Error", "Nessun shapefile trovato nell'archivio zip.")
                        return

                    qgis_file_path = os.path.join(temp_dir, shp_files[0])

                    dest_dir = os.path.join(self.download_path, file_name)
                    if not os.path.exists(dest_dir):
                        os.makedirs(dest_dir)

                    with zipfile.ZipFile(dest_zip_path, 'r') as zip_ref:
                        zip_ref.extractall(dest_dir)

                except zipfile.BadZipFile:
                    QApplication.restoreOverrideCursor()
                    QMessageBox.critical(self, "Error", "Il file scaricato non è un archivio ZIP valido.")
                    return
            elif file_format == "csv":
                dest_csv_path = os.path.join(self.download_path, f"{file_name}.csv")
                shutil.copyfile(temp_file_path, dest_csv_path)

                if not save_only:
                    uri = f"file:///{dest_csv_path}?delimiter=,"
                    qgis_file_path = uri
                else:
                    qgis_file_path = dest_csv_path
            elif file_format == "kml":
                dest_kml_path = os.path.join(self.download_path, f"{file_name}.kml")
                shutil.copyfile(temp_file_path, dest_kml_path)
                qgis_file_path = dest_kml_path
            elif file_format == "kmz":
                dest_kmz_path = os.path.join(self.download_path, f"{file_name}.kmz")
                shutil.copyfile(temp_file_path, dest_kmz_path)

                if not save_only:
                    try:
                        with zipfile.ZipFile(temp_file_path, 'r') as kmz:
                            kml_file = None
                            for file in kmz.namelist():
                                if file.endswith('.kml'):
                                    kml_file = file
                                    break

                            if kml_file:
                                kmz.extract(kml_file, temp_dir)
                                qgis_file_path = os.path.join(temp_dir, kml_file)
                            else:
                                qgis_file_path = dest_kmz_path
                    except zipfile.BadZipFile:
                        QApplication.restoreOverrideCursor()
                        QMessageBox.critical(self, "Error", "Il file KMZ scaricato non è valido.")
                        return
                else:
                    qgis_file_path = dest_kmz_path
            else:
                dest_path = os.path.join(self.download_path, f"{file_name}.{file_format}")
                shutil.copyfile(temp_file_path, dest_path)
                qgis_file_path = dest_path

            self.progress_bar.setValue(80)

            if not save_only:
                layer_name = f"ISTAT_{boundary_type}_{date_str}"

                if file_format == "csv":
                    vector_layer = QgsVectorLayer(uri, layer_name, "delimitedtext")
                elif file_format in ["kml", "kmz"]:
                    vector_layer = QgsVectorLayer(qgis_file_path, layer_name, "ogr")
                else:
                    if file_format == "zip":
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

                    province_code = self.province_combo.currentData()
                    province_name = self.province_combo.currentText().split('-', 1)[1] if '-' in self.province_combo.currentText() else self.province_combo.currentText()
                    boundary_type = f"unita-territoriali-sovracomunali/{province_code}/comuni"
                    display_type = f"comuni della provincia di {province_name}"
                else:
                    display_type = boundary_type

                if vector_layer.isValid():
                    QgsProject.instance().addMapLayer(vector_layer)
                    QgsMessageLog.logMessage(f"Dati caricati con successo: {layer_name}", "ISTAT Downloader", Qgis.MessageLevel.Info)
                else:
                    QMessageBox.critical(self, "Error", f"Il file {file_format} scaricato non è valido.")
                    self.progress_bar.setVisible(False)
                    QApplication.restoreOverrideCursor()
                    return

            self.progress_bar.setValue(100)

            if save_only:
                message = f"Dati {boundary_type} del {date_str[:4]}-{date_str[4:6]}-{date_str[6:]} scaricati con successo in:\n{self.download_path}"
            else:
                message = f"Dati {boundary_type} del {date_str[:4]}-{date_str[4:6]}-{date_str[6:]} scaricati con successo in:\n{self.download_path}\n\ne caricati nel progetto QGIS."

            QMessageBox.information(self, "Operazione completata", message)

        except Exception as e:
            QgsMessageLog.logMessage(f"Errore: {str(e)}", "ISTAT Downloader", Qgis.MessageLevel.Critical)
            QMessageBox.critical(self, "Error", f"Si è verificato un errore: {str(e)}")

        finally:
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

        show_region_filter = (current_type == "Regioni")
        show_province_filter = (current_type == "Unità Territoriali Sovracomunali (Province)")

        self.region_filter_container.setVisible(show_region_filter)

        if hasattr(self, 'province_filter_container'):
            self.province_filter_container.setVisible(show_province_filter)
        else:
            self.create_province_filter()
            self.province_filter_container.setVisible(show_province_filter)

        if show_region_filter:
            self.populate_region_combo()

        if show_province_filter:
            self.populate_province_combo()

        self.update_url_preview()

        self.adjustSize()

        if show_region_filter or show_province_filter:
            self.setMinimumHeight(580)
        else:
            self.setMinimumHeight(480)

    def populate_region_combo(self):
        """Popola il combo box delle regioni"""
        self.region_combo.clear()

        try:
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

            date_str = self.date_combo.currentText()

            self.region_combo.addItem("Caricamento regioni...")
            QApplication.processEvents()

            regions_url = f"{self.base_url}{date_str}/regioni.csv"
            url_disponibile = self.check_url_exists(regions_url)

            if url_disponibile:
                temp_file, _ = urllib.request.urlretrieve(regions_url)
                available_regions = set()

                with open(temp_file, 'r', encoding='utf-8') as f:
                    next(f)
                    for line in f:
                        parts = line.strip().split(',')
                        if len(parts) >= 2:
                            cod_reg = parts[0].strip('"')
                            available_regions.add(cod_reg)

                self.region_combo.clear()

                for cod_reg in sorted(regioni_istat.keys(), key=int):
                    if cod_reg in available_regions or not available_regions:
                        nome_reg = regioni_istat[cod_reg]
                        self.region_combo.addItem(f"{nome_reg}", cod_reg)
            else:
                self.region_combo.clear()
                for cod_reg, nome_reg in sorted(regioni_istat.items(), key=lambda x: int(x[0])):
                    self.region_combo.addItem(f"{nome_reg}", cod_reg)

            self.region_combo.currentIndexChanged.connect(self.update_url_preview)
            self.region_data_combo.currentIndexChanged.connect(self.update_url_preview)

            self.update_region_filter_state(self.region_filter_check.isChecked())

        except Exception as e:
            QgsMessageLog.logMessage(f"Errore nel caricare le regioni: {str(e)}", "ISTAT Downloader", Qgis.MessageLevel.Critical)
            self.region_combo.clear()
            self.region_combo.addItem("Errore nel caricare le regioni")

    def update_url_preview(self):
        """Aggiorna l'anteprima URL in base alle opzioni selezionate"""
        try:
            date_str = self.date_combo.currentText()
            selected_type = self.type_combo.currentText()
            boundary_type = self.boundary_types[selected_type]
            file_format = self.formats[self.format_combo.currentText()]

            if (selected_type == "Regioni" and
                self.region_filter_container.isVisible() and
                self.region_combo.count() > 0 and
                self.region_filter_check.isChecked() and
                self.region_combo.currentText() != "Caricamento regioni..." and
                self.region_combo.currentText() != "Errore nel caricare le regioni"):

                region_code = self.region_combo.currentData()

                if self.region_data_combo.currentText() == "Province della regione":
                    boundary_type = f"regioni/{region_code}/unita-territoriali-sovracomunali"
                else:
                    boundary_type = f"regioni/{region_code}/comuni"

            elif (selected_type == "Unità Territoriali Sovracomunali (Province)" and
                hasattr(self, 'province_filter_container') and
                self.province_filter_container.isVisible() and
                self.province_combo.count() > 0 and
                self.province_combo.currentText() != "Caricamento province..." and
                self.province_combo.currentText() != "Errore nel caricare le province" and
                self.province_comuni_check.isChecked()):

                province_code = self.province_combo.currentData()
                boundary_type = f"unita-territoriali-sovracomunali/{province_code}/comuni"

            url = f"{self.base_url}{date_str}/{boundary_type}.{file_format}"
            self.current_url = url
            self.url_preview.setText(url)

        except Exception as e:
            self.url_preview.setText(f"Errore nell'aggiornare l'URL: {str(e)}")
            self.current_url = ""

    def create_province_filter(self):
        """Crea e configura il container per il filtro province"""
        self.province_filter_container = QWidget()
        province_grid = QGridLayout(self.province_filter_container)
        province_grid.setContentsMargins(0, 0, 0, 0)
        province_grid.setSpacing(10)
        province_grid.setColumnMinimumWidth(1, 300)

        search_label = QLabel("Cerca provincia:")
        search_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        search_label.setFixedWidth(200)

        self.province_search = QLineEdit()
        self.province_search.setPlaceholderText("Digita per cercare una provincia...")
        self.province_search.setClearButtonEnabled(True)
        self.province_search.textChanged.connect(self.filter_provinces)
        self.province_search.setMinimumWidth(300)
        self.province_search.setMaximumWidth(300)

        province_grid.addWidget(search_label, 0, 0)
        province_grid.addWidget(self.province_search, 0, 1)

        province_label = QLabel("Filtro provincia:")
        province_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        province_label.setFixedWidth(200)

        self.province_combo = QComboBox()
        self.province_combo.setMinimumWidth(300)
        self.province_combo.setMaximumWidth(300)
        self.province_combo.setMaxVisibleItems(15)
        self.province_combo.setStyleSheet("QComboBox { combobox-popup: 0; padding: 5px; }")

        province_grid.addWidget(province_label, 1, 0)
        province_grid.addWidget(self.province_combo, 1, 1)

        self.province_comuni_check = QCheckBox("Scarica solo comuni di questa provincia")
        self.province_comuni_check.setChecked(False)
        province_grid.addWidget(self.province_comuni_check, 2, 1)

        self.province_filter_container.setVisible(False)

        province_grid.setColumnStretch(0, 0)
        province_grid.setColumnStretch(1, 1)

        self.province_combo.currentIndexChanged.connect(self.update_url_preview)
        self.province_comuni_check.toggled.connect(self.update_url_preview)

    def filter_provinces(self, text):
        """Filtra le province in base al testo di ricerca"""
        current_data = self.province_combo.currentData() if self.province_combo.currentIndex() >= 0 else None

        if not text and hasattr(self, 'all_provinces') and self.all_provinces:
            self.province_combo.blockSignals(True)
            self.province_combo.clear()

            for province in self.all_provinces:
                self.province_combo.addItem(province['text'], province['data'])

            if current_data is not None:
                for i in range(self.province_combo.count()):
                    if self.province_combo.itemData(i) == current_data:
                        self.province_combo.setCurrentIndex(i)
                        break

            self.province_combo.blockSignals(False)
            self.update_url_preview()
            return

        if text:
            self.province_combo.blockSignals(True)
            self.province_combo.clear()

            search_text = text.lower()
            found_provinces = []

            if hasattr(self, 'all_provinces') and self.all_provinces:
                for province in self.all_provinces:
                    if search_text in province['text'].lower():
                        found_provinces.append(province)

                for province in found_provinces:
                    self.province_combo.addItem(province['text'], province['data'])

            self.province_combo.blockSignals(False)

            if self.province_combo.count() == 1:
                self.province_combo.setCurrentIndex(0)

            self.update_url_preview()

    def populate_province_combo(self):
        """Popola il combo box delle province direttamente dai dati dell'API"""
        self.province_combo.clear()
        self.all_provinces = []

        if hasattr(self, 'province_search'):
            self.province_search.clear()

        self.province_combo.addItem("Caricamento province...")
        QApplication.processEvents()

        try:
            date_str = self.date_combo.currentText()
            provinces_url = f"{self.base_url}{date_str}/unita-territoriali-sovracomunali.csv"
            url_disponibile = self.check_url_exists(provinces_url)

            if not url_disponibile:
                QgsMessageLog.logMessage(f"URL province non disponibile: {provinces_url}", "ISTAT Downloader", Qgis.MessageLevel.Warning)
                self.province_combo.clear()
                self.province_combo.addItem("Dati non disponibili per questa data")
                return

            province_from_api = []

            try:
                temp_file, _ = urllib.request.urlretrieve(provinces_url)

                with open(temp_file, 'r', encoding='utf-8') as f:
                    header_line = next(f)
                    header = header_line.strip().split(',')

                    col_indices = {}
                    for i, col in enumerate(header):
                        col_clean = col.strip('"')
                        if col_clean in ['cod_prov', 'cod_ut', 'cod_provincia']:
                            col_indices['cod_prov'] = i
                        elif col_clean in ['den_prov', 'den_uts', 'den_provincia']:
                            col_indices['den_prov'] = i
                        elif col_clean in ['den_pcm', 'den_ita']:
                            col_indices['den_pcm'] = i
                        elif col_clean in ['sigla_prov', 'sigla', 'sigla_provincia']:
                            col_indices['sigla'] = i

                    if 'cod_prov' not in col_indices:
                        col_indices['cod_prov'] = 0

                    for line in f:
                        parts = line.strip().split(',')
                        if len(parts) <= col_indices['cod_prov']:
                            continue

                        cod_prov = parts[col_indices['cod_prov']].strip('"')
                        nome_prov = None

                        if 'den_prov' in col_indices and len(parts) > col_indices['den_prov']:
                            nome_temp = parts[col_indices['den_prov']].strip('"')
                            if nome_temp and nome_temp != "-":
                                nome_prov = nome_temp

                        if (nome_prov is None or nome_prov == "-") and 'den_pcm' in col_indices and len(parts) > col_indices['den_pcm']:
                            nome_temp = parts[col_indices['den_pcm']].strip('"')
                            if nome_temp and nome_temp != "-":
                                nome_prov = nome_temp

                        if (nome_prov is None or nome_prov == "-") and 'sigla' in col_indices and len(parts) > col_indices['sigla']:
                            nome_temp = parts[col_indices['sigla']].strip('"')
                            if nome_temp and nome_temp != "-":
                                nome_prov = nome_temp

                        if nome_prov is None or nome_prov == "-":
                            nome_prov = f"Provincia {cod_prov}"

                        display_text = f"{cod_prov}-{nome_prov}"
                        province_from_api.append((display_text, cod_prov))

                if province_from_api:
                    self.province_combo.clear()
                    province_from_api.sort(key=lambda x: int(x[1]) if x[1].isdigit() else float('inf'))
                    for display_text, cod_prov in province_from_api:
                        self.province_combo.addItem(display_text, cod_prov)
                else:
                    self.province_combo.clear()
                    self.province_combo.addItem("Nessuna provincia trovata per questa data")

            except Exception as e:
                QgsMessageLog.logMessage(f"Errore nel processare CSV province: {str(e)}", "ISTAT Downloader", Qgis.MessageLevel.Critical)
                self.province_combo.clear()
                self.province_combo.addItem(f"Errore: {str(e)}")

        except Exception as e:
            QgsMessageLog.logMessage(f"Errore generale nel caricare le province: {str(e)}", "ISTAT Downloader", Qgis.MessageLevel.Critical)
            self.province_combo.clear()
            self.province_combo.addItem("Errore nel caricare le province")

        self.province_combo.currentIndexChanged.connect(self.update_url_preview)
        self.province_comuni_check.toggled.connect(self.update_url_preview)

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
        if self.region_filter_container.isVisible():
            self.populate_region_combo()

        if hasattr(self, 'province_filter_container') and self.province_filter_container.isVisible():
            self.populate_province_combo()

    def copy_url_to_clipboard(self):
        """Copia l'URL corrente negli appunti del sistema"""
        if hasattr(self, 'current_url') and self.current_url:
            clipboard = QApplication.clipboard()
            clipboard.setText(self.current_url)

            self.copy_feedback.setText("URL copiato negli appunti!")
            self.copy_feedback.setVisible(True)

            QTimer.singleShot(2000, lambda: self.copy_feedback.setVisible(False))
        else:
            self.copy_feedback.setText("Nessun URL valido disponibile")
            self.copy_feedback.setStyleSheet("color: #F44336; font-style: italic; font-size: 11px;")
            self.copy_feedback.setVisible(True)

            QTimer.singleShot(2000, lambda: self.copy_feedback.setVisible(False))

    def update_region_filter_state(self, checked):
        """Aggiorna lo stato del filtro regioni in base alla checkbox"""
        self.region_combo.setEnabled(checked)
        self.region_data_combo.setEnabled(checked)

        if not checked:
            self.region_combo.setStyleSheet("color: #999999;")
            self.region_data_combo.setStyleSheet("color: #999999;")
        else:
            self.region_combo.setStyleSheet("")
            self.region_data_combo.setStyleSheet("")

        self.update_url_preview()
