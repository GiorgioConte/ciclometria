"""Download asincrono degli archivi annuali da FrankNet.

Il sito pubblica un indice (``page.php``) con un collegamento per anno
nella forma ``YYYY.HTM``. I file scaricati vengono conservati in cache
in ``data/raw/`` così l'archivio CSV può essere ricostruito offline.
"""

from __future__ import annotations

import logging
import os
import random
import re
import socket
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Final, Literal
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

import anyio
import httpx2

from lotto_ciclometria.errors import DownloadError

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

logger = logging.getLogger(__name__)

BASE_URL_DEFAULT: Final = "https://www.franknet.altervista.org/lotto/"
ENV_BASE_URL: Final = "LOTTO_BASE_URL"
PAGINA_INDICE: Final = "page.php"

StatoDownload = Literal["scaricato", "invariato", "omesso"]

_RE_LINK_ANNO: Final = re.compile(r'href="(\d{4})\.HTM"', re.IGNORECASE)

_LIMITE_CONCORRENZA: Final = 4
_PAUSA_MINIMA_S: Final = 0.15
_PAUSA_MASSIMA_S: Final = 0.45
_FUSO_RIFERIMENTO: Final = ZoneInfo("Europe/Rome")


def _anno_corrente() -> int:
    """Anno in corso nel fuso italiano, quello delle estrazioni."""
    return datetime.now(tz=_FUSO_RIFERIMENTO).year


@dataclass(frozen=True, slots=True)
class EsitoAnno:
    """Esito del trattamento di un singolo archivio annuale."""

    anno: int
    stato: StatoDownload


def base_url() -> str:
    """URL di base configurabile per test o mirror."""
    return os.environ.get(ENV_BASE_URL, BASE_URL_DEFAULT)


def crea_client() -> httpx2.AsyncClient:
    """Client httpx2 con i default di produzione, tarato sulla gentilezza."""
    limiti = httpx2.Limits(
        max_connections=_LIMITE_CONCORRENZA,
        max_keepalive_connections=4,
        keepalive_expiry=30.0,
    )
    timeout = httpx2.Timeout(connect=5.0, read=30.0, write=10.0, pool=10.0)
    trasporto = httpx2.AsyncHTTPTransport(
        http2=True,
        retries=3,
        limits=limiti,
        socket_options=[(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)],
    )
    return httpx2.AsyncClient(
        transport=trasporto,
        timeout=timeout,
        follow_redirects=True,
        headers={
            "User-Agent": "lotto-ciclometria/0.1 (studio personale di ciclometria)"
        },
    )


async def scarica_indice(client: httpx2.AsyncClient) -> tuple[int, ...]:
    """Elenca gli anni disponibili nella pagina indice."""
    try:
        risposta = await client.get(urljoin(base_url(), PAGINA_INDICE))
        risposta.raise_for_status()
    except httpx2.HTTPError as errore:
        risorsa = urljoin(base_url(), PAGINA_INDICE)
        raise DownloadError(risorsa, str(errore)) from errore
    trovati: list[str] = _RE_LINK_ANNO.findall(risposta.content.decode("latin-1"))
    anni = sorted({int(trovata) for trovata in trovati})
    if not anni:
        risorsa = urljoin(base_url(), PAGINA_INDICE)
        raise DownloadError(risorsa, "nessun link annuale nell'indice")
    return tuple(anni)


async def sincronizza(
    directory_raw: Path,
    *,
    anni: Sequence[int] | None = None,
    forza: bool = False,
) -> tuple[EsitoAnno, ...]:
    """Scarica gli anni richiesti (default: tutti dall'indice) in cache locale."""
    await anyio.Path(directory_raw).mkdir(parents=True, exist_ok=True)
    async with crea_client() as client:
        richiesti = (
            list(anni) if anni is not None else list(await scarica_indice(client))
        )
        limiter = anyio.CapacityLimiter(_LIMITE_CONCORRENZA)
        esiti: list[EsitoAnno] = []
        async with anyio.create_task_group() as gruppo:

            async def uno(anno: int) -> None:
                esiti.append(
                    await _scarica_anno(client, limiter, directory_raw, anno, forza)
                )

            for anno in richiesti:
                gruppo.start_soon(uno, anno)
        return tuple(esiti)


async def _scarica_anno(
    client: httpx2.AsyncClient,
    limiter: anyio.CapacityLimiter,
    directory_raw: Path,
    anno: int,
    forza: bool,
) -> EsitoAnno:
    destinazione = anyio.Path(directory_raw / f"{anno}.HTM")
    if await destinazione.exists() and not forza and anno < _anno_corrente():
        return EsitoAnno(anno, "omesso")
    await anyio.sleep(random.uniform(_PAUSA_MINIMA_S, _PAUSA_MASSIMA_S))  # noqa: S311 — jitter di cortesia, non crittografia
    async with limiter:
        url = urljoin(base_url(), f"{anno}.HTM")
        try:
            risposta = await client.get(url)
            risposta.raise_for_status()
        except httpx2.HTTPError as errore:
            raise DownloadError(url, str(errore)) from errore
    contenuto = risposta.content.decode("latin-1")
    if (
        await destinazione.exists()
        and await destinazione.read_text(
            encoding="utf-8",
        )
        == contenuto
    ):
        return EsitoAnno(anno, "invariato")
    await destinazione.write_text(contenuto, encoding="utf-8")
    logger.info("scaricato %s (%d caratteri)", destinazione.name, len(contenuto))
    return EsitoAnno(anno, "scaricato")
