# Guida al Plugin ISTAT Boundaries Downloader per QGIS

## Introduzione
ISTAT Boundaries Downloader è un plugin per QGIS che ti permette di scaricare i confini amministrativi italiani forniti dall'ISTAT (Istituto Nazionale di Statistica) tramite l'API onData. Questo strumento semplifica l'acquisizione dei dati geografici ufficiali per regioni, province, comuni e ripartizioni geografiche dell'Italia, con la possibilità di selezionare diverse date di riferimento.

## Installazione

1. Apri QGIS
2. Dal menu, seleziona **Plugin > Gestisci e installa plugin**
3. Vai alla scheda "Installa da ZIP"
4. Seleziona il file ZIP del plugin
5. Clicca su "Installa plugin"

Dopo l'installazione, troverai l'icona del plugin nella barra degli strumenti di QGIS.

## Utilizzo del Plugin

### Avvio del Plugin
Clicca sull'icona ![icona plugin](icon.png) nella barra degli strumenti o accedi dal menu **Plugin > ISTAT Boundaries Downloader**.

### Interfaccia Principale
L'interfaccia del plugin si presenta con le seguenti opzioni:

1. **Data di riferimento**: Seleziona la data di riferimento per i confini amministrativi
   - Le date disponibili vanno dal 1991 al 2024
   - Il formato è AAAAMMGG (Anno-Mese-Giorno)

2. **Tipo di confine**: Scegli il tipo di confine amministrativo da scaricare
   - Regioni
   - Unità Territoriali Sovracomunali (Province)
   - Comuni
   - Ripartizioni Geografiche

3. **Formato**: Seleziona il formato di file desiderato
   - Shapefile (.zip)
   - GeoPackage (.gpkg)

4. **Salva in**: Specifica la cartella di destinazione dove salvare i file scaricati
   - Clicca su "Sfoglia" per selezionare una cartella diversa

5. **Solo salvataggio locale**: Se selezionato, i dati verranno solo salvati localmente senza essere caricati automaticamente in QGIS

6. **URL di download**: Visualizza l'URL che sarà utilizzato per scaricare i dati

### Funzionalità Principali

#### Download dei Confini
1. Seleziona le opzioni desiderate
2. Clicca sul pulsante "Sfoglia" per scegliere la cartella di destinazione
3. Se desiderato, seleziona l'opzione "Solo salvataggio locale"
4. Clicca sul pulsante "Scarica"
5. Il plugin scaricherà i dati e:
   - Salverà i file nella cartella specificata
   - Se non hai selezionato "Solo salvataggio locale", caricherà automaticamente il layer in QGIS

### Risultati del Download

Quando scarichi i confini amministrativi, il plugin:

1. **Per Shapefile (.zip)**:
   - Salva il file ZIP nella cartella di destinazione
   - Estrae i file nella sottocartella con un nome descrittivo
   - Carica il layer in QGIS (se l'opzione "Solo salvataggio locale" non è selezionata)

2. **Per GeoPackage (.gpkg)**:
   - Salva il file GPKG nella cartella di destinazione
   - Carica il layer in QGIS (se l'opzione "Solo salvataggio locale" non è selezionata)

## Risoluzione dei Problemi

### Risorsa non Disponibile
Se ricevi un messaggio "Risorsa non disponibile", significa che la combinazione di data e tipo di confine selezionata non esiste. Puoi:
1. Cliccare su "Sì" per visualizzare date alternative suggerite
2. Scegliere una delle date suggerite e riprovare

### Altri Errori
In caso di errori durante il download o l'elaborazione dei file:
1. Controlla la tua connessione Internet
2. Verifica di avere i permessi necessari per scrivere nella cartella di destinazione
3. Consulta il log di QGIS (Menu > Visualizza > Pannelli > Log Messaggi) per dettagli sull'errore

## Riferimenti
I dati sono forniti dall'API onData disponibile su [www.confini-amministrativi.it](https://www.confini-amministrativi.it/)

---

*Plugin sviluppato da Totò Fiandaca - pigrecoinfinito@gmail.com*