# D-015: No Embeddings Until P9-Semantic Trigger

- **Date:** 2026-09-26
- **Status:** Accepted
- **Blocks:** —

## Context

~13 sample items; no retrieval problem today. Vector DB would be padding.

## Decision

No embeddings/vector DB in the locked spine. If a later **P9-semantic** trigger appears (real corpus size), use **local** embeddings first.

## Alternatives considered

Qdrant/Pinecone now; OpenAI embeddings by default.

## Consequences

Keeps B0–B7 thin; backlog only.
