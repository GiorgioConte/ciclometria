"""Comandi di gestione dell'archivio storico (download e ricostruzione CSV)."""

from __future__ import annotations

import os
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Final
from zoneinfo import ZoneInfo

import anyio
import typer

from lotto_ciclometria import db, vista
from lotto_ciclometria.downloader import EsitoAnno, sincronizza
from lotto_ciclometria.errors import DownloadError, ParseError
from lotto_ciclometria.parser import parse_anno
from lotto_ciclometria.store import salva

if TYPE_CHECKING:
    from lotto_ciclometria.models import Estrazione

PRIMO_ANNO_STORICO = 1871
_FUSO_RIFERIMENTO: Final = ZoneInfo("Europe/Rome")


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


def sincronizza_archivio(
    percorso_dati: Path,
    *,
    da: int | None = None,
    a: int | None = None,
    forza: bool = False,
) -> None:
    """Aggiorna la cache raw da FrankNet e ricostruisce l'archivio CSV."""
    directory_raw = percorso_dati / "raw"

    async def _scarica_tutti() -> tuple[EsitoAnno, ...]:
        return await sincronizza(
            directory_raw, anni=_intervallo_anni(da, a), forza=forza
        )

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
    if os.environ.get("DATABASE_URL"):
        db.importa_csv(destinazione)
    prima = riepilogo.prima_data.isoformat() if riepilogo.prima_data else "?"
    ultima = riepilogo.ultima_data.isoformat() if riepilogo.ultima_data else "?"
    sintesi = f"{riepilogo.estrazioni} estrazioni ({prima} → {ultima})"
    scartate = f"{scarti_totali} righe scartate"
    vista.console.print(f"Archivio scritto in {destinazione}: {sintesi}, {scartate}.")


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
    if solo_build:
        _ricostruisci_archivio(percorso_dati / "raw", percorso_dati / "archivio.csv")
        return
    sincronizza_archivio(percorso_dati, da=da, a=a, forza=forza)


def registra_comandi(app: typer.Typer) -> None:
    """Registra i comandi dell'archivio sull'applicazione Typer."""
    app.command()(download)
