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

### Format an address (structured output)

Returns a JSON object with `address1`, `address2`, `city`, `state`, `postal`, and `country` fields:

```bash
curl 'http://localhost:8001/format?address=201+n+state+st,+freeburg+il+62258'
# {"address1":"201 N STATE ST","address2":"","city":"FREEBURG","state":"IL","postal":"62258","country":"US"}
```

`country` is auto-detected as `"US"` when the postal code matches a US ZIP pattern (5 or 9 digits):

```bash
curl 'http://localhost:8001/format?address=201+n+state+st,+freeburg+il+62243-1234'
# {"address1":"201 N STATE ST","address2":"","city":"FREEBURG","state":"IL","postal":"62243-1234","country":"US"}
```

Auto-detected as `"CA"` when the postal code matches a Canadian format (A1A 1A1):

```bash
curl 'http://localhost:8001/format?address=123+ottawa+st,+toronto+on+m5h+2n2'
# {"address1":"123 OTTAWA ST","address2":"","city":"TORONTO","state":"ON","postal":"M5H 2N2","country":"CA"}
```

With optional `language` and `country` parameters for disambiguation:

```bash
curl 'http://localhost:8001/format?address=30+W+26th+St,+New+York,+NY&language=en&country=us'
# {"address1":"30 W 26TH ST","address2":"","city":"NEW YORK","state":"NY","postal":"","country":""}
```

Includes `address2` for units, suites, etc.:

```bash
curl 'http://localhost:8001/format?address=760+fountain+view+dr+apt+d+mascoutah+il+62258'
# {"address1":"760 FOUNTAIN VIEW DR","address2":"APT D","city":"MASCOUTAH","state":"IL","postal":"62258","country":"US"}
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
