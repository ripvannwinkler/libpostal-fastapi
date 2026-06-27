# syntax=docker/dockerfile:1

FROM python:3.12-alpine AS builder

RUN apk add --no-cache \
    build-base \
    linux-headers \
    autoconf \
    automake \
    libtool \
    curl \
    git

ARG TARGETARCH

# Build libpostal from source
RUN git clone --depth=1 https://github.com/openvenues/libpostal /code/libpostal && \
    cd /code/libpostal && \
    ./bootstrap.sh && \
    ([ "$TARGETARCH" = "arm64" ] && ./configure --datadir=/usr/share/libpostal --disable-sse2 || ./configure --datadir=/usr/share/libpostal) && \
    make -j4 && \
    make install && \
    ldconfig

# Create venv and install Python deps
RUN python3.12 -m venv /opt/venv && \
    . /opt/venv/bin/activate && \
    pip install --upgrade pip setuptools wheel

COPY requirements.txt .
RUN PYPPOSTAL_LIBS=/usr/local/lib \
    LD_LIBRARY_PATH=/usr/local/lib \
    PKG_CONFIG_PATH=/usr/local/lib/pkgconfig \
    /opt/venv/bin/pip install -r requirements.txt

# Final stage
FROM python:3.12-alpine

ENV VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    LD_LIBRARY_PATH=/usr/local/lib

RUN apk add --no-cache openblas

COPY --from=builder /usr/share/libpostal /usr/share/libpostal
COPY --from=builder /usr/local/lib/libpostal.so.1* /usr/local/lib/
COPY --from=builder /usr/local/include/libpostal /usr/local/include/libpostal
COPY --from=builder /opt/venv /opt/venv

RUN python -c "from postal.parser import parse_address; address = '123 Beech Lake Ct. Roswell, GA 30076'; print(parse_address(address))"

WORKDIR /code
COPY server.py .
EXPOSE 8001/tcp
CMD ["uvicorn", "server:app", "--port", "8001", "--host", "0.0.0.0"]
