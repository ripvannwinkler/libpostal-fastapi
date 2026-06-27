# libpostal-fastapi

Latest [libpostal](https://github.com/openvenues/libpostal) built from source, wrapped in a [FastAPI](https://github.com/tiangolo/fastapi) microservice.

## Build

```bash
docker build -t libpostal-fastapi .
```

The Dockerfile uses `python:3.12-alpine` as the base image and compiles libpostal from source during the build stage.

## Run

Start the server:

```bash
docker run --rm -p 8001:8001 libpostal-fastapi
```

The server starts on port `8001`. View interactive API docs at [`http://localhost:8001/docs`](http://localhost:8001/docs).

## Usage

### Parse an address

```bash
curl 'http://localhost:8001/parse?address=30+W+26th+St,+New+York,+NY'
# [["30","house_number"],["w 26th st","road"],["new york","city"],["ny","state"]]
```

With optional `language` and `country` parameters:

```bash
curl 'http://localhost:8001/parse?address=30+W+26th+St,+New+York,+NY&language=en&country=us'
# [["30","house_number"],["w 26th st","road"],["new york","city"],["ny","state"]]
```

### Expand an address

```bash
curl 'http://localhost:8001/expand?address=30+W+26th+St,+New+York,+NY'
# ["30 west 26th saint new york ny","30 west 26th street new york ny",...]
```

### Expand and parse

Expands an address into variants, then parses each variant:

```bash
curl 'http://localhost:8001/expandparse?address=30+W+26th+St,+New+York,+NY&language=en&country=us'
# [[["30","house_number"],["west 26th saint","road"],["new york","city"],["ny","state"]],...]
```

## Test

Run the integration test suite against a running container:

```bash
./test.sh
```

Or specify a custom base URL:

```bash
./test.sh http://my-host:8001
```

The test script validates all three endpoints with US, UK, and Canadian addresses.
