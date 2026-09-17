"""Test della memoria delle previsioni e del suo allineamento."""

from datetime import date
from pathlib import Path

import pytest

from lotto_ciclometria.errors import ParseError
from lotto_ciclometria.memoria import (
    StatoVoce,
    VoceMemoria,
    allinea,
    carica_memoria,
    registra,
    salva_memoria,
)
from lotto_ciclometria.metodi import Previsione
from lotto_ciclometria.models import Estrazione, Ruota

PREVISIONE = Previsione(
    data_riferimento=date(2026, 7, 30),
    ruota=Ruota.BARI,
    ambate=(25, 70),
    abbinamenti=((25, 10), (25, 40), (70, 55), (70, 85)),
)

INTESTAZIONE = (
    "data,ruota,ambata1,ambata2,colpi,colpo_ambata1,colpo_ambata2,abbinamenti\n"
)


def serie_bari() -> list[Estrazione]:
    """Estrazioni successive alla previsione: 25 al colpo 1, 70 al colpo 3."""
    return [
        Estrazione.crea(date(2026, 8, 1), Ruota.BARI, (25, 1, 4, 8, 11)),
        Estrazione.crea(date(2026, 8, 4), Ruota.BARI, (2, 6, 9, 12, 15)),
        Estrazione.crea(date(2026, 8, 6), Ruota.BARI, (70, 3, 7, 10, 13)),
    ]


def test_registra_da_previsione() -> None:
    voce = registra(PREVISIONE, colpi=9)
    assert voce.data_riferimento == date(2026, 7, 30)
    assert voce.ruota == Ruota.BARI
    assert voce.ambate == (25, 70)
    assert voce.abbinamenti == ((25, 10), (25, 40), (70, 55), (70, 85))
    assert voce.colpi == 9
    assert voce.colpo_ambata1 is None
    assert voce.colpo_ambata2 is None


def test_roundtrip_salva_carica(tmp_path: Path) -> None:
    percorso = tmp_path / "memoria.csv"
    voce = registra(PREVISIONE, colpi=9)
    salva_memoria([voce], percorso)
    assert carica_memoria(percorso) == (voce,)


def test_carica_file_assente_restituisce_memoria_vuota(tmp_path: Path) -> None:
    assert carica_memoria(tmp_path / "memoria.csv") == ()


def test_carica_intestazione_inattesa_solleva_parse_error(tmp_path: Path) -> None:
    percorso = tmp_path / "memoria.csv"
    percorso.write_text("data,ruota\n2026-07-30,BARI\n", encoding="utf-8")
    with pytest.raises(ParseError):
        carica_memoria(percorso)


def test_carica_riga_incompleta_solleva_parse_error(tmp_path: Path) -> None:
    percorso = tmp_path / "memoria.csv"
    percorso.write_text(INTESTAZIONE + "2026-07-30,BARI,25,70\n", encoding="utf-8")
    with pytest.raises(ParseError):
        carica_memoria(percorso)


def test_carica_campi_non_numerici_solleva_parse_error(tmp_path: Path) -> None:
    percorso = tmp_path / "memoria.csv"
    percorso.write_text(
        INTESTAZIONE + "2026-07-30,BARI,venticinque,70,9,,,\n",
        encoding="utf-8",
    )
    with pytest.raises(ParseError):
        carica_memoria(percorso)


def test_carica_abbinamenti_malformati_solleva_parse_error(tmp_path: Path) -> None:
    percorso = tmp_path / "memoria.csv"
    percorso.write_text(
        INTESTAZIONE + "2026-07-30,BARI,25,70,9,,,25-10;x\n",
        encoding="utf-8",
    )
    with pytest.raises(ParseError):
        carica_memoria(percorso)


def test_salva_deduplica_sulla_stessa_chiave(tmp_path: Path) -> None:
    percorso = tmp_path / "memoria.csv"
    vecchia = registra(PREVISIONE, colpi=9)
    aggiornata = VoceMemoria(
        data_riferimento=vecchia.data_riferimento,
        ruota=vecchia.ruota,
        ambate=vecchia.ambate,
        abbinamenti=vecchia.abbinamenti,
        colpi=vecchia.colpi,
        colpo_ambata1=1,
        colpo_ambata2=None,
    )
    salva_memoria([vecchia, aggiornata], percorso)
    salvate = carica_memoria(percorso)
    assert len(salvate) == 1
    assert salvate[0].colpo_ambata1 == 1


def test_allinea_aggiorna_i_colpi_e_chiude_la_voce() -> None:
    voce = registra(PREVISIONE, colpi=9)
    esiti = allinea([voce], serie_bari())
    assert len(esiti) == 1
    assert esiti[0].voce.colpo_ambata1 == 1
    assert esiti[0].voce.colpo_ambata2 == 3
    assert esiti[0].stato is StatoVoce.CHIUSA


def test_allinea_scaduta_senza_uscite_entro_la_finestra() -> None:
    voce = registra(PREVISIONE, colpi=2)
    esiti = allinea([voce], serie_bari())
    assert esiti[0].stato is StatoVoce.SCADUTA
    assert esiti[0].voce.colpo_ambata2 is None


def test_allinea_aperta_con_finestra_non_ancora_esaurita() -> None:
    voce = registra(PREVISIONE, colpi=9)
    esiti = allinea([voce], serie_bari()[:1])
    assert esiti[0].stato is StatoVoce.APERTA
    assert esiti[0].voce.colpo_ambata1 == 1


def test_allinea_aperta_senza_estrazioni_successive() -> None:
    voce = registra(PREVISIONE, colpi=9)
    precedenti = [
        Estrazione.crea(date(2026, 7, 29), Ruota.BARI, (1, 2, 3, 4, 5)),
    ]
    esiti = allinea([voce], precedenti)
    assert esiti[0].stato is StatoVoce.APERTA
    assert esiti[0].voce.colpo_ambata1 is None


def test_allinea_ignora_le_altre_ruote() -> None:
    voce = registra(PREVISIONE, colpi=2)
    altre = [
        Estrazione.crea(date(2026, 8, 1), Ruota.ROMA, (25, 70, 1, 2, 3)),
        Estrazione.crea(date(2026, 8, 4), Ruota.ROMA, (4, 5, 6, 7, 8)),
    ]
    esiti = allinea([voce], altre)
    # Le estrazioni di un'altra ruota non risolvono né esauriscono la voce.
    assert esiti[0].stato is StatoVoce.APERTA
    assert esiti[0].voce.colpo_ambata1 is None


def test_allinea_idempotente() -> None:
    voce = registra(PREVISIONE, colpi=9)
    prima = allinea([voce], serie_bari())
    seconda = allinea([e.voce for e in prima], serie_bari())
    assert seconda == prima
