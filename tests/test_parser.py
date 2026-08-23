"""Test del parser degli archivi annuali FrankNet."""

from datetime import date

import pytest

from lotto_ciclometria.errors import ParseError
from lotto_ciclometria.models import Ruota
from lotto_ciclometria.parser import parse_anno

HEADER_2026 = (
    " 2026         BARI           CAGLIARI         FIRENZE         "
    "GENOVA          MILANO          NAPOLI          PALERMO          "
    "ROMA          TORINO          VENEZIA       NAZIONALE    2026"
)

RIGA_2026_A = (
    "02 gen  69 48 61 60 29  77 53 87 29 64  01 83 38 53 19  86 46 57 41 30"
    "  64 72 41 14 03  73 05 29 70 86  41 66 84 14 26  41 14 60 78 88"
    "  21 70 22 52 43  19 54 80 64 46  01 38 70 18 69    1"
)

RIGA_2026_B = (
    "03 gen  33 13 81 04 08  16 86 49 87 14  02 34 12 06 74  65 45 89 90 14"
    "  16 22 31 52 44  78 15 13 11 29  51 21 33 22 20  07 42 36 66 46"
    "  19 62 48 81 35  67 36 09 64 50  18 53 11 47 55    2"
)

HTML_MODERNO = (
    "<html><head><title>Estrazioni Lotto 2026</title></head><body>\n"
    '<div align="center">\n'
    '<pre style="border-style: ridge"><b><span style="background-color: #00FFFF">'
    f"{HEADER_2026}</span>\n"
    f"{RIGA_2026_A}\n"
    f"{RIGA_2026_B}\n"
    "</b></pre>\n"
    "</div>\n"
    "</body></html>\n"
)

HEADER_1871 = (
    " 1871        BARI          CAGLIARI         FIRENZE         "
    "GENOVA          MILANO          NAPOLI          PALERMO          "
    "ROMA           TORINO          VENEZIA     1871"
)

RIGA_1871 = (
    "07 gen  -- -- -- -- --  -- -- -- -- --  15 71 18 64 81  -- -- -- -- --"
    "  63 69 56 09 55  36 22 73 24 31  72 58 86 77 14  42 33 20 18 79"
    "  02 09 63 27 04  29 52 31 80 07    1"
)

HTML_STORICO = (
    "<html><head><title>Estrazioni Lotto 1871</title></head><body>\n"
    '<div align="center">\n'
    '<pre style="border-style: ridge"><b><span style="background-color: #00FFFF">'
    f"{HEADER_1871}</span>\n"
    f"{RIGA_1871}\n"
    "</b></pre>\n"
    "</div>\n"
    "</body></html>\n"
)


def test_parse_anno_moderno_conteggia_tutte_le_ruote() -> None:
    risultato = parse_anno(HTML_MODERNO, 2026, "2026.HTM")
    assert len(risultato.estrazioni) == 22
    assert risultato.scarti == 0


def test_parse_anno_prima_estrazione_bari() -> None:
    risultato = parse_anno(HTML_MODERNO, 2026, "2026.HTM")
    bari = risultato.estrazioni[0]
    assert bari.data == date(2026, 1, 2)
    assert bari.ruota == Ruota.BARI
    assert bari.numeri == (69, 48, 61, 60, 29)


def test_parse_anno_nazionale_ultima_ruota() -> None:
    risultato = parse_anno(HTML_MODERNO, 2026, "2026.HTM")
    nazionale = risultato.estrazioni[-1]
    assert nazionale.ruota == Ruota.NAZIONALE
    assert nazionale.data == date(2026, 1, 3)
    assert nazionale.numeri == (18, 53, 11, 47, 55)


def test_parse_anno_storico_salta_ruote_mancanti() -> None:
    risultato = parse_anno(HTML_STORICO, 1871, "1871.HTM")
    ruote = {estrazione.ruota for estrazione in risultato.estrazioni}
    assert Ruota.BARI not in ruote
    assert Ruota.CAGLIARI not in ruote
    assert Ruota.GENOVA not in ruote
    assert len(risultato.estrazioni) == 7


def test_parse_anno_storico_valori_firenze() -> None:
    risultato = parse_anno(HTML_STORICO, 1871, "1871.HTM")
    firenze = risultato.estrazioni[0]
    assert firenze.ruota == Ruota.FIRENZE
    assert firenze.numeri == (15, 71, 18, 64, 81)
    assert firenze.data == date(1871, 1, 7)


def test_parse_anno_riga_data_invalida_conteggia_scarto() -> None:
    html = HTML_MODERNO.replace(RIGA_2026_B, "32 gen  01 02 03 04 05")
    risultato = parse_anno(html, 2026, "2026.HTM")
    assert len(risultato.estrazioni) == 11
    assert risultato.scarti == 1


def test_parse_anno_senza_dati_solleva_parse_error() -> None:
    with pytest.raises(ParseError):
        parse_anno("<html><body><p>vuoto</p></body></html>", 2099, "2099.HTM")
