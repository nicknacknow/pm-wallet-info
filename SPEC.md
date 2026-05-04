# pm-wallet-info Technical Spec

This document is intentionally lightweight for the initial scaffold.

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
