"""Errori tipizzati del dominio."""

from __future__ import annotations


class LottoError(Exception):
    """Base di tutti gli errori del toolkit."""


class ParseError(LottoError):
    """Un sorgente (HTML o CSV) non rispetta il formato atteso."""

    sorgente: str
    dettaglio: str

    def __init__(self, sorgente: str, dettaglio: str) -> None:
        """Registra il sorgente incriminato e il dettaglio del difetto."""
        super().__init__(f"{sorgente}: {dettaglio}")
        self.sorgente = sorgente
        self.dettaglio = dettaglio


class DownloadError(LottoError):
    """Il recupero di una pagina dell'archivio è fallito."""

    risorsa: str
    motivo: str

    def __init__(self, risorsa: str, motivo: str) -> None:
        """Registra la risorsa non raggiungibile e il motivo del fallimento."""
        super().__init__(f"download di {risorsa} fallito: {motivo}")
        self.risorsa = risorsa
        self.motivo = motivo


class EstrazioneInvalidaError(LottoError):
    """I numeri forniti non formano un'estrazione valida."""

    motivo: str

    def __init__(self, motivo: str) -> None:
        """Registra il motivo per cui l'estrazione è invalida."""
        super().__init__(motivo)
        self.motivo = motivo
