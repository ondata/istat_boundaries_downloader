# -*- coding: utf-8 -*-
"""
/***************************************************************************
 ISTAT Boundaries Downloader - Help Dialog
 ***************************************************************************/
"""

from qgis.PyQt.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QTextBrowser
from qgis.PyQt.QtCore import QSize
from qgis.PyQt.QtGui import QIcon


HELP_HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body { font-family: Arial, sans-serif; font-size: 13px; color: #222; margin: 10px 16px; }
  h1 { font-size: 18px; color: #2E7D32; margin-bottom: 4px; }
  h2 { font-size: 14px; color: #2E7D32; margin-top: 18px; margin-bottom: 4px; border-bottom: 1px solid #c8e6c9; padding-bottom: 2px; }
  h3 { font-size: 13px; color: #388E3C; margin-top: 12px; margin-bottom: 2px; }
  p, li { line-height: 1.55; margin: 4px 0; }
  ul { padding-left: 20px; }
  code { background: #f0f4f0; padding: 1px 4px; border-radius: 3px; font-size: 12px; }
  .note { background: #fff8e1; border-left: 4px solid #FFC107; padding: 6px 10px; margin: 8px 0; border-radius: 0 4px 4px 0; }
  .tip  { background: #e8f5e9; border-left: 4px solid #4CAF50; padding: 6px 10px; margin: 8px 0; border-radius: 0 4px 4px 0; }
  table { border-collapse: collapse; width: 100%; margin: 8px 0; }
  th { background: #e8f5e9; color: #2E7D32; text-align: left; padding: 5px 8px; }
  td { padding: 4px 8px; border-bottom: 1px solid #e0e0e0; }
</style>
</head>
<body>

<h1>ISTAT Boundaries Downloader</h1>
<p>Plugin QGIS per scaricare i confini amministrativi italiani (ISTAT) tramite le <a href="https://www.confini-amministrativi.it/">API onData</a>.</p>

<h2>Avvio rapido</h2>
<ol>
  <li>Clicca sull'icona del plugin nella barra degli strumenti (o dal menu <b>Plugin → ISTAT Boundaries Downloader</b>)</li>
  <li>Scegli la <b>data di riferimento</b></li>
  <li>Scegli il <b>tipo di confine</b></li>
  <li>Scegli il <b>formato</b> di output</li>
  <li>Seleziona la <b>cartella di destinazione</b> con "Sfoglia"</li>
  <li>Clicca <b>Scarica</b></li>
</ol>

<h2>Campi del dialogo</h2>

<h3>Data di riferimento</h3>
<p>Seleziona l'anno di validità dei confini. Il catalogo copre dal <b>1991</b> al <b>2026</b>.
Non tutte le combinazioni data/tipo sono disponibili: l'URL di anteprima viene aggiornato in tempo reale.</p>

<h3>Tipo di confine amministrativo</h3>
<table>
  <tr><th>Tipo</th><th>Descrizione</th></tr>
  <tr><td>Ripartizioni Geografiche</td><td>Nord-Ovest, Nord-Est, Centro, Sud, Isole</td></tr>
  <tr><td>Regioni</td><td>20 regioni italiane</td></tr>
  <tr><td>Unità Territoriali Sovracomunali (Province)</td><td>Province / città metropolitane</td></tr>
  <tr><td>Comuni</td><td>Tutti i comuni italiani</td></tr>
</table>

<h3>Filtro per regione</h3>
<p>Disponibile quando si seleziona <b>Regioni</b>. Attiva la checkbox per abilitarlo e scegli:</p>
<ul>
  <li><b>Province della regione</b>: scarica solo le province di quella regione</li>
  <li><b>Comuni della regione</b>: scarica solo i comuni di quella regione</li>
</ul>

<h3>Filtro per provincia</h3>
<p>Disponibile quando si seleziona <b>Province</b>. Usa il campo di ricerca per trovare la provincia e attiva la checkbox per scaricare i <b>comuni di quella provincia</b>.</p>

<h3>Formato disponibile</h3>
<table>
  <tr><th>Formato</th><th>Note</th></tr>
  <tr><td>Shapefile (.zip)</td><td>Estratto automaticamente in sottocartella</td></tr>
  <tr><td>GeoPackage (.gpkg)</td><td>File unico, consigliato</td></tr>
  <tr><td>CSV (.csv)</td><td>Solo dati tabellari, senza geometrie</td></tr>
  <tr><td>KML (.kml)</td><td>Compatibile con Google Earth</td></tr>
  <tr><td>KMZ (.kmz)</td><td>Versione compressa del KML</td></tr>
</table>

<h3>Opzioni di salvataggio</h3>
<ul>
  <li><b>Salva in</b>: cartella dove verranno salvati i file (default: Documenti)</li>
  <li><b>Solo salvataggio locale</b>: scarica il file senza caricarlo automaticamente in QGIS</li>
</ul>

<h3>URL di Download</h3>
<p>Mostra l'URL che verrà usato per il download. Clicca l'icona di copia per copiarlo negli appunti.</p>

<h2>Compatibilità</h2>
<div class="tip">Il plugin è compatibile con <b>QGIS 3.20+</b> e <b>QGIS 4.x</b> (Qt6/PyQt6).</div>

<h2>Segnalazione problemi</h2>
<p>Per segnalare bug o richiedere funzionalità:
<a href="https://github.com/ondata/confini-amministrativi-istat_qgis_plugin/issues">GitHub Issues</a></p>

<h2>Crediti</h2>
<ul>
  <li><b>Sviluppatore</b>: Totò Fiandaca (<a href="mailto:pigrecoinfinito@gmail.com">pigrecoinfinito@gmail.com</a>)</li>
  <li><b>Dati</b>: <a href="https://www.confini-amministrativi.it/">confini-amministrativi.it</a> (onData) — fonte ISTAT</li>
  <li><b>Licenza</b>: GPL v3.0</li>
</ul>

</body>
</html>
"""


class HelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Guida — ISTAT Boundaries Downloader")
        self.resize(620, 580)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        browser = QTextBrowser()
        browser.setHtml(HELP_HTML)
        browser.setOpenExternalLinks(True)
        browser.setStyleSheet("QTextBrowser { background-color: #ffffff; color: #222222; }")
        layout.addWidget(browser)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch(1)
        close_btn = QPushButton("Chiudi")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)
