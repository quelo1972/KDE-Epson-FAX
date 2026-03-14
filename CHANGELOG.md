# Changelog
Tutte le modifiche rilevanti al progetto saranno documentate in questo file.

Il formato segue le linee guida di Keep a Changelog e Semantic Versioning.

## [v1.0.1] - 2026-03-14

### Changed
- Aggiornato il changelog con versione v1.0.

## [v1.0] - 2026-03-14

### Added
- Logging applicativo con rotazione file.
- Modulo di validazione per numeri fax e PDF.
- Storico con filtri avanzati: data, stato, ricerca testuale.
- Soglia configurabile per evidenziare fax in coda/in corso.
- Opzioni di evidenziazione con colore personalizzato.
- Colonna `Durata` e `Eta` nello storico.
- Azioni rapide nello storico: reinvia, annulla, apri file/cartella.
- Menu contestuale con copia di Job ID, numero fax e percorso file.
- Scorciatoie tastiera per ricerca e azioni rapide.
- Tooltip informativi su durate e soglie.
- Esportazione CSV estesa con `Completed At`, `Duration`, `Age`.

### Changed
- Tray unificato (evitata duplicazione tra `main.py` e `MainWindow`).
- Rilevamento stampanti con preferenza per backend fax.
- Stato `active_jobs` reso thread-safe.
- UI storico migliorata: ordinamento, legenda colori, conteggi risultati.
- Persistenza preferenze UI con `QSettings`.
- UX migliorata con indicatori di stato e icone.

### Fixed
- Risolto crash su `cellDoubleClicked` dovuto a firma errata.
- Corretto sorting numerico per `Job ID`, `Durata`, `Eta`.
- Corretto aggiornamento stato tray quando la finestra viene nascosta.

### Removed
- Modulo duplicato di rilevamento stampanti (`core/cups_detector.py`).
- File `__pycache__` tracciati accidentalmente nel repository.
