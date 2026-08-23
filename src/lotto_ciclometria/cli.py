"""Interfaccia a riga di comando del toolkit."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Final
from zoneinfo import ZoneInfo

import anyio
import typer

from lotto_ciclometria import vista
from lotto_ciclometria.analisi import (
    filtra,
    frequenze_distanze,
    frequenze_numeri,
    frequenze_somme,
    ritardi,
)
from lotto_ciclometria.downloader import EsitoAnno, sincronizza
from lotto_ciclometria.errors import DownloadError, ParseError
from lotto_ciclometria.metodi import previsione_attiva, verifica_retroattiva
from lotto_ciclometria.models import Estrazione, Ruota
from lotto_ciclometria.parser import parse_anno
from lotto_ciclometria.store import carica, salva

app = typer.Typer(
    help="Toolkit di ciclometria sull'archivio storico del Lotto.",
    no_args_is_help=True,
    add_completion=False,
)

PRIMO_ANNO_STORICO = 1871
ESTRAZIONI_CERCHIO = 5
_FUSO_RIFERIMENTO: Final = ZoneInfo("Europe/Rome")


class Vista(StrEnum):
    """Aspetti statistici disponibili per il comando ``stats``."""

    NUMERI = "numeri"
    RITARDI = "ritardi"
    DISTANZE = "distanze"
    SOMME = "somme"


def _archivio(dir_dati: Path) -> tuple[Estrazione, ...]:
    """Carica l'archivio CSV interrompendo il comando se assente o invalido."""
    try:
        return carica(dir_dati / "archivio.csv")
    except ParseError as errore:
        vista.console.print(f"[red]{errore}[/red]")
        raise typer.Exit(code=1) from errore


@app.command()
def download(
    da: Annotated[
        int | None,
        typer.Option(
            "--da", min=PRIMO_ANNO_STORICO, help="Primo anno da sincronizzare."
        ),
    ] = None,
    a: Annotated[
        int | None,
        typer.Option(
            "--a", min=PRIMO_ANNO_STORICO, help="Ultimo anno da sincronizzare."
        ),
    ] = None,
    forza: Annotated[
        bool,
        typer.Option("--forza", help="Riscarica gli anni già presenti in cache."),
    ] = False,
    solo_build: Annotated[
        bool,
        typer.Option(
            "--solo-build",
            help="Ricostruisce il CSV dalla cache locale senza contattare la rete.",
        ),
    ] = False,
    dir_dati: Annotated[
        str,
        typer.Option(
            "--dir-dati", help="Directory dei dati (cache raw e archivio.csv)."
        ),
    ] = "data",
) -> None:
    """Sincronizza gli archivi annuali HTML e costruisce l'archivio CSV."""
    percorso_dati = Path(dir_dati)
    directory_raw = percorso_dati / "raw"
    if not solo_build:
        anni = _intervallo_anni(da, a)

        async def _scarica_tutti() -> tuple[EsitoAnno, ...]:
            return await sincronizza(directory_raw, anni=anni, forza=forza)

        try:
            esiti = anyio.run(_scarica_tutti)
        except DownloadError as errore:
            vista.console.print(f"[red]{errore}[/red]")
            raise typer.Exit(code=1) from errore
        conteggi = Counter(esito.stato for esito in esiti)
        scaricati = conteggi.get("scaricato", 0)
        invariati = conteggi.get("invariato", 0)
        omessi = conteggi.get("omesso", 0)
        dettaglio = f"{scaricati} scaricati, {invariati} invariati, {omessi} omessi"
        vista.console.print(f"Sincronizzati {len(esiti)} anni: {dettaglio}.")
    _ricostruisci_archivio(directory_raw, percorso_dati / "archivio.csv")


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
    vista.stampa_previsione(previsione_attiva(estrazioni, ruota=ruota))


def _intervallo_anni(da: int | None, a: int | None) -> list[int] | None:
    """Traduce le opzioni --da/--a nell'elenco degli anni (None = tutti)."""
    if da is None and a is None:
        return None
    inizio = PRIMO_ANNO_STORICO if da is None else da
    fine = datetime.now(tz=_FUSO_RIFERIMENTO).year if a is None else a
    if inizio > fine:
        vista.console.print(
            "[red]L'anno iniziale (--da) supera l'anno finale (--a).[/red]"
        )
        raise typer.Exit(code=1)
    return list(range(inizio, fine + 1))


def _ricostruisci_archivio(directory_raw: Path, destinazione: Path) -> None:
    """Rilegge tutta la cache raw e riscrive l'archivio CSV deduplicato."""
    percorsi = sorted(
        percorso for percorso in directory_raw.glob("*.HTM") if percorso.stem.isdigit()
    )
    if not percorsi:
        vista.console.print(
            "[yellow]Cache vuota: nessun file annuale da interpretare.[/yellow]"
        )
        raise typer.Exit(code=1)
    estrazioni: list[Estrazione] = []
    scarti_totali = 0
    for percorso in percorsi:
        anno = int(percorso.stem)
        try:
            risultato = parse_anno(
                percorso.read_text(encoding="utf-8"), anno, percorso.name
            )
        except ParseError as errore:
            vista.console.print(f"[yellow]Anno ignorato — {errore}[/yellow]")
            continue
        estrazioni.extend(risultato.estrazioni)
        scarti_totali += risultato.scarti
    riepilogo = salva(estrazioni, destinazione)
    prima = riepilogo.prima_data.isoformat() if riepilogo.prima_data else "?"
    ultima = riepilogo.ultima_data.isoformat() if riepilogo.ultima_data else "?"
    sintesi = f"{riepilogo.estrazioni} estrazioni ({prima} → {ultima})"
    scartate = f"{scarti_totali} righe scartate"
    vista.console.print(f"Archivio scritto in {destinazione}: {sintesi}, {scartate}.")


def main() -> None:
    """Punto d'ingresso installato come script ``lotto``."""
    app()


if __name__ == "__main__":
    main()
