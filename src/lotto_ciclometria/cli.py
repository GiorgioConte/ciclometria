"""Interfaccia a riga di comando del toolkit."""

from __future__ import annotations

import os
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Annotated

import typer

from lotto_ciclometria import db, vista
from lotto_ciclometria.analisi import (
    filtra,
    frequenze_distanze,
    frequenze_numeri,
    frequenze_somme,
    ritardi,
)
from lotto_ciclometria.comandi_archivio import registra_comandi, sincronizza_archivio
from lotto_ciclometria.errors import ParseError
from lotto_ciclometria.memoria import (
    allinea as allinea_voci,
)
from lotto_ciclometria.memoria import (
    carica_memoria,
    salva_memoria,
)
from lotto_ciclometria.memoria import (
    registra as registra_voce,
)
from lotto_ciclometria.metodi import (
    previsione_attiva,
    verifica_periodo,
    verifica_retroattiva,
)
from lotto_ciclometria.models import Estrazione, Ruota
from lotto_ciclometria.store import carica

app = typer.Typer(
    help="Toolkit di ciclometria sull'archivio storico del Lotto.",
    no_args_is_help=True,
    add_completion=False,
)
registra_comandi(app)

ESTRAZIONI_CERCHIO = 5


class Vista(StrEnum):
    """Aspetti statistici disponibili per il comando ``stats``."""

    NUMERI = "numeri"
    RITARDI = "ritardi"
    DISTANZE = "distanze"
    SOMME = "somme"


def _archivio(dir_dati: Path) -> tuple[Estrazione, ...]:
    """Carica PostgreSQL o, in assenza di URL, l'archivio CSV locale."""
    try:
        if os.environ.get("DATABASE_URL"):
            db.inizializza_schema()
            estrazioni = db.carica_estrazioni()
            if not estrazioni and (dir_dati / "archivio.csv").exists():
                db.importa_csv(dir_dati / "archivio.csv")
                estrazioni = db.carica_estrazioni()
            return estrazioni
        return carica(dir_dati / "archivio.csv")
    except ParseError as errore:
        vista.console.print(f"[red]{errore}[/red]")
        raise typer.Exit(code=1) from errore


@app.command()
def stats(
    ruota: Annotated[
        Ruota | None,
        typer.Option("--ruota", help="Limita l'analisi a una ruota (default: tutte)."),
    ] = None,
    quale_vista: Annotated[
        Vista,
        typer.Option("--vista", help="Aspetto statistico da mostrare."),
    ] = Vista.NUMERI,
    dal: Annotated[
        datetime | None,
        typer.Option(
            "--dal",
            help="Considera solo le estrazioni a partire da questa data (AAAA-MM-GG).",
        ),
    ] = None,
    limite: Annotated[
        int,
        typer.Option("--limite", min=1, help="Numero di righe da mostrare."),
    ] = 10,
    dir_dati: Annotated[
        str,
        typer.Option("--dir-dati", help="Directory dei dati."),
    ] = "data",
) -> None:
    """Statistiche classiche: frequenze, ritardi, distanze, somme caratteristiche."""
    dal_scelta = dal.date() if dal is not None else None
    selezionate = filtra(_archivio(Path(dir_dati)), ruota=ruota, dal=dal_scelta)
    if not selezionate:
        vista.console.print(
            "[yellow]Nessuna estrazione corrisponde ai filtri richiesti.[/yellow]"
        )
        raise typer.Exit(code=1)
    suffisso = f" — {ruota.value}" if ruota is not None else ""
    match quale_vista:
        case Vista.NUMERI:
            vista.stampa_frequenze(
                frequenze_numeri(selezionate),
                limite=limite,
                titolo=f"Frequenze{suffisso}",
            )
        case Vista.RITARDI:
            vista.stampa_ritardi(ritardi(selezionate), limite=limite)
        case Vista.DISTANZE:
            vista.stampa_distanze(frequenze_distanze(selezionate), limite=limite)
        case Vista.SOMME:
            vista.stampa_somme(frequenze_somme(selezionate), limite=limite)


