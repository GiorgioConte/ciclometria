"""Persistenza dell'archivio in formato CSV."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING, Final

from lotto_ciclometria.errors import ParseError
from lotto_ciclometria.models import Estrazione, Ruota

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

INTESTAZIONE_CSV: Final = ("data", "ruota", "n1", "n2", "n3", "n4", "n5")


@dataclass(frozen=True, slots=True)
class RiepilogoArchivio:
    """Sintesi dello stato dell'archivio su disco."""

    estrazioni: int
    prima_data: date | None
    ultima_data: date | None


def salva(estrazioni: Iterable[Estrazione], percorso: Path) -> RiepilogoArchivio:
    """Scrive l'archivio ordinato e deduplicato; restituisce la sintesi."""
    univoche: dict[tuple[date, int], Estrazione] = {}
    for estrazione in estrazioni:
        univoche.setdefault(estrazione.chiave_ordinamento, estrazione)
    ordinate = sorted(univoche.values(), key=lambda e: e.chiave_ordinamento)
    percorso.parent.mkdir(parents=True, exist_ok=True)
    with percorso.open("w", newline="", encoding="utf-8") as flusso:
        scrittore = csv.writer(flusso)
        scrittore.writerow(INTESTAZIONE_CSV)
        for estrazione in ordinate:
            scrittore.writerow(
                (
                    estrazione.data.isoformat(),
                    estrazione.ruota.value,
                    *estrazione.numeri,
                ),
            )
    return _riepilogo(ordinate)


def carica(percorso: Path) -> tuple[Estrazione, ...]:
    """Legge l'archivio CSV validando ogni riga al confine."""
    try:
        with percorso.open(newline="", encoding="utf-8") as flusso:
            lettore = csv.reader(flusso)
            intestazione = next(lettore, None)
            if intestazione != list(INTESTAZIONE_CSV):
                motivo = f"intestazione inattesa: {intestazione}"
                raise ParseError(str(percorso), motivo)
            lette = tuple(
                _parse_riga_csv(riga, percorso, numero)
                for numero, riga in enumerate(lettore, start=2)
            )
    except FileNotFoundError as errore:
        motivo = "archivio non trovato: eseguire prima `lotto download`"
        raise ParseError(str(percorso), motivo) from errore
    return tuple(sorted(lette, key=lambda e: e.chiave_ordinamento))


def riepilogo_da_estrazioni(estrazioni: Iterable[Estrazione]) -> RiepilogoArchivio:
    """Sintesi dell'archivio senza alcuna scrittura su disco."""
    return _riepilogo(list(estrazioni))


def _riepilogo(ordinate: list[Estrazione]) -> RiepilogoArchivio:
    date_ordinate = [estrazione.data for estrazione in ordinate]
    return RiepilogoArchivio(
        estrazioni=len(ordinate),
        prima_data=min(date_ordinate) if date_ordinate else None,
        ultima_data=max(date_ordinate) if date_ordinate else None,
    )


def _parse_riga_csv(riga: list[str], percorso: Path, numero_riga: int) -> Estrazione:
    dove = f"{percorso}:{numero_riga}"
    if len(riga) != len(INTESTAZIONE_CSV):
        motivo = f"attese {len(INTESTAZIONE_CSV)} colonne, trovate {len(riga)}"
        raise ParseError(dove, motivo)
    try:
        data_estrazione = date.fromisoformat(riga[0])
        numeri = tuple(int(valore) for valore in riga[2:])
        return Estrazione(data_estrazione, Ruota(riga[1]), numeri)
    except (ValueError, IndexError) as errore:
        raise ParseError(dove, str(errore)) from errore
