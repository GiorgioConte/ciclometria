"""Parser degli archivi annuali HTML pubblicati da FrankNet.

Ogni file ``YYYY.HTM`` contiene blocchi ``<pre>`` con un'intestazione che
elenca le ruote presenti nell'archivio e righe dati nella forma::

    02 gen  69 48 61 60 29  77 53 87 29 64 ...  01 38 70 18 69    1

dove ogni gruppo di cinque valori appartiene a una ruota; i gruppi senza
dati storici sono riempiti con ``--``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Final

from lotto_ciclometria.errors import EstrazioneInvalidaError, ParseError
from lotto_ciclometria.models import Estrazione, Ruota

_RE_NOME_RUOTA: Final = re.compile(
    r"BARI|CAGLIARI|FIRENZE|GENOVA|MILANO|NAPOLI|PALERMO|ROMA|TORINO|VENEZIA|NAZIONALE",
)
_RE_TAG: Final = re.compile(r"<[^>]*>")
_RE_PREFISSO_DATI: Final = re.compile(r"^\s*\d{1,2}\s+[a-z]{3}\s")
_RUOTE_MINIME_INTESTAZIONE: Final = 2
_RE_RIGA_DATI: Final = re.compile(
    r"^\s*(\d{1,2})\s+([a-z]{3})\s+((?:--|\d{2})(?:\s+(?:--|\d{2}))*)\s+(\d+)\s*$",
)

_MESI: Final[dict[str, int]] = {
    "gen": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "mag": 5,
    "giu": 6,
    "lug": 7,
    "ago": 8,
    "set": 9,
    "ott": 10,
    "nov": 11,
    "dic": 12,
}


@dataclass(frozen=True, slots=True)
class RisultatoAnno:
    """Esito del parsing di un archivio annuale."""

    estrazioni: tuple[Estrazione, ...]
    scarti: int


def parse_anno(
    contenuto: str, anno: int, nome_file: str = "<archivio>"
) -> RisultatoAnno:
    """Estrae tutte le estrazioni valide da un file annuale.

    Le righe riconoscibili come dati ma non interpretabili vengono contate
    come scarti; un file privo di qualsiasi estrazione è un errore strutturale.
    """
    ruote_correnti: tuple[Ruota, ...] = ()
    estrazioni: list[Estrazione] = []
    scarti = 0
    for riga in contenuto.splitlines():
        pulita = _RE_TAG.sub("", riga)
        nomi_ruota = [trovata.group() for trovata in _RE_NOME_RUOTA.finditer(pulita)]
        if len(nomi_ruota) >= _RUOTE_MINIME_INTESTAZIONE:
            ruote_correnti = tuple(Ruota(nome) for nome in nomi_ruota)
            continue
        corrispondenza = _RE_RIGA_DATI.match(pulita)
        if corrispondenza is None:
            if _RE_PREFISSO_DATI.match(pulita):
                scarti += 1
            continue
        lette = _parse_riga(corrispondenza, anno, ruote_correnti)
        if lette is None:
            scarti += 1
            continue
        estrazioni.extend(lette)
    if not estrazioni:
        motivo = "nessuna estrazione riconosciuta nel file"
        raise ParseError(nome_file, motivo)
    return RisultatoAnno(estrazioni=tuple(estrazioni), scarti=scarti)


def _parse_riga(
    corrispondenza: re.Match[str],
    anno: int,
    ruote_correnti: tuple[Ruota, ...],
) -> list[Estrazione] | None:
    """Converte una riga dati nelle estrazioni per ruota (None = scarto)."""
    giorno = int(corrispondenza.group(1))
    mese = _MESI.get(corrispondenza.group(2))
    token = corrispondenza.group(3).split()
    if mese is None or not ruote_correnti or len(token) != 5 * len(ruote_correnti):
        return None
    try:
        data_estrazione = date(anno, mese, giorno)
    except ValueError:
        return None
    estrazioni_riga: list[Estrazione] = []
    for indice, ruota in enumerate(ruote_correnti):
        gruppo = token[indice * 5 : (indice + 1) * 5]
        if "--" in gruppo:
            continue
        try:
            numeri = tuple(int(v) for v in gruppo)
            estrazioni_riga.append(Estrazione(data_estrazione, ruota, numeri))
        except (EstrazioneInvalidaError, ValueError):
            return None
    return estrazioni_riga
