# syntax=docker/dockerfile:1.22.0
FROM python:3.13-slim AS base

RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libc6-dev && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /go/src/github.com/longhorn/longhorn-tests
COPY . .

FROM base AS validate
RUN ./scripts/validate && touch /validate.done

FROM scratch AS ci-artifacts
COPY --from=validate /validate.done /validate.done
