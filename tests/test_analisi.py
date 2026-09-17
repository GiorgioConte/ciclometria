"""Test delle analisi statistiche classiche."""

from datetime import date

from lotto_ciclometria.analisi import (
    filtra,
    frequenze_numeri,
    ritardi,
)
from lotto_ciclometria.models import Estrazione, Ruota


def crea(giorno: int, numeri: tuple[int, ...], ruota: Ruota = Ruota.BARI) -> Estrazione:
    """Fabbrica un'estrazione di prova."""
    return Estrazione.crea(date(2026, 1, giorno), ruota, numeri)


def test_frequenze_numeri_completa_per_tutti_i_90() -> None:
    estrazioni = [crea(2, (1, 2, 3, 4, 5)), crea(3, (1, 6, 7, 8, 9))]
    frequenze = dict(frequenze_numeri(estrazioni))
    assert frequenze[1] == 2
    assert frequenze[90] == 0
    assert len(frequenze) == 90


def test_frequenze_ordinate_per_conteggio_decrescente() -> None:
    estrazioni = [crea(2, (1, 2, 3, 4, 5)), crea(3, (1, 6, 7, 8, 9))]
    coppie = frequenze_numeri(estrazioni)
    conteggi = [conteggio for _, conteggio in coppie]
    assert conteggi == sorted(conteggi, reverse=True)


def test_ritardi_attuale_e_massimo() -> None:
    estrazioni = [
        crea(2, (50, 1, 2, 3, 4)),
        crea(3, (1, 5, 6, 7, 8)),
        crea(4, (1, 9, 10, 11, 12)),
    ]
    ritardi_mappa = {r.numero: r for r in ritardi(estrazioni)}
    assert ritardi_mappa[1].attuale == 0
    assert ritardi_mappa[1].massimo == 0
    assert ritardi_mappa[50].attuale == 2
    assert ritardi_mappa[50].massimo == 2


def test_filtra_per_ruota_e_data() -> None:
    estrazioni = [
        crea(2, (1, 2, 3, 4, 5)),
        crea(3, (6, 7, 8, 9, 10), Ruota.ROMA),
    ]
    solo_bari = filtra(estrazioni, ruota=Ruota.BARI)
    assert len(solo_bari) == 1


def test_filtra_al_include_il_giorno_limite() -> None:
    estrazioni = [
        crea(29, (1, 2, 3, 4, 5)),
        crea(30, (6, 7, 8, 9, 10)),
        crea(31, (11, 12, 13, 14, 15)),
    ]
    selezionate = filtra(estrazioni, al=date(2026, 1, 31))
    assert len(selezionate) == 3
    entro_luglio = filtra(estrazioni, al=date(2026, 1, 30))
    assert len(entro_luglio) == 2


def test_filtra_dal_e_al_insieme() -> None:
    estrazioni = [crea(giorno, (1, 2, 3, 4, 5)) for giorno in (1, 15, 31)]
    selezionate = filtra(estrazioni, dal=date(2026, 1, 15), al=date(2026, 1, 31))
    assert [e.data.day for e in selezionate] == [15, 31]
