"""Analisi statistiche classiche su un archivio di estrazioni."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from itertools import combinations
from typing import TYPE_CHECKING, Final

from lotto_ciclometria.cicli import distanze_figura, somma_caratteristica

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import date

    from lotto_ciclometria.models import Estrazione, Ruota

NUMERI_TOTALI: Final = 90
DISTANZE_TOTALI: Final = 45


@dataclass(frozen=True, slots=True)
class RitardoNumero:
    """Stato di ritardo di un singolo numero su una serie di estrazioni."""

    numero: int
    frequenza: int
    ultimo: date | None
    attuale: int
    massimo: int


def filtra(
    estrazioni: Sequence[Estrazione],
    *,
    ruota: Ruota | None = None,
    dal: date | None = None,
    al: date | None = None,
) -> tuple[Estrazione, ...]:
    """Ordina cronologicamente e applica i filtri richiesti (estremi inclusi)."""
    selezione = [
        estrazione
        for estrazione in estrazioni
        if (ruota is None or estrazione.ruota == ruota)
        and (dal is None or estrazione.data >= dal)
        and (al is None or estrazione.data <= al)
    ]
    return tuple(sorted(selezione, key=lambda e: e.chiave_ordinamento))


def frequenze_numeri(estrazioni: Sequence[Estrazione]) -> tuple[tuple[int, int], ...]:
    """Occorrenze per ciascun numero 1..90, ordinate per conteggio decrescente."""
    contatore = Counter(
        numero for estrazione in estrazioni for numero in estrazione.numeri
    )
    coppie = [
        (numero, contatore.get(numero, 0)) for numero in range(1, NUMERI_TOTALI + 1)
    ]
    return tuple(sorted(coppie, key=lambda coppia: (-coppia[1], coppia[0])))


def ritardi(estrazioni: Sequence[Estrazione]) -> tuple[RitardoNumero, ...]:
    """Ritardo attuale e storico di ogni numero sulla serie ordinata.

    ``attuale`` conta le estrazioni dall'ultima uscita; ``massimo`` è il
    peggiore intervallo osservato tra uscite consecutive, comprensivo del
    ritardo ancora in corso.
    """
    totale = len(estrazioni)
    ultima_uscita: dict[int, int] = {}
    frequenze: Counter[int] = Counter()
    gap_chiusi: dict[int, int] = {}
    for posizione, estrazione in enumerate(estrazioni):
        for numero in estrazione.numeri:
            frequenze[numero] += 1
            if numero in ultima_uscita:
                gap = posizione - ultima_uscita[numero] - 1
                gap_chiusi[numero] = max(gap_chiusi.get(numero, gap), gap)
            ultima_uscita[numero] = posizione
    risultati: list[RitardoNumero] = []
    for numero in range(1, NUMERI_TOTALI + 1):
        uscita = ultima_uscita.get(numero)
        if uscita is None:
            risultati.append(RitardoNumero(numero, 0, None, totale, totale))
            continue
        attuale = totale - 1 - uscita
        ultimo = estrazioni[uscita].data
        massimo = max(gap_chiusi.get(numero, attuale), attuale)
        risultati.append(
            RitardoNumero(numero, frequenze[numero], ultimo, attuale, massimo)
        )
    return tuple(risultati)


def frequenze_distanze(estrazioni: Sequence[Estrazione]) -> tuple[tuple[int, int], ...]:
    """Frequenza delle distanze ciclometriche (1..45) su tutte le figure."""
    contatore = Counter(
        valore
        for estrazione in estrazioni
        for valore in distanze_figura(estrazione.numeri)
    )
    coppie = [
        (distanza, contatore.get(distanza, 0))
        for distanza in range(1, DISTANZE_TOTALI + 1)
    ]
    return tuple(sorted(coppie, key=lambda coppia: (-coppia[1], coppia[0])))


def frequenze_somme(estrazioni: Sequence[Estrazione]) -> tuple[tuple[int, int], ...]:
    """Distribuzione della somma caratteristica delle estrazioni."""
    contatore = Counter(
        somma_caratteristica(estrazione.numeri) for estrazione in estrazioni
    )
    return tuple(sorted(contatore.items(), key=lambda coppia: (-coppia[1], coppia[0])))


def ambi_piu_frequenti(
    estrazioni: Sequence[Estrazione], quantita: int
) -> tuple[tuple[tuple[int, int], int], ...]:
    """Gli ambi (coppie non ordinate) più ricorrenti nella stessa estrazione."""
    contatore: Counter[tuple[int, int]] = Counter()
    for estrazione in estrazioni:
        for primo, secondo in combinations(estrazione.numeri, 2):
            coppia = (min(primo, secondo), max(primo, secondo))
            contatore[coppia] += 1
    return tuple(contatore.most_common(quantita))
