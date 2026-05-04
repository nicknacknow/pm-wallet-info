# pm-wallet-info Technical Spec

This document is intentionally lightweight for the initial scaffold.

## Progress log

- Scaffolded the repository with `README.md`, `SPEC.md`, `app/`, and `tests/`
- Kept the service boundary intentionally broad so the first implementation can evolve the schema and RPC shape
- Deferred observability and the cron refresh worker to later iterations
- Added local env handling and repo hygiene files so the initial commit stays clean
- Started the runtime implementation: settings, DB schema, enrichment worker, and gRPC surface
- Confirmed the service should write to the shared `trade_store` database rather than a separate Postgres instance
- Adjusted the runtime to connect to the host-mapped shared Postgres instance used by pm-trades-db
- Verified the sample wallet's Polymarket profile endpoint returns 404, and the RPC surfaces that as `NOT_FOUND`
- Plan to split `app/` into clearer `pubsub/` and `rpc/` areas on the next refactor pass
- Completed the first structure pass: `app/api`, `app/pubsub`, and `app/rpc`

## Goal

Build a service that enriches wallet data from Polygonscan and Polymarket, stores the owned data in Postgres, and exposes it to internal consumers over gRPC.

## Scope for the first pass

- Define the service boundary clearly
- Keep trade ingest and enrichment separate from `pm-trades-db`
- Establish a minimal project structure that mirrors the other services in this project
- Leave room for future observability and a later refresh worker

## Early implementation notes

- The exact tables are not fixed yet and may evolve during implementation
- The worker and RPC server should live behind the same service boundary unless a concrete reason appears to split them
- Docker and compose should follow the patterns already used by the related services

## Future work

- Observability: metrics, structured logging, tracing, dashboards
- Background cron refresh for stale wallets
- Re-evaluate data model details after the first working version
- Add more granular submodules under `app/api`, `app/pubsub`, or `app/rpc` if the implementation grows further
