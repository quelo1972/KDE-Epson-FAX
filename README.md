# KDE Epson Fax Pro

Applicazione desktop per inviare fax tramite CUPS con un'interfaccia KDE/Plasma
realizzata in PyQt6. Include rubrica, storico dettagliato, filtri e notifiche.

## Funzionalita principali
- Invio fax da PDF tramite backend CUPS (`lp` con opzione `phone=...`).
- Selezione stampante e rubrica contatti.
- Storico con filtri per data, stato e ricerca testuale.
- Azioni rapide: reinvio, annulla, apri file, apri cartella.
- Evidenziazione fax in coda oltre soglia configurabile.
- Esportazione CSV dello storico.
- Notifiche desktop tramite `notify-send`.
- Log applicativo con rotazione.

## Requisiti
- Linux con CUPS configurato.
- Python 3.x
- PyQt6
- Comandi disponibili nel PATH:
  - `lp`, `lpstat`, `cancel` (CUPS)
  - `notify-send`
  - `xdg-open`

## Installazione dipendenze (esempio)
```
python3 -m venv venv
source venv/bin/activate
pip install PyQt6
```

## Avvio
```
python3 main.py
```

## Uso rapido
1. Seleziona la stampante fax.
2. Scegli un contatto o inserisci manualmente il numero.
3. Seleziona un PDF.
4. Clicca "Invia Fax".

## Storico
Lo storico include:
- Filtri data, stato e ricerca.
- Soglia in minuti per evidenziare fax in coda/in corso.
- Colori di stato e icone.
- Colonna "Durata" e "Eta".

Scorciatoie utili:
- `Ctrl+F` ricerca
- `Ctrl+R` reinvia
- `Ctrl+D` annulla
- `Ctrl+O` apri file
- `Ctrl+Shift+O` apri cartella
- `Ctrl+C` copia cella selezionata

## Dati e log
- Database: `~/.local/share/kde-epson-fax/fax.db`
- Log: `~/.local/share/kde-epson-fax/logs/app.log`

## Struttura progetto
- `main.py`: bootstrap applicazione.
- `ui/`: interfaccia grafica.
- `core/`: logica di invio, database, rilevamento stampanti, validazioni.
- `resources/`: risorse varie (se presenti).
- `packaging/`: script o file di packaging (se presenti).

## Note su CUPS
L'app usa:
- `lp -d <printer> -o phone=<numero> <file.pdf>`
- `lpstat` per stato code
- `cancel <job_id>` per annullare

Assicurati che la stampante fax sia configurata con backend `epsonfax://`.

## Troubleshooting
Se l'invio non parte:
- Verifica `lpstat -a` e `lpstat -v`.
- Controlla che `notify-send` sia installato.
- Controlla i log in `~/.local/share/kde-epson-fax/logs/app.log`.

Se lo storico non aggiorna:
- Verifica permessi sul database in `~/.local/share/kde-epson-fax`.
- Controlla eventuali errori in console o nel log.

## Licenza
Non specificata. Se vuoi, aggiungila in `LICENSE`.
