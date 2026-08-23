"""Matematica ciclometrica pura: il cerchio dei 90 numeri.

I 90 numeri del Lotto sono disposti su una circonferenza; la distanza
ciclometrica tra due numeri è il percorso più breve lungo il cerchio
e non può superare il diametro (45 posizioni).
"""

from __future__ import annotations

from itertools import combinations
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Sequence

DIAMETRO: Final = 45
LATO_TRIANGOLO: Final = 30
POSIZIONI_CERCHIO: Final = 90


def distanza(a: int, b: int) -> int:
    """Distanza ciclometrica tra due numeri: sempre compresa tra 0 e 45."""
    differenza = abs(a - b)
    return min(differenza, POSIZIONI_CERCHIO - differenza)


def diametrale(n: int) -> int:
    """Numero opposto sul cerchio (± 45 posizioni)."""
    opposto = n + DIAMETRO
    return opposto - POSIZIONI_CERCHIO if opposto > POSIZIONI_CERCHIO else opposto


def fuori_90(somma: int) -> int:
    """Somma ciclotica di un ambo: se supera 90 si sottrae 90 una volta."""
    return somma - POSIZIONI_CERCHIO if somma > POSIZIONI_CERCHIO else somma


def somma_caratteristica(numeri: Sequence[int]) -> int:
    """Somma dei cinque numeri ridotta nell'intervallo 1..90."""
    totale = sum(numeri)
    return ((totale - 1) % POSIZIONI_CERCHIO) + 1


def distanze_figura(numeri: Sequence[int]) -> tuple[int, ...]:
    """Le distanze di tutte le coppie della figura, ordinate in modo crescente."""
    ordinati = sorted(numeri)
    tutte = sorted(distanza(a, b) for a, b in combinations(ordinati, 2))
    return tuple(tutte)


def _coppie_diametrali(ordinati: Sequence[int]) -> list[tuple[int, int]]:
    return [
        coppia for coppia in combinations(ordinati, 2) if distanza(*coppia) == DIAMETRO
    ]


def ha_diametri(numeri: Sequence[int]) -> int:
    """Quante coppie diametrali (distanza 45) contiene la figura."""
    return len(_coppie_diametrali(sorted(numeri)))


def triangoli_equilateri(numeri: Sequence[int]) -> tuple[tuple[int, int, int], ...]:
    """Triple di numeri equidistanti di 30 posizioni (triangoli inscritti)."""
    trovati = [
        tripla
        for tripla in combinations(sorted(numeri), 3)
        if all(distanza(x, y) == LATO_TRIANGOLO for x, y in combinations(tripla, 2))
    ]
    return tuple(trovati)


def rettangoli(numeri: Sequence[int]) -> tuple[tuple[int, int, int, int], ...]:
    """Rettangoli inscritti: due coppie diametrali con quattro vertici distinti."""
    coppie = _coppie_diametrali(sorted(numeri))
    trovati: list[tuple[int, int, int, int]] = []
    for prima, seconda in combinations(coppie, 2):
        if set(prima).isdisjoint(seconda):
            trovati.append((*prima, *seconda))
    return tuple(trovati)
