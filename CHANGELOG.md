# Changelog

Tutte le modifiche notevoli a questo progetto vengono documentate in questo
file. Il formato segue [Keep a Changelog](https://keepachangelog.com/it/1.1.0/)
e il versioning aderisce a [Semantic Versioning](https://semver.org/lang/it/).

## [Non rilasciato]

## [0.1.0] - 2026-08-23

### Aggiunto

- Download asincrono degli archivi annuali FrankNet (1871–oggi) in cache
  locale `data/raw/`, con limite di concorrenza, jitter di cortesia e salto
  degli anni già presenti.
- Parser degli archivi annuali HTML con conteggio delle righe scartate.
- Archivio CSV deduplicato e ordinato in `data/archivio.csv`.
- Matematica ciclometrica del cerchio dei 90: distanza, diametrale,
  fuori_90, somma caratteristica, coppie diametrali, triangoli equilateri
  (lato 30) e rettangoli inscritti.
- Analisi statistiche: frequenze dei numeri, ritardi attuali/massimi,
  distribuzione delle distanze e delle somme caratteristiche.
- Metodo della distanza 30 (Matteo Palumbo) con verifica retroattiva su
  tutta la serie storica e confronto esplicito con la probabilità del caso.
- CLI `lotto`: comandi `download`, `stats`, `cerchio`, `figure`,
  `distanza30`.
- Immagine Docker multi-stadio basata su uv con volume condiviso `./data`.
