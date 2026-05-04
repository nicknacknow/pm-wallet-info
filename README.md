# pm-wallet-info

`pm-wallet-info` is the enrichment and query service for wallet-level Polymarket data.

This repository starts as a barebones scaffold. The first implementation pass should stay focused on service boundaries, ownership, and a minimal runtime shape that matches the related services in this project.

## Intended responsibilities

- Consume trade-derived wallet activity from the shared event stream
- Enrich wallet data from external sources
- Serve internal callers through a typed RPC interface
- Store only wallet/profile data owned by this service

## Notes

- Follow the same container and compose conventions used by the sibling services in this project.
- Keep the first version small and easy to reason about.
- Prefer clear ownership boundaries over premature consolidation.

## Future work

- Add observability: metrics, structured logging, and tracing
- Add the background cron refresh worker
- Revisit whether any additional enrichment tables or RPC methods are needed after the first implementation
