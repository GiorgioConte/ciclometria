"""Presentazione dei risultati con Rich."""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from lotto_ciclometria.cicli import (
    diametrale,
    ha_diametri,
    rettangoli,
    somma_caratteristica,
    triangoli_equilateri,
)
from lotto_ciclometria.metodi import tasso_casuale

if TYPE_CHECKING:
    from collections.abc import Sequence

    from lotto_ciclometria.analisi import RitardoNumero
    from lotto_ciclometria.metodi import EsitoTrigger, Previsione, ReportVerifica
    from lotto_ciclometria.models import Estrazione, Ruota

console: Final = Console()

VUOTO: Final = "—"


def _tabella(titolo: str, colonne: Sequence[str]) -> Table:
    tabella = Table(title=titolo, header_style="bold cyan")
    for colonna in colonne:
        tabella.add_column(colonna, justify="right")
    return tabella


def stampa_frequenze(
    frequenze: Sequence[tuple[int, int]], *, limite: int, titolo: str
) -> None:
    """Classifica dei numeri per uscite decrescenti."""
    tabella = _tabella(titolo, ("Numero", "Uscite"))
    for numero, conteggio in frequenze[:limite]:
        tabella.add_row(str(numero), str(conteggio))
    console.print(tabella)


def stampa_ritardi(valori: Sequence[RitardoNumero], *, limite: int) -> None:
    """Numeri ordinati per ritardo attuale decrescente."""
    ordinati = sorted(
        valori, key=lambda valore: (-valore.attuale, -valore.massimo, valore.numero)
    )
    tabella = _tabella("Ritardi", ("Numero", "Attuale", "Massimo", "Uscite", "Ultimo"))
    tabella.columns[4].justify = "left"
    for valore in ordinati[:limite]:
        ultimo = valore.ultimo.isoformat() if valore.ultimo else VUOTO
        tabella.add_row(
            str(valore.numero),
            str(valore.attuale),
            str(valore.massimo),
            str(valore.frequenza),
            ultimo,
        )
    console.print(tabella)


def stampa_distanze(frequenze: Sequence[tuple[int, int]], *, limite: int) -> None:
    """Distribuzione delle distanze ciclometriche tra coppie della figura."""
    tabella = _tabella("Distanze ciclometriche", ("Distanza", "Occorrenze"))
    for valore, conteggio in frequenze[:limite]:
        tabella.add_row(str(valore), str(conteggio))
    console.print(tabella)


def stampa_somme(frequenze: Sequence[tuple[int, int]], *, limite: int) -> None:
    """Distribuzione delle somme caratteristiche ridotte a 1..90."""
    tabella = _tabella("Somma caratteristica", ("Somma", "Estrazioni"))
    for valore, conteggio in frequenze[:limite]:
        tabella.add_row(str(valore), str(conteggio))
    console.print(tabella)


def stampa_cerchio(ultime: Sequence[Estrazione], *, ruota: Ruota) -> None:
    """Ultime estrazioni con il diametrale di ciascun numero tra parentesi."""
    tabella = Table(title=f"Cerchio dei 90 — {ruota.value}", header_style="bold cyan")
    tabella.add_column("Data", justify="left")
    tabella.add_column("Numeri (diametrale)", justify="left")
    tabella.add_column("Somma caratteristica", justify="right")
    for estrazione in ultime:
        rappresentazione = "  ".join(
            f"{numero}({diametrale(numero)})" for numero in estrazione.numeri
        )
        tabella.add_row(
            estrazione.data.isoformat(),
            rappresentazione,
            str(somma_caratteristica(estrazione.numeri)),
        )
    console.print(tabella)


def _testo_tripla(tripla: Sequence[int]) -> str:
    return "-".join(str(numero) for numero in tripla)


def _testo_quadrupla(quadrupla: Sequence[int]) -> str:
    return "·".join(str(numero) for numero in quadrupla)


