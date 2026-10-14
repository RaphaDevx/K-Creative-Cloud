# ADR 0002: Shared Rust command core

## Status
Accepted

## Context
GUI, shortcuts and LLM MCP must edit the same project with undo and persistence. Existing suite is Python/Electron and has substantial assets.

## Decision
Add a standalone Rust JSON CLI as state authority. Keep Python HTTP/media adapters and current desktop shell; add one integrated web workspace. Avoid an early rewrite of mature codecs and model runtimes.

## Consequences
Rust operations are independently testable. Python serializes CLI access. Browser UI has no separate project database. Existing applications remain available. This is an incremental editor implementation, not parity with commercial suites.

## Replacement
Keep action and project JSON contract stable when replacing CLI transport with a long-running Rust service.
