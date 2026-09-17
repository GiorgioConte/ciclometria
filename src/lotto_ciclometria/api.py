"""API JSON per l'integrazione con n8n."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import FastAPI, Header, HTTPException

from lotto_ciclometria import db
from lotto_ciclometria.comandi_archivio import sincronizza_archivio
from lotto_ciclometria.metodi import (
    Previsione,
    previsione_attiva,
    tasso_casuale,
    verifica_retroattiva,
)
from lotto_ciclometria.models import ORDINE_RUOTE

app = FastAPI(title="Lotto Ciclometria API", version="0.1.0")
FUSO_RIFERIMENTO = ZoneInfo("Europe/Rome")


def _verifica_token(token: str | None) -> None:
    atteso = os.environ.get("API_TOKEN")
    if atteso and token != atteso:
        raise HTTPException(status_code=401, detail="Token non valido")


def _previsione_json(previsione: Previsione | None) -> dict[str, object] | None:
    if previsione is None:
        return None
    return {
        "data_riferimento": previsione.data_riferimento.isoformat(),
        "ruota": previsione.ruota.value,
        "ambate": list(previsione.ambate),
        "abbinamenti": [list(coppia) for coppia in previsione.abbinamenti],
    }


@app.get("/health")
def health() -> dict[str, str]:
    """Endpoint per healthcheck e diagnostica del container."""
    return {"status": "ok"}


@app.post("/daily-report")
def daily_report(
    x_api_token: Annotated[str | None, Header()] = None,
) -> dict[str, object]:
    """Aggiorna l'archivio e produce il payload da passare al nodo IA."""
    _verifica_token(x_api_token)
    directory = Path(os.environ.get("DATA_DIR", "data"))
    oggi = datetime.now(tz=FUSO_RIFERIMENTO).date()
    sincronizza_archivio(directory, da=oggi.year)
    estrazioni = db.carica_estrazioni()
    risultato: list[dict[str, object]] = []
    for ruota in ORDINE_RUOTE:
        report = verifica_retroattiva(estrazioni, ruota=ruota, colpi=9)
        risultato.append(
            {
                "ruota": ruota.value,
                "trigger": report.totale_trigger,
                "successi_ambata1": report.n_hit_ambata1,
                "successi_ambata2": report.n_hit_ambata2,
                "tasso_ambata1": (
                    report.n_hit_ambata1 / report.totale_trigger
                    if report.totale_trigger
                    else None
                ),
                "tasso_ambata2": (
                    report.n_hit_ambata2 / report.totale_trigger
                    if report.totale_trigger
                    else None
                ),
                "previsione_attiva": _previsione_json(
                    previsione_attiva(estrazioni, ruota=ruota)
                ),
            }
        )
    return {
        "data_elaborazione": oggi.isoformat(),
        "colpi": 9,
        "caso_atteso": tasso_casuale(9),
        "estrazioni": len(estrazioni),
        "ruote": risultato,
        "avvertenza": (
            "Analisi statistica e ricreativa: nessun valore predittivo "
            "dimostrato. Gioca responsabilmente."
        ),
    }
