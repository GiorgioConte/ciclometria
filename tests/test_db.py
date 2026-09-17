"""Test delle parti PostgreSQL che non richiedono un server."""

from lotto_ciclometria.db import (
    SCHEMA,
    deserializza_abbinamenti,
    serializza_abbinamenti,
)


def test_roundtrip_abbinamenti() -> None:
    abbinamenti = ((25, 10), (70, 85))
    assert deserializza_abbinamenti(serializza_abbinamenti(abbinamenti)) == abbinamenti


def test_schema_contiene_tabelle_e_chiavi() -> None:
    assert "CREATE TABLE IF NOT EXISTS estrazioni" in SCHEMA
    assert "CREATE TABLE IF NOT EXISTS memoria" in SCHEMA
    assert "PRIMARY KEY (data, ruota)" in SCHEMA
    assert "PRIMARY KEY (data_riferimento, ruota)" in SCHEMA
