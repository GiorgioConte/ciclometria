"""Test del metodo Palumbo (distanza 30) e della verifica retroattiva."""

from datetime import date

from lotto_ciclometria.metodi import (
    previsione_attiva,
    trova_trigger,
    verifica_periodo,
    verifica_retroattiva,
)
from lotto_ciclometria.models import Estrazione, Ruota


def crea(data_gg: int, numeri: tuple[int, ...]) -> Estrazione:
    """Fabbrica un'estrazione di prova su una ruota fissa."""
    return Estrazione.crea(date(2026, 1, data_gg), Ruota.BARI, numeri)


def crea_su(data: date, numeri: tuple[int, ...]) -> Estrazione:
    """Fabbrica un'estrazione di prova con data esplicita."""
    return Estrazione.crea(data, Ruota.BARI, numeri)


def test_trova_trigger_con_ambo_distanza_30() -> None:
    estrazione = crea(2, (42, 72, 15, 33, 88))
    trigger = trova_trigger(estrazione)
    assert len(trigger) == 1
    assert trigger[0].base == (42, 72)
    assert trigger[0].ambata1 == 57
    assert trigger[0].ambata2 == 12


def test_trova_trigger_assente() -> None:
    assert trova_trigger(crea(2, (1, 5, 9, 13, 17))) == ()


def test_verifica_retroattiva_colpi_entro_finestra() -> None:
    estrazioni = [
        crea(2, (10, 40, 77, 82, 63)),  # trigger: ambate 25 e 70
        crea(3, (25, 1, 4, 8, 11)),  # ambata1 al colpo 1
        crea(5, (70, 2, 6, 9, 12)),  # ambata2 al colpo 2
    ]
    report = verifica_retroattiva(estrazioni, ruota=Ruota.BARI, colpi=2)
    assert report.totale_trigger == 1
    assert report.esiti[0].colpo_ambata1 == 1
    assert report.esiti[0].colpo_ambata2 == 2


def test_verifica_retroattiva_fuori_finestra() -> None:
    estrazioni = [
        crea(2, (10, 40, 77, 82, 63)),
        crea(20, (1, 4, 8, 11, 15)),
        crea(22, (2, 6, 9, 12, 16)),
    ]
    report = verifica_retroattiva(estrazioni, ruota=Ruota.BARI, colpi=2)
    assert report.totale_trigger == 1
    assert report.n_hit_ambata1 == 0
    assert report.n_hit_ambata2 == 0


def test_verifica_ignora_altre_ruote() -> None:
    estrazioni = [
        crea(2, (10, 40, 77, 82, 63)),
        Estrazione.crea(date(2026, 1, 3), Ruota.ROMA, (25, 1, 4, 8, 11)),
    ]
    report = verifica_retroattiva(estrazioni, ruota=Ruota.BARI, colpi=3)
    assert report.esiti[0].colpo_ambata1 is None


def test_previsione_attiva_dall_ultimo_trigger() -> None:
    estrazioni = [
        crea(2, (1, 4, 8, 11, 15)),
        crea(5, (10, 40, 77, 82, 63)),
    ]
    previsione = previsione_attiva(estrazioni, ruota=Ruota.BARI)
    assert previsione is not None
    assert previsione.ambate == (25, 70)
    assert previsione.abbinamenti == ((25, 10), (25, 40), (70, 55), (70, 85))


def test_previsione_nessun_trigger_storico() -> None:
    assert previsione_attiva([crea(2, (1, 5, 9, 13, 17))], ruota=Ruota.BARI) is None


def test_verifica_periodo_conta_uscita_oltre_il_limite() -> None:
    """Trigger a luglio con `al` a fine luglio: l'uscita di agosto conta comunque."""
    estrazioni = [
        crea_su(date(2026, 7, 30), (10, 40, 77, 82, 63)),  # trigger: ambate 25 e 70
        crea_su(date(2026, 8, 2), (25, 1, 4, 8, 11)),  # ambata1 al colpo 1
        crea_su(date(2026, 8, 4), (70, 2, 6, 9, 12)),  # ambata2 al colpo 2
    ]
    report = verifica_periodo(
        estrazioni,
        ruota=Ruota.BARI,
        colpi=9,
        dal=date(2026, 7, 1),
        al=date(2026, 7, 31),
    )
    assert report.totale_trigger == 1
    assert report.esiti[0].colpo_ambata1 == 1
    assert report.esiti[0].colpo_ambata2 == 2


def test_verifica_periodo_include_il_giorno_al() -> None:
    estrazioni = [
        crea_su(date(2026, 7, 31), (10, 40, 77, 82, 63)),
        crea_su(date(2026, 8, 2), (25, 1, 4, 8, 11)),
    ]
    report = verifica_periodo(
        estrazioni, ruota=Ruota.BARI, colpi=9, al=date(2026, 7, 31)
    )
    assert report.totale_trigger == 1
    assert report.esiti[0].colpo_ambata1 == 1


def test_verifica_periodo_esclude_trigger_prima_di_dal() -> None:
    estrazioni = [
        crea_su(date(2026, 6, 30), (10, 40, 77, 82, 63)),
        crea_su(date(2026, 7, 2), (25, 1, 4, 8, 11)),
    ]
    report = verifica_periodo(
        estrazioni, ruota=Ruota.BARI, colpi=9, dal=date(2026, 7, 1)
    )
    assert report.totale_trigger == 0


def test_verifica_periodo_senza_limiti_equivalente_a_retroattiva() -> None:
    estrazioni = [
        crea(2, (10, 40, 77, 82, 63)),
        crea(3, (25, 1, 4, 8, 11)),
        crea(5, (70, 2, 6, 9, 12)),
    ]
    periodo = verifica_periodo(estrazioni, ruota=Ruota.BARI, colpi=3)
    retroattiva = verifica_retroattiva(estrazioni, ruota=Ruota.BARI, colpi=3)
    assert periodo == retroattiva
