# pm-wallet-info

`pm-wallet-info` is the enrichment and query service for wallet-level Polymarket data.

This repository starts as a barebones scaffold. The first implementation pass should stay focused on service boundaries, ownership, and a minimal runtime shape that matches the related services in this project.

## Current status

- Repository scaffold only
- No runtime code yet
- Local environment files are kept out of version control by default
- This service is intended to share the same Postgres instance and logical database as pm-trades-db
- The wallet service currently points at the shared `trade_store` database on the project network
- The repo is now split into `app/api`, `app/pubsub`, and `app/rpc` for clearer ownership

## Intended responsibilities

- Consume trade-derived wallet activity from the shared event stream
- Enrich wallet data from external sources
- Serve internal callers through a typed RPC interface
- Store only wallet/profile data owned by this service

## Structure

- `app/api` contains the outbound HTTP clients for Polygonscan and Polymarket
- `app/pubsub` contains the Redis consumer and enrichment orchestration
- `app/rpc` contains the gRPC service implementation

## Notes

- Follow the same container and compose conventions used by the sibling services in this project.
- Keep the first version small and easy to reason about.
- Prefer clear ownership boundaries over premature consolidation.
- Run this service against the shared `trade_store` database on the `pm-project` network, not a separate database.
- The container connects to the shared Postgres instance via `host.docker.internal:5432`, which is the host-mapped `trade_store` database from pm-trades-db.
- The wallet service listens on the `trades.raw` Redis channel to match `pminspect`.

## Future work

- Add observability: metrics, structured logging, and tracing
- Add the background cron refresh worker
- Revisit whether any additional enrichment tables or RPC methods are needed after the first implementation