def stampa_figure(selezionate: Sequence[Estrazione]) -> None:
    """Tabella delle figure inscritte presenti in ciascuna estrazione."""
    tabella = Table(title="Figure inscritte", header_style="bold cyan")
    tabella.add_column("Data", justify="left")
    tabella.add_column("Ruota", justify="left")
    tabella.add_column("Diametri", justify="right")
    tabella.add_column("Triangoli (lato 30)", justify="left")
    tabella.add_column("Rettangoli", justify="left")
    for estrazione in selezionate:
        triangoli_trovati = triangoli_equilateri(estrazione.numeri)
        rettangoli_trovati = rettangoli(estrazione.numeri)
        triangoli = " ".join(map(_testo_tripla, triangoli_trovati)) or VUOTO
        quadrilateri = " ".join(map(_testo_quadrupla, rettangoli_trovati)) or VUOTO
        tabella.add_row(
            estrazione.data.isoformat(),
            estrazione.ruota.value,
            str(ha_diametri(estrazione.numeri)),
            triangoli,
            quadrilateri,
        )
    console.print(tabella)


def stampa_report(report: ReportVerifica, *, ruota: Ruota) -> None:
    """Sintesi della verifica retroattiva confrontata col caso."""
    totale = report.totale_trigger
    if totale == 0:
        console.print(f"[yellow]Nessun ambo a distanza 30 su {ruota.value}.[/yellow]")
        return
    caso = tasso_casuale(report.colpi)
    tasso1 = report.n_hit_ambata1 / totale
    tasso2 = report.n_hit_ambata2 / totale
    riga1 = (
        f"Ambata 1 (metà della somma): {report.n_hit_ambata1}/{totale} "
        f"({tasso1:.1%}) — caso {caso:.1%}\n"
    )
    riga2 = (
        f"Ambata 2 (diametrale):       {report.n_hit_ambata2}/{totale} "
        f"({tasso2:.1%}) — caso {caso:.1%}"
    )
    contenuto = (
        f"Trigger osservati: {totale} — finestra {report.colpi} colpi\n{riga1}{riga2}"
    )
    console.print(
        Panel(contenuto, title=f"Verifica retroattiva — {ruota.value}", expand=False)
    )


def stampa_esiti(esiti: Sequence[EsitoTrigger], *, limite: int) -> None:
    """Dettaglio dei trigger più recenti con i colpi di uscita."""
    visibili = esiti[-limite:]
    tabella = Table(title=f"Ultimi {len(visibili)} trigger", header_style="bold cyan")
    tabella.add_column("Data trigger", justify="left")
    tabella.add_column("Ambo base", justify="left")
    tabella.add_column("Ambate", justify="left")
    tabella.add_column("Colpo ambata 1", justify="right")
    tabella.add_column("Colpo ambata 2", justify="right")
    for esito in visibili:
        trigger = esito.trigger
        colpo1 = str(esito.colpo_ambata1) if esito.colpo_ambata1 is not None else VUOTO
        colpo2 = str(esito.colpo_ambata2) if esito.colpo_ambata2 is not None else VUOTO
        tabella.add_row(
            trigger.data.isoformat(),
            f"{trigger.base[0]}-{trigger.base[1]}",
            f"{trigger.ambata1} / {trigger.ambata2}",
            colpo1,
            colpo2,
        )
    console.print(tabella)


def stampa_previsione(previsione: Previsione | None) -> None:
    """Sviluppo del metodo sull'ultimo trigger ancora in gioco."""
    if previsione is None:
        console.print("[yellow]Nessun trigger attivo sulla ruota.[/yellow]")
        return
    abbinamenti = "; ".join(
        f"{primo}-{secondo}" for primo, secondo in previsione.abbinamenti
    )
    contenuto = (
        f"Trigger del {previsione.data_riferimento.isoformat()} "
        f"su {previsione.ruota.value}\n"
        f"Ambate: {previsione.ambate[0]} e {previsione.ambate[1]}\n"
        f"Abbinamenti: {abbinamenti}"
    )
    console.print(
        Panel(contenuto, title="Previsione attiva (distanza 30)", expand=False)
    )
