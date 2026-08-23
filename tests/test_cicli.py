"""Test della matematica ciclometrica pura."""

from lotto_ciclometria.cicli import (
    diametrale,
    distanza,
    distanze_figura,
    fuori_90,
    ha_diametri,
    rettangoli,
    somma_caratteristica,
    triangoli_equilateri,
)


def test_distanza_semplice() -> None:
    assert distanza(10, 40) == 30


def test_distanza_attraverso_lo_zero() -> None:
    assert distanza(70, 10) == 30


def test_distanza_massimo_45() -> None:
    assert distanza(10, 55) == 45


def test_distanza_diametrale_esatta() -> None:
    assert distanza(45, 90) == 45


def test_diametrale_meta_bassa() -> None:
    assert diametrale(1) == 46


def test_diametrale_meta_alta() -> None:
    assert diametrale(57) == 12


def test_diametrale_estremi() -> None:
    assert diametrale(45) == 90
    assert diametrale(90) == 45


def test_fuori_90_senza_superamento() -> None:
    assert fuori_90(72) == 72


def test_fuori_90_con_superamento() -> None:
    assert fuori_90(114) == 24


def test_somma_caratteristica() -> None:
    # 69+48+61+60+29 = 267 -> 267 - 90*2 = 87
    assert somma_caratteristica((69, 48, 61, 60, 29)) == 87


def test_distanze_figura_dieci_coppie() -> None:
    distanze = distanze_figura((69, 48, 61, 60, 29))
    assert len(distanze) == 10
    assert distanza(29, 48) in distanze
    assert distanze[0] == 1  # la coppia più vicina: 60-61


def test_ha_diametri_conta_le_coppie() -> None:
    assert ha_diametri((5, 50, 20, 65, 77)) == 2
    assert ha_diametri((5, 50, 21, 65, 77)) == 1


def test_triangolo_equilatero_presente() -> None:
    triangoli = triangoli_equilateri((10, 40, 70, 1, 2))
    assert (10, 40, 70) in triangoli


def test_triangolo_equilatero_assente() -> None:
    assert triangoli_equilateri((10, 41, 70, 1, 2)) == ()


def test_rettangolo_due_coppie_diametrali() -> None:
    rettangoli_trovati = rettangoli((5, 50, 20, 65, 77))
    assert len(rettangoli_trovati) == 1
    assert rettangoli_trovati[0] == (5, 50, 20, 65)


def test_rettangolo_assente() -> None:
    assert rettangoli((5, 50, 21, 64, 77)) == ()