@app.command()
def cerchio(
    ruota: Annotated[
        Ruota,
        typer.Argument(help="Ruota da rappresentare sul cerchio dei 90."),
    ],
    dir_dati: Annotated[
        str,
        typer.Option("--dir-dati", help="Directory dei dati."),
    ] = "data",
) -> None:
    """Le ultime estrazioni della ruota con i diametrali di ciascun numero."""
    selezionate = filtra(_archivio(Path(dir_dati)), ruota=ruota)[-ESTRAZIONI_CERCHIO:]
    if not selezionate:
        vista.console.print(
            f"[yellow]Nessuna estrazione presente per la ruota {ruota.value}.[/yellow]"
        )
        raise typer.Exit(code=1)
    vista.stampa_cerchio(selezionate, ruota=ruota)


@app.command()
def figure(
    ruota: Annotated[
        Ruota | None,
        typer.Option("--ruota", help="Limita a una ruota (default: tutte)."),
    ] = None,
    dal: Annotated[
        datetime | None,
        typer.Option(
            "--dal", help="Considera solo le estrazioni da questa data (AAAA-MM-GG)."
        ),
    ] = None,
    ultime: Annotated[
        int,
        typer.Option("--ultime", min=1, help="Quante estrazioni recenti analizzare."),
    ] = 10,
    dir_dati: Annotated[
        str,
        typer.Option("--dir-dati", help="Directory dei dati."),
    ] = "data",
) -> None:
    """Diametri, triangoli equilateri (lato 30) e rettangoli nelle ultime estrazioni."""
    dal_scelta = dal.date() if dal is not None else None
    selezionate = filtra(_archivio(Path(dir_dati)), ruota=ruota, dal=dal_scelta)[
        -ultime:
    ]
    if not selezionate:
        vista.console.print(
            "[yellow]Nessuna estrazione corrisponde ai filtri richiesti.[/yellow]"
        )
        raise typer.Exit(code=1)
    vista.stampa_figure(selezionate)


@app.command(name="distanza30")
def distanza30(
    ruota: Annotated[
        Ruota,
        typer.Argument(help="Ruota su cui verificare il metodo."),
    ],
    colpi: Annotated[
        int,
        typer.Option(
            "--colpi", min=1, help="Ampiezza della finestra di verifica retroattiva."
        ),
    ] = 9,
    ultimi: Annotated[
        int,
        typer.Option("--ultimi", min=1, help="Trigger recenti da elencare."),
    ] = 10,
    registra: Annotated[
        bool,
        typer.Option("--registra", help="Salva la previsione attiva in memoria."),
    ] = False,
    dir_dati: Annotated[
        str,
        typer.Option("--dir-dati", help="Directory dei dati."),
    ] = "data",
) -> None:
    """Metodo Palumbo (distanza 30): ambata metà-somma, diametrale e abbinamenti."""
    estrazioni = _archivio(Path(dir_dati))
    report = verifica_retroattiva(estrazioni, ruota=ruota, colpi=colpi)
    vista.stampa_report(report, ruota=ruota)
    vista.stampa_esiti(report.esiti, limite=ultimi)
    previsione = previsione_attiva(estrazioni, ruota=ruota)
    vista.stampa_previsione(previsione)
    if registra:
        if previsione is None:
            vista.console.print(
                "[yellow]Nessuna previsione attiva da registrare.[/yellow]"
            )
            return
        voce = registra_voce(previsione, colpi=colpi)
        if os.environ.get("DATABASE_URL"):
            db.inizializza_schema()
            voci = db.carica_memoria()
            if not voci and (Path(dir_dati) / "memoria.csv").exists():
                db.importa_memoria_csv(Path(dir_dati) / "memoria.csv")
                voci = db.carica_memoria()
            db.salva_memoria([*voci, voce])
        else:
            percorso_memoria = Path(dir_dati) / "memoria.csv"
            salva_memoria([*carica_memoria(percorso_memoria), voce], percorso_memoria)
        data_rif = previsione.data_riferimento.isoformat()
        nome_ruota = previsione.ruota.value
        messaggio = "[green]Previsione registrata in memoria ({}, {}).[/green]"
        vista.console.print(messaggio.format(data_rif, nome_ruota))


