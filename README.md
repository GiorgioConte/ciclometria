# lotto-ciclometria

Toolkit Python per scaricare l'archivio storico delle estrazioni del Lotto
pubblicato su [FrankNet](https://www.franknet.altervista.org/lotto/page.php)
e studiarlo con le tecniche di **ciclometria**: il cerchio dei 90 numeri, le
distanze cicliche, i diametrali e le figure inscritte.

> ⚠️ Avvertenza: la ciclometria è una pratica esoterica senza alcun valore
> predittivo dimostrato. Questo strumento ha finalità di analisi statistica
> e ricreativa. Il gioco può causare dipendenza patologica: è vietato ai
> minori di 18 anni. Gioca responsabilmente.

## Comandi disponibili

| Comando | Descrizione |
| --- | --- |
| `lotto download` | Scarica gli archivi annuali HTML in `data/raw/` e costruisce `data/archivio.csv`. |
| `lotto stats` | Frequenze dei numeri, ritardi, distribuzione delle distanze o delle somme caratteristiche. |
| `lotto cerchio` | Le ultime estrazioni di una ruota con il diametrale di ciascun numero. |
| `lotto figure` | Coppie diametrali, triangoli equilateri (lato 30) e rettangoli nelle ultime estrazioni. |
| `lotto distanza30` | Metodo Palumbo: trigger, verifica retroattiva e previsione attiva. |

Esempi:

```bash
lotto download                      # tutti gli anni disponibili
lotto download --da 2000            # dal 2000 a oggi
lotto download --solo-build         # ricostruisce il CSV dalla cache, senza rete
lotto stats --ruota BARI --limite 15
lotto stats --vista ritardi --ruota MILANO
lotto cerchio NAZIONALE
lotto figure --ruota TORINO --ultime 20
lotto distanza30 BARI --colpi 9
```

## Uso con Docker

```bash
docker compose build
docker compose run --rm lotto download --da 2020
docker compose run --rm lotto distanza30 BARI
```

La directory `./data` è montata come volume: cache HTML e archivio CSV
restano sul computer ospite.

## Deploy con PostgreSQL esistente

Il `docker-compose.yml` avvia solo i servizi `lotto` e `api`: PostgreSQL deve
essere già in esecuzione e raggiungibile sulla rete Docker indicata da
`POSTGRES_NETWORK`. Copiare `.env.example` in `.env`, impostare `DATABASE_URL`,
`POSTGRES_NETWORK` e `LOTTO_API_TOKEN`, quindi avviare:

```bash
docker network create ciclometria_default 2>/dev/null || true
docker compose up -d --build api
docker compose run --rm lotto download
```

Il container PostgreSQL esistente deve essere già collegato a
`POSTGRES_NETWORK`. Il servizio `lotto` viene collegato sia alla rete del
progetto sia a quella PostgreSQL.
L'endpoint `POST /daily-report` restituisce il JSON per n8n. Il workflow di
esempio è in `n8n/workflow-report-giornaliero.json`.

## Il metodo della distanza 30

Individuato un ambo a distanza 30 nella figura di un'estrazione, la prima
ambata è la metà della somma dei due numeri e la seconda è la sua
diametrale; gli abbinamenti nascono dalle ambate con l'ambo base e con i
suoi diametrali. Il comando `distanza30` applica il metodo a ogni trigger
storico e confronta la frequenza di uscita entro K colpi con la
probabilità del caso (`1 − (85/90)^K`), così ciascuno può giudicare da sé.

## Sviluppo

Progetto gestito con [uv](https://docs.astral.sh/uv/) su Python 3.13,
tipizzazione stretta con basedpyright (`typeCheckingMode = "all"`), lint
ruff (`select = ["ALL"]`) e test pytest:

```bash
uv sync                # installa dipendenze
uv run pytest          # suite dei test
uv run basedpyright    # controllo dei tipi
uv run ruff check .    # lint
```

## Licenza

Uso personale e didattico.
