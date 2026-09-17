"""Metodo della distanza 30 (Matteo Palumbo) con verifica retroattiva.

Procedura: individuato un ambo a distanza 30 nella figura di una
estrazione, la prima ambata è la metà della somma dei due numeri e la
seconda è la sua diametrale; gli abbinamenti sono gli ambi formati dalle
ambate con l'ambo base e con i suoi diametrali.

La verifica retroattiva misura su tutto l'archivio quanti trigger si sono
verificati e con quale frequenza le ambate sono uscite entro K colpi,
come confronto onesto con il caso.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import TYPE_CHECKING, Final

from lotto_ciclometria.cicli import LATO_TRIANGOLO, diametrale, distanza
from lotto_ciclometria.models import NUMERI_PER_ESTRAZIONE, NUMERO_MASSIMO

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import date

    from lotto_ciclometria.models import Estrazione, Ruota

DISTANZA_TRIGGER: Final = LATO_TRIANGOLO


@dataclass(frozen=True, slots=True)
class Trigger30:
    """Un ambo a distanza 30 con le relative ambate derivate."""

    data: date
    ruota: Ruota
    base: tuple[int, int]
    ambata1: int
    ambata2: int


@dataclass(frozen=True, slots=True)
class EsitoTrigger:
    """Esito di un trigger osservato nei colpi successivi."""

    trigger: Trigger30
    colpo_ambata1: int | None
    colpo_ambata2: int | None


@dataclass(frozen=True, slots=True)
class ReportVerifica:
    """Sintesi della verifica retroattiva."""

    esiti: tuple[EsitoTrigger, ...]
    colpi: int
    n_hit_ambata1: int
    n_hit_ambata2: int

    @property
    def totale_trigger(self) -> int:
        """Numero di trigger sottoposti a verifica."""
        return len(self.esiti)


@dataclass(frozen=True, slots=True)
class Previsione:
    """Sviluppo del metodo sull'ultimo trigger ancora in finestra."""

    data_riferimento: date
    ruota: Ruota
    ambate: tuple[int, int]
    abbinamenti: tuple[tuple[int, int], ...]


def trova_trigger(estrazione: Estrazione) -> tuple[Trigger30, ...]:
    """Tutti gli ambi a distanza 30 presenti nella figura."""
    numeri_ordinati = sorted(estrazione.numeri)
    trigger: list[Trigger30] = []
    for primo, secondo in combinations(numeri_ordinati, 2):
        if distanza(primo, secondo) != DISTANZA_TRIGGER:
            continue
        ambata1 = (primo + secondo) // 2
        trigger.append(
            Trigger30(
                data=estrazione.data,
                ruota=estrazione.ruota,
                base=(primo, secondo),
                ambata1=ambata1,
                ambata2=diametrale(ambata1),
            ),
        )
    return tuple(trigger)


def verifica_retroattiva(
    estrazioni: Sequence[Estrazione],
    *,
    ruota: Ruota,
    colpi: int,
) -> ReportVerifica:
    """Applica il metodo a ogni trigger storico e conta gli esiti entro K colpi."""
    serie = sorted(
        (e for e in estrazioni if e.ruota == ruota),
        key=lambda e: e.chiave_ordinamento,
    )
    return _verifica_serie(serie, colpi=colpi)


def verifica_periodo(
    estrazioni: Sequence[Estrazione],
    *,
    ruota: Ruota,
    colpi: int,
    dal: date | None = None,
    al: date | None = None,
) -> ReportVerifica:
    """Verifica limitata ai trigger del periodo [dal, al], estremi inclusi.

    Gli esiti vengono cercati nei colpi successivi al trigger anche oltre
    ``al``: una simulazione «fino a fine luglio» usa dunque anche le
    estrazioni di agosto per contare le uscite.
    """
    serie = sorted(
        (e for e in estrazioni if e.ruota == ruota),
        key=lambda e: e.chiave_ordinamento,
    )
    return _verifica_serie(serie, colpi=colpi, dal=dal, al=al)


def _verifica_serie(
    serie: list[Estrazione],
    *,
    colpi: int,
    dal: date | None = None,
    al: date | None = None,
) -> ReportVerifica:
    """Cuore comune delle verifiche: filtra i trigger, guarda avanti K colpi."""
    esiti: list[EsitoTrigger] = []
    n_hit_ambata1 = 0
    n_hit_ambata2 = 0
    for posizione, estrazione in enumerate(serie):
        if dal is not None and estrazione.data < dal:
            continue
        if al is not None and estrazione.data > al:
            continue
        for trigger in trova_trigger(estrazione):
            finestra = serie[posizione + 1 : posizione + 1 + colpi]
            colpo1 = primo_colpo(finestra, trigger.ambata1)
            colpo2 = primo_colpo(finestra, trigger.ambata2)
            if colpo1 is not None:
                n_hit_ambata1 += 1
            if colpo2 is not None:
                n_hit_ambata2 += 1
            esiti.append(
                EsitoTrigger(
                    trigger=trigger, colpo_ambata1=colpo1, colpo_ambata2=colpo2
                )
            )
    return ReportVerifica(
        esiti=tuple(esiti),
        colpi=colpi,
        n_hit_ambata1=n_hit_ambata1,
        n_hit_ambata2=n_hit_ambata2,
    )


def previsione_attiva(
    estrazioni: Sequence[Estrazione],
    *,
    ruota: Ruota,
) -> Previsione | None:
    """Sviluppo derivato dal trigger più recente della ruota, se presente."""
    serie = sorted(
        (e for e in estrazioni if e.ruota == ruota),
        key=lambda e: e.chiave_ordinamento,
        reverse=True,
    )
    for estrazione in serie:
        trigger = trova_trigger(estrazione)
        if trigger:
            primo = trigger[0]
            base1, base2 = primo.base
            abbinamenti = (
                (primo.ambata1, base1),
                (primo.ambata1, base2),
                (primo.ambata2, diametrale(base1)),
                (primo.ambata2, diametrale(base2)),
            )
            return Previsione(
                data_riferimento=estrazione.data,
                ruota=ruota,
                ambate=(primo.ambata1, primo.ambata2),
                abbinamenti=abbinamenti,
            )
    return None


def tasso_casuale(colpi: int) -> float:
    """Probabilità di caso che un numero fisso esca entro K estrazioni."""
    return 1.0 - ((NUMERO_MASSIMO - NUMERI_PER_ESTRAZIONE) / NUMERO_MASSIMO) ** colpi


def primo_colpo(finestra: Sequence[Estrazione], ambata: int) -> int | None:
    """Colpo (1-based) della prima uscita dell'ambata nella finestra, se presente."""
    for colpo, estrazione in enumerate(finestra, start=1):
        if ambata in estrazione.numeri:
            return colpo
    return None
