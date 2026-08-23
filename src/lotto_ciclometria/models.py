"""Modelli di dominio immutabili."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Final

from lotto_ciclometria.errors import EstrazioneInvalidaError

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import date


class Ruota(StrEnum):
    """Le ruote del gioco del Lotto."""

    BARI = "BARI"
    CAGLIARI = "CAGLIARI"
    FIRENZE = "FIRENZE"
    GENOVA = "GENOVA"
    MILANO = "MILANO"
    NAPOLI = "NAPOLI"
    PALERMO = "PALERMO"
    ROMA = "ROMA"
    TORINO = "TORINO"
    VENEZIA = "VENEZIA"
    NAZIONALE = "NAZIONALE"


ORDINE_RUOTE: Final[tuple[Ruota, ...]] = (
    Ruota.BARI,
    Ruota.CAGLIARI,
    Ruota.FIRENZE,
    Ruota.GENOVA,
    Ruota.MILANO,
    Ruota.NAPOLI,
    Ruota.PALERMO,
    Ruota.ROMA,
    Ruota.TORINO,
    Ruota.VENEZIA,
    Ruota.NAZIONALE,
)

NUMERI_PER_ESTRAZIONE: Final = 5
NUMERO_MINIMO: Final = 1
NUMERO_MASSIMO: Final = 90


@dataclass(frozen=True, slots=True)
class Estrazione:
    """I cinque numeri usciti su una ruota in una data."""

    data: date
    ruota: Ruota
    numeri: tuple[int, ...]

    def __post_init__(self) -> None:
        """Valida la figura: cinque numeri distinti nell'intervallo 1..90."""
        if len(self.numeri) != NUMERI_PER_ESTRAZIONE:
            motivo = (
                f"attesi {NUMERI_PER_ESTRAZIONE} numeri, trovati {len(self.numeri)}"
            )
            raise EstrazioneInvalidaError(motivo)
        if len(set(self.numeri)) != NUMERI_PER_ESTRAZIONE:
            motivo_ripetuti = f"numeri ripetuti: {self.numeri}"
            raise EstrazioneInvalidaError(motivo_ripetuti)
        for numero in self.numeri:
            if not NUMERO_MINIMO <= numero <= NUMERO_MASSIMO:
                motivo = f"numero fuori intervallo 1..90: {numero}"
                raise EstrazioneInvalidaError(motivo)

    @classmethod
    def crea(
        cls,
        data: date,
        ruota: Ruota | str,
        numeri: Sequence[int],
    ) -> Estrazione:
        """Costruttore di comodo che normalizza la ruota e i numeri."""
        return cls(data=data, ruota=Ruota(ruota), numeri=tuple(numeri))

    @property
    def chiave_ordinamento(self) -> tuple[date, int]:
        """Coppia (data, ordine della ruota) per l'ordinamento canonico."""
        return (self.data, ORDINE_RUOTE.index(self.ruota))
