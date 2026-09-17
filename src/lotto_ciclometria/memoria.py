"""Memoria persistente delle previsioni registrate.

Le previsioni del metodo della distanza 30 vengono annotate in
``data/memoria.csv``; l'allineamento con le estrazioni successive
aggiorna i colpi di uscita e lo stato di ciascuna voce:

* ``aperta`` — la finestra non è ancora interamente disponibile;
* ``chiusa`` — entrambe le ambate sono uscite entro la finestra;
* ``scaduta`` — finestra esaurita senza entrambe le uscite.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, replace
from datetime import date
from enum import StrEnum
from typing import TYPE_CHECKING, Final

from lotto_ciclometria.errors import ParseError
from lotto_ciclometria.metodi import Previsione, primo_colpo
from lotto_ciclometria.models import ORDINE_RUOTE, Estrazione, Ruota

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence
    from pathlib import Path

INTESTAZIONE_MEMORIA: Final = (
    "data",
    "ruota",
    "ambata1",
    "ambata2",
    "colpi",
    "colpo_ambata1",
    "colpo_ambata2",
    "abbinamenti",
)

SEPARATORE_ABBINAMENTI: Final = ";"
SEPARATORE_COPPIA: Final = "-"


class StatoVoce(StrEnum):
    """Stato di una previsione registrata rispetto alle estrazioni note."""

    APERTA = "aperta"
    CHIUSA = "chiusa"
    SCADUTA = "scaduta"


@dataclass(frozen=True, slots=True)
class VoceMemoria:
    """Una previsione annotata con l'esito osservato nei colpi successivi."""

    data_riferimento: date
    ruota: Ruota
    ambate: tuple[int, int]
    abbinamenti: tuple[tuple[int, int], ...]
    colpi: int
    colpo_ambata1: int | None = None
    colpo_ambata2: int | None = None

    @property
    def chiave(self) -> tuple[date, int]:
        """Coppia (data, ordine della ruota) che identifica la voce."""
        return (self.data_riferimento, ORDINE_RUOTE.index(self.ruota))


@dataclass(frozen=True, slots=True)
class VoceAllineata:
    """Voce aggiornata all'archivio corrente con il relativo stato."""

    voce: VoceMemoria
    stato: StatoVoce


def registra(previsione: Previsione, *, colpi: int) -> VoceMemoria:
    """Annota una previsione attiva con la finestra di verifica scelta."""
    return VoceMemoria(
        data_riferimento=previsione.data_riferimento,
        ruota=previsione.ruota,
        ambate=previsione.ambate,
        abbinamenti=previsione.abbinamenti,
        colpi=colpi,
    )


def allinea(
    voci: Sequence[VoceMemoria],
    estrazioni: Sequence[Estrazione],
) -> tuple[VoceAllineata, ...]:
    """Aggiorna ogni voce con gli esiti nelle estrazioni successive.

    Per ciascuna voce la finestra sono le prime ``colpi`` estrazioni della
    stessa ruota successive alla data di riferimento; l'esito è ricalcolato
    da capo sull'archivio corrente, così l'operazione è idempotente.
    """
    serie_per_ruota: dict[Ruota, list[Estrazione]] = {}
    for estrazione in estrazioni:
        serie_per_ruota.setdefault(estrazione.ruota, []).append(estrazione)
    for serie in serie_per_ruota.values():
        serie.sort(key=lambda e: e.chiave_ordinamento)
    return tuple(
        _allinea_voce(voce, serie_per_ruota.get(voce.ruota, [])) for voce in voci
    )


def salva_memoria(voci: Iterable[VoceMemoria], percorso: Path) -> None:
    """Scrive le voci deduplicate per chiave con scrittura atomica."""
    univoche: dict[tuple[date, int], VoceMemoria] = {}
    for voce in voci:
        univoche[voce.chiave] = voce
    ordinate = sorted(univoche.values(), key=lambda v: v.chiave)
    percorso.parent.mkdir(parents=True, exist_ok=True)
    provvisorio = percorso.with_suffix(percorso.suffix + ".tmp")
    with provvisorio.open("w", newline="", encoding="utf-8") as flusso:
        scrittore = csv.writer(flusso)
        scrittore.writerow(INTESTAZIONE_MEMORIA)
        for voce in ordinate:
            scrittore.writerow(_riga_di(voce))
    _ = provvisorio.replace(percorso)


def carica_memoria(percorso: Path) -> tuple[VoceMemoria, ...]:
    """Legge il file di memoria; assente equivale a memoria vuota."""
    try:
        with percorso.open(newline="", encoding="utf-8") as flusso:
            lettore = csv.reader(flusso)
            intestazione = next(lettore, None)
            if intestazione != list(INTESTAZIONE_MEMORIA):
                motivo = f"intestazione inattesa: {intestazione}"
                raise ParseError(str(percorso), motivo)
            lette = tuple(
                _voce_di(riga, f"{percorso}:{numero}")
                for numero, riga in enumerate(lettore, start=2)
            )
    except FileNotFoundError:
        return ()
    return tuple(sorted(lette, key=lambda v: v.chiave))


def _allinea_voce(
    voce: VoceMemoria,
    serie: Sequence[Estrazione],
) -> VoceAllineata:
    finestra = [e for e in serie if e.data > voce.data_riferimento][: voce.colpi]
    aggiornata = replace(
        voce,
        colpo_ambata1=primo_colpo(finestra, voce.ambate[0]),
        colpo_ambata2=primo_colpo(finestra, voce.ambate[1]),
    )
    if aggiornata.colpo_ambata1 is not None and aggiornata.colpo_ambata2 is not None:
        stato = StatoVoce.CHIUSA
    elif len(finestra) < voce.colpi:
        stato = StatoVoce.APERTA
    else:
        stato = StatoVoce.SCADUTA
    return VoceAllineata(voce=aggiornata, stato=stato)


def _riga_di(voce: VoceMemoria) -> list[str]:
    coppie = [
        f"{primo}{SEPARATORE_COPPIA}{secondo}" for primo, secondo in voce.abbinamenti
    ]
    return [
        voce.data_riferimento.isoformat(),
        voce.ruota.value,
        str(voce.ambate[0]),
        str(voce.ambate[1]),
        str(voce.colpi),
        _testo_opzionale(voce.colpo_ambata1),
        _testo_opzionale(voce.colpo_ambata2),
        SEPARATORE_ABBINAMENTI.join(coppie),
    ]


def _voce_di(riga: list[str], dove: str) -> VoceMemoria:
    if len(riga) != len(INTESTAZIONE_MEMORIA):
        motivo = f"attese {len(INTESTAZIONE_MEMORIA)} colonne, trovate {len(riga)}"
        raise ParseError(dove, motivo)
    try:
        abbinamenti = tuple(_coppia_di(testo) for testo in riga[7].split(";") if testo)
        return VoceMemoria(
            data_riferimento=date.fromisoformat(riga[0]),
            ruota=Ruota(riga[1]),
            ambate=(int(riga[2]), int(riga[3])),
            abbinamenti=abbinamenti,
            colpi=int(riga[4]),
            colpo_ambata1=_intero_opzionale(riga[5]),
            colpo_ambata2=_intero_opzionale(riga[6]),
        )
    except ValueError as errore:
        raise ParseError(dove, str(errore)) from errore


def _coppia_di(testo: str) -> tuple[int, int]:
    primo, secondo = testo.split(SEPARATORE_COPPIA)
    return (int(primo), int(secondo))


def _intero_opzionale(valore: str) -> int | None:
    return int(valore) if valore else None


def _testo_opzionale(valore: int | None) -> str:
    return str(valore) if valore is not None else ""