@app.command(name="simula")
def simula(  # noqa: PLR0913, PLR0917
    ruota: Annotated[
        Ruota,
        typer.Argument(help="Ruota su cui simulare il metodo."),
    ],
    dal: Annotated[
        datetime | None,
        typer.Option(
            "--dal",
            help="Primo giorno dei trigger da simulare (AAAA-MM-GG).",
        ),
    ] = None,
    al: Annotated[
        datetime | None,
        typer.Option(
            "--al",
            help="Ultimo giorno dei trigger da simulare (AAAA-MM-GG).",
        ),
    ] = None,
    colpi: Annotated[
        int,
        typer.Option(
            "--colpi", min=1, help="Ampiezza della finestra di verifica."
        ),
    ] = 9,
    ultimi: Annotated[
        int,
        typer.Option("--ultimi", min=1, help="Trigger recenti da elencare."),
    ] = 10,
    dir_dati: Annotated[
        str,
        typer.Option("--dir-dati", help="Directory dei dati."),
    ] = "data",
) -> None:
    """Simula il metodo su un periodo di trigger e verifica gli esiti."""
    estrazioni = _archivio(Path(dir_dati))
    dal_scelta = dal.date() if dal is not None else None
    al_scelta = al.date() if al is not None else None
    report = verifica_periodo(
        estrazioni,
        ruota=ruota,
        colpi=colpi,
        dal=dal_scelta,
        al=al_scelta,
    )
    vista.stampa_report(report, ruota=ruota, titolo="Simulazione")
    vista.stampa_esiti(report.esiti, limite=ultimi)


@app.command(name="memoria")
def elenco_memoria(
    dir_dati: Annotated[
        str,
        typer.Option("--dir-dati", help="Directory dei dati."),
    ] = "data",
) -> None:
    """Mostra le previsioni registrate con il loro stato di allineamento."""
    percorso_dati = Path(dir_dati)
    if os.environ.get("DATABASE_URL"):
        voci = db.carica_memoria()
        if not voci and (percorso_dati / "memoria.csv").exists():
            db.importa_memoria_csv(percorso_dati / "memoria.csv")
            voci = db.carica_memoria()
    else:
        voci = carica_memoria(percorso_dati / "memoria.csv")
    esiti = allinea_voci(voci, _archivio(percorso_dati))
    if not esiti:
        vista.console.print(
            "[yellow]Memoria vuota: usa distanza30 --registra.[/yellow]"
        )
        raise typer.Exit(code=1)
    vista.stampa_memoria(esiti)


@app.command(name="allinea")
def allinea(
    scarica: Annotated[
        bool,
        typer.Option(
            "--scarica",
            help="Aggiorna l'archivio prima di allineare.",
        ),
    ] = False,
    dir_dati: Annotated[
        str,
        typer.Option("--dir-dati", help="Directory dei dati."),
    ] = "data",
) -> None:
    """Allinea le previsioni memorizzate con le ultime estrazioni e le risalva."""
    percorso_dati = Path(dir_dati)
    if scarica:
        sincronizza_archivio(percorso_dati)
    percorso_memoria = percorso_dati / "memoria.csv"
    if os.environ.get("DATABASE_URL"):
        voci = db.carica_memoria()
        if not voci and percorso_memoria.exists():
            db.importa_memoria_csv(percorso_memoria)
            voci = db.carica_memoria()
    else:
        voci = carica_memoria(percorso_memoria)
    esiti = allinea_voci(voci, _archivio(percorso_dati))
    if not esiti:
        vista.console.print(
            "[yellow]Memoria vuota: usa distanza30 --registra.[/yellow]"
        )
        raise typer.Exit(code=1)
    if os.environ.get("DATABASE_URL"):
        db.salva_memoria(esito.voce for esito in esiti)
    else:
        salva_memoria([esito.voce for esito in esiti], percorso_memoria)
    vista.console.print("[green]Memoria riallineata.[/green]")
    vista.stampa_memoria(esiti)


def main() -> None:
    """Punto d'ingresso installato come script ``lotto``."""
    app()


if __name__ == "__main__":
    main()
