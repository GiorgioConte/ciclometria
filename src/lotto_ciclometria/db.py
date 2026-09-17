"""Persistenza PostgreSQL dell'archivio e della memoria."""
# psycopg exposes untyped rows for the default cursor.
# pyright: reportAny=false, reportExplicitAny=false

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING, Any

import psycopg

from lotto_ciclometria.memoria import (
    VoceMemoria,
)
from lotto_ciclometria.memoria import carica_memoria as carica_memoria_csv
from lotto_ciclometria.models import Estrazione, Ruota
from lotto_ciclometria.store import carica as carica_csv

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS estrazioni (
    data date NOT NULL,
    ruota varchar(12) NOT NULL,
    n1 smallint NOT NULL,
    n2 smallint NOT NULL,
    n3 smallint NOT NULL,
    n4 smallint NOT NULL,
    n5 smallint NOT NULL,
    PRIMARY KEY (data, ruota)
);
CREATE TABLE IF NOT EXISTS memoria (
    data_riferimento date NOT NULL,
    ruota varchar(12) NOT NULL,
    ambata1 smallint NOT NULL,
    ambata2 smallint NOT NULL,
    colpi integer NOT NULL,
    colpo_ambata1 integer,
    colpo_ambata2 integer,
    abbinamenti jsonb NOT NULL,
    PRIMARY KEY (data_riferimento, ruota)
);
"""


class DatabaseConfigurazioneError(RuntimeError):
    """Il database non è configurato nell'ambiente corrente."""


def connetti() -> psycopg.Connection[Any]:
    """Apre una connessione usando ``DATABASE_URL``."""
    url = os.environ.get("DATABASE_URL")
    if not url:
        messaggio = "DATABASE_URL non configurata"
        raise DatabaseConfigurazioneError(messaggio)
    return psycopg.connect(url)


def inizializza_schema() -> None:
    """Crea le tabelle applicative se non esistono."""
    with connetti() as conn, conn.cursor() as cur:
        cur.execute(SCHEMA)


def serializza_abbinamenti(abbinamenti: tuple[tuple[int, int], ...]) -> str:
    """Serializza gli abbinamenti nel formato JSON persistito in PostgreSQL."""
    return json.dumps(abbinamenti, separators=(",", ":"))


def deserializza_abbinamenti(
    valore: str | list[list[int]],
) -> tuple[tuple[int, int], ...]:
    """Ricostruisce gli abbinamenti dal valore JSON del database."""
    dati = json.loads(valore) if isinstance(valore, str) else valore
    return tuple((int(coppia[0]), int(coppia[1])) for coppia in dati)


def salva_estrazioni(estrazioni: Iterable[Estrazione]) -> int:
    """Inserisce estrazioni senza duplicare quelle già presenti."""
    righe = [
        (e.data, e.ruota.value, *e.numeri)
        for e in {e.chiave_ordinamento: e for e in estrazioni}.values()
    ]
    if not righe:
        return 0
    inizializza_schema()
    with connetti() as conn, conn.cursor() as cur:
        cur.executemany(
            """INSERT INTO estrazioni (data, ruota, n1, n2, n3, n4, n5)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (data, ruota) DO NOTHING""",
            righe,
        )
    return len(righe)


def carica_estrazioni() -> tuple[Estrazione, ...]:
    """Carica tutte le estrazioni ordinate dal database."""
    inizializza_schema()
    with connetti() as conn, conn.cursor() as cur:
        cur.execute(
            """SELECT data, ruota, n1, n2, n3, n4, n5 FROM estrazioni
               ORDER BY data, array_position(%s::text[], ruota)""",
            ([ruota.value for ruota in Ruota],),
        )
        return tuple(
            Estrazione.crea(riga[0], riga[1], riga[2:]) for riga in cur.fetchall()
        )


def importa_csv(percorso: Path) -> int:
    """Importa il CSV storico nel database in modo idempotente."""
    inizializza_schema()
    return salva_estrazioni(carica_csv(percorso))


def importa_memoria_csv(percorso: Path) -> int:
    """Importa il CSV della memoria nel database con upsert idempotente."""
    return salva_memoria(carica_memoria_csv(percorso))


def carica_memoria() -> tuple[VoceMemoria, ...]:
    """Carica la memoria ordinata dal database."""
    inizializza_schema()
    with connetti() as conn, conn.cursor() as cur:
        cur.execute(
            """SELECT data_riferimento, ruota, ambata1, ambata2, colpi,
                   colpo_ambata1, colpo_ambata2, abbinamenti FROM memoria
                   ORDER BY data_riferimento, ruota""",
        )
        return tuple(
            VoceMemoria(
                data_riferimento=riga[0],
                ruota=Ruota(riga[1]),
                ambate=(riga[2], riga[3]),
                colpi=riga[4],
                colpo_ambata1=riga[5],
                colpo_ambata2=riga[6],
                abbinamenti=deserializza_abbinamenti(riga[7]),
            )
            for riga in cur.fetchall()
        )


def salva_memoria(voci: Iterable[VoceMemoria]) -> int:
    """Salva la memoria con upsert sulla chiave data/ruota."""
    righe = [
        (
            voce.data_riferimento,
            voce.ruota.value,
            *voce.ambate,
            voce.colpi,
            voce.colpo_ambata1,
            voce.colpo_ambata2,
            serializza_abbinamenti(voce.abbinamenti),
        )
        for voce in {voce.chiave: voce for voce in voci}.values()
    ]
    if not righe:
        return 0
    inizializza_schema()
    with connetti() as conn, conn.cursor() as cur:
        cur.executemany(
            """INSERT INTO memoria
                   (data_riferimento, ruota, ambata1, ambata2, colpi,
                    colpo_ambata1, colpo_ambata2, abbinamenti)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                   ON CONFLICT (data_riferimento, ruota) DO UPDATE SET
                   ambata1 = EXCLUDED.ambata1, ambata2 = EXCLUDED.ambata2,
                   colpi = EXCLUDED.colpi, colpo_ambata1 = EXCLUDED.colpo_ambata1,
                   colpo_ambata2 = EXCLUDED.colpo_ambata2,
                   abbinamenti = EXCLUDED.abbinamenti""",
            righe,
        )
    return len(righe)
