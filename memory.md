# memory.md — Traccia di lavoro su lotto-ciclometria

> Log vivo delle modifiche, delle decisioni e dei comandi eseguiti su questo
> progetto. Aggiornato a ogni turno di lavoro.

## Contesto

Toolkit Python (uv, Python 3.13, Typer, Rich, anyio) per studiare l'archivio
storico del Lotto con tecniche di ciclometria. Modulo di previsione esistente:
**metodo della distanza 30 (Palumbo)** in `metodi.py`, con verifica retroattiva
e previsione attiva; archivio CSV completo dal 1871 (`data/archivio.csv`,
~105 000 estrazioni).

## Richiesta dell'utente (27 ago 2026)

1. Aggiungere un **file di memoria** per le previsioni.
2. Una **funzione per allineare le ultime estrazioni** (verificare le previsioni
   registrate contro le estrazioni più recenti).
3. **Simulare a una data** e verificare con le estrazioni successive
   (esempio: simulare fino a luglio 2026, verificare su agosto) per affinare
   le tecniche di previsione.
4. (interruzione successiva) Creare `memory.md` come traccia.

## Decisioni di design (e perché)

| Decisione | Scelta | Motivazione |
|---|---|---|
| Formato della memoria | **CSV** (`data/memoria.csv`), non JSON | Coerenza con `store.py` (archivio CSV); parsing tipizzato al confine senza `Any`; `json.loads` restituisce `Any` e basedpyright in modalità `all` lo rifiuta (testato empiricamente). |
| Chiave delle voci | `(data_riferimento, ordine ruota)` | Identifica univocamente una previsione registrata; dedupe su salvataggio (l'ultima vince). |
| Stati di una voce | `APERTA` / `CHIUSA` / `SCADUTA` | Finestra non ancora coperta dall'archivio / entrambe le ambate uscite / finestra esaurita senza entrambe le uscite. Nota: senza estrazioni della ruota giusta la voce resta `APERTA` (le altre ruote non la esauriscono). |
| Allineamento | Ricalcolo idempotente da capo sull'archivio corrente | Niente flag stale; l'operazione è ripetibile e coerente. |
| Simulazione | Nuova `verifica_periodo(..., dal, al)` in `metodi.py` | Filtra i **trigger** nel periodo (estremi inclusi) ma cerca gli esiti nei colpi successivi **anche oltre `al`** (trigger di luglio verificati con le uscite di agosto). |
| `verifica_retroattiva` | Firma **invariata** | Già testata e usata da `distanza30`; gli internals condivisi vivono in `_verifica_serie`. |
| `filtra()` | Aggiunto `al: date | None = None` (estremo **incluso**) | Backward-compatible: nessun chiamante esistente usa `al`. |
| Scrittura memoria | Provvisorio `.tmp` + `Path.replace` | Scrittura atomica, file mai corrotto a metà. |
| Riuso | `_primo_colpo` di `metodi.py` reso pubblico `primo_colpo` | Niente duplicazione della logica di ricerca dei colpi. |

## File toccati

| File | Stato | Cosa |
|---|---|---|
| `src/lotto_ciclometria/analisi.py` | ✏️ modificato | `filtra()` con `al` incluso. |
| `src/lotto_ciclometria/metodi.py` | ✏️ modificato | `verifica_periodo()`, `_verifica_serie()` condivisa, `primo_colpo()` pubblico. |
| `src/lotto_ciclometria/memoria.py` | 🆕 nuovo | `VoceMemoria`, `VoceAllineata`, `StatoVoce`, `registra()`, `allinea()`, `salva_memoria()`, `carica_memoria()` (CSV atomico). |
| `tests/test_analisi.py` | ✏️ modificato | 3 test su `filtra(al=...)`. |
| `tests/test_metodi.py` | ✏️ modificato | 4 test su `verifica_periodo` (uscita oltre il limite, inclusione di `al`, esclusione prima di `dal`, equivalenza senza limiti). |
| `tests/test_memoria.py` | 🆕 nuovo | 14 test: registra, roundtrip, file assente, intestazione/righe/campi/abbinamenti malformati, dedupe, allinea (chiusa/scaduta/aperta/altre ruote/idempotente). |
| `memory.md` | 🆕 nuovo | Questo file. |

## Comandi eseguiti

```bash
uv run pytest            # baseline 34 → ora 54 test verdi
uv run basedpyright      # 0 errori (warning pre-esistenti in test_parser.py)
uv run ruff check .      # pulito
```

## Scoperte utili nel codice

- `cli.py` è a **268 LOC puri** (sopra il tetto dei 250): prima di aggiungere i
  comandi nuovi va estratto `comandi_archivio.py` (download + helper) con il
  pattern `registra_comandi(app)`.
- La ruota va filtra per `ruota` e la serie ordinata per `chiave_ordinamento`
  = `(data, ORDINE_RUOTE.index(ruota))`.
- `date` si serializza con `isoformat()` / `fromisoformat()` (precedente in `store.py`).
- L'archivio locale arrivava al 2026-08-22 (stato pre-download).

## Da fare (prossimi passi)

- [ ] Estrarre `comandi_archivio.py` da `cli.py` (LOC).
- [ ] Comandi CLI: `simula`, `memoria`, `allinea` (+ `--scarica`), `--registra` su `distanza30`.
- [ ] `vista.py`: `stampa_memoria()`.
- [ ] README aggiornato.
- [ ] Gate finali + smoke end-to-end.

## Risultati dell'aggiornamento dati

| Azione | Esito |
|---|---|
| `uv run lotto download` | **Fallito: rete non raggiungibile** (franknet.altervista.org irraggiungibile; retry httpx esauriti). Verificato con `curl`: nessuna risposta. |
| Sincronizzazione offline | Cache `data/raw/` completa (156 file, 1871–2026); `2026.HTM` del 23/08/2026. Archivio già allineato alla cache: **ultima estrazione 2026-08-22**. Manca solo l'estrazione di martedì 25/08 (oggi 27/08 è il giorno dell'estrazione, non ancora pubblicata dal sito). |
| `uv run lotto distanza30 BARI --colpi 9` (pattern) | 2390 trigger; **ambata1 39.7%**, ambata2 40.4%, caso 40.2%. Previsione attiva: trigger 2026-08-14, ambate **44 / 89**, abbinamenti 44-14; 44-74; 89-59; 89-29. |
| Simulazione 2026-07-01 → 2026-07-31 verificata su agosto | Trigger di luglio su tutte le ruote, esiti contati fino al 22/08 (oltre `al`, come da design): |

| ruota | trigger | ambata1 | ambata2 |
|---|---|---|---|
| BARI | 7 | **5/7** | 1/7 |
| CAGLIARI | 3 | 1/3 | 1/3 |
| FIRENZE | 1 | 0/1 | 0/1 |
| GENOVA | 1 | 1/1 | 0/1 |
| MILANO | 7 | 4/7 | 3/7 |
| NAPOLI | 6 | 3/6 | 3/6 |
| PALERMO | 2 | 1/2 | 0/2 |
| ROMA | 4 | 3/4 | 3/4 |
| TORINO | 3 | 2/3 | 0/3 |
| VENEZIA | 1 | 0/1 | 1/1 |
| NAZIONALE | 4 | 1/4 | 1/4 |

Totale 39 trigger di luglio: ambata1 21/39 (53.8%) e ambata2 13/39 (33.3%)
contro un caso atteso del 40.2% per singola ambata (campione piccolo, 39
trigger: non una prova, ma il segnale più buono finora osservato va a
ambata1 su BARI/MILANO/ROMA). Il machine di simulazione funziona ed è
pronto per essere esposto come comando `lotto simula`.