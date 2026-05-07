# pm-wallet-info

`pm-wallet-info` is a lightweight wallet query service for Polymarket data.

This repository starts as a barebones scaffold. The first implementation pass should stay focused on service boundaries, ownership, and a minimal runtime shape that matches the related services in this project.

## Current status

- Repository scaffold only
- No runtime code yet
- Local environment files are kept out of version control by default
- This simplified version exposes only gRPC methods backed directly by external APIs
- No Redis subscription or Postgres persistence is required
- The repo is split into `app/api`, `app/pubsub`, and `app/rpc`

## Intended responsibilities

- Serve internal callers through a typed RPC interface
- Fetch wallet/profile data directly from external sources per RPC request

## Structure

- `app/api` contains the outbound HTTP clients for Polygonscan and Polymarket
- `app/pubsub` contains the previous Redis consumer flow (not used in this simplified runtime)
- `app/rpc` contains the gRPC service implementation

## Notes

- Follow the same container and compose conventions used by the sibling services in this project.
- Keep the first version small and easy to reason about.
- Prefer clear ownership boundaries over premature consolidation.
- This version does not require Redis or Postgres.

## Future work

- Add observability: metrics, structured logging, and tracing
- Revisit whether a persisted enrichment/cache worker should be reintroduced
